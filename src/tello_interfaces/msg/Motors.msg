# tellolink Motors: log record 1307 (LogMotorCtrl), 10 Hz, only while motors are running.
std_msgs/Header header      # stamp: recv_time
uint32 tick
float32[4] pwm              # %, order: front right, front left, rear left, rear right (inferred)
