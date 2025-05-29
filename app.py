from flask import Flask, jsonify, render_template
import json
import os
import subprocess
import time

# 自動啟動 socket_server.py
socket_server_process = subprocess.Popen(["python", "web_data.py"])

# 等待 socket_server.py 啟動 (可調整秒數)
time.sleep(2)

app = Flask(__name__)
DATA_FILE = 'drone_data.json'

# 確保資料檔案存在
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({
            "flight_mode": "unknown",
            "arm_status": "unknown",
            "speed": 0,
            "altitude": 0,
            "battery": {"volt": 0, "current": 0, "battery_percent": 0},
            "rtk_status": "unknown",
            "gps_position": {"lat": 0, "lon": 0},
            "attitude": {"pitch": 0, "yaw": 0, "roll": 0},
            "charge_data": {"voltage": 0, "current": 0, "battery_percent": 0}
        }, f)

# 讀取資料檔案
def load_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_speed")
def get_speed():
    data = load_data()
    return jsonify({"speed": data["speed"]})

@app.route("/get_height")
def get_height():
    data = load_data()
    return jsonify({"height": data["altitude"]})

@app.route("/get_battery")
def get_battery():
    data = load_data()
    battery_info = data.get("battery", {})
    return jsonify({
        "volt": battery_info.get("volt", 16.8),
        "current": battery_info.get("current", 1),
        "battery_percent": battery_info.get("battery_percent", 100)
    })

@app.route("/get_flight_mode")
def get_flight_mode():
    data = load_data()
    return jsonify({"mode": data["flight_mode"]})

@app.route("/get_arming_status")
def get_arming_status():
    data = load_data()
    return jsonify({"status": data["arm_status"]})

@app.route("/get_rtk_status")
def get_rtk_status():
    data = load_data()
    return jsonify({"status": data["rtk_status"]})

@app.route("/get_drone_position")
def get_drone_position():
    data = load_data()
    return jsonify(data["gps_position"])

@app.route("/get_drone_orientation")
def get_drone_orientation():
    data = load_data()
    return jsonify(data["attitude"])

@app.route('/get_charging_data')
def get_charging_data():
    data = load_data()
    return jsonify(data["charge_data"])

if __name__ == "__main__":
    # 這裡是重點：host 設為 '0.0.0.0'，port 自訂，例如 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
