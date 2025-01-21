import streamlit as st
import time
import atexit
from camera_handler import CameraHandler
from ros_handler import ROSHandler

def main():
    st.set_page_config(
        page_title="PPE Vending Machine",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # Initialize running state
    if 'running' not in st.session_state:
        st.session_state.running = True

    # Initialize camera handler in session state
    if 'camera_handler' not in st.session_state:
        st.session_state.camera_handler = CameraHandler()
    
    camera_handler = st.session_state.camera_handler

    # Register cleanup
    if hasattr(st, 'session_state') and 'cleanup_registered' not in st.session_state:
        atexit.register(camera_handler.release)
        st.session_state.cleanup_registered = True

    # Add ROS handler initialization to your existing initialization section
    if 'ros_handler' not in st.session_state:
        st.session_state.ros_handler = ROSHandler()

    # Update the CSS with simpler, more direct styling
    st.markdown("""
        <style>
        .stButton>button {
            height: 60px;
            font-size: 20px;
            margin: 5px;
        }
        .title {
            font-size: 28px !important;
            margin: 0 !important;
            padding: 10px !important;
            text-align: left !important;
        }
        .status {
            font-size: 24px !important;
            text-align: left !important;
            margin: 5px !important;
        }
        .video-container {
            margin: 0 auto;
            width: 80%;
            max-width: 800px;
            position: relative;
            z-index: 1;
            margin-bottom: 0 !important;
        }
        .button-container {
            width: 100%;
            background: white;
            padding: 10px;
            border-top: 1px solid #ddd;
            margin-top: 0 !important;
        }
        /* Remove default Streamlit padding */
        .block-container {
            padding: 0 !important;
        }
        /* Remove extra spacing */
        div.stMarkdown {
            margin-bottom: 0 !important;
        }
        div.stButton {
            margin-bottom: 0 !important;
        }
        .element-container {
            margin-bottom: 0 !important;
        }
        .safety-status {
            font-size: 20px !important;
            text-align: left !important;
            margin: 5px !important;
            color: #2ecc71;  /* Green for locked status */
        }
        </style>
    """, unsafe_allow_html=True)

    # Wrap main content in a container
    with st.container():
        # Add stop button in sidebar
        with st.sidebar:
            if st.button("Stop Application", type="primary"):
                st.session_state.running = False
                camera_handler.release()
                st.stop()

        st.markdown("<div class='main-content'>", unsafe_allow_html=True)
        
        # Title
        st.markdown("<h1 class='title'>PPE Vending</h1>", unsafe_allow_html=True)
        
        # Status container
        status_container = st.empty()
        safety_status = st.empty()
        
        # Update status displays
        status_container.markdown("<div class='status'>Status: Ready to dispense...</div>", unsafe_allow_html=True)
        safety_status.markdown("<div class='safety-status'>Safety Gate: Locked</div>", unsafe_allow_html=True)

        # Video feed container
        st.markdown("<div class='video-container'>", unsafe_allow_html=True)
        video_placeholder = st.empty()
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

    # Button container
    with st.container():
        st.markdown("<div class='button-container'>", unsafe_allow_html=True)
        
        # Add back all your buttons
        col1, col2, col3 = st.columns([1,1,1])
        
        with col1:
            st.button("Hard Hat 🪖", key="hardhat",
                     use_container_width=True,
                     on_click=lambda: process_selection("Hard Hat", status_container))
                
        with col2:
            st.button("Beard Net 🥽", key="beardnet",
                     use_container_width=True,
                     on_click=lambda: process_selection("Beard Net", status_container))
                
        with col3:
            st.button("Gloves 🧤", key="gloves",
                     use_container_width=True,
                     on_click=lambda: process_selection("Gloves", status_container))

        col4, col5, col6 = st.columns([1,1,1])
        
        with col4:
            st.button("Safety Glasses 👓", key="glasses",
                     use_container_width=True,
                     on_click=lambda: process_selection("Safety Glasses", status_container))
                
        with col5:
            st.button("Earplugs 🎧", key="earplugs",
                     use_container_width=True,
                     on_click=lambda: process_selection("Earplugs", status_container))

        # Detection toggle and override
        col7, col8, col9 = st.columns([1,1,1])
        with col7:
            if st.toggle('Enable Detection', value=False, key='detection_toggle'):
                camera_handler.enable_detection(True)
            else:
                camera_handler.enable_detection(False)
        
        with col9:
            st.button("OVERRIDE", key="override", 
                     help="Administrative Override",
                     type="primary",
                     use_container_width=True,
                     on_click=lambda: process_selection("Override", status_container))
                     
        st.markdown("</div>", unsafe_allow_html=True)

    # Modified camera feed update loop
    while st.session_state.running:
        try:
            camera_handler.display_feed(video_placeholder)
            time.sleep(0.03)  # Small delay to prevent excessive updates
        except Exception as e:
            st.error(f"Camera error: {e}")
            break

    if not st.session_state.running:
        camera_handler.release()
        st.stop()

def process_selection(item, status_container):
    """Handle the PPE item selection and dispensing process"""
    st.session_state.selected_item = item
    ros_handler = st.session_state.ros_handler
    
    # Check safety gate status before proceeding
    if not ros_handler.check_safety_gate():
        status_container.markdown("<div class='status'>Error: Safety gate must be closed</div>", unsafe_allow_html=True)
        return
        
    # Create a new container for the progress bar
    progress_container = st.empty()
    
    # Update status in header
    status_message = f"Status: Processing request for {item}..."
    status_container.markdown(f"<div class='status'>{status_message}</div>", unsafe_allow_html=True)
    
    # Publish status to ROS
    ros_handler.publish_status(status_message)
    
    # Send dispense command to ROS
    if ros_handler.publish_dispense_command(item):
        # Use the container for the progress bar
        with st.spinner(text=None):
            progress_bar = progress_container.progress(0)
            for i in range(100):
                time.sleep(0.01)
                progress_bar.progress(i + 1, text=f"Processing {i+1}%")
        
        status_message = f"Status: {item} dispensed! Please collect."
    else:
        status_message = "Status: Failed to communicate with vending machine"
    
    status_container.markdown(f"<div class='status'>{status_message}</div>", unsafe_allow_html=True)
    ros_handler.publish_status(status_message)
    
    time.sleep(1)
    progress_container.empty()
    
    status_message = "Status: Ready to dispense..."
    status_container.markdown(f"<div class='status'>{status_message}</div>", unsafe_allow_html=True)
    ros_handler.publish_status(status_message)

if __name__ == "__main__":
    main()