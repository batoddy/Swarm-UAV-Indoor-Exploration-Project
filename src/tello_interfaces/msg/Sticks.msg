# tellolink Sticks: log record 1000 (LogController), 5 Hz. The sticks as the drone sees them.
# Tello stick signs (same as StickCommand), not ROS axes.
std_msgs/Header header      # stamp: recv_time
uint32 tick
float32 pitch               # -1..1, forward +
float32 roll                # -1..1, right +
float32 yaw                 # -1..1, clockwise +
float32 throttle            # -1..1, up +
uint8 fly_mode
uint8 motors_on             # 1 from takeoff until the motors stop
