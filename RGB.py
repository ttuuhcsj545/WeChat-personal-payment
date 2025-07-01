import cv2
import numpy as np
import mss

def find_color_near_color(
    color_a, color_b, region=None, tolerance=20, expand=None, expand_direction='all'
):
    
    
    """
    找颜色A，找到后在颜色A周边指定方向扩散范围找颜色B。

    参数:
        color_a: (R,G,B) 颜色A
        color_b: (R,G,B) 颜色B
        region: 截图区域 (x,y,w,h)，None=全屏
        tolerance: 颜色容差
        expand: 扩散像素数，None表示不扩散
        expand_direction: 扩散方向，'all'(默认)、'left'、'right'、'up'、'down'

    返回:
        (pos_a, pos_b) 或 False
    """

    with mss.mss() as sct:
        if region is None:
            mon = sct.monitors[1]
            region = (mon["left"], mon["top"], mon["width"], mon["height"])

        img = np.array(sct.grab({
            "left": region[0],
            "top": region[1],
            "width": region[2],
            "height": region[3]
        }))[:, :, :3]

    def in_range_mask(img, color, tol):
        lower = np.clip(np.array(color) - tol, 0, 255)
        upper = np.clip(np.array(color) + tol, 0, 255)
        return cv2.inRange(img, lower, upper)

    mask_a = in_range_mask(img, color_a, tolerance)
    coords_a = cv2.findNonZero(mask_a)
    if coords_a is None:
        return False

    for pt_a in coords_a:
        x_a, y_a = pt_a[0]
        abs_a = (region[0] + x_a, region[1] + y_a)

        if expand is None:
            # 不扩散，只检测颜色A处是否为颜色B
            pixel_color = img[y_a, x_a]
            diff = np.abs(pixel_color.astype(int) - np.array(color_b)).max()
            if diff <= tolerance:
                abs_b = abs_a
                return abs_a, abs_b
        else:
            # 根据方向计算扩散区域边界
            left = x_a - expand if expand_direction in ['all', 'left'] else x_a
            right = x_a + expand if expand_direction in ['all', 'right'] else x_a
            top = y_a - expand if expand_direction in ['all', 'up'] else y_a
            bottom = y_a + expand if expand_direction in ['all', 'down'] else y_a

            # 限制边界在图像内
            left = max(left, 0)
            right = min(right, region[2] - 1)
            top = max(top, 0)
            bottom = min(bottom, region[3] - 1)

            sub_img = img[top:bottom+1, left:right+1, :]
            mask_b = in_range_mask(sub_img, color_b, tolerance)
            coords_b = cv2.findNonZero(mask_b)
            if coords_b is not None:
                x_b, y_b = coords_b[0][0]
                abs_b = (region[0] + left + x_b, region[1] + top + y_b)
                return abs_a, abs_b

    return False

# 扩散20像素找颜色B
res = find_color_near_color((0,175,229), (210,210,210), expand=None,expand_direction="left")
print(res)
