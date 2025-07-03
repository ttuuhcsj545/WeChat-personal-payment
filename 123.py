import easyocr
import mss
import pygetwindow as gw
import numpy as np
from PIL import Image
import time
from WeChat_status import get_wechat_window_info
from detect_qrcode_from_screen import detect_qrcode_from_screen
from color import is_color_match_at_offset
# 初始化 OCR 模型（只初始化一次）
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=False)

# 白名单字符（仅保留需要识别的字）
whitelist = set("微信收款助手切换账号当前退出登录正在进入机")

def to_screen_coords(bbox_relative, window_bbox):
    """
    将 OCR bbox 相对截图的坐标转为屏幕绝对坐标
    参数:
        bbox_relative: OCR 返回的 bbox，比如 [[x1,y1],[x2,y2],...]
        window_bbox: 截图区域，例如 {'left': 876, 'top': 324, ...}
    返回:
        转换后的屏幕坐标 bbox
    """
    abs_bbox = []
    for point in bbox_relative:
        x, y = int(point[0]), int(point[1])  # 兼容 np.int32
        abs_x = x + window_bbox['left']
        abs_y = y + window_bbox['top']
        abs_bbox.append([abs_x, abs_y])
    return abs_bbox

def filter_text(text):
    return ''.join(c for c in text if c in whitelist)
from difflib import SequenceMatcher

def find_best_match(results, target_text):
    """
    从 OCR 结果中找到最匹配目标文字的项。
    优先级：完全匹配 > 高相似度 > 包含关系
    """
    best_item = None
    best_score = 0

    for item in results:
        text = item['text']
        
        # 完全匹配，立即返回
        if text == target_text:
            return item

        # 相似度匹配（使用 difflib）
        similarity = SequenceMatcher(None, text, target_text).ratio()

        if similarity > best_score:
            best_score = similarity
            best_item = item

    # 相似度很低，但有包含关系，也允许返回
    if best_score < 0.4:  # 可调整为相似度下限
        for item in results:
            if target_text in item['text']:
                return item
        return None

    return best_item
# 获取微信窗口左上角区域（默认 300x100，可自定义）
def get_wechat_window_corner_bbox(zhuantai):
    windows = gw.getWindowsWithTitle('微信')
    if not windows:
        print("❌ 找不到微信窗口")
        return None
    win = windows[0]
    if zhuantai:
        return {
            'top': win.top,
            'left': win.left,
            'width': win.width,
            'height': win.height,
        }
    else:
        return {
            'top': win.top,
            'left': win.left,
            'width': min(600, win.width),
            'height': min(300, win.height)
        }

def ocr_from_wechat_corner(zhuantai=False):
    bbox = get_wechat_window_corner_bbox(zhuantai)
    if not bbox:
        return []
    with mss.mss() as sct:
        sct_img = sct.grab(bbox)
        img_np = np.array(sct_img)[:, :, :3]  # 转成 RGB
        result = reader.readtext(img_np, detail=1)

        output = []
        for bbox, text, conf in result:
            filtered = filter_text(text)
            if filtered.strip():
                output.append({
                    'text': filtered,
                    'bbox': bbox,
                    'conf': conf
                })
        return output
# 主循环
while True:
    time.sleep(1)  # 每秒检测一次
    if get_wechat_window_info():  # 检测微信登录状态
        texts = ocr_from_wechat_corner()
        if find_best_match(texts, "微信收款助手") != None:
            bbox1=to_screen_coords(find_best_match(texts, "微信收款助手")["bbox"], get_wechat_window_corner_bbox(zhuantai=False))[0]
            if is_color_match_at_offset(bbox1, (210, 210, 210)):
                print("🔄 检测到：微信收款助手已选中对话框")
            else:
                print("❗ 检测到：微信收款助手未选中对话框")
        else:
            print("❗ 未检测到微信收款助手")

    else:
        if detect_qrcode_from_screen() != False: 
            qrcode=detect_qrcode_from_screen()
            print("🔄 检测到：二维码，请扫码登录",qrcode)   
        else:
            
            texts = ocr_from_wechat_corner(zhuantai=True)

            if find_best_match(texts, '当前账号') != None and find_best_match(texts, '退出登录') != None:
                print("❗ 检测到：当前账号已掉线")
            elif find_best_match(texts, '切换账号') != None:
                print("🔄 检测到：切换账号！")
            elif find_best_match(texts, '正在进入') != None:
                print("🔄 检测到：正在进入")
            elif find_best_match(texts, '手机') != None and find_best_match(texts, '登录') != None:
                print("🔄 检测到：请在手机完成登录！")
            else:
                print("❗ 未检测到微信窗口或二维码，请检查微信状态")

