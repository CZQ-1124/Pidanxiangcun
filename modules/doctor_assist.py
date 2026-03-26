import pandas as pd
import streamlit as st
from services.db_service import list_cases
from services.ai_router import structured_assessment
from modules.common import require_login

def render(user: dict):
    require_login()
    st.title("村医随身专家")
    visits = list_cases()
    if not visits:
        st.info("暂无病例。")
        return
    df = pd.DataFrame(visits)
    st.dataframe(df[["created_at","person_name","body_part","risk_level","ai_candidates","action_advice"]], use_container_width=True)
    options = {f"{v['created_at']}｜{v['person_name']}｜{v['visit_id']}": v for v in visits}
    key = st.selectbox("选择一个病例查看结构化辅助", list(options.keys()))
    case_data = options[key]
    st.json(case_data)
    if st.button("生成村医结构化辅助意见"):
        out = structured_assessment(case_data)
        st.json(out)
