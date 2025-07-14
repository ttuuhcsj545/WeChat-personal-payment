#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wechat_monitor.py
跨 Windows / Linux 通用的微信收款状态识别脚本
"""
import sys
import subprocess
import platform
import time
import sqlite3
from pathlib import Path
from difflib import SequenceMatcher

import numpy as np
import mss
from PIL import Image  # noqa: F401  pillow只是给mss依赖，不需要直接使用
import cv2
import easyocr
from pyzbar.pyzbar import decode # 用于二维码检测

try:
    import pygetwindow as gw          # Windows/macOS能用
except (ImportError, NotImplementedError):
    gw = None                         # Linux走这里

# ============ 全局配置 ============
WHITELIST = set("微信收款助手切换账号当前退出登录正在进入机")
DB_PATH = Path(__file__).with_suffix(".db")
# 初始化 EasyOCR Reader，指定中文和英文，不使用GPU，关闭详细输出
READER = easyocr.Reader(["ch_sim", "en"], gpu=False, verbose=False)
IS_WIN = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

# ============ 数据库 ============
def init_db():
    """
    初始化SQLite数据库，创建status表（如果不存在）。
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS status (
                code TEXT PRIMARY KEY,
                content TEXT
            )
            """
        )

def update_status(code: str, content: str):
    """
    更新数据库中的状态码和内容。
    每次只保留最新状态。
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM status") # 删除现有状态
        conn.execute("INSERT INTO status (code, content) VALUES (?, ?)", (code, content)) # 插入新状态

# ============ 工具函数 ============
def filter_text(txt: str) -> str:
    """
    过滤OCR识别的文本，只保留在白名单中的字符。
    """
    return "".join(c for c in txt if c in WHITELIST)

def _get_wechat_window_bbox_windows(full: bool = False):
    """
    获取Windows环境下微信窗口的边界框信息。
    参数:
        full: 如果为True，返回完整的窗口尺寸；否则限制宽度和高度。
    返回:
        包含top, left, width, height的字典，如果未找到窗口则返回None。
    """
    if gw is None:
        return None
    wins = gw.getWindowsWithTitle("微信")
    if not wins:
        return None
    w = wins[0]
    return {
        "top": w.top,
        "left": w.left,
        "width": w.width if full else min(600, w.width),
        "height": w.height if full else min(300, w.height),
    }

def _parse_wmctrl_line(line: str):
    """
    解析wmctrl命令输出的单行，提取窗口信息。
    """
    # 示例行: 0x01a00003  0 2038   0 1920 1080 localhost 微信
    parts = line.split(None, 7)
    if len(parts) < 8:
        return None
    # 提取并转换相关部分为整数
    wid, _, _, x, y, w, h, title = (
        parts[0],
        parts[1],
        parts[2],
        int(parts[3]),
        int(parts[4]),
        int(parts[5]),
        int(parts[6]),
        parts[7],
    )
    return {"wid": wid, "x": x, "y": y, "w": w, "h": h, "title": title}

def _get_wechat_window_bbox_linux(full: bool = False):
    """
    获取Linux环境下微信窗口的边界框信息。
    参数:
        full: 如果为True，返回完整的窗口尺寸；否则限制宽度和高度。
    返回:
        包含top, left, width, height的字典，如果未找到窗口则返回None。
    """
    try:
        # 使用 -lpG 获取进程ID、几何信息和窗口标题
        out = subprocess.check_output(["wmctrl", "-lpG"], text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("请先安装 wmctrl: sudo apt install wmctrl", file=sys.stderr)
        return None
    for line in out.splitlines():
        info = _parse_wmctrl_line(line)
        if info and "微信" in info["title"]:
            return {
                "top": info["y"],
                "left": info["x"],
                "width": info["w"] if full else min(600, info["w"]),
                "height": info["h"] if full else min(300, info["h"]),
            }
    return None

def get_wechat_bbox(full: bool = False):
    """
    根据操作系统获取微信窗口的边界框信息。
    """
    if IS_WIN:
        return _get_wechat_window_bbox_windows(full)
    elif IS_LINUX:
        return _get_wechat_window_bbox_linux(full)
    return None

def to_screen_coords(bbox_rel, window_bbox):
    """
    将相对窗口的坐标转换为屏幕绝对坐标。
    """
    return [
        [int(x + window_bbox["left"]), int(y + window_bbox["top"])]
        for x, y in bbox_rel
    ]

def ocr_from_wechat_corner(full: bool = False):
    """
    从微信窗口的某个区域进行OCR识别。
    参数:
        full: 如果为True，OCR整个捕获区域；否则根据get_wechat_bbox限制。
    返回:
        识别到的文本及其边界框和置信度列表。
    """
    bbox = get_wechat_bbox(full)
    if not bbox:
        return []
    with mss.mss() as sct:
        # 截取微信窗口的指定区域
        img = np.array(sct.grab(bbox))[:, :, :3]
    # 使用EasyOCR进行文本识别
    res = READER.readtext(img, detail=1)
    out = []
    for bbox_rel, text, conf in res:
        filtered = filter_text(text)
        if filtered.strip():
            out.append(
                {"text": filtered, "bbox": to_screen_coords(bbox_rel, bbox), "conf": conf}
            )
    return out

def find_best_match(results, target: str):
    """
    在OCR结果中找到与目标字符串最匹配的项。
    使用SequenceMatcher进行模糊匹配，也支持模糊包含。
    """
    best, best_score = None, 0
    for item in results:
        t = item["text"]
        if t == target: # 精确匹配优先
            return item
        score = SequenceMatcher(None, t, target).ratio()
        if score > best_score:
            best, best_score = item, score
    if best_score < 0.4:  # 如果最佳匹配分数过低，尝试模糊包含
        return next((i for i in results if target in i["text"]), None)
    return best

def get_center_from_bbox(bbox):
    """
    从OCR结果的边界框中计算中心点坐标。
    """
    xs, ys = zip(*bbox)
    return int(sum(xs) / 4), int(sum(ys) / 4)

# ============ 颜色匹配 (来源于 color.py) ============
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
        是否匹配 (True/False)
    """
    x, y = origin
    new_x = x + offset_x
    new_y = y + offset_y

    # 截取目标像素点区域 (1x1)
    with mss.mss() as sct:
        monitor = {"left": new_x, "top": new_y, "width": 1, "height": 1}
        # 确保 grab 返回的 numpy 数组至少有3个通道 (RGB)
        img = np.array(sct.grab(monitor))[:, :, :3]

    pixel = img[0, 0]  # 获取这个点的颜色

    # 计算颜色差
    diff = np.abs(pixel.astype(int) - np.array(target_color)).max()
    matched = diff <= tolerance

    # print(f"实际颜色: {pixel}, 目标颜色: {target_color}, 差值: {diff}, 匹配: {matched}")
    return matched

# ============ 二维码检测 (来源于 detect_qrcode_from_screen.py) ============
def detect_qrcode_from_screen():
    """
    截屏并检测是否包含二维码。
    如果检测到二维码，返回其内容；否则返回 False。
   
    :return: str | False
    """
    # 截取整个屏幕
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # 假设monitor 1是主屏幕
        screenshot = sct.grab(monitor)
        img = np.array(screenshot)
        # 将 BGRA (mss默认) 转换为 BGR (OpenCV处理所需)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    # 尝试用 pyzbar 解码二维码
    decoded_objects = decode(img)

    if decoded_objects:
        # 返回找到的第一个二维码的内容
        qrcode_data = decoded_objects[0].data.decode("utf-8")
        return qrcode_data
    else:
        return False

# ============ 微信窗口检测 (融合 WeChat_status.py 和 main.py) ============
def get_wechat_window_info():
    """
    简易版：只判断微信窗口是否存在并可见，并检查是否达到最小尺寸。
    """
    bbox = get_wechat_bbox(full=True) # 使用完整尺寸来检查最小尺寸要求
    if not bbox:
        print("找不到微信窗口", file=sys.stderr) # Original message from WeChat_status.py
        return False
    # 检查宽度和高度是否至少为500
    return bbox['width'] >= 500 and bbox['height'] >= 500


# ============ 主循环 ============
def main():
    init_db()
    print(f"✅ 监控启动 (DB={DB_PATH})，按 Ctrl-C 退出")
    while True:
        time.sleep(1)

        if get_wechat_window_info():  # 判断是否为微信窗口且符合基本尺寸
            texts = ocr_from_wechat_corner(full=False)
            match = find_best_match(texts, "微信收款助手")
            if match:
                first_point = match["bbox"][0]
                # 使用从 color.py 整合过来的 is_color_match_at_offset
                if is_color_match_at_offset(first_point, (210, 210, 210)):
                    update_status("100", "None")  # 100：正常收款码
                    print("✅ 收款码界面正常")
                else:
                    update_status("101", str(get_center_from_bbox(match["bbox"])))
                    print("⚠️ 收款码界面异常，可能未加载完成")
            else:
                update_status("102", "None")      # 102：收款码界面但未找到标题
                print("⚠️ 收款码界面异常，未找到标题")
        else:  # 不是收款码界面
            # 使用从 detect_qrcode_from_screen.py 整合过来的 detect_qrcode_from_screen
            qrcode = detect_qrcode_from_screen()
            if qrcode:
                update_status("300", qrcode)      # 300：登录二维码
                print(f"✅ 检测到登录二维码：{qrcode}")
            else:
                texts = ocr_from_wechat_corner(full=True)
                if find_best_match(texts, "当前账号") and find_best_match(texts, "退出登录"):
                    update_status("200", "None")  # 200：主界面
                    print("✅ 检测到微信主界面")
                elif (m := find_best_match(texts, "切换账号")):
                    update_status("201", str(get_center_from_bbox(m["bbox"])))
                    print("✅ 检测到切换账号界面")
                elif find_best_match(texts, "正在进入"):
                    update_status("202", "None")
                    print("✅ 检测到正在进入界面")
                elif find_best_match(texts, "手机") and find_best_match(texts, "登录"):
                    update_status("203", "None")
                    print("✅ 检测到手机登录界面")
                else:
                    update_status("900", "None")  # 900：未知界面
                    print("❓ 检测到未知界面")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n再见！")
        sys.exit(0)