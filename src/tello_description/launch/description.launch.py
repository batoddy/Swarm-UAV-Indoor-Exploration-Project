"""robot_state_publisher for one Tello: publishes its sensor frames on /tf_static.

    ros2 launch tello_description description.launch.py namespace:=tello1
Frames get the namespace as prefix (tello1/base_link, ...), matching tello_ros.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    urdf = os.path.join(get_package_share_directory('tello_description'), 'urdf', 'tello.urdf')
    with open(urdf) as f:
        robot_description = f.read()
    ns = LaunchConfiguration('namespace')
    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value='tello1'),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            namespace=ns,
            parameters=[{
                'robot_description': robot_description,
                'frame_prefix': PythonExpression(["'", ns, "/' if '", ns, "' else ''"]),
            }],
        ),
    ])
