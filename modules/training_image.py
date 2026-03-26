import json, uuid
import streamlit as st
from pathlib import Path
from services.training_case_selector import pick_case, pick_dual_cases
from services.ai_router import grade_training
from services.db_service import save_training_attempt
from config.settings import IMAGES_DIR
from modules.common import require_login

def _show_case_image(case: dict):
    img_path = IMAGES_DIR / str(case.get("relative_path") or case.get("file_name"))
    if not img_path.exists():
        img_path = IMAGES_DIR / str(case.get("file_name"))
    if img_path.exists():
        st.image(str(img_path), caption=case.get("file_name"))
    else:
        st.info(f"未找到真实图片：请把 {case.get('file_name')} 放入指定文件夹")

def render(user: dict):
    require_login()
    st.title("识图闯关")
    qtype = st.selectbox("题型", ["看图写病", "同病共同特点", "双图鉴别"])
    disease = st.text_input("限定病种（留空默认全部）")
    if st.button("生成题目"):
        st.session_state["image_qtype"] = qtype
        if qtype == "双图鉴别":
            st.session_state["image_case"] = pick_dual_cases()
        else:
            st.session_state["image_case"] = pick_case(disease or "全部")
    case_obj = st.session_state.get("image_case")
    if not case_obj:
        return
    if isinstance(case_obj, list):
        for i, c in enumerate(case_obj, 1):
            st.markdown(f"#### 图片 {i}")
            _show_case_image(c)
        question_payload = {"qtype": qtype, "cases": case_obj}
    else:
        _show_case_image(case_obj)
        question_payload = {"qtype": qtype, "case": case_obj}
    answer = st.text_area("你的答案")
    if st.button("提交作答并获取AI反馈"):
        gold = case_obj[0] if isinstance(case_obj, list) else case_obj
        feedback = grade_training(question_payload, answer, gold)
        save_training_attempt({
            "attempt_id": f"TRN-{uuid.uuid4().hex[:8].upper()}",
            "training_type": "识图闯关",
            "learner_name": user["name"],
            "learner_role": user["role"],
            "question_payload": json.dumps(question_payload, ensure_ascii=False),
            "user_answer": answer,
            "ai_feedback": json.dumps(feedback, ensure_ascii=False),
            "score": float(feedback.get("score", 0))
        })
        st.json(feedback)
