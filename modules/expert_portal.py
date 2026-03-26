import uuid
import pandas as pd
import streamlit as st

from modules.common import require_login, hero_banner, metric_grid, render_review_plan
from services.db_service import (
    list_seed_cases,
    update_seed_case_review,
    add_seed_case,
    list_review_queue,
    apply_expert_review,
    get_case_by_visit_id,
)
from services.storage_service import save_uploaded_image
from services.utils import resolve_image_path


def render(user: dict):
    require_login()
    hero_banner('专家终审台', '待复核单独处理；高清病例将会自动进入教学病例库。')
    tabs = st.tabs(['待复核', '教学病例库', '新增教学病例'])

    with tabs[0]:
        queue = list_review_queue()
        if not queue:
            st.info('当前没有待复核病例。')
        else:
            qdf = pd.DataFrame(queue)
            show_cols = [c for c in ['created_at', 'patient_name', 'source_type', 'submitted_by', 'status', 'note'] if c in qdf.columns]
            st.dataframe(qdf[show_cols], use_container_width=True)
            pick = st.selectbox('选择一条复核任务', qdf['submission_id'].tolist())
            row = qdf[qdf['submission_id'] == pick].iloc[0].to_dict()
            source_case = get_case_by_visit_id(row['source_id']) if row.get('source_type') == 'case_visit' else None
            if source_case:
                img = resolve_image_path(source_case.get('image_path'), None)
                if img and img.exists():
                    st.image(str(img), caption=img.name)
                metric_grid([
                    ('患者', source_case.get('person_name')),
                    ('部位', source_case.get('body_part') or '未填'),
                    ('风险', source_case.get('risk_level') or '未返回'),
                    ('候选方向', source_case.get('ai_candidates') or '未返回'),
                    ('趋势解释', source_case.get('trend_summary') or '未返回'),
                ])
            with st.form(f'expert_review_{pick}'):
                current_label = (source_case or {}).get('doctor_review_label') or (source_case or {}).get('ai_candidates', '').split('；')[0]
                current_risk = (source_case or {}).get('doctor_review_risk') or '中风险'
                risk_options = ['低风险', '中风险', '高风险', '紧急']
                idx = risk_options.index(current_risk) if current_risk in risk_options else 1
                label = st.text_input('专家最终标签', value=current_label)
                risk = st.selectbox('专家风险分层', risk_options, index=idx)
                treatment_plan = st.text_area('治疗方案（写给村医跟进）', value=(source_case or {}).get('expert_treatment_plan') or '')
                followup_plan = st.text_area('随访计划', value=(source_case or {}).get('expert_followup_plan') or '')
                review_note = st.text_area('专家备注', value=row.get('expert_review_note') or '')
                new_status = st.selectbox('复核后任务状态', ['待专家复核', '已专家复核'], index=1)
                ok = st.form_submit_button('保存终审结果', type='primary')
            if ok:
                apply_expert_review(pick, new_status, label, risk, treatment_plan, followup_plan, review_note, user['name'])
                st.success('已写回病例，并同步到村医/随访端。')
                st.rerun()
            if source_case and source_case.get('expert_treatment_plan'):
                st.markdown('#### 当前已回写方案')
                render_review_plan(source_case)

    with tabs[1]:
        rows = list_seed_cases()
        if not rows:
            st.info('暂无教学病例。')
        else:
            df = pd.DataFrame(rows)
            st.dataframe(df[['case_id', 'file_name', 'final_confirmed_diagnosis', 'doctor_review_label', 'doctor_review_risk', 'review_status', 'is_training_case']], use_container_width=True)
            case_id = st.selectbox('选择一个教学病例', df['case_id'].tolist())
            row = df[df['case_id'] == case_id].iloc[0].to_dict()
            img_path = resolve_image_path(row.get('relative_path'), row.get('file_name'))
            if img_path and img_path.exists():
                st.image(str(img_path), caption=row.get('file_name'))
            else:
                st.warning(f"未找到真实图片：{row.get('file_name')}。")
            label = st.text_input('专家最终标签', value=str(row.get('doctor_review_label') or row.get('final_confirmed_diagnosis') or ''), key='seed_label')
            risk = st.selectbox('专家风险分层', ['低风险', '中风险', '高风险', '紧急'], key='seed_risk')
            teach = st.checkbox('纳入训练集', value=bool(row.get('is_training_case')))
            status = st.selectbox('复核状态', ['待专家复核', '已专家复核'], key='seed_status')
            if st.button('保存病例库终审结果'):
                update_seed_case_review(case_id, label, risk, teach, status)
                st.success('已保存复核结果。')
                st.rerun()
            with st.expander('查看病例原始字段'):
                st.code(str(row))

    with tabs[2]:
        st.caption('用于专家新增或补充教学病例。')
        with st.form('expert_add_seed_case'):
            file_obj = st.file_uploader('上传教学图片', type=['jpg', 'jpeg', 'png', 'webp'])
            disease = st.text_input('最终诊断')
            body_site = st.text_input('部位')
            teaching_point = st.text_area('教学要点')
            gold_explanation = st.text_area('标准解释')
            referral = st.selectbox('风险/转诊级别', ['低风险', '中风险', '高风险', '紧急'])
            submit = st.form_submit_button('加入教学病例库', type='primary')
        if submit:
            if not file_obj or not disease.strip():
                st.error('请至少上传图片并填写最终诊断。')
            else:
                image_path = save_uploaded_image(file_obj, disease, '专家', body_site or '未明部位', '教学病例')
                case_id = f'SEED-{uuid.uuid4().hex[:8].upper()}'
                add_seed_case({
                    'case_id': case_id,
                    'image_id': None,
                    'patient_id_anon': case_id,
                    'file_name': image_path.split('/')[-1],
                    'relative_path': image_path,
                    'source_batch': '专家上传',
                    'original_group': disease,
                    'use_tag': '教学病例',
                    'disease_level1': '',
                    'disease_level2': disease,
                    'working_label': disease,
                    'final_confirmed_diagnosis': disease,
                    'diagnosis_status': '专家录入',
                    'pathology_confirmed': '未知',
                    'body_site': body_site,
                    'image_type': '大体图像',
                    'image_quality': '待评估',
                    'is_typical_case': '待定',
                    'danger_signal': '待定',
                    'referral_level': referral,
                    'suspected_diagnosis_1': disease,
                    'suspected_diagnosis_2': '',
                    'common_misdiagnosis': '',
                    'symptom_keywords': body_site,
                    'teaching_point': teaching_point,
                    'gold_explanation': gold_explanation,
                    'usable_for_quiz': '是',
                    'village_doctor_level': '初级',
                    'note': '',
                    'urgency_score': 3,
                    'split_suggestion': 'train_core',
                    'system_priority': 'P2',
                    'doctor_review_label': disease,
                    'doctor_review_risk': referral,
                    'is_training_case': 1,
                    'review_status': '已专家复核',
                })
                st.success('已加入教学病例库。')
                st.rerun()
