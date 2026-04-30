import rclpy
from rclpy.node import Node
import socket
import select
import yaml
import os
import sys
from geometry_msgs.msg import Twist, Pose2D
from std_msgs.msg import Float64, String

class SerialBridgeNode(Node):
    def __init__(self):
        # 1. 노드 이름은 실행 시 Launch의 'name' 인자에 의해 결정되도록 기본값 설정
        super().__init__('serial_bridge_node')

        # 2. 파라미터 선언 (Launch 파일에서 전달받음)
        self.declare_parameter('robot_name', 'robot_0')
        self.declare_parameter('port', 12345)
        self.declare_parameter('config_path', '../config/esp_ip.yaml')

        self.robot_name     = self.get_parameter('robot_name').get_parameter_value().string_value
        self.default_port   = self.get_parameter('port').get_parameter_value().integer_value
        self.yaml_path      = self.get_parameter('config_path').get_parameter_value().string_value

        # 3. 외부 YAML 파일에서 해당 로봇의 IP 정보 로드
        self.esp32_ip = None
        self.load_config_from_yaml()

        # 4. UDP 소켓 설정 (비차단 모드)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)

        # 5. 토픽 설정
        # 하지만 명시적인 관리를 위해 robot_name 파라미터를 활용합니다.
        self.get_logger().info(f'===> [{self.robot_name}] 연결 시도 (IP: {self.esp32_ip}:{self.port})')

        # 6. Subscriber & Publisher (상대 경로 및 파라미터 기반)
        # 수동 제어 및 자동 제어 구독
        # Launch에서 namespace를 설정했다면 'cmd_vel'만 써도 '/robot_0/cmd_vel'이 됩니다.
        self.sub_manual = self.create_subscription(Twist, 'cmd_vel', self.cmd_vel_callback, 10)
        self.sub_auto = self.create_subscription(Pose2D, 'action', self.auto_action_callback, 10)
        
        # 상태 및 레이턴시 발행
        self.echo_pub = self.create_publisher(Float64, 'latency_echo', 10)
        self.status_pub = self.create_publisher(String, 'status', 10)

        # 7. 로봇 피드백 수신 타이머 (100Hz)
        self.create_timer(0.01, self.receive_feedback_callback)

    def load_config_from_yaml(self):
        if not os.path.exists(self.yaml_path):
            self.get_logger().error(f'설정 파일 없음: {self.yaml_path}')
            sys.exit(1)

        try:
            with open(self.yaml_path, 'r') as f:
                config_data = yaml.safe_load(f)
                robot_info = config_data.get('robots', {}).get(self.robot_name)

                if robot_info:
                    self.esp32_ip = robot_info['ip']
                    self.port = robot_info.get('port', self.default_port)
                else:
                    self.get_logger().error(f'YAML에 {self.robot_name} 정보가 없습니다.')
                    sys.exit(1)
        except Exception as e:
            self.get_logger().error(f'Config Load Error: {e}')
            sys.exit(1)

    def cmd_vel_callback(self, msg):
        """수동 조작(Teleop) 명령 처리"""
        linear_x = msg.linear.x
        angular_z = msg.angular.z

        # 임계값 처리 (0.1 기준)
        if linear_x > 0.1: command = 'w'
        elif linear_x < -0.1: command = 's'
        elif angular_z > 0.1: command = 'a'
        elif angular_z < -0.1: command = 'd'
        else: command = 'x'

        self._send_udp(command)

    def auto_action_callback(self, msg):
        """자동 주행(Pose2D) 명령 처리"""
        # 거리(x)가 0이면 정지, 아니면 거리와 각도 전송
        if msg.x == 0.0:
            command = "x"
        else:
            # 프로토콜 예시: D[거리],A[각도]
            command = f"D{msg.x:.2f},A{msg.yaw_:.2f}\n" # C++ 클래스 변수명 yaw_ 기준
        
        self._send_udp(command)

    def _send_udp(self, command):
        """UDP 전송 공통 로직"""
        try:
            self.sock.sendto(command.encode(), (self.esp32_ip, self.port))
            # 'x'(정지)가 아닐 때만 로그 출력하여 터미널 도배 방지
            if command != 'x':
                self.get_logger().info(f'[{self.robot_name}] 전송: {command.strip()}')
        except Exception as e:
            self.get_logger().error(f'UDP Send Error: {e}')

    def receive_feedback_callback(self):
        """ESP32로부터 오는 피드백 수신"""
        try:
            ready = select.select([self.sock], [], [], 0)
            if ready[0]:
                data, addr = self.sock.recvfrom(1024)
                if data:
                    message = data.decode('utf-8').strip()
                    if "STATUS:" in message:
                        status_msg = String()
                        status_msg.data = message.replace("STATUS:", "")
                        self.status_pub.publish(status_msg)
        except Exception:
            pass

    def destroy_node(self):
        if hasattr(self, 'sock'):
            self.sock.close()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = IntegratedSerialBridgeNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()