# Barometer, from tellolink Imu (log record 2048, LogImuAtti), 10 Hz: the drone sends it inside its IMU record.
std_msgs/Header header      # stamp: recv_time
uint32 tick
float32 altitude_raw        # m, raw barometric altitude, up + (absolute; only differences are meaningful)
float32 altitude            # m, smoothed
