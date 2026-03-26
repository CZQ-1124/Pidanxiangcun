import uuid
import streamlit as st
from services.db_service import list_cases
from services.storage_service import save_uploaded_image
from services.case_pipeline import build_case_narrative, build_case_assessment
from modules.common import require_login

def render(user: dict):
    require_login()
    st.title("疑难会诊台")
    mode = st.radio("入口", ["选已有病例", "上传新图即时分析"], horizontal=True)
    case_data = None
    if mode == "选已有病例":
        visits = list_cases()
        if not visits:
            st.info("暂无已有病例。")
            return
        options = {f"{v['created_at']}｜{v['person_name']}｜{v['visit_id']}": v for v in visits}
        key = st.selectbox("选择病例", list(options.keys()))
        case_data = options[key]
    else:
        person_name = st.text_input("患者姓名")
        person_id = st.text_input("患者编号", value=f"P-{uuid.uuid4().hex[:6].upper()}")
        body_part = st.text_input("部位")
        history = st.text_area("简要病史")
        uploaded = st.file_uploader("上传云图片", type=["jpg","jpeg","png","webp"])
        if uploaded and st.button("生成案例与分析"):
            image_path = save_uploaded_image(uploaded, person_name, user["role"], body_part or "未明", "疑难会诊")
            case_data = {
                "person_name": person_name, "person_id": person_id, "body_part": body_part,
                "history": history, "image_path": image_path, "itch": False, "pain": False, "bleeding": False, "growth": False
            }
    if case_data:
        if st.button("生成疑难案例内容", key="narrative_btn"):
            narrative = build_case_narrative(case_data)
            st.markdown("#### AI自动生成案例")
            st.json(narrative)
        if st.button("生成疑难会诊分析", key="assist_btn"):
            assessment = build_case_assessment(case_data)
            st.markdown("#### AI结构化会诊意见")
            st.json(assessment)
