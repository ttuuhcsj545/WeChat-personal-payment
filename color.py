import mss
import numpy as np

def is_color_match_at_offset(
    origin, target_color, tolerance=10, offset_x=-2, offset_y=-2
):
    """
    在给定坐标基础上移动偏移后，对该位置像素与目标颜色进行模糊匹配。

    参数:
        origin: 原始坐标 (x, y)
        target_color: 要匹配的颜色 (R, G, B)
        tolerance: 允许误差（最大色差）
        offset_x: 水平方向偏移（负值为向左）
        offset_y: 垂直方向偏移（负值为向上）

    返回:
        是否匹配 (True/False)，和偏移后坐标
    """
    x, y = origin
    new_x = x + offset_x
    new_y = y + offset_y

    # 截取目标像素点区域 (1x1)
    with mss.mss() as sct:
        monitor = {"left": new_x, "top": new_y, "width": 1, "height": 1}
        img = np.array(sct.grab(monitor))[:, :, :3]  # 只取 RGB

    pixel = img[0, 0]  # 只取这个点的颜色

    # 计算颜色差
    diff = np.abs(pixel.astype(int) - np.array(target_color)).max()
    matched = diff <= tolerance

    # print(f"实际颜色: {pixel}, 目标颜色: {target_color}, 差值: {diff}, 匹配: {matched}")
    return matched