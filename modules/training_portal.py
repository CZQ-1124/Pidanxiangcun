import json
import uuid
import streamlit as st

from modules.common import require_login, hero_banner, render_training_feedback, render_assessment
from services.ai_router import grade_training, generate_case_narrative, simulate_patient_opening, simulate_patient_reply
from services.db_service import save_training_attempt
from services.training_case_selector import pick_case, pick_dual_cases
from services.utils import resolve_image_path


def _show_case_image(case: dict):
    img_path = resolve_image_path(case.get('relative_path'), case.get('file_name'))
    if img_path and img_path.exists():
        st.image(str(img_path), caption=case.get('file_name'))
    else:
        st.warning(f"未找到真实图片：{case.get('file_name')}。请把真实图片放到指定文件夹。")


def render(user: dict):
    require_login()
    hero_banner('培训学习区', '保留识图闯关、病例推演与模拟门诊三种训练模式。')
    tabs = st.tabs(['识图闯关', '病例推演', '模拟门诊'])

    with tabs[0]:
        qtype = st.selectbox('题型', ['看图写病', '同病共同特点', '双图鉴别'], key='train_qtype')
        disease = st.text_input('限定病种（留空默认全部）', key='train_disease')
        if st.button('生成题目', key='train_generate_q'):
            st.session_state['image_qtype'] = qtype
            if qtype == '双图鉴别':
                st.session_state['image_case'] = pick_dual_cases(disease or '全部')
            else:
                st.session_state['image_case'] = pick_case(disease or '全部')
        case_obj = st.session_state.get('image_case')
        if case_obj:
            if isinstance(case_obj, list):
                for i, c in enumerate(case_obj, 1):
                    st.markdown(f'#### 图片 {i}')
                    _show_case_image(c)
                question_payload = {'qtype': qtype, 'cases': case_obj}
                gold = case_obj[0]
            else:
                _show_case_image(case_obj)
                question_payload = {'qtype': qtype, 'case': case_obj}
                gold = case_obj
            answer = st.text_area('你的答案', key='train_answer_image')
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
            final_answer = st.text_area('最后请写你的诊断倾向、危险信号、处理建议、宣教与转诊意见', key='sim_final_answer')
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
