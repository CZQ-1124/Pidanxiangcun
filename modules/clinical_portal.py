import json
import uuid
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from modules.common import require_login, hero_banner, render_visit_summary, render_assessment, metric_grid, render_review_plan
from services.storage_service import save_uploaded_image, save_uploaded_audio
from services.case_pipeline import run_case_pipeline, build_case_assessment, build_case_narrative, build_mdt
from services.db_service import list_cases, list_audio_notes, save_audio_note, submit_review
from services.ai_router import transcribe_audio, summarize_clinic_audio
from services.trend_engine import build_trend_summary
from services.utils import resolve_image_path


def render(user: dict):
    require_login()
    hero_banner('村医临床工作区', '帮助您从接诊、会诊、随访与复核四条主线进行工作。')
    tabs = st.tabs(['接诊初筛', '疑难会诊 / MDT', '随访趋势 / 门诊音频', '提交专家复核'])

    with tabs[0]:
        st.subheader('新接诊：拍照后进入 AI 初筛')
        with st.form('doctor_new_visit_form'):
            person_name = st.text_input('患者姓名')
            person_id = st.text_input('患者编号', value=f'P-{uuid.uuid4().hex[:6].upper()}')
            body_part = st.selectbox('部位', ['面部', '头皮', '躯干', '上肢', '下肢', '手足', '其他'])
            duration = st.text_input('病程', placeholder='如：2周、3个月')
            itch = st.checkbox('瘙痒')
            pain = st.checkbox('疼痛')
            bleeding = st.checkbox('出血/破溃')
            growth = st.checkbox('近期增大')
            history = st.text_area('补充描述')
            uploaded = st.file_uploader('上传皮损图片', type=['jpg', 'jpeg', 'png', 'webp'], key='doctor_visit_upload')
            submitted = st.form_submit_button('开始分析', type='primary')
        if submitted:
            if not uploaded or not person_name.strip():
                st.error('请先填写患者姓名并上传图片。')
            else:
                with st.spinner('正在做图像质控与辅助分层...'):
                    image_path = save_uploaded_image(uploaded, person_name, user['role'], body_part, '首诊')
                    result = run_case_pipeline({
                        'person_id': person_id,
                        'person_name': person_name,
                        'uploader_name': user['name'],
                        'source_role': user['role'],
                        'image_path': image_path,
                        'body_part': body_part,
                        'duration': duration,
                        'itch': itch,
                        'pain': pain,
                        'bleeding': bleeding,
                        'growth': growth,
                        'history': history,
                    })
                st.session_state['latest_visit_result'] = result
        result = st.session_state.get('latest_visit_result')
        if result:
            render_visit_summary(result)
            if st.button('生成结构化辅助意见', key='after_visit_assess'):
                with st.spinner('正在调用 AI 生成结构化辅助...'):
                    assess = build_case_assessment(result)
                render_assessment(assess, '结构化辅助意见')

    with tabs[1]:
        st.subheader('疑难病例：案例生成、结构化建议与 MDT')
        mode = st.radio('入口', ['选已有病例', '上传新图即时分析'], horizontal=True, key='difficult_mode')
        case_data = None
        if mode == '选已有病例':
            visits = list_cases()
            if visits:
                options = {f"{v['created_at']}｜{v['person_name']}｜{v['visit_id']}": v for v in visits}
                key = st.selectbox('选择病例', list(options.keys()), key='difficult_existing_case')
                case_data = options[key]
            else:
                st.info('暂无已有病例。')
        else:
            p_name = st.text_input('患者姓名', key='difficult_person_name')
            p_id = st.text_input('患者编号', value=f'P-{uuid.uuid4().hex[:6].upper()}', key='difficult_person_id')
            body_part = st.text_input('部位', key='difficult_body')
            history = st.text_area('简要病史', key='difficult_history')
            uploaded = st.file_uploader('上传云图片', type=['jpg', 'jpeg', 'png', 'webp'], key='difficult_upload')
            if uploaded and st.button('载入此病例', key='difficult_load'):
                image_path = save_uploaded_image(uploaded, p_name or '未命名患者', user['role'], body_part or '未明部位', '疑难会诊')
                case_data = {
                    'person_name': p_name,
                    'person_id': p_id,
                    'body_part': body_part,
                    'history': history,
                    'image_path': image_path,
                    'itch': False,
                    'pain': False,
                    'bleeding': False,
                    'growth': False,
                }
                st.session_state['difficult_case_data'] = case_data
        if not case_data:
            case_data = st.session_state.get('difficult_case_data')
        if case_data:
            img = resolve_image_path(case_data.get('image_path'), case_data.get('file_name'))
            if img and img.exists():
                st.image(str(img), caption=img.name)
            cols = st.columns(3)
            if cols[0].button('生成案例内容'):
                with st.spinner('正在生成教学案例...'):
                    narrative = build_case_narrative(case_data)
                render_assessment(narrative, 'AI 案例内容')
            if cols[1].button('生成村医结构化建议'):
                with st.spinner('正在生成结构化建议...'):
                    assessment = build_case_assessment(case_data)
                render_assessment(assessment, '村医结构化建议')
            if cols[2].button('发起 MDT 多视角'):
                with st.spinner('正在生成 MDT 意见...'):
                    mdt = build_mdt(case_data)
                render_assessment(mdt, 'MDT 多视角意见')

    with tabs[2]:
        st.subheader('连续档案与门诊音频')
        name = st.text_input('患者姓名', key='trend_patient_name')
        if name:
            visits = list_cases(name)
            if visits:
                summary = build_trend_summary(visits)
                st.success(summary['summary'])
                df = pd.DataFrame(visits)
                df['created_at'] = pd.to_datetime(df['created_at'])
                fig, ax = plt.subplots(figsize=(8, 3.2))
                ax.plot(df['created_at'], df['risk_score'], marker='o', linewidth=2)
                ax.set_yticks([0, 1, 2, 3], ['待复拍', '低风险', '中风险', '高风险'])
                ax.set_title(f'{name} 风险曲线')
                ax.grid(alpha=0.2)
                st.pyplot(fig)
                latest = visits[-1]
                metric_grid([
                    ('最新风险', latest.get('risk_level') or '未返回'),
                    ('最新建议', latest.get('action_advice') or '未返回'),
                    ('专家治疗方案', latest.get('expert_treatment_plan') or '暂未回写'),
                    ('专家随访计划', latest.get('expert_followup_plan') or '暂未回写'),
                ])
                st.dataframe(df[['created_at', 'body_part', 'risk_level', 'action_advice']], use_container_width=True)
                if latest.get('expert_treatment_plan'):
                    st.markdown('#### 专家回写方案')
                    render_review_plan(latest)
            else:
                st.info('该患者还没有图片随访记录。')
            notes = list_audio_notes(name)
            if notes:
                st.markdown('#### 历史门诊纪要')
                ndf = pd.DataFrame(notes)
                st.dataframe(ndf[['created_at', 'status', 'summary_text', 'audio_path']], use_container_width=True)
        st.markdown('---')
        st.markdown('#### 新增门诊音频')
        person_name = st.text_input('归档到患者姓名', key='audio_patient_name')
        person_id = st.text_input('患者编号', key='audio_patient_id')
        visit_id = st.text_input('对应 visit_id（可留空）', key='audio_visit_id')
        audio_file = st.file_uploader('上传门诊录音文件', type=['wav', 'mp3', 'm4a'], key='audio_upload')
        mic_audio = st.audio_input('或直接录音', key='audio_input_live') if hasattr(st, 'audio_input') else None
        if st.button('保存并整理门诊纪要', key='audio_process_btn'):
            source_audio = mic_audio or audio_file
            if not source_audio or not person_name.strip():
                st.error('请先指定患者并上传/录制音频。')
            else:
                audio_path = save_uploaded_audio(source_audio, person_name, user['role'], '门诊录音')
                with st.spinner('正在转写音频...'):
                    asr = transcribe_audio(audio_path)
                structured = summarize_clinic_audio(asr.get('transcript_text', '')) if asr.get('transcript_text') else {}
                save_audio_note({
                    'note_id': f'AUD-{uuid.uuid4().hex[:8].upper()}',
                    'person_id': person_id,
                    'person_name': person_name,
                    'visit_id': visit_id,
                    'audio_path': audio_path,
                    'transcript_text': asr.get('transcript_text'),
                    'summary_text': structured.get('patient_summary') if structured else asr.get('summary_text'),
                    'structured_json': json.dumps(structured, ensure_ascii=False),
                    'created_by': user['name'],
                    'created_role': user['role'],
                    'status': asr.get('status'),
                })
                if asr.get('status') != 'transcribed':
                    st.warning(asr.get('summary_text') or '音频已保存，但未完成真实转写。')
                if asr.get('transcript_text'):
                    st.text_area('原始转写', value=asr.get('transcript_text', ''), height=160)
                if isinstance(structured, dict) and structured:
                    render_assessment(structured, 'AI 结构化门诊纪要')

    with tabs[3]:
        st.subheader('提交给专家做终审')
        visits = list_cases()
        if not visits:
            st.info('暂无可提交病例。')
        else:
            options = {f"{v['created_at']}｜{v['person_name']}｜{v['visit_id']}": v for v in visits}
            key = st.selectbox('选择病例提交复核', list(options.keys()), key='submit_review_case')
            note = st.text_area('提交说明', placeholder='例如：疑似黑色素瘤，拟纳入危险图训练集。')
            if st.button('提交到专家复核队列', type='primary'):
                case = options[key]
                submit_review({
                    'submission_id': f'RVW-{uuid.uuid4().hex[:8].upper()}',
                    'source_type': 'case_visit',
                    'source_id': case['visit_id'],
                    'patient_name': case['person_name'],
                    'submitted_by': user['name'],
                    'submitted_role': user['role'],
                    'note': note,
                })
                st.success('已提交到专家复核队列。')
