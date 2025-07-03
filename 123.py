import easyocr
import mss
import pygetwindow as gw
import numpy as np
from PIL import Image
import time
from WeChat_status import get_wechat_window_info
from detect_qrcode_from_screen import detect_qrcode_from_screen
from color import is_color_match_at_offset
from difflib import SequenceMatcher

# 初始化 OCR 模型（只初始化一次）
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=False)

# 白名单字符（仅保留需要识别的字）
whitelist = set("微信收款助手切换账号当前退出登录正在进入机")

def filter_text(text):
    return ''.join(c for c in text if c in whitelist)

def to_screen_coords(bbox_relative, window_bbox):
    """将 OCR bbox 相对截图坐标转为屏幕绝对坐标"""
    return [[int(x + window_bbox['left']), int(y + window_bbox['top'])] for x, y in bbox_relative]

def get_center(bbox):
    """获取四点 bbox 中心点坐标"""
    x = sum(p[0] for p in bbox) / 4
    y = sum(p[1] for p in bbox) / 4
    return int(x), int(y)

def find_best_match(results, target_text):
    """从 OCR 结果中找到最匹配的目标文字"""
    best_item = None
    best_score = 0
    for item in results:
        text = item['text']
        if text == target_text:
            return item
        similarity = SequenceMatcher(None, text, target_text).ratio()
        if similarity > best_score:
            best_score = similarity
            best_item = item
    if best_score < 0.4:
        for item in results:
            if target_text in item['text']:
                return item
        return None
    return best_item

def get_wechat_window_corner_bbox(full=False):
    """获取微信窗口的左上角区域或整个窗口"""
    windows = gw.getWindowsWithTitle('微信')
    if not windows:
        print("❌ 找不到微信窗口")
        return None
    win = windows[0]
    return {
        'top': win.top,
        'left': win.left,
        'width': win.width if full else min(600, win.width),
        'height': win.height if full else min(300, win.height)
    }

def ocr_from_wechat_corner(full=False):
    """OCR 从微信窗口截图中识别文字"""
    bbox = get_wechat_window_corner_bbox(full)
    if not bbox:
        return []
    with mss.mss() as sct:
        sct_img = sct.grab(bbox)
        img_np = np.array(sct_img)[:, :, :3]
        result = reader.readtext(img_np, detail=1)
        output = []
        for bbox_rel, text, conf in result:
            filtered = filter_text(text)
            if filtered.strip():
                output.append({
                    'text': filtered,
                    'bbox': to_screen_coords(bbox_rel, bbox),
                    'conf': conf
                })
        return output

# 主循环
while True:
    time.sleep(1)  # 每秒检查一次

    if get_wechat_window_info():
        texts = ocr_from_wechat_corner(full=False)
        match = find_best_match(texts, "微信收款助手")
        if match:
            first_point = match['bbox'][0]
            if is_color_match_at_offset(first_point, (210, 210, 210)):
                print("🔄 检测到：微信收款助手已选中对话框")
            else:
                print("❗ 检测到：微信收款助手未选中对话框")
        else:
            print("❗ 未检测到微信收款助手")

    else:
        qrcode = detect_qrcode_from_screen()
        if qrcode:
            print("🔄 检测到：二维码，请扫码登录", qrcode)
        else:
            texts = ocr_from_wechat_corner(full=True)

            if find_best_match(texts, '当前账号') and find_best_match(texts, '退出登录'):
                print("❗ 检测到：当前账号已掉线")
            elif find_best_match(texts, '切换账号'):
                print("🔄 检测到：切换账号！")
            elif find_best_match(texts, '正在进入'):
                print("🔄 检测到：正在进入")
            elif find_best_match(texts, '手机') and find_best_match(texts, '登录'):
                print("🔄 检测到：请在手机完成登录！")
            else:
                print("❗ 未检测到微信窗口或二维码，请检查微信状态")