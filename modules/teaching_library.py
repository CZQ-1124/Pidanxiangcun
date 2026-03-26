import pandas as pd
import streamlit as st
from modules.common import require_login, hero_banner, metric_grid
from services.db_service import list_seed_cases
from services.utils import resolve_image_path


def render(user: dict):
    require_login()
    hero_banner('教学病例库', '来自真实图片和患者提交')
    rows = list_seed_cases()
    if not rows:
        st.info('暂无病例。')
        return
    df = pd.DataFrame(rows)
    disease = st.selectbox('按病种筛选', ['全部'] + sorted(df['final_confirmed_diagnosis'].dropna().unique().tolist()))
    if disease != '全部':
        df = df[df['final_confirmed_diagnosis'] == disease]
    st.dataframe(df[['case_id', 'file_name', 'final_confirmed_diagnosis', 'doctor_review_risk', 'review_status']], use_container_width=True)
    case_id = st.selectbox('选择病例', df['case_id'].tolist())
    row = df[df['case_id'] == case_id].iloc[0].to_dict()
    img_path = resolve_image_path(row.get('relative_path'), row.get('file_name'))
    if img_path and img_path.exists():
        st.image(str(img_path), caption=row.get('file_name'))
    else:
        st.warning(f"未找到真实图片：{row.get('file_name')}。")
    metric_grid([
        ('最终诊断', row.get('final_confirmed_diagnosis') or '未填'),
        ('专家终审标签', row.get('doctor_review_label') or '未填'),
        ('专家风险', row.get('doctor_review_risk') or '未填'),
        ('教学要点', row.get('teaching_point') or '未填'),
        ('标准解释', row.get('gold_explanation') or '未填'),
    ])
    with st.expander('查看原始字段'):
        st.code(str(row))
