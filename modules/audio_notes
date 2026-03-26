import json, uuid
import streamlit as st
from services.storage_service import save_uploaded_audio
from services.ai_router import transcribe_audio, summarize_clinic_audio
from services.db_service import save_audio_note, list_cases
from modules.common import require_login

def render(user: dict):
    require_login()
    st.title("音频门诊纪要")
    st.caption("请您先进入具体患者，再录音或上传录音。系统将会保存原始音频，自动进行转写和结构化整理。")
    person_name = st.text_input("患者姓名")
    person_id = st.text_input("患者编号")
    visits = list_cases(person_name) if person_name else []
    visit_options = {"不绑定具体就诊": ""} | {f"{v['created_at']}｜{v['visit_id']}": v['visit_id'] for v in visits}
    visit_label = st.selectbox("绑定到哪一次就诊", list(visit_options.keys()))
    visit_id = visit_options[visit_label]
    audio_file = st.audio_input("现场录音")
    upload_file = st.file_uploader("或上传录音文件", type=["wav","mp3","m4a","mp4","mpeg"])
    source = audio_file or upload_file
    if st.button("保存并整理门诊纪要"):
        if not source or not person_name:
            st.error("请先填写患者并提供录音。")
            return
        audio_path = save_uploaded_audio(source, person_name, user["role"], "门诊纪要")
        asr = transcribe_audio(audio_path)
        summary = summarize_clinic_audio(asr.get("transcript_text","")) if asr.get("transcript_text") else {}
        payload = {
            "note_id": f"AUD-{uuid.uuid4().hex[:8].upper()}",
            "person_id": person_id,
            "person_name": person_name,
            "visit_id": visit_id,
            "audio_path": audio_path,
            "transcript_text": asr.get("transcript_text",""),
            "summary_text": summary.get("patient_summary","") if summary else "",
            "structured_json": json.dumps(summary, ensure_ascii=False) if summary else "{}",
            "created_by": user["name"],
            "created_role": user["role"],
            "status": asr.get("status","saved_only")
        }
        save_audio_note(payload)
        st.success("已归档到患者连续档案。")
        st.write("音频文件：", audio_path)
        if asr.get("status") == "asr_not_configured":
            st.warning("当前未配置语音转写模型，所以仅保存原始音频，没有伪造转写结果。")
        elif asr.get("status") == "asr_error":
            st.error(f"语音转写失败：{asr.get('summary_text')}")
        else:
            st.markdown("#### 原始转写")
            st.write(asr.get("transcript_text"))
            st.markdown("#### AI门诊纪要")
            st.json(summary)
