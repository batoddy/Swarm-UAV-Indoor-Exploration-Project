# tellolink Osd: log record 12 (LogOsdGeneral), ~1.7 Hz. The drone's own status summary.
# World frame of the drone, ROS axes: x = yaw 0 direction, y = left of it, z up (no compass: not true ENU). vel.
# Angles: ROS roll/pitch/yaw of base_link (FLU): roll right side down +, pitch nose down +, yaw counter-clockwise +.
std_msgs/Header header      # stamp: recv_time
uint32 tick
float32 height              # m
float32 vel_x               # m/s, 0.1 steps
float32 vel_y
float32 vel_z
float32 pitch               # rad
float32 roll                # rad
float32 yaw                 # rad
uint8 fly_mode
float32 tof_height          # m
float32 fly_time            # s
float32 yaw_rate            # rad/s, counter-clockwise +
