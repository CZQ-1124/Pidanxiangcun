import streamlit as st
from services.runtime_config import config_status, save_runtime_config
from services.ai_router import call_text_json
from modules.common import hero_banner, metric_grid


def render(user: dict | None = None, embedded: bool = False):
    if embedded:
        st.subheader('系统设置')
    else:
        hero_banner('系统设置', '配置 AiHubMix 或其他兼容 OpenAI 的接口，再进入各身份工作台。')
    status = config_status()
    metric_grid([
        ('文本模型', '已连接' if status['text_ready'] else '未配置'),
        ('视觉模型', '已连接' if status['vision_ready'] else '未配置'),
        ('音频转写', '已连接' if status['audio_ready'] else '未配置'),
    ])
    with st.form('ai_settings_form'):
        base_url = st.text_input('AI_BASE_URL', value=status['AI_BASE_URL'])
        api_key = st.text_input('AI_API_KEY', value=status['AI_API_KEY'], type='password')
        text_model = st.text_input('TEXT_MODEL', value=status['TEXT_MODEL'])
        vision_model = st.text_input('VISION_MODEL', value=status['VISION_MODEL'])
        audio_model = st.text_input('AUDIO_MODEL', value=status['AUDIO_MODEL'])
        thinking_mode = st.selectbox('THINKING_MODE', ['omit', 'disabled', 'auto', 'enabled'], index=['omit', 'disabled', 'auto', 'enabled'].index(status['THINKING_MODE']))
        timeout = st.number_input('AI_TIMEOUT_SEC', min_value=5, max_value=120, value=int(float(status['AI_TIMEOUT_SEC'] or 25)))
        submitted = st.form_submit_button('保存到 .env', type='primary')
    if submitted:
        save_runtime_config({
            'AI_BASE_URL': base_url,
            'AI_API_KEY': api_key,
            'TEXT_MODEL': text_model,
            'VISION_MODEL': vision_model,
            'AUDIO_MODEL': audio_model,
            'THINKING_MODE': thinking_mode,
            'AI_TIMEOUT_SEC': str(timeout),
        })
        st.success('已保存配置。')
        st.rerun()

    if st.button('测试文本模型连通性'):
        with st.spinner('正在测试文本模型...'):
            result = call_text_json(
                '你是测试助手。',
                '返回 JSON：{"ok": true, "message": "连接正常"}',
                {'ok': False, 'message': ''},
            )
        if result.get('_status') == 'ok':
            st.success(result.get('message') or '连接正常。')
        else:
            st.error(result.get('_error') or '测试失败。')
            with st.expander('查看原始返回'):
                st.code(str(result))

    st.caption('先在这里配置，再进入训练评分、疑难会诊、自动结构化等功能。')
