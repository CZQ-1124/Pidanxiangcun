import streamlit as st
from services.db_service import list_cases
from services.case_pipeline import build_mdt
from modules.common import require_login

def render(user: dict):
    require_login()
    st.title("多学科会诊台")
    visits = list_cases()
    if not visits:
        st.info("暂无病例。")
        return
    options = {f"{v['created_at']}｜{v['person_name']}｜{v['visit_id']}": v for v in visits}
    key = st.selectbox("选择病例", list(options.keys()))
    case_data = options[key]
    if st.button("启动MDT会诊"):
        out = build_mdt(case_data)
        st.markdown("#### 皮肤科主任")
        st.write(out.get("derm_director"))
        st.markdown("#### 皮损形态学专家")
        st.write(out.get("morphology_expert"))
        st.markdown("#### 病理科主任")
        st.write(out.get("pathology_view"))
        st.markdown("#### 综合意见")
        st.write(out.get("integrated_plan"))
