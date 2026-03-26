import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from services.db_service import list_cases, list_audio_notes
from modules.common import require_login, hero_banner, metric_grid, render_review_plan


def render(user: dict):
    require_login()
    hero_banner('康复随访台', '查看连续记录、风险曲线与专家回写的治疗方案。')
    name = st.text_input('患者姓名', value=user['name'] if user['role'] == '村民' else '')
    if not name:
        st.info('请输入患者姓名。')
        return
    visits = list_cases(name)
    if not visits:
        st.warning('暂无记录。')
        return
    df = pd.DataFrame(visits)
    df['created_at'] = pd.to_datetime(df['created_at'])
    latest = visits[-1]
    metric_grid([
        ('最新风险', latest.get('risk_level') or '未返回'),
        ('最新建议', latest.get('action_advice') or '未返回'),
        ('专家治疗方案', latest.get('expert_treatment_plan') or '暂未回写'),
        ('专家随访计划', latest.get('expert_followup_plan') or '暂未回写'),
    ])
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.plot(df['created_at'], df['risk_score'], marker='o', linewidth=2)
    ax.set_yticks([0, 1, 2, 3], ['待复拍', '低风险', '中风险', '高风险'])
    ax.set_title(f'{name} 风险曲线')
    ax.grid(alpha=0.2)
    st.pyplot(fig)
    st.dataframe(df[['created_at', 'body_part', 'risk_level', 'action_advice', 'trend_summary']], use_container_width=True)
    if latest.get('expert_treatment_plan'):
        st.markdown('#### 专家回写方案')
        render_review_plan(latest)
    notes = list_audio_notes(name)
    if notes:
        st.markdown('#### 对应门诊录音纪要')
        ndf = pd.DataFrame(notes)
        st.dataframe(ndf[['created_at', 'status', 'summary_text']], use_container_width=True)
