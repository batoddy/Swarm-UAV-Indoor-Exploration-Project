"""
Tello ROS 2 bridge: publishes what the drone sends and forwards commands. No estimation or fusion.

Topic and service names are relative; give the drone name as the namespace:
    ros2 run tello_pkg tello_ros --ros-args -r __ns:=/tello1

Published
    raw/<record>     tello_interfaces/<Record>   every tellolink record, same fields, converted to
                     ROS axes (REP-103) and SI units (see TO_ROS): body FLU; world x = yaw 0,
                     y left, z up (no compass); angles rad. Sticks keep Tello signs.
                     Topics: status, wifi, imu, baro, gyro, mvo, tof, nav, osd, sticks,
                     attitude_target, motors, battery, unsolved, frame (raw H.264).
    raw/std/imu              sensor_msgs/Imu          base_link FLU, m/s^2, rad/s
    raw/std/imu/temperature  sensor_msgs/Temperature
    raw/std/tof              sensor_msgs/Range
    raw/std/battery          sensor_msgs/BatteryState  from the status packet
    raw/std/image            sensor_msgs/Image         bgr8, frame camera_optical
Subscribed
    cmd_sticks       tello_interfaces/StickCommand  stick fractions -1..1, Tello signs; set to 0 if
                     none arrives for CMD_TIMEOUT s
    fast_mode        std_msgs/Bool                  False (slow) until set
Services (std_srvs/Trigger; the command is sent once, the drone does not acknowledge it:
check raw/status to see whether it took effect)
    takeoff, land, emergency

Stamps: recv_time (host time.monotonic() at packet arrival) mapped to ROS time. raw records also
carry the drone's tick. TF (base_link, camera, tof) comes from tello_description.
"""
import array
import math
import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.time import Time
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import BatteryState, Image, Imu, Range, Temperature
from std_msgs.msg import Bool
from std_srvs.srv import Trigger
import tello_interfaces.msg as tmsg
from tello_pkg.tellolink import Tello

GRAVITY = 9.80665
CMD_TIMEOUT = 0.5           # s without cmd_sticks -> sticks 0
# ToF Range limits. Field of view is unknown; ~25 deg is typical (must be > 0 for rviz).
TOF_MIN, TOF_MAX, TOF_FOV = 0.1, 10.0, 0.44

# (tellolink event, topic under raw/, message type). The IMU record also carries the barometer,
# which is published on its own topic.
RAW = [
    (Tello.EVENT_STATUS, 'status', tmsg.Status),
    (Tello.EVENT_WIFI, 'wifi', tmsg.Wifi),
    (Tello.EVENT_IMU, 'imu', tmsg.Imu),
    (Tello.EVENT_IMU, 'baro', tmsg.Baro),
    (Tello.EVENT_GYRO, 'gyro', tmsg.Gyro),
    (Tello.EVENT_MVO, 'mvo', tmsg.Mvo),
    (Tello.EVENT_TOF, 'tof', tmsg.Tof),
    (Tello.EVENT_NAV, 'nav', tmsg.Nav),
    (Tello.EVENT_OSD, 'osd', tmsg.Osd),
    (Tello.EVENT_STICKS, 'sticks', tmsg.Sticks),
    (Tello.EVENT_ATTITUDE_TARGET, 'attitude_target', tmsg.AttitudeTarget),
    (Tello.EVENT_MOTORS, 'motors', tmsg.Motors),
    (Tello.EVENT_BATTERY, 'battery', tmsg.Battery),
    (Tello.EVENT_UNSOLVED, 'unsolved', tmsg.Unsolved),
    (Tello.EVENT_FRAME, 'frame', tmsg.Frame),
]


def ned_to_enu(x, y, z):
    """Convert a vector from the drone's frame (z down) to the ROS frame (z up)."""
    return x, -y, -z


def stale_imu(d):
    """Stale IMU records sent right after connect have an all-zero quaternion."""
    return d.q0 * d.q0 + d.q1 * d.q1 + d.q2 * d.q2 + d.q3 * d.q3 < 1e-12


def flu(x, y, z):
    """Drone frame (y right, z down) -> ROS frame (y left, z up). Same for body (FRD -> FLU)."""
    return x, -y, -z


def vec(rec, prefix, scale=1.0):
    """Fields prefix_x/y/z of a record, scaled and converted to the ROS frame."""
    x, y, z = (getattr(rec, f'{prefix}_{a}') for a in 'xyz')
    if x is None:
        return {}
    return dict(zip((f'{prefix}_x', f'{prefix}_y', f'{prefix}_z'), flu(x * scale, y * scale, z * scale)))


def _imu(r):
    return {**vec(r, 'acc', GRAVITY), **vec(r, 'gyro'), **vec(r, 'lin_acc'), **vec(r, 'vel'),
            **vec(r, 'gyro_bias'), 'q2': -r.q2, 'q3': -r.q3}


def _osd(r):
    rad = math.radians
    return {**vec(r, 'vel'), 'roll': rad(r.roll), 'pitch': -rad(r.pitch), 'yaw': -rad(r.yaw),
            'yaw_rate': -rad(r.yaw_rate)}


def _attitude(r):
    return {'target_pitch': -r.target_pitch, 'target_yaw': -r.target_yaw,
            'pitch': -r.pitch, 'yaw': -r.yaw}


# raw topic -> message fields that differ from the tellolink record: ROS frame (REP-103) and SI units
# (imu.acc g -> m/s^2, osd angles degrees -> rad), or a different name (baro). Other fields are
# copied from the record field of the same name.
TO_ROS = {
    'status': lambda r: {'vel_y': -r.vel_y, 'vel_z': -r.vel_z},
    'imu': _imu,
    'baro': lambda r: {'altitude_raw': r.baro_raw, 'altitude': r.baro},
    'gyro': lambda r: {f'stage{i}': flu(*st) for i, st in enumerate(r.stages)},
    'mvo': lambda r: {**vec(r, 'vel'), **vec(r, 'pos')},
    'nav': lambda r: {**vec(r, 'vel'), **vec(r, 'pos'), 'tof_vel': -r.tof_vel},
    'osd': _osd,
    'attitude_target': _attitude,
}


def field_value(v, ftype):
    """Python value -> value for a message field of type ftype."""
    if ftype.startswith('sequence<uint8'):      # bytes (Unsolved.payload, Frame.data)
        return array.array('B', v)
    if ftype.startswith('float') and '[' in ftype:
        return [float(c) for c in v]            # Gyro.stage*, Motors.pwm
    if v is None:                               # optional field missing in this record
        return math.nan if ftype.startswith('float') else -1
    if ftype.startswith('float'):
        return float(v)
    if ftype == 'boolean':
        return bool(v)
    return int(v)


class TelloNode(Node):
    """Connects to one Tello, publishes its data, forwards sticks and commands."""

    def __init__(self):
        super().__init__('tello')
        self.declare_parameter('local_ip', '')        # adapter IP; '' = any
        self.declare_parameter('connect_timeout', 10.0)

        ns = self.get_namespace().strip('/')
        prefix = ns + '/' if ns else ''
        self.base_frame = prefix + 'base_link'
        self.tof_frame = prefix + 'tof'
        self.optical_frame = prefix + 'camera_optical'

        # recv_time is time.monotonic(); this offset turns it into ROS time.
        self._time_offset_ns = self.get_clock().now().nanoseconds - time.monotonic_ns()
        self._last_cmd = None           # time.monotonic() of the last cmd_sticks

        self.pub_imu = self.create_publisher(Imu, 'raw/std/imu', 10)
        self.pub_temp = self.create_publisher(Temperature, 'raw/std/imu/temperature', 10)
        self.pub_tof = self.create_publisher(Range, 'raw/std/tof', 10)
        self.pub_battery = self.create_publisher(BatteryState, 'raw/std/battery', 10)
        self.pub_image = self.create_publisher(Image, 'raw/std/image', qos_profile_sensor_data)

        self.create_subscription(tmsg.StickCommand, 'cmd_sticks', self._on_sticks, 10)
        self.create_subscription(Bool, 'fast_mode', self._on_fast_mode, 10)
        self.create_timer(0.1, self._cmd_watchdog)
        self.create_service(Trigger, 'takeoff', self._command('takeoff'))
        self.create_service(Trigger, 'land', self._command('land'))
        self.create_service(Trigger, 'emergency', self._command('emergency'))

        self.drone = d = Tello(local_ip=self.get_parameter('local_ip').value or None)
        d.subscribe(d.EVENT_CONNECTED, lambda *_: self.get_logger().info('Tello connected.'))
        d.subscribe(d.EVENT_DISCONNECTED,
                    lambda *_: self.get_logger().warn('Tello connection lost, reconnecting...'))

        video = True
        try:
            # FFmpeg prints 'non-existing PPS' / 'decode_slice_header error' for every frame
            # until the first keyframe arrives; tellolink skips those frames anyway.
            import av.logging
            av.logging.set_level(av.logging.FATAL)
        except ImportError:
            video = False
            self.get_logger().warn("'av' not installed (sudo apt install python3-av): no video.")

        for event, topic, msg_type in RAW:
            if event == d.EVENT_FRAME and not video:
                continue
            fields = [(n, t) for n, t in msg_type.get_fields_and_field_types().items()
                      if n != 'header']
            pub = self.create_publisher(msg_type, 'raw/' + topic, 2 if topic == 'frame' else 10)
            skip = stale_imu if event == d.EVENT_IMU else None
            d.subscribe(event, self._raw_publisher(pub, msg_type, fields, TO_ROS.get(topic), skip))
        d.subscribe(d.EVENT_IMU, self._on_imu)
        d.subscribe(d.EVENT_TOF, self._on_tof)
        d.subscribe(d.EVENT_STATUS, self._on_status)
        if video:
            d.subscribe(d.EVENT_FRAME, self._on_frame)

        self.get_logger().info('Connecting to Tello...')
        try:
            d.connect(timeout=self.get_parameter('connect_timeout').value)
        except TimeoutError:
            # tellolink keeps sending connection requests in the background.
            self.get_logger().warn('Tello did not answer yet; still trying in the background.')

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    def _command(self, name):
        def handle(request, response):
            if not self.drone.connected:
                response.success, response.message = False, 'not connected'
                return response
            if name != 'takeoff':
                self._stop()
            getattr(self.drone, name)()
            response.success, response.message = True, 'sent'
            return response
        return handle

    def _stop(self):
        self.drone.set_sticks(0.0, 0.0, 0.0, 0.0)
        self._last_cmd = None

    def _on_sticks(self, msg):
        self.drone.set_sticks(pitch=msg.pitch, roll=msg.roll, yaw=msg.yaw, throttle=msg.throttle)
        self._last_cmd = time.monotonic()

    def _on_fast_mode(self, msg):
        self.drone.set_fast_mode(msg.data)
        self.get_logger().info(f"Fast mode {'on' if msg.data else 'off'}.")

    def _cmd_watchdog(self):
        last = self._last_cmd
        if last is not None and time.monotonic() - last > CMD_TIMEOUT:
            self._stop()

    # ------------------------------------------------------------------
    # Publishing (tellolink callbacks: run in tellolink's threads, keep them short)
    # ------------------------------------------------------------------
    def _stamp(self, recv_time):
        return Time(nanoseconds=int(recv_time * 1e9) + self._time_offset_ns).to_msg()

    def _raw_publisher(self, pub, msg_type, fields, convert, skip=None):
        def publish(drone, rec):
            if skip is not None and skip(rec):
                return
            ros = convert(rec) if convert else {}
            msg = msg_type()
            msg.header.stamp = self._stamp(rec.recv_time)
            for name, ftype in fields:
                v = ros[name] if name in ros else getattr(rec, name)
                setattr(msg, name, field_value(v, ftype))
            pub.publish(msg)
        return publish

    def _on_imu(self, drone, d):
        if stale_imu(d):
            return
        w, x, y, z = d.q0, d.q1, -d.q2, -d.q3         # FRD in NED -> FLU in ENU
        n = math.sqrt(w * w + x * x + y * y + z * z)
        msg = Imu()
        msg.header.stamp = self._stamp(d.recv_time)
        msg.header.frame_id = self.base_frame
        o = msg.orientation
        o.w, o.x, o.y, o.z = w / n, x / n, y / n, z / n
        a = msg.angular_velocity
        a.x, a.y, a.z = ned_to_enu(d.gyro_x, d.gyro_y, d.gyro_z)        # rad/s
        # acc is in g (specific force): at rest +9.81 m/s^2 on z, as ROS expects
        la = msg.linear_acceleration
        la.x, la.y, la.z = (GRAVITY * c for c in ned_to_enu(d.acc_x, d.acc_y, d.acc_z))
        self.pub_imu.publish(msg)

        if d.temperature is not None:
            t = Temperature()
            t.header = msg.header
            t.temperature = float(d.temperature)
            self.pub_temp.publish(t)

    def _on_tof(self, drone, d):
        msg = Range()
        msg.header.stamp = self._stamp(d.recv_time)
        msg.header.frame_id = self.tof_frame
        msg.radiation_type = Range.INFRARED
        msg.field_of_view = TOF_FOV
        msg.min_range = TOF_MIN
        msg.max_range = TOF_MAX
        msg.range = float(d.distance)
        self.pub_tof.publish(msg)

    def _on_status(self, drone, d):
        msg = BatteryState()
        msg.header.stamp = self._stamp(d.recv_time)
        msg.header.frame_id = self.base_frame
        msg.voltage = float(d.battery_voltage)
        msg.percentage = d.battery_percent / 100.0
        msg.temperature = msg.current = msg.charge = math.nan
        msg.capacity = msg.design_capacity = math.nan
        msg.power_supply_status = BatteryState.POWER_SUPPLY_STATUS_DISCHARGING
        msg.power_supply_technology = BatteryState.POWER_SUPPLY_TECHNOLOGY_LIPO
        msg.present = True
        self.pub_battery.publish(msg)

    def _on_frame(self, drone, f):
        msg = Image()
        msg.header.stamp = self._stamp(f.recv_time)
        msg.header.frame_id = self.optical_frame
        msg.height, msg.width = f.image.shape[:2]
        msg.encoding = 'bgr8'
        msg.step = msg.width * 3
        msg.data = f.image.tobytes()
        self.pub_image.publish(msg)

    def destroy_node(self):
        self._stop()
        st = self.drone.status
        if self.drone.connected and st is not None and st.em_sky:
            self.get_logger().warn('Shutting down while airborne: sending land.')
            for _ in range(3):
                self.drone.land()
                time.sleep(0.1)
        self.drone.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = TelloNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
