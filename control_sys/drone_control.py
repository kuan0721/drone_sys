import time
import sys
from pymavlink import mavutil

class LowBatteryResumeException(Exception):
    """Raised when voltage drops below threshold to trigger low-battery flow."""
    pass

class DroneController:
    def __init__(self, connection_string, voltage_threshold=15.2, takeoff_altitude=15, square_size=10):
        self.connection_string = connection_string
        self.voltage_threshold = voltage_threshold  # Voltage in volts
        self.takeoff_altitude = takeoff_altitude
        self.square_size = square_size

        # State variables
        self.master = None
        self.initial_yaw_pre_takeoff = None
        self.recorded_position = None
        self.recorded_next_waypoint = None
        self.recorded_yaw_low_battery = None
        self.next_waypoint = None

    def connect(self):
        self.master = mavutil.mavlink_connection(self.connection_string)
        self.master.wait_heartbeat()
        print("Connected to drone!")

    def get_arm_status(self):
        hb = self.master.recv_match(type='HEARTBEAT', blocking=True, timeout=2)
        if hb:
            armed = bool(hb.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
            return "armed" if armed else "disarmed"
        return "unknown"

    def get_initial_yaw(self):
        msg = self.master.recv_match(type='VFR_HUD', blocking=True, timeout=2)
        return msg.heading if msg else 0

    def get_voltage(self):
        msg = self.master.recv_match(type='SYS_STATUS', blocking=True, timeout=2)
        if msg and msg.voltage_battery:
            # voltage_battery in mV
            return msg.voltage_battery / 1000.0
        return None

    def check_voltage(self):
        v = self.get_voltage()
        if v is not None:
            print(f"[Voltage] {v:.3f} V")
            if v < self.voltage_threshold:
                self.recorded_position = self.get_gps_position()
                self.recorded_next_waypoint = self.next_waypoint
                self.recorded_yaw_low_battery = self.get_initial_yaw()
                print(f"Low voltage -> {v:.3f} V, initiating RTL")
                self.low_battery_rtl()
                raise LowBatteryResumeException()

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
        for _ in range(10):
            self.check_voltage()
            time.sleep(1)

    def fly_to_point(self, x, y, z):
        self.master.mav.set_position_target_local_ned_send(
            0, self.master.target_system, self.master.target_component,
            mavutil.mavlink.MAV_FRAME_LOCAL_NED,
            int(0b110111111000), x, y, -z, 0,0,0,0,0,0,0,0
        )
        print(f"Flying to {x},{y},{z}")
        for _ in range(10):
            self.check_voltage()
            time.sleep(1)

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
            if adjusted and alt <= 0.2:
                break
            time.sleep(0.2)

    def low_battery_rtl(self):
        print("Low-Battery RTL...")
        self._rtl_and_land()
        self.resume_mission()

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