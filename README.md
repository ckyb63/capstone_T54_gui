# AI PPE Vending Machine GUI

A Streamlit-based graphical user interface for an AI-powered PPE (Personal Protective Equipment) vending machine. This interface features real-time PPE detection status, automated safety gate control, and a vending interface.

## Features

- Real-time PPE detection status indicators
- Automated safety gate control based on PPE detection
- Touch-friendly interface for PPE dispensing
- Visual progress tracking for dispensing operations
- Administrative override capability
- Debug simulation panel for testing
- Prepared integrations for:
  - Real-time camera feed with YOLO object detection
  - ROS communication for vending machine control

## Project Structure

- `mainStreamlitGUI.py`: Original GUI implementation
- `expStreamlit.py`: Enhanced version with PPE detection status and automated controls

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd <project-directory>
```

2. Install Python dependencies:

```bash
pip install streamlit
```

## Usage

Run the enhanced GUI:

```bash
streamlit run expStreamlit.py
```

### Features Overview

1. PPE Detection Status:
   - Each PPE item shows real-time detection status
   - Visual indicators (✅ Detected, 🔴 Missing)
   - Automatic safety gate control

2. Safety Gate Control:
   - Automatically opens when all PPE detected
   - Automatically closes if any PPE missing
   - Status display in main interface

3. Debug Panel:
   - Simulate PPE detection
   - Monitor system status
   - Test vending operations

4. Administrative Override:
   - Force all PPE to detected state
   - Override safety gate control
   - Reset system state

## Development

### Current Status
- Basic GUI functionality implemented
- PPE detection simulation working
- Automated safety gate control
- Status indicators for all PPE items

### Future Integrations
- Camera feed with YOLO detection
- ROS communication for physical vending
- User authentication for override
- Logging system

## Team

- GUI Development: Max Chen

## License
