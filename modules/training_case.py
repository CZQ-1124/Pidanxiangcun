import json, uuid
import streamlit as st
from services.training_case_selector import pick_case
from services.ai_router import generate_case_narrative, grade_training
from services.db_service import save_training_attempt
from modules.common import require_login

def render(user: dict):
    require_login()
    st.title("病例推演")
    disease = st.text_input("限定病种（留空默认全部）")
    if st.button("生成教学病例"):
        case = pick_case(disease or "全部")
        st.session_state["case_train_case"] = case
        if case:
            st.session_state["case_train_narrative"] = generate_case_narrative(case)
    case = st.session_state.get("case_train_case")
    narrative = st.session_state.get("case_train_narrative")
    if not case:
        return
    st.markdown("#### AI自动生成病例")
    st.json(narrative)
    answer = st.text_area("你的结构化判断")
    if st.button("提交病例分析"):
        payload = {"qtype": "病例分析", "narrative": narrative}
        feedback = grade_training(payload, answer, case)
        save_training_attempt({
            "attempt_id": f"TRN-{uuid.uuid4().hex[:8].upper()}",
            "training_type": "病例推演",
            "learner_name": user["name"],
            "learner_role": user["role"],
            "question_payload": json.dumps(payload, ensure_ascii=False),
            "user_answer": answer,
            "ai_feedback": json.dumps(feedback, ensure_ascii=False),
            "score": float(feedback.get("score", 0))
        })
        st.json(feedback)
