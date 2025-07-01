from match_screen_template import match_screen_template
from detect_qrcode_from_screen import detect_qrcode_from_screen
from WeChat_status import get_wechat_window_info
import os
def start():
    if get_wechat_window_info():
        is_ma1,ssc1,hhh1=match_screen_template("res/Payment box-selected.png")
        if is_ma1:
            return "001"#状态正常
        else:
            is_ma2,ssc2,hhh2=match_screen_template("res/Payment box.png")
        if is_ma2:
            return "003",ssc2#未选中
        else:
            return "404"#未知
    else:
        uis=detect_qrcode_from_screen()
        if uis ==False:
            is_ma3,ssc3,hhh3=match_screen_template("res/Switch account.png")
            if is_ma3 ==True:
                return "004",ssc3#切换账号
            else:
                return "404_1"#未知
        else:
            return "002",uis


print(start())