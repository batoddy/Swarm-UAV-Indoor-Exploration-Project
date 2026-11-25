# tellolink Mvo: log record 29 (LogNewMvoFeedback), 5 Hz. The drone's own optical-flow estimate.
# World frame of the drone, ROS axes: x = yaw 0 direction, y = left of it, z up (no compass: not true ENU).
std_msgs/Header header      # stamp: recv_time
uint32 tick
float32 vel_x               # m/s
float32 vel_y
float32 vel_z
float32 pos_x               # m; jumps at takeoff; pos_z up +
float32 pos_y
float32 pos_z
float32 height              # m above ground; NaN if the record did not carry it
int16 flags                 # validity bits; -1 if the record did not carry it
