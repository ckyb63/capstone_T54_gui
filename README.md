# AI PPE Vending Machine GUI

A PyQt5-based graphical user interface for an AI-powered PPE (Personal Protective Equipment) vending machine. This interface features real-time PPE detection status, automated safety gate control, and a vending interface integrated with ROS2.

## Features

### Core Functionality
- Real-time PPE detection status indicators for:
  - Hard Hat
  - Beard Net
  - Gloves
  - Safety Glasses
  - Ear Plugs
- Automated safety gate control based on PPE detection status
- Touch-friendly interface for PPE dispensing
- ROS2 integration for vending machine control
- Administrative override capability with safety confirmation

### Safety Features
- Visual status indicators (O/X) for each PPE item
- Color-coded status display (green for detected, red for missing)
- Safety gate status display with automatic locking/unlocking
- Dispense cooldown timer to prevent rapid requests
- 10-second override timer with countdown display

### System Integration
- ROS2 publishers and subscribers for:
  - PPE detection status (`ppe_status` topic)
  - Dispense requests (`pleaseDispense` topic)
  - Gate control status (`gate` topic)
- Real-time status updates and feedback
- Threaded ROS2 communication

## Project Structure

- `PyQt5/`
  - `ppe_gui.py`: Main GUI implementation with ROS2 integration
  - `dummy_ppe_status.py`: Test publisher for simulating PPE detection

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd <project-directory>
```

2. Install dependencies:

```bash
pip install PyQt5 rclpy
```

3. Set up ROS2 environment:

```bash
source /opt/ros/<ros-distro>/setup.bash
```

## Usage

1. Start the ROS2 core:

```bash
ros2 run
```

2. Run the GUI:

```bash
python3 PyQt5/ppe_gui.py
```

3. For testing, run the dummy PPE status publisher:

```bash
python3 PyQt5/dummy_ppe_status.py
```

### Interface Overview

1. Main Display:
   - Title and status message
   - Safety gate status indicator
   - Camera feed placeholder
   - PPE status grid with dispense buttons
   - Override control with countdown

2. Status Indicators:
   - Real-time PPE detection status
   - Gate lock/unlock status
   - System messages and warnings
   - Override countdown timer

3. Control Features:
   - Individual PPE dispense buttons
   - Administrative override with confirmation
   - Automatic safety gate control
   - Visual feedback for all operations

## Development

### Current Status
- Complete GUI implementation with PyQt5
- Full ROS2 integration
- Working safety controls and override system
- Simulation support for testing

### Future Integrations
- Live camera feed integration
- User authentication system
- Enhanced logging and monitoring
- Additional safety features

## Team

- GUI Development: Max Chen