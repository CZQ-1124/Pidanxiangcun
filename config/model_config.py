from services.runtime_config import get_runtime_config, config_status


def AI_BASE_URL() -> str:
    return get_runtime_config()['AI_BASE_URL']


def AI_API_KEY() -> str:
    return get_runtime_config()['AI_API_KEY']


def TEXT_MODEL() -> str:
    return get_runtime_config()['TEXT_MODEL']


def VISION_MODEL() -> str:
    return get_runtime_config()['VISION_MODEL']


def AUDIO_MODEL() -> str:
    return get_runtime_config()['AUDIO_MODEL']


def THINKING_MODE() -> str:
    return get_runtime_config()['THINKING_MODE']


def AI_TIMEOUT_SEC() -> int:
    try:
        return int(float(get_runtime_config()['AI_TIMEOUT_SEC']))
    except Exception:
        return 25


def ai_ready() -> bool:
    return bool(config_status()['text_ready'])


def vision_ready() -> bool:
    return bool(config_status()['vision_ready'])


def audio_ready() -> bool:
    return bool(config_status()['audio_ready'])
