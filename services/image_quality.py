from PIL import Image
import numpy as np

def check_image_quality(image_path: str) -> dict:
    img = Image.open(image_path).convert("L")
    arr = np.array(img)
    h, w = arr.shape
    brightness = float(arr.mean())
    sharpness = float(np.abs(np.diff(arr, axis=0)).mean() + np.abs(np.diff(arr, axis=1)).mean()) / 2
    problems = []
    if w < 512 or h < 512:
        problems.append("分辨率偏低")
    if brightness < 35:
        problems.append("图像过暗")
    if brightness > 225:
        problems.append("图像过曝")
    if sharpness < 6:
        problems.append("图像可能模糊")
    quality_ok = len(problems) == 0
    return {
        "image_quality": "合格" if quality_ok else "需复拍",
        "quality_ok": quality_ok,
        "quality_message": "图像质量基本合格" if quality_ok else "；".join(problems) + "，建议重拍并让皮损占画面主体"
    }
