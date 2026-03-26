import re
from pathlib import Path
from datetime import datetime
from config.settings import UPLOAD_IMAGE_DIR, UPLOAD_AUDIO_DIR, IMAGES_DIR, ROOT_DIR


def slugify_cn(value: str) -> str:
    value = str(value or '').strip()
    value = re.sub(r'[^\w\u4e00-\u9fff-]+', '_', value)
    value = re.sub(r'_+', '_', value).strip('_')
    return value or 'unknown'


def build_image_filename(person_name: str, role_name: str, body_part: str, visit_kind: str, suffix: str) -> str:
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    suffix = suffix.lower() if str(suffix).startswith('.') else f'.{str(suffix).lower()}'
    return f"{slugify_cn(person_name)}_{slugify_cn(role_name)}_{slugify_cn(body_part)}_{slugify_cn(visit_kind)}_{ts}{suffix}"


def build_audio_filename(person_name: str, role_name: str, visit_type: str, suffix: str) -> str:
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    suffix = suffix.lower() if str(suffix).startswith('.') else f'.{str(suffix).lower()}'
    return f"{slugify_cn(person_name)}_{slugify_cn(role_name)}_{slugify_cn(visit_type)}_audio_{ts}{suffix}"


def ensure_dirs():
    UPLOAD_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def resolve_image_path(relative_path: str | None = None, file_name: str | None = None) -> Path | None:
    candidates: list[Path] = []
    raw_paths = [p for p in [relative_path, file_name] if p]
    for raw in raw_paths:
        s = str(raw).strip().replace('\\', '/')
        s = re.sub(r'^\./', '', s)
        if s.startswith('images/'):
            s = s[len('images/'):]
        candidates.extend([
            IMAGES_DIR / s,
            ROOT_DIR / s,
            IMAGES_DIR / Path(s).name,
        ])
    seen = set()
    deduped = []
    for p in candidates:
        key = str(p)
        if key not in seen:
            deduped.append(p)
            seen.add(key)
    for p in deduped:
        if p.exists():
            return p
    return deduped[0] if deduped else None
