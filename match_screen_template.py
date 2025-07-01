import cv2
import numpy as np
import mss
import mss.tools

def match_screen_template(template_path, threshold=0.8):
    """
    自动截屏，并在截屏中匹配模板图
    :param template_path: 模板图路径
    :param threshold: 匹配阈值（默认 0.8）
    :return: (is_match: bool, position: (x, y), similarity: float)
    """
    # 1. 读取模板图
    template = cv2.imread(template_path)
    if template is None:
        raise FileNotFoundError("模板图路径错误")

    w, h = template.shape[1], template.shape[0]

    # 2. 截取整个屏幕
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # 主屏幕（多个屏幕可调）
        screenshot = sct.grab(monitor)
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)  # 转换为 BGR 供 OpenCV 使用

    # 3. 模板匹配
    res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)

    if max_val >= threshold:
        return True, max_loc, max_val
    else:
        return False, None, max_val
    


