# tellolink Nav: log record 2064 (LogImuEx), 10 Hz. Position and velocity the controller uses.
# World frame of the drone, ROS axes: x = yaw 0 direction, y = left of it, z up (no compass: not true ENU).
std_msgs/Header header      # stamp: recv_time
uint32 tick
float32 vel_x               # m/s
float32 vel_y
float32 vel_z
float32 pos_x               # m; does not jump at takeoff / landing
float32 pos_y
float32 pos_z               # m, barometric altitude, up + (absolute; only differences are meaningful)
float32 tof_vel             # m/s, rate of height change, up +
float32 height              # m above ground
uint16 flags
uint16 counter
