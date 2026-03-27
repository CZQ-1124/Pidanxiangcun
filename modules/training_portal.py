import json
import uuid
import streamlit as st

from modules.common import require_login, hero_banner, render_training_feedback, render_assessment
from services.ai_router import (
    grade_training,
    generate_case_narrative,
    simulate_patient_opening,
    simulate_patient_reply,
)
from services.db_service import save_training_attempt
from services.training_case_selector import pick_case, pick_dual_cases
from services.utils import resolve_image_path


def _show_case_image(case: dict):
    img_path = resolve_image_path(case.get('relative_path'), case.get('file_name'))
    if img_path and img_path.exists():
        st.image(str(img_path), caption=case.get('file_name'))
    else:
        st.warning(f"未找到真实图片：{case.get('file_name')}。请把真实图片放到指定文件夹。")


def _case_identity(case: dict) -> str:
    return str(
        case.get('case_id')
        or case.get('file_name')
        or case.get('relative_path')
        or uuid.uuid4().hex
    )


def _extract_disease_name(case: dict) -> str:
    """
    尽量从病例字典中提取病种名称。
    不同数据表字段命名可能不同，所以这里做兼容兜底。
    """
    for key in [
        'disease_name',
        'disease',
        'diagnosis',
        'label',
        'gt_label',
        'target_label',
        'category',
        'disease_label',
    ]:
        value = case.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ''


def _pick_same_disease_cases(disease_filter: str = '全部', max_trials: int = 40):
    """
    为“同病共同特点”题型抽取两张图：
    - 若用户限定了病种，则反复抽取该病种下的两张不同图片；
    - 若未限定病种，则尝试在全库中找到同一病种的两张不同图片。
    """
    disease_filter = disease_filter or '全部'

    # 场景1：用户手动限定了病种
    if disease_filter != '全部':
        picked = {}
        for _ in range(max_trials):
            case = pick_case(disease_filter)
            if not case:
                continue
            case_id = _case_identity(case)
            picked[case_id] = case
            if len(picked) >= 2:
                return list(picked.values())[:2]
        return None

    # 场景2：未限定病种，需要自动找同一病种的两张图
    buckets = {}
    for _ in range(max_trials):
        case = pick_case('全部')
        if not case:
            continue

        disease_name = _extract_disease_name(case)
        if not disease_name:
            continue

        case_id = _case_identity(case)
        if disease_name not in buckets:
            buckets[disease_name] = {}
        buckets[disease_name][case_id] = case

        if len(buckets[disease_name]) >= 2:
            return list(buckets[disease_name].values())[:2]

    return None


def _render_image_hint(qtype: str):
    if qtype == '看图写病':
        st.info('请根据单张图片写出最可能的疾病名称，并简要说明判断依据。')
    elif qtype == '同病共同特点':
        st.info('系统将调用同一病种的两张图片。请只概括两图共同的皮损形态学特点，不需要回答病名。')
    elif qtype == '双图鉴别':
        st.info('系统将调用两张图片。请比较两图差异，并写出你的鉴别要点。')


def render(user: dict):
    require_login()
    hero_banner('培训学习区', '保留识图闯关、病例推演与模拟门诊三种训练模式。')
    tabs = st.tabs(['识图闯关', '病例推演', '模拟门诊'])

    with tabs[0]:
        qtype = st.selectbox('题型', ['看图写病', '同病共同特点', '双图鉴别'], key='train_qtype')
        disease = st.text_input('限定病种（留空默认全部）', key='train_disease')

        _render_image_hint(qtype)

        if st.button('生成题目', key='train_generate_q'):
            st.session_state['image_qtype'] = qtype
            st.session_state['image_case'] = None

            if qtype == '双图鉴别':
                st.session_state['image_case'] = pick_dual_cases(disease or '全部')
            elif qtype == '同病共同特点':
                st.session_state['image_case'] = _pick_same_disease_cases(disease or '全部')
            else:
                st.session_state['image_case'] = pick_case(disease or '全部')

        case_obj = st.session_state.get('image_case')
        current_qtype = st.session_state.get('image_qtype', qtype)

        if case_obj:
            if current_qtype == '同病共同特点':
                if isinstance(case_obj, list) and len(case_obj) >= 2:
                    st.markdown('#### 训练任务')
                    st.info('下面两张图来自同一种皮肤病。请仅描述两图共同的皮损特点，不要写病名。')

                    for i, c in enumerate(case_obj[:2], 1):
                        st.markdown(f'#### 图片 {i}')
                        _show_case_image(c)

                    question_payload = {
                        'qtype': current_qtype,
                        'cases': case_obj[:2],
                        'focus': '共同皮损特点',
                        'do_not_answer_disease_name': True,
                    }
                    gold = case_obj[0]
                    answer = st.text_area('请写出两张图共同的皮损特点', key='train_answer_image')

                else:
                    st.warning('当前病例库暂未找到同一病种的两张可用图片。可尝试手动输入某个病种后再生成。')
                    answer = None
                    question_payload = None
                    gold = None

            elif isinstance(case_obj, list):
                for i, c in enumerate(case_obj, 1):
                    st.markdown(f'#### 图片 {i}')
                    _show_case_image(c)

                st.markdown('#### 训练任务')
                st.info('请比较两张图的差异，并写出你的鉴别要点。')

                question_payload = {'qtype': current_qtype, 'cases': case_obj}
                gold = case_obj[0]
                answer = st.text_area('请写出两图的差异及鉴别要点', key='train_answer_image')

            else:
                _show_case_image(case_obj)
                question_payload = {'qtype': current_qtype, 'case': case_obj}
                gold = case_obj
                answer = st.text_area('你的答案', key='train_answer_image')

            if question_payload and answer is not None:
                if st.button('提交作答并获取 AI 反馈', key='train_submit_image', type='primary'):
                    with st.spinner('正在评分...'):
                        feedback = grade_training(question_payload, answer, gold)

                    save_training_attempt({
                        'attempt_id': f'TRN-{uuid.uuid4().hex[:8].upper()}',
                        'training_type': '识图闯关',
                        'learner_name': user['name'],
                        'learner_role': user['role'],
                        'question_payload': json.dumps(question_payload, ensure_ascii=False),
                        'user_answer': answer,
                        'ai_feedback': json.dumps(feedback, ensure_ascii=False),
                        'score': float(feedback.get('score', 0) or 0),
                    })

                    render_training_feedback(feedback)

    with tabs[1]:
        disease2 = st.text_input('限定病种（留空默认全部）', key='case_train_disease')
        if st.button('生成教学病例', key='case_train_generate'):
            case = pick_case(disease2 or '全部')
            st.session_state['case_train_case'] = case
            if case:
                st.session_state['case_train_narrative'] = generate_case_narrative(case)

        case = st.session_state.get('case_train_case')
        narrative = st.session_state.get('case_train_narrative')

        if case:
            st.markdown('#### AI 自动生成病例')
            render_assessment(narrative, '教学病例内容')
            answer = st.text_area('你的结构化判断', key='case_train_answer')

            if st.button('提交病例分析', key='case_train_submit', type='primary'):
                payload = {'qtype': '病例分析', 'narrative': narrative}
                with st.spinner('正在评分...'):
                    feedback = grade_training(payload, answer, case)

                save_training_attempt({
                    'attempt_id': f'TRN-{uuid.uuid4().hex[:8].upper()}',
                    'training_type': '病例推演',
                    'learner_name': user['name'],
                    'learner_role': user['role'],
                    'question_payload': json.dumps(payload, ensure_ascii=False),
                    'user_answer': answer,
                    'ai_feedback': json.dumps(feedback, ensure_ascii=False),
                    'score': float(feedback.get('score', 0) or 0),
                })

                render_training_feedback(feedback)

    with tabs[2]:
        if st.button('生成模拟门诊场景', key='sim_generate'):
            case = pick_case()
            st.session_state['sim_case'] = case
            if case:
                st.session_state['sim_opening'] = simulate_patient_opening(case)
                st.session_state['sim_dialogue'] = []

        case = st.session_state.get('sim_case')
        opening = st.session_state.get('sim_opening')

        if case:
            _show_case_image(case)
            st.markdown('#### 患者开场')
            st.info((opening or {}).get('opening_statement'))

            q = st.text_input('你要问患者什么？', key='sim_question')

            if st.button('记录这一轮问诊', key='sim_add_turn'):
                with st.spinner('患者正在回答...'):
                    reply = simulate_patient_reply(case, st.session_state.get('sim_dialogue', []), q)
                patient_reply = reply.get('patient_reply') or '本轮未生成回复。'
                st.session_state['sim_dialogue'].append({'doctor': q, 'patient': patient_reply})

            for turn in st.session_state.get('sim_dialogue', []):
                st.markdown(f"**村医：** {turn['doctor']}")
                st.markdown(f"**患者：** {turn['patient']}")

            final_answer = st.text_area(
                '最后请写你的诊断倾向、危险信号、处理建议、宣教与转诊意见',
                key='sim_final_answer'
            )

            if st.button('结束模拟并评分', key='sim_submit', type='primary'):
                payload = {
                    'qtype': '模拟门诊',
                    'opening': opening,
                    'dialogue': st.session_state.get('sim_dialogue', []),
                }

                with st.spinner('正在评分...'):
                    feedback = grade_training(payload, final_answer, case)

                save_training_attempt({
                    'attempt_id': f'TRN-{uuid.uuid4().hex[:8].upper()}',
                    'training_type': '模拟门诊',
                    'learner_name': user['name'],
                    'learner_role': user['role'],
                    'question_payload': json.dumps(payload, ensure_ascii=False),
                    'user_answer': final_answer,
                    'ai_feedback': json.dumps(feedback, ensure_ascii=False),
                    'score': float(feedback.get('score', 0) or 0),
                })

                render_training_feedback(feedback)
