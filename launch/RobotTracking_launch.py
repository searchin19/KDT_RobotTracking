import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess, DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.conditions import IfCondition, LaunchConfigurationEquals
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # 1. 실행 인자 선언
    # type: 'real'이면 webcam_node 실행, 'sim'이면 미실행
    type_arg = DeclareLaunchArgument(
        'type',
        default_value='real',
        description='Execution type: real or sim'
    )

    # username: 경로 조립에 사용 (기본값은 현재 시스템 사용자 이름으로 설정 가능)
    username_arg = DeclareLaunchArgument(
        'username',
        default_value='user09',
        description='User name for file paths'
    )
	
	#신규 실행 인자 arg1 선언
    arg1_declaration = DeclareLaunchArgument(
        'arg1',
        default_value='/dev/ttyUSB0', # 예시: 기본 시리얼 포트 경로
        description='Serial port for bridge node'
    )

    # 2. 인자 값 참조 설정
    exec_type = LaunchConfiguration('type')
    username = LaunchConfiguration('username')
	arg1_val = LaunchConfiguration('arg1')

    # 3. 경로 동적 생성 (Python f-string 대신 Launch 시스템의 문자열 조합 방식 사용)
    # /home/<username>/ros2_ws/src/tracking_pj/tracking_pj/app.py
    app_path = [
        '/home/', username, '/ros2_ws/src/tracking_pj/tracking_pj/app.py'
    ]

    return LaunchDescription([
        type_arg,
        username_arg,

        # 1. 웹캠 노드 (type이 'real'일 때만 실행)
        Node(
            package='tracking_pj',
            executable='webcam_node',
            name='webcam_node',
            condition=LaunchConfigurationEquals('type', 'real')
        ),

        # 2. 시리얼 브릿지 노드
        Node(
            package='tracking_pj',
            executable='serial_bridge_node',
            name='serial_bridge_node'
			# 노드 실행 파일 뒤에 붙을 인자들 예시: --port /dev/ttyUSB0
            arguments=['--port', arg1_val]
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

        # 5. Flask 서버 실행 (동적으로 생성된 app_path 사용)
        ExecuteProcess(
            cmd=['python3', app_path],
            output='screen'
        )
    ])