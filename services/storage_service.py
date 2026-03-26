from pathlib import Path
from services.utils import build_image_filename, build_audio_filename, ensure_dirs
from config.settings import UPLOAD_IMAGE_DIR, UPLOAD_AUDIO_DIR

def save_uploaded_image(file_obj, person_name: str, role_name: str, body_part: str, visit_kind: str) -> str:
    ensure_dirs()
    suffix = Path(file_obj.name).suffix or ".jpg"
    filename = build_image_filename(person_name, role_name, body_part, visit_kind, suffix)
    dest = UPLOAD_IMAGE_DIR / filename
    dest.write_bytes(file_obj.getvalue())
    return str(dest)

def save_uploaded_audio(file_obj, person_name: str, role_name: str, visit_type: str) -> str:
    ensure_dirs()
    suffix = Path(file_obj.name).suffix or ".wav"
    filename = build_audio_filename(person_name, role_name, visit_type, suffix)
    dest = UPLOAD_AUDIO_DIR / filename
    dest.write_bytes(file_obj.getvalue())
    return str(dest)
