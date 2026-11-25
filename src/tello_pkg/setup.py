from setuptools import find_packages, setup

package_name = 'tello_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/rviz', ['rviz/tello.rviz']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='batoddy',
    maintainer_email='batoddy@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'tello_ros = tello_pkg.tello_ros:main',
            'tello_teleop = tello_pkg.tello_teleop:main',
        ],
    },
)
