# tellolink UnsolvedRecord: a log record whose meaning is not decoded.
std_msgs/Header header      # stamp: recv_time
uint32 tick
uint16 record_id
uint8[] payload             # raw bytes (XOR removed)
