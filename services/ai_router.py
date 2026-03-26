import base64
import json
import re
from pathlib import Path
from typing import Any, Dict

from openai import OpenAI

from services.runtime_config import config_status, get_runtime_config


JSON_RE = re.compile(r"\{.*\}", re.S)


def _client() -> OpenAI:
    cfg = get_runtime_config()
    timeout = 25
    try:
        timeout = int(float(cfg.get('AI_TIMEOUT_SEC', 25)))
    except Exception:
        pass
    return OpenAI(api_key=cfg['AI_API_KEY'], base_url=cfg['AI_BASE_URL'], timeout=timeout)


def _thinking_kwargs() -> Dict[str, Any]:
    mode = get_runtime_config().get('THINKING_MODE', 'omit')
    if mode in {'disabled', 'auto', 'enabled'}:
        return {'thinking': {'type': mode}}
    return {}


def _safe_json(text: str, fallback: dict) -> dict:
    if not text:
        return dict(fallback)
    raw = text.strip()
    try:
        return json.loads(raw)
    except Exception:
        m = JSON_RE.search(raw)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    out = dict(fallback)
    out['_raw'] = raw[:4000]
    return out


def _image_data_url(image_path: str) -> str:
    image_bytes = Path(image_path).read_bytes()
    suffix = Path(image_path).suffix.lower().replace('.', '') or 'jpeg'
    if suffix == 'jpg':
        suffix = 'jpeg'
    b64 = base64.b64encode(image_bytes).decode('utf-8')
    return f'data:image/{suffix};base64,{b64}'


def call_text_json(system_prompt: str, user_prompt: str, fallback: dict) -> dict:
    status = config_status()
    if not status['text_ready']:
        out = dict(fallback)
        out['_status'] = 'not_configured'
        out['_error'] = '未配置文本模型或 API key。请先在“系统设置”中保存 AiHubMix 配置。'
        return out

    client = _client()
    cfg = get_runtime_config()
    request_variants = [
        {
            'model': cfg['TEXT_MODEL'],
            'messages': [
                {'role': 'system', 'content': system_prompt + ' 只输出合法 JSON，不要加解释。'},
                {'role': 'user', 'content': user_prompt},
            ],
            'temperature': 0.2,
            **_thinking_kwargs(),
        },
        {
            'model': cfg['TEXT_MODEL'],
            'messages': [
                {'role': 'system', 'content': system_prompt + ' 只输出合法 JSON，不要加解释。'},
                {'role': 'user', 'content': user_prompt},
            ],
            'temperature': 0.2,
        },
    ]
    last_error = None
    for kwargs in request_variants:
        try:
            resp = client.chat.completions.create(**kwargs)
            text = resp.choices[0].message.content or ''
            result = _safe_json(text, fallback)
            result['_status'] = 'ok'
            return result
        except Exception as e:
            last_error = str(e)
            continue
    out = dict(fallback)
    out['_status'] = 'error'
    out['_error'] = last_error or '未知错误'
    return out


def analyze_skin_image(image_path: str, context: dict) -> dict:
    fallback = {
        'visual_summary': '',
        'candidates': [],
        'danger_signs': [],
        'confidence': 'low',
    }
    status = config_status()
    if not status['vision_ready']:
        fallback['_status'] = 'not_configured'
        fallback['_error'] = '未配置视觉模型或 API key。'
        return fallback

    prompt = f'''
你是皮肤图像辅助分析器。只能做结构化辅助，不做最终确诊。请只输出 JSON：
{{
  "visual_summary": "一句话图像摘要",
  "candidates": ["候选疾病1","候选疾病2","候选疾病3"],
  "danger_signs": ["危险信号1","危险信号2"],
  "confidence": "high|medium|low"
}}

病史：
部位：{context.get('body_part')}
病程：{context.get('duration')}
瘙痒：{context.get('itch')}
疼痛：{context.get('pain')}
出血/破溃：{context.get('bleeding')}
近期增大：{context.get('growth')}
备注：{context.get('history')}
'''
    client = _client()
    cfg = get_runtime_config()
    variants = [
        {
            'model': cfg['VISION_MODEL'],
            'messages': [
                {'role': 'system', 'content': '只输出 JSON，不写额外文字。'},
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': prompt},
                        {'type': 'image_url', 'image_url': {'url': _image_data_url(image_path)}},
                    ],
                },
            ],
            'temperature': 0.1,
        }
    ]
    last_error = None
    for kwargs in variants:
        try:
            resp = client.chat.completions.create(**kwargs)
            text = resp.choices[0].message.content or ''
            out = _safe_json(text, fallback)
            out['_status'] = 'ok'
            return out
        except Exception as e:
            last_error = str(e)
    out = dict(fallback)
    out['_status'] = 'error'
    out['_error'] = last_error or '未知视觉模型错误'
    return out


def structured_assessment(case_data: dict) -> dict:
    fallback = {
        'differentials': [],
        'follow_questions': [],
        'action_points': [],
        'referral_threshold': '需人工判断',
        'patient_friendly_summary': '',
    }
    system = '你是皮肤科村医辅助决策助手，只给结构化辅助建议，不做确定诊断。'
    user = f'''
请根据下面病例输出 JSON：
{{
 "differentials": ["鉴别1","鉴别2","鉴别3"],
 "follow_questions": ["需追问1","需追问2","需追问3"],
 "action_points": ["建议1","建议2","建议3"],
 "referral_threshold": "一句话说明何时需要转诊",
 "patient_friendly_summary": "给患者/家属看的通俗摘要"
}}
病例：{json.dumps(case_data, ensure_ascii=False)}
'''
    return call_text_json(system, user, fallback)


def mdt_consult(case_data: dict) -> dict:
    fallback = {
        'derm_director': '',
        'morphology_expert': '',
        'pathology_view': '',
        'integrated_plan': '',
    }
    system = '你是皮肤科多学科会诊协调助手。以三位专家视角输出结构化 JSON。'
    user = f'''
请对病例生成三种视角和综合意见，输出 JSON：
{{
 "derm_director": "皮肤科主任视角",
 "morphology_expert": "皮损形态学专家视角",
 "pathology_view": "病理科主任视角",
 "integrated_plan": "综合会诊结论"
}}
病例：{json.dumps(case_data, ensure_ascii=False)}
'''
    return call_text_json(system, user, fallback)


def generate_case_narrative(case_data: dict) -> dict:
    fallback = {
        'chief_complaint': '',
        'history_of_present_illness': '',
        'key_points': [],
        'case_summary': '',
    }
    system = '你是皮肤科教学病例撰写助手。'
    user = f'''
请根据病例生成教学案例文本，输出 JSON：
{{
 "chief_complaint": "主诉",
 "history_of_present_illness": "现病史",
 "key_points": ["关键点1","关键点2","关键点3"],
 "case_summary": "案例简介"
}}
病例：{json.dumps(case_data, ensure_ascii=False)}
'''
    return call_text_json(system, user, fallback)


def grade_training(question_payload: dict, user_answer: str, gold_case: dict) -> dict:
    fallback = {
        'score': 0,
        'strengths': [],
        'missed_points': [],
        'feedback': '',
    }
    system = '你是皮肤科村医培训评分器。评分必须基于病例金标准，输出具体、可执行反馈。'
    user = f'''
请根据题目、作答、金标准评分，输出 JSON：
{{
 "score": 0,
 "strengths": ["做对点1","做对点2"],
 "missed_points": ["遗漏点1","遗漏点2"],
 "feedback": "总体反馈"
}}
题目：{json.dumps(question_payload, ensure_ascii=False)}
作答：{user_answer}
金标准：{json.dumps(gold_case, ensure_ascii=False)}
'''
    return call_text_json(system, user, fallback)


def simulate_patient_opening(seed_case: dict) -> dict:
    fallback = {
        'opening_statement': f"医生，我这处{seed_case.get('body_site', '皮疹')}最近不太对劲。",
        'hidden_facts': ['病程信息待追问', '症状变化待追问', '既往处理待追问'],
    }
    system = '你是皮肤科模拟门诊中的患者角色。'
    user = f'''
基于病例生成模拟门诊开场白和隐藏信息，输出 JSON：
{{
 "opening_statement": "患者第一句主诉",
 "hidden_facts": ["需要医生追问后才能得到的信息1","信息2","信息3"]
}}
病例：{json.dumps(seed_case, ensure_ascii=False)}
'''
    return call_text_json(system, user, fallback)


def simulate_patient_reply(seed_case: dict, dialogue: list[dict], doctor_question: str) -> dict:
    fallback = {
        'patient_reply': '这个问题本轮未能由 AI 生成回复，请继续记录问诊。',
    }
    system = '你在扮演皮肤科门诊患者。回答要符合病例设定，不要泄露未被问到的全部信息。'
    user = f'''
请根据病例与既往对话，只输出 JSON：
{{"patient_reply": "患者本轮回答"}}
病例：{json.dumps(seed_case, ensure_ascii=False)}
既往对话：{json.dumps(dialogue, ensure_ascii=False)}
本轮医生提问：{doctor_question}
'''
    return call_text_json(system, user, fallback)


def transcribe_audio(audio_path: str) -> dict:
    status = config_status()
    if not status['audio_ready']:
        return {
            'status': 'asr_not_configured',
            'transcript_text': '',
            'summary_text': '未配置音频转写模型。',
            'structured': {},
        }
    client = _client()
    cfg = get_runtime_config()
    try:
        with open(audio_path, 'rb') as f:
            resp = client.audio.transcriptions.create(model=cfg['AUDIO_MODEL'], file=f)
        transcript = getattr(resp, 'text', '') or ''
        return {
            'status': 'transcribed',
            'transcript_text': transcript,
            'summary_text': '',
            'structured': {},
        }
    except Exception as e:
        return {
            'status': 'asr_error',
            'transcript_text': '',
            'summary_text': str(e),
            'structured': {},
        }


def summarize_clinic_audio(transcript_text: str) -> dict:
    fallback = {
        'chief_complaint': '',
        'course': '',
        'body_part': '',
        'symptoms': '',
        'prior_treatment': '',
        'danger_signs': '',
        'doctor_advice': '',
        'referral_advice': '',
        'followup_plan': '',
        'patient_summary': '',
    }
    if not transcript_text.strip():
        return dict(fallback)
    system = '你是门诊录音整理助手。把转写内容整理为门诊纪要。'
    user = f'''
请根据转写内容提取结构化门诊纪要，输出 JSON：
{{
 "chief_complaint": "主诉",
 "course": "病程",
 "body_part": "部位",
 "symptoms": "症状",
 "prior_treatment": "既往处理",
 "danger_signs": "危险信号",
 "doctor_advice": "医生建议",
 "referral_advice": "转诊建议",
 "followup_plan": "随访时间点",
 "patient_summary": "门诊摘要"
}}
转写内容：{transcript_text}
'''
    return call_text_json(system, user, fallback)
