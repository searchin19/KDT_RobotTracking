import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess, DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, TextSubstitution
from launch.conditions import IfCondition
from launch.substitutions import EqualsSubstitution

def generate_launch_description():
    # 1. 실행 인자 선언
    arg_mode = DeclareLaunchArgument(
        'mode',
        default_value='real',
        description='Execution type: real or sim'
    )

    arg_user = DeclareLaunchArgument(
        'user',
        default_value='user09',
        description='User name for file paths'
    )
    
    arg_webcam_port = DeclareLaunchArgument(
        'webcam',
        default_value='/dev/video0',
        description='usb port name for webcam'
    )

    # 2. 인자 값 참조 설정
    mode        = LaunchConfiguration('mode')
    user        = LaunchConfiguration('user')
    webcam_port = LaunchConfiguration('webcam')

    # 3. 경로 동적 생성
    # ExecuteProcess의 cmd 리스트 내에서 LaunchConfiguration을 직접 조합하려면 
    # 별도의 처리가 필요하므로, 가장 안정적인 문자열 조합 방식을 사용합니다.
    app_path = PathJoinSubstitution([
        '/home', user, 'ros2_ws', 'src', 'tracking_pj', 'tracking_pj', 'app.py'
    ])

    return LaunchDescription([
        # 인자 등록 (누락하면 안 됨)
        arg_mode,
        arg_user,
        arg_webcam_port,

        # 1. 웹캠 노드 (mode가 'real'일 때만 실행)
        Node(
            package='tracking_pj',
            executable='webcam_node',
            name='webcam_node',
            condition=IfCondition(EqualsSubstitution(mode, 'real')),
            parameters=[{'device': webcam_port}] # 웹캠 포트 전달 예시
        ),

        # 2. Image 전처리 및 AruCo Mark Detect
        Node(
            package='tracking_pj',
            executable='aruco_detector_node',
            name='aruco_detector_node',
            condition=IfCondition(EqualsSubstitution(mode, 'real')),
        ),

        # 3. Tracking Path Calculator
        Node(
            package='tracking_pj',
            executable='tracker_node',
            name='tracker_node'
        ),

        # 2. 시리얼 브릿지 노드
        Node(
            package='tracking_pj',
            executable='serial_bridge_node',
            name='serial_bridge_node'
        ),

        # 3. Rosbridge WebSocket
        Node(
            package='rosbridge_server',
            executable='rosbridge_websocket',
            name='rosbridge_server'
        ),

        # 4. Web Video Server
        Node(
            package='web_video_server',
            executable='web_video_server',
            name='web_video_server'
        ),

        # 5. Flask 서버 실행
        ExecuteProcess(
            cmd=['python3', app_path],
            output='screen'
        )
    ])