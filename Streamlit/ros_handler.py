#!/usr/bin/env python3
try:
    import rospy
    from std_msgs.msg import String
    ROS_AVAILABLE = True
except ImportError:
    ROS_AVAILABLE = False
    print("ROS not available - running in mock mode")

class ROSHandler:
    def __init__(self):
        """Initialize ROS node and publishers"""
        self.is_connected = False
        
        if ROS_AVAILABLE:
            try:
                # Initialize ROS node
                rospy.init_node('ppe_vending_gui', anonymous=True)
                
                # Publishers
                self.dispense_pub = rospy.Publisher('ppe_dispense_command', String, queue_size=10)
                self.status_pub = rospy.Publisher('ppe_status', String, queue_size=10)
                
                # Subscribers (if needed)
                rospy.Subscriber('ppe_machine_status', String, self.status_callback)
                
                self.is_connected = True
                print("ROS initialized successfully")
            except Exception as e:
                print(f"ROS initialization failed: {e}")
        else:
            print("Running in mock mode - ROS commands will be printed to console")

    def publish_dispense_command(self, item):
        """Publish dispense command for specific PPE item"""
        if self.is_connected:
            try:
                self.dispense_pub.publish(item)
                return True
            except Exception as e:
                print(f"Failed to publish dispense command: {e}")
                return False
        else:
            # Mock mode - just print the command
            print(f"[MOCK] Publishing dispense command: {item}")
            return True

    def publish_status(self, status):
        """Publish GUI status"""
        if self.is_connected:
            try:
                self.status_pub.publish(status)
            except Exception as e:
                print(f"Failed to publish status: {e}")
        else:
            # Mock mode - just print the status
            print(f"[MOCK] Publishing status: {status}")

    def status_callback(self, msg):
        """Handle status messages from the vending machine"""
        if self.is_connected:
            # Handle incoming status messages
            print(f"Received status: {msg.data}")
        pass 