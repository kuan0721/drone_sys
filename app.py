# -*- coding: utf-8 -*-
from flask import Flask, jsonify, render_template
import json
import os
import subprocess
import time

# ------------------------------------------------------------------
# 範例作法：啟動 web_data.py（負責訂閱 MQTT 並寫入 drone_data.json）
# ------------------------------------------------------------------
socket_server_process = subprocess.Popen(["python3", "web_data.py"])
# 等待 web_data.py 啟動、連上 MQTT，以及開始寫入 drone_data.json
time.sleep(2)

app = Flask(__name__)
DATA_FILE = 'drone_data.json'

# 若資料檔不存在，就先建立一個空的 JSON 檔
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump({}, f)


def load_data():
    """
    從 drone_data.json 讀取最新一筆資料並回傳 dict
    如果檔案格式錯誤或空白，就回傳空 dict
    """
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


@app.route("/")
def index():
    """
    根目錄顯示 index.html（假設你有對應的前端頁面）
    """
    return render_template("index.html")


@app.route("/get_flight_mode")
def get_flight_mode():
    """
    回傳目前的飛行模式（flight_mode 字串）
    如果不存在，回傳 "unknown"
    """
    data = load_data()
    mode = data.get("flight_mode", "unknown")
    return jsonify({"flight_mode": mode})


@app.route("/get_arming_status")
def get_arming_status():
    """
    回傳目前的解鎖/綁定狀態（arm_status 字串）
    如果不存在，回傳 "unknown"
    """
    data = load_data()
    status = data.get("arm_status", "unknown")
    return jsonify({"arm_status": status})


@app.route("/get_speed")
def get_speed():
    """
    回傳目前的飛行速度（speed，單位 m/s）
    如果不存在，回傳 0.0
    """
    data = load_data()
    speed = data.get("speed", 0.0)
    return jsonify({"speed": speed})


@app.route("/get_altitude")
def get_altitude():
    """
    回傳目前的高度（altitude，單位 m）
    如果不存在，回傳 0.0
    """
    data = load_data()
    altitude = data.get("altitude", 0.0)
    return jsonify({"altitude": altitude})


@app.route("/get_battery")
def get_battery():
    """
    回傳電池資訊：volt (V)、current (A)、battery_percent (%)
    如果不存在，所有欄位都回傳 0
    """
    data = load_data()
    batt = data.get("battery", {})
    return jsonify({
        "volt": batt.get("volt", 0.0),
        "current": batt.get("current", 0.0),
        "battery_percent": batt.get("battery_percent", 0)
    })


@app.route("/get_rtk_status")
def get_rtk_status():
    """
    回傳 RTK 定位狀態（rtk_status 字串），可能值如 "fixed", "floated", "no RTK", "unknown"
    如果不存在，回傳 "unknown"
    """
    data = load_data()
    status = data.get("rtk_status", "unknown")
    return jsonify({"rtk_status": status})


@app.route("/get_drone_position")
def get_drone_position():
    """
    回傳目前緯度/經度：lat (-90~90), lon (-180~180)
    如果不存在，lat 與 lon 都回傳 0.0
    """
    data = load_data()
    gps = data.get("gps_position", {})
    return jsonify({
        "lat": gps.get("lat", 0.0),
        "lon": gps.get("lon", 0.0)
    })


@app.route("/get_drone_orientation")
def get_drone_orientation():
    """
    回傳目前姿態：pitch (度)、yaw (度)、roll (度)
    如果不存在，皆回傳 0.0
    """
    data = load_data()
    att = data.get("attitude", {})
    return jsonify({
        "pitch": att.get("pitch", 0.0),
        "yaw": att.get("yaw", 0.0),
        "roll": att.get("roll", 0.0)
    })


@app.route("/get_charge_data")
def get_charge_data():
    """
    回傳充電相關資訊（與 battery 類似，但放在 charge_data 內）
    包含：voltage (V)、current (A)、battery_percent (%)
    如果不存在，所有欄位都回傳 0
    """
    data = load_data()
    charge = data.get("charge_data", {})
    return jsonify({
        "voltage": charge.get("voltage", 0.0),
        "current": charge.get("current", 0.0),
        "battery_percent": charge.get("battery_percent", 0)
    })


if __name__ == "__main__":
    # 偵錯模式開啟，host 設為 0.0.0.0 代表可從外部存取
    app.run(host='0.0.0.0', port=5000, debug=True)
