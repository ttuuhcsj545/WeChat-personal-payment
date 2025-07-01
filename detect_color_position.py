import cv2
import numpy as np
import mss

def sift_match_on_screen(template_path, min_match_count=50, tolerance=0.75):
    # 读取小图（模板）
    img_template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if img_template is None:
        return None,None

    # 获取屏幕截图
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # 全屏
        screenshot = np.array(sct.grab(monitor))[:, :, :3]
        img_screen = cv2.cvtColor(screenshot, cv2.COLOR_RGB2GRAY)

    # 初始化 SIFT
    sift = cv2.SIFT_create()

    # 检测关键点和描述符
    kp1, des1 = sift.detectAndCompute(img_template, None)
    kp2, des2 = sift.detectAndCompute(img_screen, None)

    if des1 is None or des2 is None:
        return None,None

    # BF + KNN + Ratio Test
    bf = cv2.BFMatcher()
    matches = bf.knnMatch(des1, des2, k=2)

    good = []
    for m, n in matches:
        if m.distance < tolerance * n.distance:
            good.append(m)

    if len(good) >= min_match_count:
        # 获取匹配点坐标
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

        # 计算单应性矩阵
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

        if M is not None:
            h, w = img_template.shape
            pts = np.float32([[0,0],[w,0],[w,h],[0,h]]).reshape(-1,1,2)
            dst = cv2.perspectiveTransform(pts, M)

            # 获取四个角坐标（返回整数）
            corners = [(int(p[0][0]), int(p[0][1])) for p in dst]
            return True , corners[0] 
           
        else:
        
            return None,None
    else:
        return None,None

# 调用
# coords,qwe = sift_match_on_screen("res/small.png")
# print(coords)
# print(qwe)
