import streamlit as st
import uuid
from services.storage_service import save_uploaded_image
from services.case_pipeline import run_case_pipeline
from modules.common import require_login, hero_banner, render_visit_summary


def render(user: dict):
    require_login()
    hero_banner('村民随手拍', '请您尽量保证光线充足，图片清晰，不合格的图片请您重拍后上传。')
    with st.form('visit_form'):
        person_name = st.text_input('患者姓名', value=user['name'] if user['role'] == '村民' else '')
        person_id = st.text_input('患者编号', value=f"P-{uuid.uuid4().hex[:6].upper()}")
        uploader_name = st.text_input('上传人', value=user['name'])
        body_part = st.selectbox('部位', ['面部', '头皮', '躯干', '上肢', '下肢', '手足', '其他'])
        duration = st.text_input('病程', placeholder='如：2周、3个月')
        itch = st.checkbox('瘙痒')
        pain = st.checkbox('疼痛')
        bleeding = st.checkbox('出血/破溃')
        growth = st.checkbox('近期增大')
        history = st.text_area('补充描述')
        uploaded = st.file_uploader('上传皮损图片', type=['jpg', 'jpeg', 'png', 'webp'])
        submitted = st.form_submit_button('开始分析', type='primary')
    if submitted:
        if not uploaded or not person_name.strip():
            st.error('请先填写患者姓名并上传图片。')
            return
        image_path = save_uploaded_image(uploaded, person_name, user['role'], body_part, '首诊' if user['role'] == '村民' else '上传')
        with st.spinner('正在分析图片...'):
            result = run_case_pipeline({
                'person_id': person_id,
                'person_name': person_name,
                'uploader_name': uploader_name,
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
        st.success('已写入连续档案。')
        render_visit_summary(result)
