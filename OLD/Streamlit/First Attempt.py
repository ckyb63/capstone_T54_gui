import streamlit as st
import time
import threading
from queue import Queue
import sys
import atexit

def cleanup():
    """Cleanup function to be called on exit"""
    global running
    running = False
    # Force stop any running threads
    for thread in threading.enumerate():
        if thread != threading.main_thread():
            thread._stop()

def main():
    global running
    running = True
    
    # Register cleanup function
    atexit.register(cleanup)
    
    st.set_page_config(
        page_title="PPE Vending Machine",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # Custom CSS for a more touch-friendly interface and layout
    st.markdown("""
        <style>
        .stButton>button {
            height: 60px;
            font-size: 20px;
            margin: 5px;
        }
        .big-font {
            font-size: 24px !important;
        }
        .title {
            font-size: 28px !important;
            margin-bottom: 5px !important;
            text-align: left !important;
        }
        .status {
            font-size: 24px !important;
            text-align: left !important;
            margin-bottom: 15px !important;
            line-height: 28px !important;
        }
        .video-container {
            margin: 0 auto;
            width: 80%;
            max-width: 800px;
            clear: both;
            position: fixed;  /* Fix video container position */
            top: 100px;      /* Adjust top position as needed */
            left: 50%;
            transform: translateX(-50%);
            z-index: 1;      /* Ensure video stays above elements */
        }
        .button-container {
            position: fixed;  /* Fix button container position */
            bottom: 20px;    /* Position from bottom */
            left: 0;
            right: 0;
            z-index: 2;      /* Buttons above video */
            background: white; /* Optional: add background to buttons */
            padding: 10px;
        }
        .placeholder-box {
            background-color: #808080;
            width: 100%;
            height: 400px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 24px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Title
    st.markdown("<h1 class='title'>PPE Vending</h1>", unsafe_allow_html=True)
    
    # Create a placeholder for status that can be updated
    status_container = st.empty()
    status_container.markdown("<div class='status'>Status: Ready to dispense...</div>", unsafe_allow_html=True)

    # Large centered video feed placeholder using a gray box
    st.markdown("<div class='video-container'>", unsafe_allow_html=True)
    st.markdown("<div class='placeholder-box'>Camera Feed Placeholder</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Button grid at bottom
    st.markdown("<div class='button-container'>", unsafe_allow_html=True)
    button_container = st.container()
    with button_container:
        # Create 3x2 grid layout for buttons with even spacing
        st.markdown("""
            <style>
            .stButton>button {
                width: 100%;
                margin: 10px 0;
                padding: 20px;
                font-size: 24px;
            }
            </style>
        """, unsafe_allow_html=True)
        
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

        # Override button spanning all columns
        col7, col8, col9 = st.columns([1,1,1])
        with st.container():
            st.button("OVERRIDE", key="override", 
                     help="Administrative Override",
                     type="primary",
                     use_container_width=True,
                     on_click=lambda: process_selection("Override", status_container))
    st.markdown("</div>", unsafe_allow_html=True)

def process_selection(item, status_container):
    """Handle the PPE item selection and dispensing process"""
    st.session_state.selected_item = item
    
    # Create a new container for the progress bar with no_rerun=True to prevent UI refresh
    progress_container = st.empty()
    
    # Update status in header
    status_container.markdown(f"<div class='status'>Status: Processing request for {item}...</div>", unsafe_allow_html=True)
    
    # Use the container for the progress bar with no_rerun=True
    with st.spinner(text=None):  # Spinner without darkening the UI
        progress_bar = progress_container.progress(0)
        for i in range(100):
            time.sleep(0.01)  # Reduced delay for faster processing
            progress_bar.progress(i + 1, text=f"Processing {i+1}%")
    
    status_container.markdown(f"<div class='status'>Status: {item} dispensed! Please collect.</div>", unsafe_allow_html=True)
    
    time.sleep(1)  # Reduced delay
    progress_container.empty()  # Only clear the progress bar
    status_container.markdown("<div class='status'>Status: Ready to dispense...</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()