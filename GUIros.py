#!/usr/bin/env python3
# This is the GUI for the PPE Vending Machine made with Streamlit
# Author: Max Chen
# Date: 2025-01-28

import streamlit as st
import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from std_msgs.msg import String

class PPEVendingGUI(Node):
    def __init__(self):
        """Initialize the ROS2 node and GUI"""
        super().__init__('ppe_vending_gui')
        
        # Initialize ROS publishers
        self.publishers = {
            'hardhat': self.create_publisher(Bool, 'ppe/hardhat/dispense', 10),
            'beardnet': self.create_publisher(Bool, 'ppe/beardnet/dispense', 10),
            'gloves': self.create_publisher(Bool, 'ppe/gloves/dispense', 10),
            'glasses': self.create_publisher(Bool, 'ppe/glasses/dispense', 10),
            'earplugs': self.create_publisher(Bool, 'ppe/earplugs/dispense', 10),
            'safety_gate': self.create_publisher(Bool, 'safety_gate_state', 10)
        }
        
        # Initialize ROS subscriber
        self.subscription = self.create_subscription(
            String,
            'ppestate',
            self.ppe_state_callback,
            10
        )
        
        # Initialize GUI state
        self.init_session_state()
        # Store the last received message
        self.last_ppe_state = None
        # Store last published states
        self.last_published_states = {
            'hardhat': False,
            'beardnet': False,
            'gloves': False,
            'glasses': False,
            'earplugs': False,
            'safety_gate': True
        }

    def init_session_state(self):
        """Initialize session state"""
        if 'safety_gate_locked' not in st.session_state:
            st.session_state.safety_gate_locked = True
        if 'selected_item' not in st.session_state:
            st.session_state.selected_item = None
        if 'ppe_status' not in st.session_state:
            # Initialize all PPE as missing
            st.session_state.ppe_status = {
                'hardhat': False,
                'beardnet': False,
                'gloves': False,
                'glasses': False,
                'earplugs': False
            }

    def reset_system(self):
        """Reset system to initial state"""
        # Reset all PPE to missing
        for ppe in st.session_state.ppe_status:
            st.session_state.ppe_status[ppe] = False
        st.session_state.selected_item = None

    def create_ppe_button(self, label, emoji, key, status_container, disabled=False, help_text=None):
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

    def process_selection(self, item, status_container):
        """Handle PPE selection and update status"""
        st.session_state.selected_item = item
        
        # Publish dispense request first
        if not self.publish_dispense_request(item):
            status_container.markdown(
                "<div class='status'>Status: Failed to send dispense request!</div>",
                unsafe_allow_html=True
            )
            return
        
        # Create progress bar container
        progress_container = st.empty()
        
        # Update status
        status_message = f"Status: Processing request for {item}..."
        status_container.markdown(f"<div class='status'>{status_message}</div>", unsafe_allow_html=True)
        
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

    def check_all_ppe_detected(self):
        """Check if all PPE are detected"""
        return all(st.session_state.ppe_status.values())

    def publish_dispense_request(self, ppe_item):
        """Publish a request to dispense a specific PPE item"""
        try:
            # Convert item name to match topic format
            ppe_topic = ppe_item.lower().replace(' ', '')
            msg = Bool()
            msg.data = True
            self.publishers[ppe_topic].publish(msg)
            self.get_logger().info(f'Publishing dispense request for: {ppe_topic}')
            return True
        except Exception as e:
            self.get_logger().error(f'Error publishing dispense request: {e}')
            return False

    def publish_safety_gate_state(self):
        """Publish the current safety gate state"""
        try:
            current_state = st.session_state.safety_gate_locked
            if current_state != self.last_published_states['safety_gate']:
                msg = Bool()
                msg.data = current_state
                self.publishers['safety_gate'].publish(msg)
                self.last_published_states['safety_gate'] = current_state
                self.get_logger().info(f'Published safety gate state: {current_state}')
        except Exception as e:
            self.get_logger().error(f'Error publishing safety gate state: {e}')

    def update_safety_gate(self):
        """Update safety gate based on PPE detection"""
        if self.check_all_ppe_detected():
            st.session_state.safety_gate_locked = False
        else:
            st.session_state.safety_gate_locked = True
        # Publish the new state
        self.publish_safety_gate_state()

    def toggle_ppe_detection(self, ppe):
        """Toggle PPE detection status and update safety gate"""
        st.session_state.ppe_status[ppe] = not st.session_state.ppe_status[ppe]
        # Update last published state
        self.last_published_states[ppe] = st.session_state.ppe_status[ppe]
        self.update_safety_gate()

    def parse_ppe_state(self, msg):
        """Parse incoming PPE state message and update GUI status
        
        Args:
            msg: ROS message containing PPE states
                (hardhat, beardnet, gloves, glasses, earplugs)
        """
        try:
            # Assuming msg is a tuple/list of 5 boolean values
            ppe_items = ['hardhat', 'beardnet', 'gloves', 'glasses', 'earplugs']
            
            # Update session state with new values
            for ppe, state in zip(ppe_items, msg):
                st.session_state.ppe_status[ppe] = bool(state)
            
            # Store last received message
            self.last_ppe_state = msg
            
            # Update safety gate based on new states
            self.update_safety_gate()
            
            # Force GUI refresh if needed
            st.rerun()
            
        except Exception as e:
            print(f"Error parsing PPE state message: {e}")

    def ppe_state_callback(self, msg):
        """Callback for PPE state subscription"""
        try:
            # Parse the incoming string message
            # Expected format: "hardhat,beardnet,gloves,glasses,earplugs"
            states = [state.lower() == 'true' for state in msg.data.split(',')]
            if len(states) == 5:  # Ensure we got all 5 PPE states
                self.parse_ppe_state(states)
            else:
                self.get_logger().warning('Received malformed PPE state message')
        except Exception as e:
            self.get_logger().error(f'Error in PPE state callback: {e}')

    def run(self):
        """Main GUI loop"""
        st.set_page_config(
            page_title="PPE Vending Machine",
            layout="wide",
            initial_sidebar_state="collapsed"
        )
        
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
        
        # Camera placeholder
        st.markdown("### Camera Feed")
        placeholder = st.empty()
        placeholder.markdown(
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
            if self.create_ppe_button(
                "Hard Hat", "🪖", "hardhat",
                status_container,
                disabled=not st.session_state.safety_gate_locked,
                help_text="Click to dispense Hard Hat"
            ):
                self.process_selection("Hard Hat", status_container)
        
        with col2:
            if self.create_ppe_button(
                "Beard Net", "🥽", "beardnet",
                status_container,
                disabled=not st.session_state.safety_gate_locked,
                help_text="Click to dispense Beard Net"
            ):
                self.process_selection("Beard Net", status_container)
        
        with col3:
            if self.create_ppe_button(
                "Gloves", "🧤", "gloves",
                status_container,
                disabled=not st.session_state.safety_gate_locked,
                help_text="Click to dispense Gloves"
            ):
                self.process_selection("Gloves", status_container)
        
        # Second row
        col4, col5, col6 = st.columns(3)
        with col4:
            if self.create_ppe_button(
                "Safety Glasses", "👓", "glasses",
                status_container,
                disabled=not st.session_state.safety_gate_locked,
                help_text="Click to dispense Safety Glasses"
            ):
                self.process_selection("Safety Glasses", status_container)
        
        with col5:
            if self.create_ppe_button(
                "Earplugs", "🎧", "earplugs",
                status_container,
                disabled=not st.session_state.safety_gate_locked,
                help_text="Click to dispense Earplugs"
            ):
                self.process_selection("Earplugs", status_container)
        
        with col6:
            if self.create_ppe_button(
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
                self.toggle_ppe_detection(ppe)
                st.rerun()

        # Show detection status
        st.sidebar.markdown("#### Current Status")
        for ppe, detected in st.session_state.ppe_status.items():
            status = "✅ Detected" if detected else "🔴 Missing"
            st.sidebar.markdown(f"{ppe.title()}: {status}")

def main(args=None):
    rclpy.init(args=args)
    gui = PPEVendingGUI()
    
    try:
        gui.run()
    except KeyboardInterrupt:
        pass
    finally:
        # Cleanup
        gui.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
