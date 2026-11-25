# tellolink Status: flight status packet (0x0056), 10 Hz (no tick). ROS axes and SI units.
# World frame of the drone, ROS axes: x = yaw 0 direction, y = left of it, z up (no compass: not true ENU).
std_msgs/Header header      # stamp: recv_time (host time when the packet arrived)
float32 height              # m
float32 vel_x               # m/s, world x
float32 vel_y               # m/s, world y (left)
float32 vel_z               # m/s, up +
float32 fly_time            # s, increases only while airborne
uint8 battery_percent       # %
float32 battery_voltage     # V
int16 battery_left          # meaning unknown, always 0
uint8 fly_mode              # 6 steady on ground / in air, 11 takeoff, 12 landing
bool em_sky                 # airborne
bool em_ground              # only ~0.5 s while motors spin up at takeoff; NOT "on the ground"
bool em_open                # motors running
bool drone_hover
bool outage_recording
bool battery_low
bool battery_lower
bool factory_mode
bool imu_state
bool pressure_state
bool down_visual_state
bool power_state
bool battery_state
bool gravity_state
bool wind_state
uint8 imu_calibration_state
uint8 throw_fly_timer
uint8 camera_state
uint8 electrical_machinery_state
bool front_in
bool front_out
bool front_lsc
bool temperature_height
