import sqlite3
import streamlit as st
import pandas as pd
from config.settings import DB_PATH
from services.db_service import list_seed_cases
from modules.common import require_login

def render(user: dict):
    require_login()
    st.title("专家复核台")
    rows = list_seed_cases()
    if not rows:
        st.info("暂无病例。")
        return
    df = pd.DataFrame(rows)
    st.dataframe(df[["case_id","working_label","final_confirmed_diagnosis","referral_level","review_status","is_training_case"]], use_container_width=True)
    options = {r["case_id"]: r for r in rows}
    cid = st.selectbox("选择病例", list(options.keys()))
    row = options[cid]
    label = st.text_input("专家最终标签", value=str(row.get("doctor_review_label") or row.get("final_confirmed_diagnosis") or ""))
    risk = st.selectbox("专家风险分层", ["低风险","中风险","高风险"], index=1)
    teach = st.checkbox("纳入训练集", value=bool(row.get("is_training_case")))
    status = st.selectbox("复核状态", ["待专家复核","已专家复核"])
    if st.button("保存复核结果"):
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "UPDATE seed_cases SET doctor_review_label=?, doctor_review_risk=?, is_training_case=?, review_status=? WHERE case_id=?",
            (label, risk, int(teach), status, cid)
        )
        conn.commit()
        conn.close()
        st.success("已保存。")
