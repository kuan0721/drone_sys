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
time.sleep(2)

app = Flask(__name__)
DATA_FILE = 'drone_data.json'
CHARGING_FILE = 'charging_history.json'

# 若資料檔不存在，就先建立一個空的 JSON 檔
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump({}, f)

def load_data():
    """從 drone_data.json 讀取最新一筆資料並回傳 dict"""
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def load_charging_data():
    """載入充電歷程數據"""
    try:
        with open(CHARGING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_flight_mode")
def get_flight_mode():
    data = load_data()
    mode = data.get("flight_mode", "unknown")
    return jsonify({"flight_mode": mode})

@app.route("/get_arming_status")
def get_arming_status():
    data = load_data()
    status = data.get("arm_status", "unknown")
    return jsonify({"arm_status": status})

@app.route("/get_speed")
def get_speed():
    data = load_data()
    speed = data.get("speed", 0.0)
    return jsonify({"speed": speed})

@app.route("/get_altitude")
def get_altitude():
    data = load_data()
    altitude = data.get("altitude", 0.0)
    return jsonify({"altitude": altitude})

@app.route("/get_battery")
def get_battery():
    data = load_data()
    batt = data.get("battery", {})
    volt = batt.get("volt", 0.0)
    min_v, max_v = 14.8, 16.8

    # 用volt換算battery_percent
    if volt is not None:
        percent = (volt - min_v) / (max_v - min_v) * 100
        percent = max(0, min(100, percent))
        percent = round(percent, 1)
    else:
        percent = 0

    return jsonify({
        "volt": volt,
        "current": batt.get("current", 0.0),
        "battery_percent": percent,
        "battery_present": batt.get("battery_present", False)
    })




@app.route("/get_rtk_status")
def get_rtk_status():
    data = load_data()
    status = data.get("rtk_status", "unknown")
    return jsonify({"rtk_status": status})

@app.route("/get_drone_position")
def get_drone_position():
    data = load_data()
    gps = data.get("gps_position", {})
    return jsonify({
        "lat": gps.get("lat", 0.0),
        "lon": gps.get("lon", 0.0)
    })

@app.route("/get_drone_orientation")
def get_drone_orientation():
    data = load_data()
    att = data.get("attitude", {})
    return jsonify({
        "pitch": att.get("pitch", 0.0),
        "yaw": att.get("yaw", 0.0),
        "roll": att.get("roll", 0.0)
    })

@app.route("/get_charge_data")
def get_charge_data():
    """回傳當前電池充電狀態"""
    data = load_data()
    batt = data.get("battery", {})
    
    # 計算充電百分比（假設14V=0%, 16.8V=100%）
    voltage = batt.get("volt", 0.0)
    if voltage > 0:
        charge_percent = max(0, min(100, (voltage - 14.0) / (16.8 - 14.0) * 100))
    else:
        charge_percent = 0
    
    return jsonify({
        "voltage": voltage,
        "current": batt.get("current", 0.0),
        "battery_percent": round(charge_percent, 1)
    })

@app.route("/get_charging_history")
def get_charging_history():
    """回傳完整充電歷程"""
    charging_data = load_charging_data()
    return jsonify({
        "charging_sessions": charging_data,
        "total_sessions": len(charging_data)
    })

@app.route("/get_latest_charging_curve")
def get_latest_charging_curve():
    """回傳最新一次充電曲線數據，用於圖表顯示"""
    charging_data = load_charging_data()
    
    if not charging_data:
        return jsonify({
            "labels": [],
            "data": [],
            "session_info": None
        })
    
    # 取得最新的充電會話
    latest_session = charging_data[-1]
    charging_curve = latest_session.get('charging_curve', [])
    
    # 準備圖表數據
    labels = []
    data = []
    
    for point in charging_curve:
        # 時間標籤 (分:秒 格式)
        minutes = int(point['time_minutes'])
        seconds = int((point['time_minutes'] - minutes) * 60)
        labels.append(f"{minutes}:{seconds:02d}")
        data.append(point['percentage'])
    
    session_info = {
        'start_time': latest_session.get('start_time'),
        'duration_minutes': latest_session.get('duration_minutes', 0),
        'start_voltage': latest_session.get('start_voltage', 0),
        'end_voltage': latest_session.get('end_voltage', 0),
        'is_complete': latest_session.get('end_time') is not None
    }
    
    return jsonify({
        "labels": labels,
        "data": data,
        "session_info": session_info
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)