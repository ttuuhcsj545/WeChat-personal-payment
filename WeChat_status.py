import pygetwindow as gw

def get_wechat_window_info():
    windows = gw.getWindowsWithTitle('微信')
    if not windows:
        print("找不到微信窗口")
        return None
    win = windows[0]  # 取第一个匹配窗口
    info = {
        'title': win.title,
        'left': win.left,
        'top': win.top,
        'width': win.width,
        'height': win.height
    }
    return win.width>=500 and win.height>=500
