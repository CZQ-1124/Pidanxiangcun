import json, uuid
import streamlit as st
from services.training_case_selector import pick_case
from services.ai_router import simulate_patient_opening, grade_training
from services.db_service import save_training_attempt
from modules.common import require_login

def render(user: dict):
    require_login()
    st.title("模拟门诊")
    if st.button("生成模拟门诊场景"):
        case = pick_case()
        st.session_state["sim_case"] = case
        if case:
            st.session_state["sim_opening"] = simulate_patient_opening(case)
            st.session_state["sim_dialogue"] = []
    case = st.session_state.get("sim_case")
    opening = st.session_state.get("sim_opening")
    if not case:
        return
    st.markdown("#### 患者开场")
    st.write(opening.get("opening_statement"))
    q = st.text_input("你要问患者什么？")
    if st.button("记录这一轮问诊"):
        st.session_state["sim_dialogue"].append({"doctor": q, "patient": "本版本先记录问诊文本，并在最终环节由AI整体评分。"})
    for turn in st.session_state.get("sim_dialogue", []):
        st.write(f"村医：{turn['doctor']}")
        st.write(f"患者：{turn['patient']}")
    final_answer = st.text_area("最后请写你的诊断倾向、危险信号、处理建议、宣教与转诊意见")
    if st.button("结束模拟并评分"):
        payload = {"qtype": "模拟门诊", "opening": opening, "dialogue": st.session_state.get("sim_dialogue", [])}
        feedback = grade_training(payload, final_answer, case)
        save_training_attempt({
            "attempt_id": f"TRN-{uuid.uuid4().hex[:8].upper()}",
            "training_type": "模拟门诊",
            "learner_name": user["name"],
            "learner_role": user["role"],
            "question_payload": json.dumps(payload, ensure_ascii=False),
            "user_answer": final_answer,
            "ai_feedback": json.dumps(feedback, ensure_ascii=False),
            "score": float(feedback.get("score", 0))
        })
        st.json(feedback)
