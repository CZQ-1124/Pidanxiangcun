import uuid
from datetime import datetime
from services.image_quality import check_image_quality
from services.ai_router import analyze_skin_image, structured_assessment, generate_case_narrative, mdt_consult
from services.risk_engine import stratify_risk
from services.db_service import save_case, list_cases, upsert_patient
from services.trend_engine import build_trend_summary

def run_case_pipeline(case_data: dict) -> dict:
    if not case_data.get("case_id"):
        case_data["case_id"] = f"PIDAN-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    if not case_data.get("visit_id"):
        case_data["visit_id"] = f"VISIT-{uuid.uuid4().hex[:10].upper()}"
    upsert_patient(case_data["person_id"], case_data["person_name"])
    quality = check_image_quality(case_data["image_path"])
    merged = {**case_data, **quality}
    if quality["quality_ok"]:
        visual = analyze_skin_image(case_data["image_path"], case_data)
        merged["ai_visual_summary"] = visual.get("visual_summary", "")
        merged["ai_candidates"] = "；".join(visual.get("candidates", []))
        merged["ai_confidence"] = visual.get("confidence", "low")
        risk = stratify_risk(merged, visual)
    else:
        merged["ai_visual_summary"] = ""
        merged["ai_candidates"] = ""
        merged["ai_confidence"] = "low"
        risk = stratify_risk(merged, {"danger_signs": [], "confidence": "low"})
    merged.update(risk)
    history = list_cases(case_data["person_name"])
    curve = build_trend_summary(history + [dict(created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), risk_score=merged["risk_score"], risk_level=merged["risk_level"])])
    merged["trend_summary"] = curve["summary"]
    save_case(merged)
    return merged

def build_case_assessment(case_data: dict) -> dict:
    return structured_assessment(case_data)

def build_case_narrative(case_data: dict) -> dict:
    return generate_case_narrative(case_data)

def build_mdt(case_data: dict) -> dict:
    return mdt_consult(case_data)
