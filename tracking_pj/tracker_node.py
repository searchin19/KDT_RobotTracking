import rclpy
from rclpy.node import Node
import math
import numpy as np
from geometry_msgs.msg import PoseArray, Pose2D
from std_msgs.msg import String

class TrackerNode(Node):
    def __init__(self):
        super().__init__('tracker_node')
        
        self.sub_markers = self.create_subscription(PoseArray, '/detected_markers', self.marker_callback, 10)
        self.pub_action = self.create_publisher(Pose2D, '/robot_1/action', 10)
        self.sub_status = self.create_subscription(String, '/robot_1/status', self.status_callback, 10)

        self.STOP_DISTANCE = 30.0
        self.robot_status = "IDLE"

    def status_callback(self, msg):
        self.robot_status = msg.data

    def marker_callback(self, msg):
        markers = {int(p.position.z): p.position for p in msg.poses}

        # ID 0(타겟)과 ID 1(추적기)이 모두 있을 때 연산
        if 0 in markers and 1 in markers:
            p0 = markers[0]
            p1 = markers[1]

            # 3D 거리 계산 (tvec 기반)
            dist = math.sqrt((p0.x - p1.x)**2 + (p0.y - p1.y)**2 + (p0.z - p1.z)**2)
            
            # 각도 계산 (단순화를 위해 x, y 평면 기준)
            rel_angle = math.degrees(math.atan2(p0.y - p1.y, p0.x - p1.x))

            # 제어 명령 발행
            action = Pose2D()
            if dist < self.STOP_DISTANCE:
                action.x = 0.0
                action.theta = 0.0
            else:
                action.x = float(dist)
                action.theta = float(rel_angle)
            
            self.pub_action.publish(action)

def main():
    rclpy.init()
    node = TrackerNode()
    rclpy.spin(node)
    rclpy.shutdown()