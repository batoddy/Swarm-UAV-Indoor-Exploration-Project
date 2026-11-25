cmake_minimum_required(VERSION 3.8)
project(tello_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/AttitudeTarget.msg"
  "msg/Baro.msg"
  "msg/Battery.msg"
  "msg/Frame.msg"
  "msg/Gyro.msg"
  "msg/Imu.msg"
  "msg/Motors.msg"
  "msg/Mvo.msg"
  "msg/Nav.msg"
  "msg/Osd.msg"
  "msg/Status.msg"
  "msg/StickCommand.msg"
  "msg/Sticks.msg"
  "msg/Tof.msg"
  "msg/Unsolved.msg"
  "msg/Wifi.msg"
  DEPENDENCIES std_msgs
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
