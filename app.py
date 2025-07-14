from flask import Flask, render_template_string, request, jsonify
import sqlite3
import qrcode
import io
import base64
import pyautogui
import ast

app = Flask(__name__)

# 状态码定义
wechat_states = {
    100: {"key": "dialog_selected", "desc": "✅ 微信收款助手对话框已选中"},
    101: {"key": "dialog_not_selected", "desc": "⚠️ 微信收款助手未选中"},
    102: {"key": "no_wechat_assistant", "desc": "⚠️ 未检测到微信收款助手"},

    200: {"key": "account_logged_out", "desc": "❌ 当前账号已掉线"},
    201: {"key": "switching_account", "desc": "🔄 正在切换账号"},
    202: {"key": "logging_in", "desc": "🔄 正在进入微信"},
    203: {"key": "mobile_login_required", "desc": "📱 请在手机完成登录"},

    300: {"key": "qrcode_detected", "desc": "🔄 二维码识别成功，等待扫码"},

    900: {"key": "no_window_or_qrcode", "desc": "❗ 未检测到微信窗口或二维码"},
    901: {"key": "unknown", "desc": "❓ 未知状态"}
}

DB_PATH = 'status.db'

def get_latest_status():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT code, content FROM status LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    if row:
        return int(row[0]), row[1]
    return None, None

def generate_qrcode_base64(data):
    qr = qrcode.QRCode(box_size=6, border=1)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()

def click_coord(x, y):
    try:
        pyautogui.moveTo(x, y, duration=0.2)
        pyautogui.click()
        print(f"🖱️ 已点击坐标: ({x}, {y})")
    except Exception as e:
        print(f"❌ 点击失败: {e}")

@app.route('/')
def index():
    code, content = get_latest_status()
    if code is None:
        return "❌ 暂无状态数据"

    state_info = wechat_states.get(code, wechat_states[901])

    show_button = False
    show_qrcode = False
    qrcode_img = None
    coord = None

    if content != "None":
        if "http" in content.lower():
            show_qrcode = True
            qrcode_img = generate_qrcode_base64(content)
        else:
            try:
                coord = ast.literal_eval(content)
                if isinstance(coord, (list, tuple)) and len(coord) == 2 and all(isinstance(i, int) for i in coord):
                    coord = list(coord)
                    show_button = True
            except:
                coord = None

    html = '''
    <html>
    <head>
        <title>微信状态监控</title>
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    </head>
    <body>
        <h2>状态代码: {{ code }} | Key: {{ state_info.key }}</h2>
        <p>描述: {{ state_info.desc }}</p>

        {% if show_qrcode %}
            <h3>二维码内容:</h3>
            <img src="data:image/png;base64,{{ qrcode_img }}" alt="二维码"/>
        {% elif show_button %}
            <h3>点击按钮:</h3>
            <button id="click_btn">点击坐标 {{ coord }}</button>
            <p id="click_result"></p>
            <script>
                $('#click_btn').click(function(){
                    $.post('/click', {x: {{ coord[0] }}, y: {{ coord[1] }}}, function(data){
                        $('#click_result').text(data.message);
                    });
                });
            </script>
        {% else %}
            <p>内容: {{ content }}</p>
        {% endif %}
    </body>
    </html>
    '''

    return render_template_string(html,
                                  code=code,
                                  state_info=state_info,
                                  content=content,
                                  show_button=show_button,
                                  show_qrcode=show_qrcode,
                                  qrcode_img=qrcode_img,
                                  coord=coord)

@app.route('/click', methods=['POST'])
def click():
    try:
        x = int(request.form.get('x'))
        y = int(request.form.get('y'))
        click_coord(x, y)
        return jsonify({"message": f"✅ 已点击坐标 ({x}, {y})"})
    except Exception as e:
        return jsonify({"message": f"❌ 点击失败: {e}"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)