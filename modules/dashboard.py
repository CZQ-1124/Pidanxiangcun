import streamlit as st
from services.db_service import list_cases, list_audio_notes, list_seed_cases, list_review_queue
from services.runtime_config import config_status
from modules.common import hero_banner, metric_grid, render_status_pills


def render(user: dict):
    hero_banner('皮蛋工作台', '围绕连续档案、随访趋势、村医辅助与专家终审运行。')
    role = user['role']
    status = config_status()
    render_status_pills(status)
    metric_grid([
        ('连续随访记录', len(list_cases())),
        ('音频纪要', len(list_audio_notes())),
        ('教学病例', len(list_seed_cases(training_only=True))),
        ('待复核任务', len(list_review_queue('待专家复核'))),
    ])
    if role == '村民':
        st.info('这里是村民主系统：上传皮损图片、查看个人风险曲线、查看随访建议。')
    elif role == '家属':
        st.info('这里是家属协同系统：绑定村民、查看趋势曲线、查看门诊纪要摘要。')
    elif role == '村医':
        st.info('这里是村医工作系统：接诊初筛、疑难会诊、MDT、多次随访、门诊录音归档，以及培训学习。')
    else:
        st.info('这里是专家终审系统：待复核病例、教学病例维护、终审标签与治疗方案。')
