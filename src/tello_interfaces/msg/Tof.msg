# tellolink Tof: log record 16 (LogTof), 5 Hz. Downward distance sensor.
std_msgs/Header header      # stamp: recv_time
uint32 tick
float32 distance            # m; 0.1 on the ground (smallest value)
uint8 flag
uint8 counter               # +4 per record
