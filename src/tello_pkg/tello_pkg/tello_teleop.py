"""
Keyboard teleop for tello_ros: publishes cmd_sticks and calls the takeoff / land / emergency services.

Run in the drone's namespace (keys work while the window has focus):
    ros2 run tello_pkg tello_teleop --ros-args -r __ns:=/tello1

Keys:
    T takeoff    L land    P emergency (motors stop, the drone falls if airborne)
    W / S forward / back    A / D left / right
    Up / Down rise / descend    Left / Right turn
    ESC or closing the window quits (cmd_sticks stops; tello_ros then sets the sticks to 0)
"""
import os

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame  # noqa: E402
import rclpy  # noqa: E402
from rclpy.node import Node  # noqa: E402
from std_srvs.srv import Trigger  # noqa: E402
from tello_interfaces.msg import StickCommand  # noqa: E402

RATE = 20.0     # cmd_sticks publish rate (Hz)


class TeleopNode(Node):
    """Keyboard -> cmd_sticks and flight commands."""

    def __init__(self):
        super().__init__('tello_teleop')
        # stick fractions 0..1, as in tellolink's keyboard_control.py
        self.declare_parameter('speed', 0.3)        # forward / back / sideways
        self.declare_parameter('vertical', 0.3)
        self.declare_parameter('turn', 0.3)
        self.pub = self.create_publisher(StickCommand, 'cmd_sticks', 10)
        self.actions = {
            pygame.K_t: ('takeoff', self.create_client(Trigger, 'takeoff')),
            pygame.K_l: ('land', self.create_client(Trigger, 'land')),
            pygame.K_p: ('emergency', self.create_client(Trigger, 'emergency')),
        }
        self.status = 'ready'

    def call(self, key):
        name, client = self.actions[key]
        if not client.service_is_ready():
            self.status = f'{name}: tello_ros not running'
            return
        self.status = f'{name}: sending'
        client.call_async(Trigger.Request()).add_done_callback(lambda f: self._done(name, f))

    def _done(self, name, future):
        r = future.result()
        self.status = f"{name}: {r.message}"
        self.get_logger().info(self.status)

    def sticks(self, pressed):
        speed, vertical, turn = (self.get_parameter(p).value
                                 for p in ('speed', 'vertical', 'turn'))
        msg = StickCommand()          # Tello signs: right +, forward +, clockwise +, up +
        msg.pitch = float(pressed[pygame.K_w] - pressed[pygame.K_s]) * speed
        msg.roll = float(pressed[pygame.K_d] - pressed[pygame.K_a]) * speed
        msg.throttle = float(pressed[pygame.K_UP] - pressed[pygame.K_DOWN]) * vertical
        msg.yaw = float(pressed[pygame.K_RIGHT] - pressed[pygame.K_LEFT]) * turn
        return msg


def main(args=None):
    rclpy.init(args=args)
    node = TeleopNode()
    pygame.init()
    screen = pygame.display.set_mode((560, 150))
    pygame.display.set_caption(f'Tello teleop {node.get_namespace()}')
    font = pygame.font.SysFont(None, 24)
    clock = pygame.time.Clock()
    try:
        running = True
        while running and rclpy.ok():
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in node.actions:
                        node.call(event.key)
            msg = node.sticks(pygame.key.get_pressed())
            node.pub.publish(msg)
            rclpy.spin_once(node, timeout_sec=0)

            screen.fill((30, 30, 30))
            lines = [
                'T takeoff   L land   P emergency   ESC quit',
                'WASD move   Up/Down rise/descend   Left/Right turn',
                f'sticks  pitch {msg.pitch:+.1f}  roll {msg.roll:+.1f}  '
                f'throttle {msg.throttle:+.1f}  yaw {msg.yaw:+.1f}',
                node.status,
            ]
            for i, line in enumerate(lines):
                screen.blit(font.render(line, True, (230, 230, 230)), (12, 12 + 32 * i))
            pygame.display.flip()
            clock.tick(RATE)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.pub.publish(StickCommand())    # stop
        pygame.quit()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
