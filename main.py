from control_sys.drone_control import DroneController, LowBatteryResumeException
from control_sys.data import DataMonitor
import signal


def main():
    #drone = DroneController('udp:127.0.0.1:14550')
    drone = DroneController('/dev/ttyACM1')
    drone.connect()

    monitor = DataMonitor(drone)
    monitor.start()

    signal.signal(signal.SIGINT, lambda sig, frm: drone.return_to_launch())

    drone.arm_and_takeoff()

    waypoints = [
        (drone.square_size, 0),
        (drone.square_size, drone.square_size),
        (0, drone.square_size),
        (0, 0)
    ]

    # 繞三圈
    for lap in range(3):
        print(f"Starting lap {lap+1} of 3")
        for wp in waypoints:
            drone.next_waypoint = wp
            try:
                x, y = wp
                drone.fly_to_point(x, y, drone.takeoff_altitude)
            except LowBatteryResumeException:
                if drone.recorded_next_waypoint in waypoints:
                    break
        print(f"Completed lap {lap+1}")

    print("Mission complete: 3 laps done.")

    # 最後執行同低電量下降流程，但不充電、不復原
    drone.final_rtl()

if __name__ == '__main__':
    main()