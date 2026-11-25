# tellolink Imu: log record 2048 (LogImuAtti), 10 Hz. ROS axes and SI units.
# Body frame: base_link FLU (x forward, y left, z up). acc, gyro, gyro_bias.
# World frame of the drone, ROS axes: x = yaw 0 direction, y = left of it, z up (no compass: not true ENU). lin_acc, vel.
# q: orientation of base_link in that world frame.
std_msgs/Header header      # stamp: recv_time
uint32 tick                 # drone counter, ~2,343,850 Hz, wraps every ~30.5 min
float32 acc_x               # m/s^2, specific force (z ~ +9.81 at rest)
float32 acc_y
float32 acc_z
float32 gyro_x              # rad/s
float32 gyro_y
float32 gyro_z
float32 q0                  # quaternion, q0 = w
float32 q1
float32 q2
float32 q3
float32 lin_acc_x           # m/s^2, gravity removed
float32 lin_acc_y
float32 lin_acc_z
float32 vel_x               # m/s
float32 vel_y
float32 vel_z
float32 gyro_bias_x         # NaN if the record did not carry it
float32 gyro_bias_y
float32 gyro_bias_z
float32 temperature         # deg C; NaN if the record did not carry it
