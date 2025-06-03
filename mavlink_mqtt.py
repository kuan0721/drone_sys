import serial
import time
import threading
import json
from pymavlink import mavutil
import paho.mqtt.client as mqtt

# ---------------------
# USB 電壓監控類別
# ---------------------
class VoltageReader:
    def __init__(self, port: str, baud: int = 9600, timeout: float = 1.0):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.ser = None
        self._stop_flag = threading.Event()
        self.latest_voltage = None

    def open(self):
        self.ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
        print(f"Opened {self.port} at {self.baud}bps")

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Serial closed")

    def start(self):
        if not self.ser or not self.ser.is_open:
            self.open()
        self._stop_flag.clear()
        threading.Thread(target=self._read_loop, daemon=True).start()

    def stop(self):
        self._stop_flag.set()

    def _read_loop(self):
        try:
            while not self._stop_flag.is_set():
                line = self.ser.readline().decode('ascii', errors='ignore').strip()
                if line:
                    try:
                        voltage = float(line)
                        self.latest_voltage = voltage  # 保留最新數值
                    except ValueError:
                        pass
                time.sleep(0.1)
        except Exception as e:
            print(f"VoltageReader 錯誤: {e}")
        finally:
            self.close()

# ---------------------
# 主要參數
# ---------------------
MQTT_BROKER = 'test.mosquitto.org'
MQTT_PORT = 1883
MQTT_TOPIC = 'goodrich/drone/data'
MAV_CONNECTION_STR = '/dev/ttyACM1'   # 請依你的實際埠位修改
USB_PORT = '/dev/ttyUSB0'             # 請依你的 USB 修改

# ---------------------
# 主程式
# ---------------------
def main():
    # 啟動 USB 電壓監控
    voltage_reader = VoltageReader(port=USB_PORT, baud=9600)
    voltage_reader.start()
    time.sleep(1)  # 給 USB 一點啟動緩衝

    # 建立 MAVLink 連線
    print("連線至 MAVLink...")
    master = mavutil.mavlink_connection(MAV_CONNECTION_STR)
    master.wait_heartbeat()
    print("MAVLink 已連線")

    # 主動要求定期發送 MAVLink 訊息
    for msgid in [
        mavutil.mavlink.MAVLINK_MSG_ID_VFR_HUD,
        mavutil.mavlink.MAVLINK_MSG_ID_ATTITUDE,
        mavutil.mavlink.MAVLINK_MSG_ID_GLOBAL_POSITION_INT,
        mavutil.mavlink.MAVLINK_MSG_ID_SYS_STATUS
    ]:
        master.mav.command_long_send(
            master.target_system,
            master.target_component,
            mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
            0,
            msgid,
            1000000,  # 1秒
            0, 0, 0, 0, 0
        )

    # 建立 MQTT 連線
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    print(f"已連線 MQTT Broker：{MQTT_BROKER}:{MQTT_PORT}，Topic：{MQTT_TOPIC}")

    try:
        while True:
            # 快速抓取一輪各 MAVLink 訊息（0.3秒內最新一包）
            messages = {}
            start = time.time()
            while time.time() - start < 0.3:
                msg = master.recv_match(blocking=False)
                if msg is None:
                    time.sleep(0.01)
                    continue
                if msg.get_type() == 'BAD_DATA':
                    continue
                messages[msg.get_type()] = msg

            # 預設資料
            payload = {
                "flight_mode": None,
                "arm_status": None,
                "speed": None,
                "altitude": None,
                "battery": {
                    "volt": None,
                    "current": None,
                    "battery_percent": None
                },
                "gps_position": {
                    "lat": None,
                    "lon": None
                },
                "attitude": {
                    "pitch": None,
                    "yaw": None,
                    "roll": None
                }
            }

            # 1. HEARTBEAT
            hb = messages.get("HEARTBEAT")
            if hb:
                try:
                    payload["flight_mode"] = mavutil.mode_string_v10(hb)
                except:
                    payload["flight_mode"] = str(hb.custom_mode)
                payload["arm_status"] = "armed" if (hb.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED) else "disarmed"

            # 2. VFR_HUD
            vh = messages.get("VFR_HUD")
            if vh:
                payload["speed"] = round(vh.groundspeed, 2)
                payload["altitude"] = round(vh.alt, 2)

            # 3. ATTITUDE
            att = messages.get("ATTITUDE")
            if att:
                payload["attitude"] = {
                    "pitch": round(att.pitch * 57.2958, 2),
                    "roll":  round(att.roll * 57.2958, 2),
                    "yaw":   round(att.yaw * 57.2958, 2)
                }

            # 4. GLOBAL_POSITION_INT
            gp = messages.get("GLOBAL_POSITION_INT")
            if gp:
                payload["gps_position"] = {
                    "lat": gp.lat / 1e7,
                    "lon": gp.lon / 1e7
                }

            # 5. SYS_STATUS（電池剩餘% & 電流）
            bat = messages.get("SYS_STATUS")
            if bat:
                payload["battery"]["battery_percent"] = bat.battery_remaining
                if bat.current_battery != -1:
                    payload["battery"]["current"] = bat.current_battery / 100.0  # 換成 A
                else:
                    payload["battery"]["current"] = None

            # 6. 電壓（USB 讀取最新值）
            payload["battery"]["volt"] = voltage_reader.latest_voltage

            # 送 MQTT
            client.publish(MQTT_TOPIC, json.dumps(payload))
            print(f"Published: {json.dumps(payload)}")

            time.sleep(1)

    except KeyboardInterrupt:
        print("使用者手動中斷。")
    finally:
        voltage_reader.stop()
        client.disconnect()
        print("程式結束，資源釋放。")

if __name__ == '__main__':
    main()
