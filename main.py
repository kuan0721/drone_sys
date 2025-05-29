from control_sys.drone_control import DroneController, LowBatteryResumeException
import signal


def main():
    drone = DroneController('/dev/ttyACM1', voltage_port='/dev/ttyUSB0', voltage_threshold=15.2)
    drone.connect()
    signal.signal(signal.SIGINT, lambda sig, frm: drone.return_to_launch())

    drone.arm_and_takeoff()
    waypoints = [(drone.square_size,0), (drone.square_size,drone.square_size), (0,drone.square_size), (0,0)]
    for lap in range(3):
        print(f"Lap {lap+1}/3")
        for wp in waypoints:
            drone.next_waypoint = wp
            try:
                drone.fly_to_point(*wp, drone.takeoff_altitude)
            except LowBatteryResumeException:
                break
    print("Mission done, final landing")
    drone.final_rtl()

if __name__ == '__main__':
    main()