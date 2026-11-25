# tellolink Frame: one video frame as raw H.264 (Annex-B) bytes (no tick). The decoded image is on raw/std/image.
std_msgs/Header header      # stamp: recv_time of the frame's last UDP packet
bool keyframe
uint8[] data
