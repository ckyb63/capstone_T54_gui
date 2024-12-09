# AI PPE Vending Machine GUI

A Streamlit-based graphical user interface for an AI-powered PPE (Personal Protective Equipment) vending machine. This interface integrates real-time camera feed, YOLO object detection, and ROS communication for controlling the physical vending machine.

## Features

- Real-time camera feed with YOLO object detection
- Touch-friendly interface for PPE item selection
- ROS integration for vending machine control
- Visual dispensing progress tracking
- Administrative override capability
- Clean shutdown system

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <project-directory>
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install ROS dependencies (if not already installed):
```bash
sudo apt-get install ros-noetic-desktop-full python3-rospy
```

## Usage

1. Start ROS core:
```bash
roscore
```

2. Launch the GUI:
```bash
streamlit run "First Attempt With camera.py"
```

## Project Structure

- `First Attempt With camera.py`: Main GUI application
- `camera_handler.py`: Camera feed management
- `yolo_detector.py`: YOLO object detection integration
- `ros_handler.py`: ROS communication interface

## ROS Communication

### Published Topics
- `/ppe_dispense_command`: Commands for dispensing items
- `/ppe_status`: GUI status updates

### Subscribed Topics
- `/ppe_machine_status`: Vending machine status updates

### Testing ROS Communication
Monitor topics:
```bash
rostopic echo /ppe_dispense_command
rostopic echo /ppe_status
```

## Development

### For GUI Development
Modify `First Attempt With camera.py` for:
- UI changes
- New features
- Event handling

### For ROS Integration
Modify `ros_handler.py` for:
- New ROS topics
- Custom message types
- Additional callbacks

### For Computer Vision
Modify `yolo_detector.py` for:
- YOLO model integration
- Detection parameters
- Processing pipeline

## Team

- GUI Development: [Your Name]
- ROS Integration: [Team Member]
- Computer Vision: [Team Member]

## License

[Your License]
