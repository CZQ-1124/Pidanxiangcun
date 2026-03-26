import os
from pathlib import Path
from typing import Dict
from dotenv import load_dotenv, set_key
from config.settings import ROOT_DIR

ENV_PATH = ROOT_DIR / '.env'
load_dotenv(ENV_PATH)

DEFAULTS = {
    'AI_BASE_URL': 'https://aihubmix.com/v1',
    'AI_API_KEY': '',
    'TEXT_MODEL': 'doubao-seed-2-0-mini',
    'VISION_MODEL': 'qwen3-vl-flash',
    'AUDIO_MODEL': '',
    'THINKING_MODE': 'omit',  # omit/disabled/auto/enabled
    'AI_TIMEOUT_SEC': '25',
}


def _session_value(key: str):
    try:
        import streamlit as st
        return st.session_state.get(key)
    except Exception:
        return None


def get_runtime_config() -> Dict[str, str]:
    cfg = {}
    for key, default in DEFAULTS.items():
        cfg[key] = str(_session_value(key) or os.getenv(key, default) or default)
    return cfg


def save_runtime_config(payload: Dict[str, str]):
    ENV_PATH.touch(exist_ok=True)
    for key, default in DEFAULTS.items():
        value = str(payload.get(key, default))
        set_key(str(ENV_PATH), key, value)
        os.environ[key] = value
        try:
            import streamlit as st
            st.session_state[key] = value
        except Exception:
            pass


def config_status() -> Dict[str, str | bool]:
    cfg = get_runtime_config()
    text_ready = bool(cfg['AI_API_KEY'] and cfg['AI_BASE_URL'] and cfg['TEXT_MODEL'])
    vision_ready = bool(cfg['AI_API_KEY'] and cfg['AI_BASE_URL'] and cfg['VISION_MODEL'])
    audio_ready = bool(cfg['AI_API_KEY'] and cfg['AI_BASE_URL'] and cfg['AUDIO_MODEL'])
    return {
        **cfg,
        'text_ready': text_ready,
        'vision_ready': vision_ready,
        'audio_ready': audio_ready,
    }
