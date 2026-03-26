from pathlib import Path

APP_NAME = "皮蛋乡村系统"
ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "data" / "cases.db"
SEED_XLSX = ROOT_DIR / "data" / "seed_case_library.xlsx"
SEED_CSV = ROOT_DIR / "data" / "seed_case_library.csv"
IMAGES_DIR = ROOT_DIR / "images"
UPLOAD_IMAGE_DIR = ROOT_DIR / "uploads" / "images"
UPLOAD_AUDIO_DIR = ROOT_DIR / "uploads" / "audio"
DATE_FMT = "%Y-%m-%d %H:%M:%S"

RISK_SCORE_MAP = {"低风险": 1, "中风险": 2, "高风险": 3, "待复拍": 0, "紧急": 3}
