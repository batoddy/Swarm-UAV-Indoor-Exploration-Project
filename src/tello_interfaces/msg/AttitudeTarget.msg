# tellolink AttitudeTarget: log record 1304 (LogAttitudeControl), 2.5 Hz, only while motors are running.
# ROS angles (FLU): roll right side down +, pitch nose down +, yaw counter-clockwise +.
std_msgs/Header header      # stamp: recv_time
uint32 tick
float32 target_yaw          # rad
float32 target_roll
float32 target_pitch
float32 yaw                 # rad, actual
float32 roll
float32 pitch
