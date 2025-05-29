import time
import json
from pymavlink import mavutil
import paho.mqtt.client as mqtt

MQTT_BROKER = 'test.mosquitto.org'
MQTT_PORT = 1883
MQTT_TOPIC = 'goodrich/drone/data'


def connect_mavlink(connection_str):
    master = mavutil.mavlink_connection(connection_str)
    master.wait_heartbeat()
    print("MAVLink connected")
    return master


def publish_loop(master):
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    while True:
        data = {}
        # heartbeat
        hb = master.recv_match(type='HEARTBEAT', blocking=True, timeout=1)
        data['arm_status'] = 'armed' if (hb and hb.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED) else 'disarmed'
        # attitude
        att = master.recv_match(type='ATTITUDE', blocking=True, timeout=1)
        if att:
            data['pitch'] = round(att.pitch * 57.2958, 2)
            data['roll']  = round(att.roll  * 57.2958, 2)
            data['yaw']   = round(att.yaw   * 57.2958, 2)
        # gps
        gp = master.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=1)
        if gp:
            data['lat'] = gp.lat / 1e7
            data['lon'] = gp.lon / 1e7
            data['alt'] = round(gp.relative_alt / 1000.0, 2)
        # battery
        bat = master.recv_match(type='SYS_STATUS', blocking=True, timeout=1)
        if bat:
            data['volt'] = round(bat.voltage_battery / 1000.0, 2)
            data['percent'] = bat.battery_remaining
        # publish
        client.publish(MQTT_TOPIC, json.dumps(data))
        print(f"Published: {data}")
        time.sleep(1)


if __name__ == '__main__':
    mav = connect_mavlink('udp:127.0.0.1:14550')
    try:
        publish_loop(mav)
    except KeyboardInterrupt:
        print("Stopping MQTT publisher")