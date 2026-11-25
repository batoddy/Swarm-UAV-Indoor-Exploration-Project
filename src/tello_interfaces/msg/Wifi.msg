# tellolink Wifi: Wi-Fi packet (0x001A), 1 Hz (no tick).
std_msgs/Header header      # stamp: recv_time
uint8 strength              # signal strength
int16 disturb               # interference; -1 if the packet did not carry it
