from detect_qrcode_from_screen import detect_qrcode_from_screen
from WeChat_status import get_wechat_window_info
from detect_color_position import sift_match_on_screen
from color import is_color_match_at_offset
def start():
    if get_wechat_window_info():#检测微信登录状态
        zhi ,zuobiao= sift_match_on_screen("res/"small.png)
        if zhi:
            if is_color_match_at_offset(zuobiao, (210, 210, 210)): #检测是否选中
                return "001"#已选中对话框
            else:
               return "004"#未选中对话框
        else:
            return "005"#未置顶
        
    else:
        uis=detect_qrcode_from_screen()
        if uis ==False:
            zhi1 ,zuobiao1= sift_match_on_screen("res/Switch account.png")
            if zhi1:
                return "003",zuobiao1#切换账号
            else:
                return "404"#未知
        else:
            
            return "002",uis#二维码登录
# 001>已选中对话框
# 002>二维码登录
# 003>切换账号
# 004>未选中对话框
# 005>未置顶
# 404>未知
print(start())