# tellolink Gyro: log record 1305 (LogGyro), 20 Hz, only while motors are running.
# Three processing stages of the same gyro, each (x, y, z), body frame FLU; unit not verified (rad/s likely).
std_msgs/Header header      # stamp: recv_time
uint32 tick
float32[3] stage0
float32[3] stage1
float32[3] stage2
