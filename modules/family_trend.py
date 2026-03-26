import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from services.db_service import list_cases, list_audio_notes
from services.trend_engine import build_trend_summary
from modules.common import require_login, hero_banner, metric_grid, render_review_plan


def render(user: dict):
    require_login()
    hero_banner('亲情云守护', '在这里您可以查看您父母的连续风险曲线、门诊纪要与专家回写方案。')
    default_name = st.text_input('村民姓名', value=user.get('bind_name', ''))
    if not default_name:
        st.info('请输入要查看的村民姓名。')
        return
    visits = list_cases(default_name)
    if not visits:
        st.warning('暂无该村民的随访记录。')
        return
    summary = build_trend_summary(visits)
    st.success(summary['summary'])
    df = pd.DataFrame(visits)
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'])
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.plot(df['created_at'], df['risk_score'], marker='o', linewidth=2)
    ax.set_yticks([0, 1, 2, 3], ['待复拍', '低风险', '中风险', '高风险'])
    ax.set_xlabel('时间')
    ax.set_ylabel('风险曲线')
    ax.set_title(f'{default_name} 连续风险趋势')
    ax.grid(alpha=0.2)
    st.pyplot(fig)
    latest = visits[-1]
    metric_grid([
        ('最新风险', latest.get('risk_level') or '未返回'),
        ('最新建议', latest.get('action_advice') or '未返回'),
        ('专家治疗方案', latest.get('expert_treatment_plan') or '暂未回写'),
        ('专家随访计划', latest.get('expert_followup_plan') or '暂未回写'),
    ])
    st.dataframe(df[['created_at', 'body_part', 'risk_level', 'action_advice', 'trend_summary']], use_container_width=True)
    if latest.get('expert_treatment_plan'):
        st.markdown('#### 专家回写方案')
        render_review_plan(latest)
    notes = list_audio_notes(default_name)
    if notes:
        st.markdown('#### 门诊纪要')
        ndf = pd.DataFrame(notes)
        st.dataframe(ndf[['created_at', 'status', 'summary_text', 'audio_path']], use_container_width=True)
