"""
robotics_data.py
Robotics engineering job role profiles.
"""

job_skill_profiles = {
    "Robotics Engineer": {
        "skills": [
            "c++", "python", "ros", "ros2", "matlab", "simulink",
            "control systems", "pid control", "kinematics", "dynamics",
            "trajectory planning", "motion planning", "sensors", "lidar",
            "camera", "imu", "encoders", "computer vision", "opencv",
            "slam", "tensorflow", "pytorch", "deep learning",
            "embedded systems", "microcontrollers", "arduino",
            "raspberry pi", "fpga", "pcb design", "cad", "solidworks",
            "autocad", "mechanical design", "linux", "git", "agile"
        ],
        "weights": {
            "c++": 5, "python": 4, "ros": 5, "control systems": 5,
            "kinematics": 4, "sensors": 4, "computer vision": 4,
            "slam": 4, "embedded systems": 4, "git": 3
        }
    },
    "Robotics Software Engineer": {
        "skills": [
            "c++", "python", "ros", "ros2", "gazebo", "rviz",
            "moveit", "navigation stack", "control systems", "path planning",
            "motion planning", "slam", "computer vision", "opencv",
            "tensorflow", "pytorch", "deep learning", "reinforcement learning",
            "sensor fusion", "kalman filter", "particle filter", "lidar",
            "camera", "imu", "linux", "ubuntu", "cmake", "git",
            "docker", "agile", "unit testing"
        ],
        "weights": {
            "c++": 5, "python": 4, "ros": 5, "ros2": 4, "gazebo": 4,
            "slam": 5, "path planning": 4, "sensor fusion": 4,
            "computer vision": 4, "git": 3
        }
    },
    "Robotics Hardware Engineer": {
        "skills": [
            "mechanical design", "cad", "solidworks", "autocad", "fusion 360",
            "3d printing", "machining", "materials science", "manufacturing",
            "electronics", "pcb design", "altium", "kicad", "eagle",
            "microcontrollers", "arduino", "raspberry pi", "stm32",
            "motors", "servos", "stepper motors", "actuators", "sensors",
            "imu", "lidar", "encoders", "power electronics", "battery systems",
            "soldering", "prototyping", "testing", "debugging", "git"
        ],
        "weights": {
            "mechanical design": 5, "cad": 5, "solidworks": 4,
            "pcb design": 4, "electronics": 5, "microcontrollers": 4,
            "actuators": 4, "sensors": 4, "prototyping": 4
        }
    },
    "Autonomous Vehicle Engineer": {
        "skills": [
            "c++", "python", "ros", "ros2", "autoware", "apollo",
            "lidar", "radar", "camera", "imu", "gps", "sensor fusion",
            "kalman filter", "ekf", "ukf", "slam", "perception",
            "object detection", "yolo", "deep learning", "tensorflow",
            "pytorch", "opencv", "path planning", "motion planning",
            "behavior planning", "control systems", "mpc", "pid",
            "carla", "lgsvl", "simulation", "linux", "ubuntu", "git",
            "docker", "automotive standards", "iso 26262"
        ],
        "weights": {
            "c++": 5, "python": 5, "ros": 5, "sensor fusion": 5,
            "slam": 5, "perception": 5, "deep learning": 4,
            "path planning": 4, "control systems": 4, "simulation": 4
        }
    },
    "Industrial Robotics Engineer": {
        "skills": [
            "plc programming", "ladder logic", "siemens", "allen bradley",
            "abb", "fanuc", "kuka", "yaskawa", "robot programming",
            "rapid", "karel", "scada", "hmi", "industrial automation",
            "pneumatics", "hydraulics", "sensors", "actuators",
            "motion control", "servo motors", "stepper motors", "vfd",
            "safety systems", "iso 10218", "ce marking", "cad",
            "solidworks", "autocad", "process improvement", "lean",
            "six sigma", "troubleshooting", "maintenance"
        ],
        "weights": {
            "plc programming": 5, "robot programming": 5, "abb": 4,
            "fanuc": 4, "kuka": 4, "industrial automation": 5,
            "motion control": 4, "safety systems": 4, "troubleshooting": 4
        }
    },
    "Drone Engineer": {
        "skills": [
            "c++", "python", "px4", "ardupilot", "mavlink", "ros",
            "gazebo", "control systems", "pid control", "kalman filter",
            "sensor fusion", "imu", "gps", "lidar", "camera",
            "computer vision", "opencv", "slam", "path planning",
            "obstacle avoidance", "deep learning", "tensorflow",
            "embedded systems", "microcontrollers", "stm32",
            "raspberry pi", "battery systems", "motors", "esc",
            "aerodynamics", "flight dynamics", "simulation", "linux",
            "git"
        ],
        "weights": {
            "c++": 5, "python": 4, "px4": 5, "ardupilot": 4,
            "control systems": 5, "sensor fusion": 4, "computer vision": 4,
            "slam": 4, "embedded systems": 4, "git": 3
        }
    }
}