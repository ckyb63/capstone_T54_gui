import streamlit as st
import time
# import cv2
# from camera_handler import CameraHandler

def main():
    # Page config must be the first Streamlit command
    st.set_page_config(
        page_title="PPE Vending Machine",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Try to import ROS, but continue if not available
    global ROS_AVAILABLE
    try:
        import rospy
        from std_msgs.msg import String
        ROS_AVAILABLE = True
    except ImportError:
        ROS_AVAILABLE = False
        st.warning("ROS (Robot Operating System) is not available. Running in simulation mode.")
    
    # Initialize session state
    init_session_state()
    vending_pub = init_ros()
    
    # Custom CSS
    st.markdown("""
        <style>
        .stButton > button {
            height: 60px;
            font-size: 20px;
            margin: 5px;
        }
        .status {
            font-size: 24px !important;
            text-align: left !important;
            margin: 5px !important;
        }
        .block-container {
            padding: 0 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Title and status
    st.title("PPE Vending Machine")
    status_container = st.empty()
    
    # Status and safety gate display
    col1, col2 = st.columns([3, 1])
    with col1:
        status_container.markdown("<div class='status'>Status: Ready to dispense...</div>", unsafe_allow_html=True)
    with col2:
        gate_status = "🟢 Gate Locked" if st.session_state.safety_gate_locked else "🔴 Gate Open"
        st.markdown(f"<div class='status'>{gate_status}</div>", unsafe_allow_html=True)
    
    # Camera feed section
    st.markdown("### Camera Feed")
    
    # Simple placeholder for camera feed
    st.markdown(
        "<div style='width:100%;height:400px;background:transparent;"
        "display:flex;align-items:center;justify-content:center;"
        "border:2px dashed #666;margin:10px 0;'>"
        "Camera Feed Placeholder</div>", 
        unsafe_allow_html=True
    )
    
    # PPE Selection Grid
    st.markdown("### PPE Selection")
    
    # First row
    col1, col2, col3 = st.columns(3)
    with col1:
        if create_ppe_button(
            "Hard Hat", "🪖", "hardhat",
            status_container,
            disabled=not st.session_state.safety_gate_locked,
            help_text="Click to dispense Hard Hat"
        ):
            process_selection("Hard Hat", status_container, vending_pub)
    
    with col2:
        if create_ppe_button(
            "Beard Net", "🥽", "beardnet",
            status_container,
            disabled=not st.session_state.safety_gate_locked,
            help_text="Click to dispense Beard Net"
        ):
            process_selection("Beard Net", status_container, vending_pub)
    
    with col3:
        if create_ppe_button(
            "Gloves", "🧤", "gloves",
            status_container,
            disabled=not st.session_state.safety_gate_locked,
            help_text="Click to dispense Gloves"
        ):
            process_selection("Gloves", status_container, vending_pub)
    
    # Second row
    col4, col5, col6 = st.columns(3)
    with col4:
        if create_ppe_button(
            "Safety Glasses", "👓", "glasses",
            status_container,
            disabled=not st.session_state.safety_gate_locked,
            help_text="Click to dispense Safety Glasses"
        ):
            process_selection("Safety Glasses", status_container, vending_pub)
    
    with col5:
        if create_ppe_button(
            "Earplugs", "🎧", "earplugs",
            status_container,
            disabled=not st.session_state.safety_gate_locked,
            help_text="Click to dispense Earplugs"
        ):
            process_selection("Earplugs", status_container, vending_pub)
    
    with col6:
        if create_ppe_button(
            "OVERRIDE", "🔓", "override",
            status_container,
            disabled=False,
            help_text="Administrative Override"
        ):
            # Mark all PPE as detected
            for ppe in st.session_state.ppe_status:
                st.session_state.ppe_status[ppe] = True
            st.session_state.safety_gate_locked = False
            st.rerun()

    # Debug controls
    st.sidebar.markdown("### Debug Controls")
    
    # Safety Gate Status Display
    st.sidebar.markdown("#### System Status")
    gate_status = "🟢 Locked" if st.session_state.safety_gate_locked else "🔴 Open"
    st.sidebar.markdown(f"Safety Gate: {gate_status}")
    
    # PPE Detection Simulation
    st.sidebar.markdown("#### PPE Detection")
    for ppe in st.session_state.ppe_status:
        if st.sidebar.button(
            f"{'✅' if st.session_state.ppe_status[ppe] else '🔴'} Toggle {ppe.title()}",
            key=f"toggle_{ppe}",
            help=f"Click to toggle {ppe} detection"
        ):
            toggle_ppe_detection(ppe)
            st.rerun()

    # Show detection status
    st.sidebar.markdown("#### Current Status")
    for ppe, detected in st.session_state.ppe_status.items():
        status = "✅ Detected" if detected else "🔴 Missing"
        st.sidebar.markdown(f"{ppe.title()}: {status}")

    # Show ROS status
    if ROS_AVAILABLE:
        st.sidebar.markdown(f"ROS: {'✅ Connected' if st.session_state.ros_connected else '❌ Disconnected'}")

def init_session_state():
    """Initialize session state"""
    if 'safety_gate_locked' not in st.session_state:
        st.session_state.safety_gate_locked = True
    if 'selected_item' not in st.session_state:
        st.session_state.selected_item = None
    if 'ppe_status' not in st.session_state:
        st.session_state.ppe_status = {
            'hardhat': False,
            'beardnet': False,
            'gloves': False,
            'glasses': False,
            'earplugs': False
        }
    # Remove camera initialization
    # if 'camera_connected' not in st.session_state:
    #     st.session_state.camera_connected = False

def init_ros():
    """Initialize ROS node and publishers"""
    if not ROS_AVAILABLE:
        return None
        
    try:
        rospy.init_node('ppe_gui', anonymous=True)
        vending_pub = rospy.Publisher('vending_commands', String, queue_size=10)
        st.session_state.ros_connected = True
        return vending_pub
    except Exception as e:
        st.error(f"Failed to initialize ROS: {e}")
        st.session_state.ros_connected = False
        return None

def send_vending_command(publisher, item):
    """Send vending command via ROS"""
    if not ROS_AVAILABLE:
        st.info(f"Simulation: Would send command to dispense {item}")
        return True
        
    if publisher is not None:
        try:
            command = f"dispense_{item.lower().replace(' ', '_')}"
            publisher.publish(String(command))
            return True
        except Exception as e:
            st.error(f"Failed to send command: {e}")
    return False

def create_ppe_button(label, emoji, key, status_container, disabled=False, help_text=None):
    """Create a PPE button with status indicator"""
    col1, col2 = st.columns([4, 1])
    
    with col1:
        clicked = st.button(
            f"{label} {emoji}",
            key=key,
            disabled=disabled,
            help=help_text,
            use_container_width=True
        )
    
    with col2:
        is_detected = st.session_state.ppe_status.get(key, False)
        status_icon = "✅" if is_detected else "🔴"
        status_text = "Detected" if is_detected else "Missing!"
        st.markdown(f"<div style='text-align: center; font-size: 20px;'>{status_icon}</div>", unsafe_allow_html=True)
    
    return clicked

def process_selection(item, status_container, vending_pub):
    """Handle PPE selection and update status"""
    st.session_state.selected_item = item
    
    # Create progress bar container
    progress_container = st.empty()
    
    # Update status
    status_message = f"Status: Processing request for {item}..."
    status_container.markdown(f"<div class='status'>{status_message}</div>", unsafe_allow_html=True)
    
    # Send vending command
    if st.session_state.ros_connected:
        send_vending_command(vending_pub, item)
    
    # Show progress
    with st.spinner(text=None):
        progress_bar = progress_container.progress(0)
        for i in range(100):
            time.sleep(0.01)
            progress_bar.progress(i + 1, text=f"Processing {i+1}%")
    
    # Update completion status
    status_message = f"Status: {item} dispensed! Please collect."
    status_container.markdown(f"<div class='status'>{status_message}</div>", unsafe_allow_html=True)
    
    time.sleep(1)
    progress_container.empty()
    
    # Reset status
    status_message = "Status: Ready to dispense..."
    status_container.markdown(f"<div class='status'>{status_message}</div>", unsafe_allow_html=True)

def check_all_ppe_detected():
    """Check if all PPE are detected"""
    return all(st.session_state.ppe_status.values())

def update_safety_gate():
    """Update safety gate based on PPE detection"""
    if check_all_ppe_detected():
        st.session_state.safety_gate_locked = False
    else:
        st.session_state.safety_gate_locked = True

def toggle_ppe_detection(ppe):
    """Toggle PPE detection status and update safety gate"""
    st.session_state.ppe_status[ppe] = not st.session_state.ppe_status[ppe]
    update_safety_gate()

# Move ROS_AVAILABLE to global scope
ROS_AVAILABLE = False

if __name__ == "__main__":
    main()
