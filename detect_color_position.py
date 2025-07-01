import cv2
import numpy as np
import mss
def get_top_left_quadrant():
    import mss
    monitor = mss.mss().monitors[1]  # 主屏幕
    w = monitor['width']
    h = monitor['height']
    return (0, 0, w // 2, h // 2)  # (left, top, width, height)
def detect_color_position(target_color, region=None, tolerance=5):
    """
    检测屏幕或指定区域内是否存在指定颜色。

    参数:
        target_color: (R, G, B) 要检测的颜色
        region: (x, y, w, h) 指定区域，若为 None 则使用整个屏幕
        tolerance: 颜色容差（默认 ±20）

    返回:
        若检测到，返回 (x, y) 屏幕绝对坐标
        否则返回 False
    """
    with mss.mss() as sct:
        # 使用整个屏幕
        if region is None:
            monitor = sct.monitors[1]  # 第一个是所有屏幕的合并区域，第1号是主屏幕
            region = (monitor["left"], monitor["top"], monitor["width"], monitor["height"])
        
        # 截图
        screenshot = np.array(sct.grab({
            "left": region[0],
            "top": region[1],
            "width": region[2],
            "height": region[3]
        }))[:, :, :3]  # RGB

    lower = np.array([max(c - tolerance, 0) for c in target_color])
    upper = np.array([min(c + tolerance, 255) for c in target_color])
    
    mask = cv2.inRange(screenshot, lower, upper)
    coords = cv2.findNonZero(mask)
    print("匹配像素数：", len(coords) if coords is not None else 0)

    if coords is not None:
        pt = coords[0][0]  # 第一个匹配点
        abs_x = region[0] + pt[0]
        abs_y = region[1] + pt[1]
        return (abs_x, abs_y)
    else:
        return False
aaa=(9,196,250)
print(detect_color_position(aaa,get_top_left_quadrant()))
