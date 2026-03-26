from config.settings import RISK_SCORE_MAP

def stratify_risk(case_data: dict, visual_result: dict) -> dict:
    high = 0
    medium = 0
    text_signs = " ".join(visual_result.get("danger_signs", [])).lower()
    if case_data.get("bleeding"):
        high += 1
    if case_data.get("growth"):
        high += 1
    if case_data.get("pain"):
        medium += 1
    for kw in ["出血", "破溃", "边界不规则", "色素不均", "非对称", "恶性", "黑色素瘤"]:
        if kw in text_signs:
            high += 1
    if visual_result.get("confidence") == "low":
        medium += 1
    if not case_data.get("quality_ok", True):
        return {"risk_level": "待复拍", "risk_score": RISK_SCORE_MAP["待复拍"], "action_advice": case_data.get("quality_message")}
    if high >= 2:
        return {"risk_level": "高风险", "risk_score": RISK_SCORE_MAP["高风险"], "action_advice": "建议尽快转上级医院或皮肤科专科进一步评估。"}
    if high >= 1 or medium >= 1:
        return {"risk_level": "中风险", "risk_score": RISK_SCORE_MAP["中风险"], "action_advice": "建议48小时内由村医查看，必要时补拍、补问病史并决定是否转诊。"}
    return {"risk_level": "低风险", "risk_score": RISK_SCORE_MAP["低风险"], "action_advice": "建议观察、规范护肤，并按计划复拍随访。"}
