import time
import sys
import signal
import json
import threading
from datetime import datetime
from pymavlink import mavutil
from voltage_reader import VoltageReader

class LowBatteryResumeException(Exception):
    """Raised when voltage drops below threshold to trigger low-battery flow."""
    pass

class DroneController:
    def __init__(self, connection_string, voltage_port, voltage_threshold=15.2,
                 voltage_baud=9600, takeoff_altitude=15, square_size=10):
        self.connection_string = connection_string
        self.voltage_threshold = voltage_threshold
        self.takeoff_altitude = takeoff_altitude
        self.square_size = square_size

        # MAVLink
        self.master = None
        self.initial_yaw_pre_takeoff = None
        self.recorded_position = None
        self.recorded_next_waypoint = None
        self.recorded_yaw_low_battery = None
        self.next_waypoint = None

        # Voltage reader
        self.voltage_reader = VoltageReader(port=voltage_port, baud=voltage_baud)
        self.voltage_reader.register_callback(threshold=self.voltage_threshold,
                                              callback=self._on_low_voltage)

        # 充電歷程記錄
        self.charging_data = []
        self.charging_start_time = None
        self.is_charging = False
        self.charging_thread = None
        self.charging_stop_flag = threading.Event()

    def connect(self):
        # MAVLink connection
        self.master = mavutil.mavlink_connection(self.connection_string)
        self.master.wait_heartbeat()
        print("Connected to drone via MAVLink!")

        # Start voltage monitoring
        self.voltage_reader.start()
        print(f"Started voltage reader on {self.voltage_reader.port}")

    def _on_low_voltage(self, voltage):
        print(f"⚠️ Voltage {voltage:.3f} V below threshold {self.voltage_threshold} V, initiating low-battery RTL")
        self.recorded_position = self.get_gps_position()
        self.recorded_next_waypoint = self.next_waypoint
        self.recorded_yaw_low_battery = self.get_initial_yaw()
        self.low_battery_rtl()
        raise LowBatteryResumeException()

    def start_charging_monitor(self):
        """開始充電監控和記錄"""
        if self.is_charging:
            return
        
        self.is_charging = True
        self.charging_start_time = datetime.now()
        self.charging_stop_flag.clear()
        self.charging_data = []  # 清空之前的充電記錄
        
        print("🔋 開始充電監控...")
        self.charging_thread = threading.Thread(target=self._charging_monitor_loop, daemon=True)
        self.charging_thread.start()

    def stop_charging_monitor(self):
        """停止充電監控"""
        if not self.is_charging:
            return
        
        self.is_charging = False
        self.charging_stop_flag.set()
        
        # 保存充電記錄到檔案
        self.save_charging_history()
        print("🔋 充電監控已停止")

    def _charging_monitor_loop(self):
        """充電監控迴圈"""
        try:
            while not self.charging_stop_flag.is_set():
                # 取得當前電壓
                current_voltage = self.voltage_reader.latest_voltage if self.voltage_reader.latest_voltage else 0
                
                # 計算充電時間（秒）
                elapsed_time = (datetime.now() - self.charging_start_time).total_seconds()
                
                # 估算電池百分比（假設滿電16.8V，低電15.2V）
                voltage_range = 16.8 - 15.2  # 1.6V 範圍
                voltage_above_min = max(0, current_voltage - 15.2)
                battery_percent = min(100, (voltage_above_min / voltage_range) * 100)
                
                # 記錄充電資料點
                charging_point = {
                    "timestamp": datetime.now().isoformat(),
                    "elapsed_seconds": elapsed_time,
                    "voltage": current_voltage,
                    "battery_percent": round(battery_percent, 1),
                    "charging_rate": self._calculate_charging_rate()
                }
                
                self.charging_data.append(charging_point)
                
                # 每5筆資料保存一次（避免資料遺失）
                if len(self.charging_data) % 5 == 0:
                    self.save_charging_history()
                
                # 檢查是否充電完成（電壓達到16.5V以上視為充飽）
                if current_voltage >= 16.5:
                    print(f"🔋 充電完成！最終電壓: {current_voltage:.2f}V")
                    break
                
                time.sleep(2)  # 每2秒記錄一次
                
        except Exception as e:
            print(f"充電監控錯誤: {e}")
        finally:
            self.stop_charging_monitor()

    def _calculate_charging_rate(self):
        """計算充電速率 (V/min)"""
        if len(self.charging_data) < 2:
            return 0
        
        # 取最近兩個資料點計算速率
        current = self.charging_data[-1]
        previous = self.charging_data[-2]
        
        voltage_diff = current["voltage"] - previous["voltage"]
        time_diff = current["elapsed_seconds"] - previous["elapsed_seconds"]
        
        if time_diff > 0:
            # 轉換為每分鐘的電壓變化
            return (voltage_diff / time_diff) * 60
        return 0

    def save_charging_history(self):
        """保存充電歷程到JSON檔案"""
        charging_history = {
            "session_id": self.charging_start_time.strftime("%Y%m%d_%H%M%S"),
            "start_time": self.charging_start_time.isoformat(),
            "end_time": datetime.now().isoformat() if not self.is_charging else None,
            "total_duration_seconds": (datetime.now() - self.charging_start_time).total_seconds(),
            "data_points": self.charging_data,
            "summary": {
                "initial_voltage": self.charging_data[0]["voltage"] if self.charging_data else 0,
                "final_voltage": self.charging_data[-1]["voltage"] if self.charging_data else 0,
                "initial_percent": self.charging_data[0]["battery_percent"] if self.charging_data else 0,
                "final_percent": self.charging_data[-1]["battery_percent"] if self.charging_data else 0,
                "avg_charging_rate": sum(point["charging_rate"] for point in self.charging_data) / len(self.charging_data) if self.charging_data else 0
            }
        }
        
        try:
            with open('charging_history.json', 'w', encoding='utf-8') as f:
                json.dump(charging_history, f, indent=2, ensure_ascii=False)
            print(f"📊 充電記錄已保存 ({len(self.charging_data)} 個資料點)")
        except Exception as e:
            print(f"保存充電記錄失敗: {e}")

    # 原有的其他方法保持不變...
    def get_arm_status(self):
        hb = self.master.recv_match(type='HEARTBEAT', blocking=True, timeout=2)
        if hb:
            armed = bool(hb.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
            return "armed" if armed else "disarmed"
        return "unknown"

    def get_initial_yaw(self):
        msg = self.master.recv_match(type='VFR_HUD', blocking=True, timeout=2)
        return msg.heading if msg else 0

    def get_gps_position(self):
        msg = self.master.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=2)
        return (msg.lat / 1e7, msg.lon / 1e7) if msg else (0, 0)

    def rotate_yaw(self, angle, relative=0):
        self.master.mav.command_long_send(
            self.master.target_system, self.master.target_component,
            mavutil.mavlink.MAV_CMD_CONDITION_YAW,
            0, angle,10, relative,0,0,0,0
        )
        time.sleep(8)

    def arm_and_takeoff(self):
        self.initial_yaw_pre_takeoff = self.get_initial_yaw()
        print(f"Recorded pre-takeoff yaw: {self.initial_yaw_pre_takeoff}")

        self.master.set_mode_apm('GUIDED')
        time.sleep(1)
        for _ in range(5):
            self.master.mav.command_long_send(
                self.master.target_system, self.master.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0, 1,0,0,0,0,0,0
            )
            time.sleep(2)
            if self.get_arm_status() == "armed":
                print("Armed")
                break
        else:
            print("Arming failed.")
            sys.exit(1)

        self.master.mav.command_long_send(
            self.master.target_system, self.master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0, 0,0,0,0,0,0, self.takeoff_altitude
        )
        print(f"Taking off to {self.takeoff_altitude}m...")
        time.sleep(10)

    def fly_to_point(self, x, y, z):
        self.master.mav.set_position_target_local_ned_send(
            0, self.master.target_system, self.master.target_component,
            mavutil.mavlink.MAV_FRAME_LOCAL_NED,
            int(0b110111111000), x, y, -z, 0,0,0,0,0,0,0,0
        )
        print(f"Flying to {x},{y},{z}")
        time.sleep(10)

    def _rtl_and_land(self):
        self.master.set_mode_apm('RTL')
        while True:
            hb = self.master.recv_match(type='HEARTBEAT', blocking=True)
            if hb and hb.custom_mode == 6:
                break
            time.sleep(0.5)
        adjusted = False
        while True:
            msg = self.master.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
            if not msg:
                continue
            alt = msg.relative_alt / 1000.0
            if alt <= 9 and not adjusted:
                self.master.set_mode_apm('GUIDED')
                time.sleep(1)
                self.rotate_yaw(self.initial_yaw_pre_takeoff)
                self.master.mav.command_long_send(
                    self.master.target_system, self.master.target_component,
                    mavutil.mavlink.MAV_CMD_NAV_LAND,
                    0, 0,0,0,0,0,0,0
                )
                adjusted = True
                
                # 降落後開始充電監控
                if alt <= 0.5:  # 接近地面時開始充電
                    print("🔋 無人機已降落，開始充電程序...")
                    self.start_charging_monitor()
                    
            if adjusted and alt <= 0.2:
                break
            time.sleep(0.2)



    def low_battery_rtl(self):
        print("Low-Battery RTL...")
        self._rtl_and_land()
        # 等待充電完成
        self.wait_for_charging_complete()
        self.resume_mission()

    def wait_for_charging_complete(self):
        """等待充電完成"""
        print("⏳ 等待充電完成...")
        while self.is_charging:
            time.sleep(5)
            # 檢查充電進度
            if self.charging_data:
                latest = self.charging_data[-1]
                print(f"充電進度: {latest['battery_percent']:.1f}% ({latest['voltage']:.2f}V)")
        
        print("✅ 充電完成，準備恢復任務")
        time.sleep(2)  # 給一點緩衝時間

    def emergency_rtl(self):
        print("Emergency RTL: immediate landing")
        self._rtl_and_land()
        print("Emergency landing complete.")
        sys.exit(0)

    def final_rtl(self):
        print("Final RTL: landing procedure...")
        self._rtl_and_land()
        print("Final landing complete.")
        sys.exit(0)

    def return_to_launch(self):
        self.emergency_rtl()

    def resume_mission(self):
        print("Resuming mission...")
        # 停止充電監控
        self.stop_charging_monitor()
        
        self.arm_and_takeoff()
        lat, lon = self.recorded_position
        self.master.mav.set_position_target_global_int_send(
            0, self.master.target_system, self.master.target_component,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
            int(0b0000111111111000), int(lat*1e7), int(lon*1e7), self.takeoff_altitude,
            0,0,0,0,0,0,0,0
        )
        time.sleep(15)
        self.rotate_yaw(self.recorded_yaw_low_battery)
        print("Mission resumed.")