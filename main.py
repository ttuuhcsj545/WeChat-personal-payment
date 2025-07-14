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
from PIL import Image  # noqa: F401  pillow 只是给 mss 依赖
import cv2
import easyocr

try:
    import pygetwindow as gw          # Windows/macOS 能用
except (ImportError, NotImplementedError):
    gw = None                         # Linux 走这里
# ============ 全局配置 ============
WHITELIST = set("微信收款助手切换账号当前退出登录正在进入机")
DB_PATH = Path(__file__).with_suffix(".db")
READER = easyocr.Reader(["ch_sim", "en"], gpu=False, verbose=False)
IS_WIN = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

# ============ 数据库 ============
def init_db():
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
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM status")
        conn.execute("INSERT INTO status (code, content) VALUES (?, ?)", (code, content))

# ============ 工具函数 ============
def filter_text(txt: str) -> str:
    return "".join(c for c in txt if c in WHITELIST)

def _get_wechat_window_bbox_windows(full: bool = False):
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
    parts = line.split(None, 7)
    if len(parts) < 8:
        return None
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
    try:
        out = subprocess.check_output(["wmctrl", "-lpG"], text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
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
    if IS_WIN:
        return _get_wechat_window_bbox_windows(full)
    elif IS_LINUX:
        return _get_wechat_window_bbox_linux(full)
    return None

def to_screen_coords(bbox_rel, window_bbox):
    return [
        [int(x + window_bbox["left"]), int(y + window_bbox["top"])]
        for x, y in bbox_rel
    ]

def ocr_from_wechat_corner(full: bool = False):
    bbox = get_wechat_bbox(full)
    if not bbox:
        return []
    with mss.mss() as sct:
        img = np.array(sct.grab(bbox))[:, :, :3]
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
    best, best_score = None, 0
    for item in results:
        t = item["text"]
        if t == target:
            return item
        score = SequenceMatcher(None, t, target).ratio()
        if score > best_score:
            best, best_score = item, score
    if best_score < 0.4:  # 允许模糊包含
        return next((i for i in results if target in i["text"]), None)
    return best

def get_center_from_bbox(bbox):
    xs, ys = zip(*bbox)
    return int(sum(xs) / 4), int(sum(ys) / 4)

# ============ 颜色匹配/二维码/窗口检测 ============
def is_color_match_at_offset(pt, rgb, tol=15):
    """检测屏幕某点是否接近指定颜色"""
    x, y = pt
    with mss.mss() as sct:
        grab = sct.grab({"left": x, "top": y, "width": 1, "height": 1})
        px = grab.pixel(0, 0)[:3]
    return all(abs(int(px[i]) - rgb[i]) <= tol for i in range(3))

def detect_qrcode_from_screen():
    """全屏截一次图并尝试识别二维码内容（返回 str 或 None）"""
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # 主屏
        img = np.array(sct.grab(monitor))[:, :, :3]
    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(img)
    return data if data else None

def get_wechat_window_info():
    """简易版：只判断微信窗口是否存在并可见"""
    return bool(get_wechat_bbox(full=False))

# ============ 主循环 ============
def main():
    init_db()
    print(f"✅ 监控启动 (DB={DB_PATH})，按 Ctrl-C 退出")
    while True:
        time.sleep(1)

        if get_wechat_window_info():  # 收款码界面
            texts = ocr_from_wechat_corner(full=False)
            match = find_best_match(texts, "微信收款助手")
            if match:
                first_point = match["bbox"][0]
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
            qrcode = detect_qrcode_from_screen()
            if qrcode:
                update_status("300", qrcode)      # 300：登录二维码
                print(f"✅ 检测到登录二维码：{qrcode}")
            else:
                texts = ocr_from_wechat_corner(full=True)
                if find_best_match(texts, "当前账号") and find_best_match(texts, "退出登录"):
                    update_status("200", "None")  # 200：主界面
                elif (m := find_best_match(texts, "切换账号")):
                    update_status("201", str(get_center_from_bbox(m["bbox"])))
                elif find_best_match(texts, "正在进入"):
                    update_status("202", "None")
                elif find_best_match(texts, "手机") and find_best_match(texts, "登录"):
                    update_status("203", "None")
                else:
                    update_status("900", "None")  # 900：未知界面

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n再见！")
        sys.exit(0)