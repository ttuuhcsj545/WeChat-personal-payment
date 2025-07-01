import cv2
import numpy as np
import mss
from pyzbar.pyzbar import decode

def detect_qrcode_from_screen():
    """
    截屏并检测是否包含二维码。
    如果检测到二维码，返回其内容；否则返回 False。
    :return: str | False
    """
    # 截取整个屏幕
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    # 尝试用 pyzbar 解码二维码
    decoded_objects = decode(img)

    if decoded_objects:
        # 只取第一个二维码（如有多个可遍历）
        qrcode_data = decoded_objects[0].data.decode("utf-8")
        return qrcode_data
    else:
        return False