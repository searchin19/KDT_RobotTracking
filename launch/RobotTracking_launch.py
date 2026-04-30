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
        '/home', user, 'ros2_ws', 'src', 'kdt_robot_tracking', 'kdt_robot_tracking', 'app.py'
    ])

    return LaunchDescription([
        # 인자 등록 (누락하면 안 됨)
        arg_mode,
        arg_user,
        arg_webcam_port,

        # ros <==> gazebo bridge. mode가 'sim'일 때만 실행되도록 설정.
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name='gz_bridge',
            arguments=[
                # 카메라 영상 브릿지 (GZ -> ROS)
                '/usb_camera/image_raw@sensor_msgs/msg/Image[gz.msgs.Image',
                # 로봇 위치 정보 브릿지 (GZ -> ROS) - 필요 시 추가
                # 문법(name remaping) : /<ROS_토픽>@<ROS_타입>[<GZ_타입>@<GZ_토픽>
                '/robot_0/pos@geometry_msgs/msg/Pose[gz.msgs.Pose@/model/robot_0/pose',
                '/robot_1/pos@geometry_msgs/msg/Pose[gz.msgs.Pose@/model/robot_1/pose'
            ],
            condition=LaunchConfigurationEquals('mode', 'sim'), # 시뮬레이션 모드에서만 실행
            output='screen'
        ),


        # 1. 웹캠 노드 (mode가 'real'일 때만 실행)
        Node(
            package='kdt_robot_tracking',
            executable='webcam_node',
            name='webcam_node',
            condition=IfCondition(EqualsSubstitution(mode, 'real')),
            parameters=[{'port': webcam_port}] # 웹캠 포트 전달 예시
        ),

        # 2. Image 전처리 및 AruCo Mark Detect
        Node(
            package='kdt_robot_tracking',
            executable='aruco_detector_node',
            name='aruco_detector_node',
            condition=IfCondition(EqualsSubstitution(mode, 'real')),
        ),

        # 3. Tracking Path Calculator
        Node(
            package='kdt_robot_tracking',
            executable='tracker_node',
            name='tracker_node'
        ),

        # 4. ROS <==> machine(ESP32) 통신 bridge
        Node(
            package='kdt_robot_tracking',
            executable='serial_bridge_node',
            name='serial_bridge_node_0',
            namespace='robot_0',
            parameters=[{'robot_name': 'robot_0'}],
            output='screen'
        ),
        Node(
            package='kdt_robot_tracking',
            executable='serial_bridge_node',
            name='serial_bridge_node_1',
            namespace='robot_1',
            parameters=[{'robot_name': 'robot_1'}],
            output='screen'
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