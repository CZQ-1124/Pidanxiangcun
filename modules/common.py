import html
import json
import streamlit as st


def require_login():
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        st.warning("请先在首页登录。")
        st.stop()


def init_theme():
    st.markdown(
        r'''
        <style>
        .stApp {background: linear-gradient(180deg, #f7fbff 0%, #f4f8fc 100%);}
        .block-container {padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1200px;}
        .pidan-hero {
            background: linear-gradient(135deg, #0f5ea8 0%, #2d85d3 55%, #7db7ee 100%);
            padding: 24px 28px; border-radius: 22px; color: white; margin-bottom: 18px;
            box-shadow: 0 10px 28px rgba(15,94,168,.18);
        }
        .pidan-hero h1 {margin: 0 0 8px 0; font-size: 32px;}
        .pidan-hero p {margin: 0; opacity: .95; font-size: 15px;}
        .pidan-card {
            background: white; border: 1px solid rgba(15,94,168,.08); border-radius: 18px;
            padding: 16px 18px; box-shadow: 0 6px 20px rgba(34,70,120,.05); margin-bottom: 12px;
        }
        .pidan-card h4 {margin: 0 0 10px 0; color: #154a75; font-size: 18px;}
        .pidan-grid {display:grid; grid-template-columns: repeat(auto-fit,minmax(180px,1fr)); gap: 10px; margin: 8px 0 12px 0;}
        .pidan-chip {display:inline-block; padding: 6px 10px; border-radius: 999px; background:#edf5fd; color:#1f5e99; margin-right: 6px; font-size:13px;}
        .pidan-kv {padding: 10px 12px; background:#f7fbff; border-radius: 14px; border:1px solid #e4eef8;}
        .pidan-kv .label {font-size: 12px; color:#64829f; margin-bottom: 6px;}
        .pidan-kv .value {font-size: 15px; color:#173c5c; font-weight: 600;}
        .pidan-ok {background:#eef8f0; border-color:#cfe9d5; color:#1f6a35;}
        .pidan-risk-low {background:#eef6ff; border-color:#d4e7ff; color:#185a96;}
        .pidan-risk-mid {background:#fff8e8; border-color:#ffe1a8; color:#8a6200;}
        .pidan-risk-high {background:#fff0f0; border-color:#ffc9c9; color:#a52d2d;}
        .pidan-risk-urgent {background:#ffe9e9; border-color:#ffb5b5; color:#9a1212;}
        div.stButton > button[kind="primary"] {border-radius: 12px;}
        </style>
        ''',
        unsafe_allow_html=True,
    )


def hero_banner(title: str, subtitle: str):
    st.markdown(f'<div class="pidan-hero"><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>', unsafe_allow_html=True)


def render_status_pills(status: dict):
    text = '已配置' if status.get('text_ready') else '未配置'
    vision = '已配置' if status.get('vision_ready') else '未配置'
    audio = '已配置' if status.get('audio_ready') else '未配置'
    st.markdown(
        f'<span class="pidan-chip">文本AI：{text}</span>'
        f'<span class="pidan-chip">视觉AI：{vision}</span>'
        f'<span class="pidan-chip">音频转写：{audio}</span>',
        unsafe_allow_html=True,
    )


def metric_grid(items):
    cells = []
    for label, value in items:
        cells.append(f'<div class="pidan-kv"><div class="label">{html.escape(str(label))}</div><div class="value">{html.escape(str(value))}</div></div>')
    st.markdown(f'<div class="pidan-grid">{"".join(cells)}</div>', unsafe_allow_html=True)


def _join_list(value):
    if isinstance(value, (list, tuple)):
        return '；'.join([str(x) for x in value if str(x).strip()]) or '未提取'
    return str(value or '未提取')


def render_visit_summary(result: dict):
    risk = str(result.get('risk_level') or '未定')
    risk_cls = 'pidan-risk-low'
    if risk == '中风险':
        risk_cls = 'pidan-risk-mid'
    elif risk == '高风险':
        risk_cls = 'pidan-risk-high'
    elif risk == '紧急':
        risk_cls = 'pidan-risk-urgent'
    st.markdown(f'<div class="pidan-card {risk_cls}"><h4>本次结果概览</h4><div class="pidan-grid">'
                f'<div class="pidan-kv"><div class="label">记录编号</div><div class="value">{html.escape(str(result.get("visit_id") or ""))}</div></div>'
                f'<div class="pidan-kv"><div class="label">病例编号</div><div class="value">{html.escape(str(result.get("case_id") or ""))}</div></div>'
                f'<div class="pidan-kv"><div class="label">风险分层</div><div class="value">{html.escape(risk)}</div></div>'
                f'<div class="pidan-kv"><div class="label">图像质控</div><div class="value">{"合格" if result.get("quality_ok") else "需重拍"}</div></div>'
                '</div></div>', unsafe_allow_html=True)
    metric_grid([
        ('图像质控说明', result.get('quality_message') or '未生成'),
        ('视觉摘要', result.get('ai_visual_summary') or '未生成'),
        ('候选方向', result.get('ai_candidates') or '未生成'),
        ('行动建议', result.get('action_advice') or '未生成'),
        ('趋势解释', result.get('trend_summary') or '未生成'),
    ])
    if result.get('expert_treatment_plan'):
        metric_grid([
            ('专家治疗方案', result.get('expert_treatment_plan')),
            ('专家随访计划', result.get('expert_followup_plan') or '未填写'),
            ('专家审核人', result.get('expert_reviewer') or '未填写'),
        ])


def render_training_feedback(feedback: dict):
    if feedback.get('_status') == 'not_configured':
        st.error(feedback.get('_error') or 'AI 未配置。请先到系统设置页完成配置。')
        return
    if feedback.get('_status') == 'error':
        st.error(feedback.get('_error') or 'AI 调用失败。')
        return
    st.markdown('### AI 评分结果')
    metric_grid([
        ('得分', feedback.get('score', '未返回')),
        ('做对的点', _join_list(feedback.get('strengths'))),
        ('遗漏点', _join_list(feedback.get('missed_points'))),
        ('反馈', feedback.get('feedback') or '未返回'),
    ])
    with st.expander('查看原始评分结果'):
        st.code(json.dumps(feedback, ensure_ascii=False, indent=2), language='json')


def render_assessment(result: dict, title: str = 'AI 结构化结果'):
    if result.get('_status') == 'not_configured':
        st.error(result.get('_error') or 'AI 未配置。')
        return
    if result.get('_status') == 'error':
        st.error(result.get('_error') or 'AI 调用失败。')
        return
    if any(k in result for k in ['score', 'strengths', 'missed_points']):
        render_training_feedback(result)
        return
    st.markdown(f'### {title}')
    fields = []
    keys = ['differentials','follow_questions','action_points','referral_threshold','patient_friendly_summary',
            'chief_complaint','history_of_present_illness','case_summary','key_points',
            'derm_director','morphology_expert','pathology_view','integrated_plan',
            'course','body_part','symptoms','prior_treatment','danger_signs','doctor_advice','referral_advice','followup_plan','patient_summary',
            'opening_statement','patient_reply','feedback']
    for key in keys:
        if key in result and result.get(key) not in [None, '', []]:
            fields.append((key, _join_list(result.get(key))))
    metric_grid([(k.replace('_', ' ').title(), v) for k, v in fields])
    with st.expander('查看原始结果'):
        st.code(json.dumps(result, ensure_ascii=False, indent=2), language='json')


def render_review_plan(case_row: dict):
    metric_grid([
        ('专家最终标签', case_row.get('doctor_review_label') or '未终审'),
        ('专家风险分层', case_row.get('doctor_review_risk') or '未终审'),
        ('治疗方案', case_row.get('expert_treatment_plan') or '未填写'),
        ('随访计划', case_row.get('expert_followup_plan') or '未填写'),
        ('审核专家', case_row.get('expert_reviewer') or '未填写'),
    ])
