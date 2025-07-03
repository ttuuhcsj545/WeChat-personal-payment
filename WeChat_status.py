import sys

if sys.platform.startswith('win'):
    import pygetwindow as gw

    def get_wechat_window_info():
        windows = gw.getWindowsWithTitle('微信')
        if not windows:
            print("找不到微信窗口")
            return False
        win = windows[0]
        width, height = win.width, win.height
        return width >= 500 and height >= 500

else:
    import subprocess

    def get_wechat_window_info():
        try:
            output = subprocess.check_output(['wmctrl', '-lG']).decode('utf-8')
        except FileNotFoundError:
            print("请先安装 wmctrl: sudo apt install wmctrl")
            return False

        for line in output.splitlines():
            if '微信' in line:
                parts = line.split()
                width = int(parts[4])
                height = int(parts[5])
                return width >= 500 and height >= 500

        print("找不到微信窗口")
        return False
