import rclpy
from rclpy.node import Node
import cv2
import numpy as np
from sensor_msgs.msg import Image
from geometry_msgs.msg import PoseArray, Pose
from cv_bridge import CvBridge

class ArucoDetectorNode(Node):
    def __init__(self):
        super().__init__('aruco_detector_node')
        self.bridge = CvBridge()
        
        # 카메라 파라미터 로드
        self.load_camera_params()

        # 통신 설정
        self.sub_image = self.create_subscription(Image, '/usb_camera/image_raw', self.image_callback, 10)
        self.pub_debug_img = self.create_publisher(Image, '/usb_camera/debug_image', 10)
        self.pub_marker_pose = self.create_publisher(PoseArray, '/detected_markers', 10)

        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.aruco_params = cv2.aruco.DetectorParameters_create()

    def load_camera_params(self):
        # 실제 환경이라면 npz 로드 로직 포함
        self.mtx = np.array([[1459.88, 0.0, 326.34], [0.0, 1600.67, 244.17], [0.0, 0.0, 1.0]])
        self.dist = np.array([0.00226, 9.375, -0.0115, 0.00222, -104.07])

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = cv2.aruco.detectMarkers(gray, self.aruco_dict, parameters=self.aruco_params)

        if ids is not None:
            rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(corners, 5.0, self.mtx, self.dist)
            
            # 마커 위치 정보 전송용 PoseArray 구성
            pose_msg = PoseArray()
            pose_msg.header = msg.header
            for i in range(len(ids)):
                p = Pose()
                p.position.x = tvecs[i][0][0] # x좌표
                p.position.y = tvecs[i][0][1] # y좌표
                p.position.z = float(ids[i][0]) # ID값을 z에 임시 저장 (커스텀 메시지 대용)
                pose_msg.poses.append(p)
            self.pub_marker_pose.publish(pose_msg)

            # 시각화
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)
        
        # 디버그용 이미지 발행
        self.pub_debug_img.publish(self.bridge.cv2_to_imgmsg(frame, "bgr8"))

def main():
    rclpy.init()
    node = ArucoDetectorNode()
    rclpy.spin(node)
    rclpy.shutdown()