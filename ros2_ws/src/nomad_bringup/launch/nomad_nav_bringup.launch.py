import os
import yaml

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def _load_defaults(package_share_dir: str):
    defaults = {
        "camera": {
            "use_realsense": True,
            "camera_name": "camera",
            "image_topic": "/camera/color/image_raw",
            "enable_depth": False,
            "color_profile": "640x480x30",
        },
        "navigation": {
            "model": "nomad",
            "topomap_dir": "topomap",
            "goal_node": -1,
            "waypoint": 2,
            "close_threshold": 3,
            "radius": 4,
            "num_samples": 8,
            "waypoint_topic": "/waypoint",
            "sampled_actions_topic": "/sampled_actions",
            "reached_goal_topic": "/topoplan/reached_goal",
            "cmd_vel_topic": "/cmd_vel",
        },
        "teleop": {
            "enable_teleop": False,
            "cmd_vel_topic": "/cmd_vel",
        },
    }

    config_path = os.path.join(package_share_dir, "config", "navigation_teleop.yaml")
    if not os.path.exists(config_path):
        return defaults

    with open(config_path, "r", encoding="utf-8") as cfg_file:
        loaded = yaml.safe_load(cfg_file) or {}

    for section, section_defaults in defaults.items():
        section_values = loaded.get(section, {})
        if isinstance(section_values, dict):
            section_defaults.update(section_values)

    return defaults


def generate_launch_description():
    package_share = get_package_share_directory("nomad_bringup")
    defaults = _load_defaults(package_share)

    use_realsense = LaunchConfiguration("use_realsense")
    enable_teleop = LaunchConfiguration("enable_teleop")
    image_topic = LaunchConfiguration("image_topic")
    cmd_vel_topic = LaunchConfiguration("cmd_vel_topic")

    declare_args = [
        DeclareLaunchArgument(
            "use_realsense",
            default_value=str(defaults["camera"]["use_realsense"]).lower(),
            description="Launch RealSense camera wrapper",
        ),
        DeclareLaunchArgument(
            "camera_name",
            default_value=str(defaults["camera"]["camera_name"]),
            description="RealSense camera node name",
        ),
        DeclareLaunchArgument(
            "image_topic",
            default_value=str(defaults["camera"]["image_topic"]),
            description="Image topic consumed by nomad navigation",
        ),
        DeclareLaunchArgument(
            "enable_depth",
            default_value=str(defaults["camera"]["enable_depth"]).lower(),
            description="Enable RealSense depth stream",
        ),
        DeclareLaunchArgument(
            "color_profile",
            default_value=str(defaults["camera"]["color_profile"]),
            description="RealSense color profile WxHxFPS",
        ),
        DeclareLaunchArgument(
            "model",
            default_value=str(defaults["navigation"]["model"]),
            description="Navigation model key from config/models.yaml",
        ),
        DeclareLaunchArgument(
            "topomap_dir",
            default_value=str(defaults["navigation"]["topomap_dir"]),
            description="Topomap image directory name under topomaps/images",
        ),
        DeclareLaunchArgument(
            "goal_node",
            default_value=str(defaults["navigation"]["goal_node"]),
            description="Goal node index (-1 means last node)",
        ),
        DeclareLaunchArgument(
            "waypoint",
            default_value=str(defaults["navigation"]["waypoint"]),
            description="Waypoint index to follow",
        ),
        DeclareLaunchArgument(
            "close_threshold",
            default_value=str(defaults["navigation"]["close_threshold"]),
            description="Temporal distance threshold for advancing topomap node",
        ),
        DeclareLaunchArgument(
            "radius",
            default_value=str(defaults["navigation"]["radius"]),
            description="Topomap localization search radius",
        ),
        DeclareLaunchArgument(
            "num_samples",
            default_value=str(defaults["navigation"]["num_samples"]),
            description="Number of sampled actions for diffusion model",
        ),
        DeclareLaunchArgument(
            "waypoint_topic",
            default_value=str(defaults["navigation"]["waypoint_topic"]),
            description="Waypoint topic for navigator/controller communication",
        ),
        DeclareLaunchArgument(
            "sampled_actions_topic",
            default_value=str(defaults["navigation"]["sampled_actions_topic"]),
            description="Topic for sampled actions visualization/debug",
        ),
        DeclareLaunchArgument(
            "reached_goal_topic",
            default_value=str(defaults["navigation"]["reached_goal_topic"]),
            description="Topic used to signal goal reached",
        ),
        DeclareLaunchArgument(
            "cmd_vel_topic",
            default_value=str(defaults["navigation"]["cmd_vel_topic"]),
            description="Velocity output topic",
        ),
        DeclareLaunchArgument(
            "enable_teleop",
            default_value=str(defaults["teleop"]["enable_teleop"]).lower(),
            description="Start teleop_twist_keyboard node",
        ),
    ]

    realsense_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [FindPackageShare("realsense2_camera"), "/launch/rs_launch.py"]
        ),
        condition=IfCondition(use_realsense),
        launch_arguments={
            "camera_name": LaunchConfiguration("camera_name"),
            "enable_color": "true",
            "enable_depth": LaunchConfiguration("enable_depth"),
            "rgb_camera.color_profile": LaunchConfiguration("color_profile"),
        }.items(),
    )

    navigate_node = Node(
        package="nomad_nav",
        executable="navigate",
        output="screen",
        emulate_tty=True,
        parameters=[
            {
                "image_topic": image_topic,
                "waypoint_topic": LaunchConfiguration("waypoint_topic"),
                "sampled_actions_topic": LaunchConfiguration("sampled_actions_topic"),
                "reached_goal_topic": LaunchConfiguration("reached_goal_topic"),
            }
        ],
        arguments=[
            "--model",
            LaunchConfiguration("model"),
            "--dir",
            LaunchConfiguration("topomap_dir"),
            "--goal-node",
            LaunchConfiguration("goal_node"),
            "--waypoint",
            LaunchConfiguration("waypoint"),
            "--close-threshold",
            LaunchConfiguration("close_threshold"),
            "--radius",
            LaunchConfiguration("radius"),
            "--num-samples",
            LaunchConfiguration("num_samples"),
        ],
    )

    pd_controller_node = Node(
        package="nomad_nav",
        executable="pd_controller",
        output="screen",
        emulate_tty=True,
        parameters=[
            {
                "waypoint_topic": LaunchConfiguration("waypoint_topic"),
                "reached_goal_topic": LaunchConfiguration("reached_goal_topic"),
                "cmd_vel_topic": cmd_vel_topic,
            }
        ],
    )

    teleop_node = Node(
        package="teleop_twist_keyboard",
        executable="teleop_twist_keyboard",
        output="screen",
        emulate_tty=True,
        condition=IfCondition(enable_teleop),
        remappings=[("/cmd_vel", cmd_vel_topic)],
    )

    return LaunchDescription(
        declare_args
        + [
            realsense_launch,
            navigate_node,
            pd_controller_node,
            teleop_node,
        ]
    )
