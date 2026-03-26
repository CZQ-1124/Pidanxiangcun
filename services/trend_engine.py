from config.settings import RISK_SCORE_MAP

def build_trend_summary(visits: list[dict]) -> dict:
    if not visits:
        return {"summary": "暂无连续记录", "curve": []}
    points = []
    for v in visits:
        points.append({"time": v["created_at"], "risk_score": v.get("risk_score", 0), "risk_level": v.get("risk_level", "")})
    if len(points) == 1:
        return {"summary": "目前仅有1次记录，建议继续复拍以观察趋势。", "curve": points}
    prev, cur = points[-2], points[-1]
    if cur["risk_score"] > prev["risk_score"]:
        txt = f"较上次风险升高：{prev['risk_level']} → {cur['risk_level']}，建议提前复查。"
    elif cur["risk_score"] < prev["risk_score"]:
        txt = f"较上次风险下降：{prev['risk_level']} → {cur['risk_level']}，可继续随访观察。"
    else:
        txt = f"与上次风险分层一致，当前维持在{cur['risk_level']}。"
    return {"summary": txt, "curve": points}
