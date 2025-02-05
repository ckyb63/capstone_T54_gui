#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import random
import time

class DummyPPEPublisher(Node):
    def __init__(self):
        super().__init__('dummy_ppe_publisher')
        
        # Create publisher
        self.publisher = self.create_publisher(
            String,
            'ppe_status',
            10)
            
        # Create timer for periodic publishing
        self.timer = self.create_timer(5.0, self.publish_ppe_status)
        
        self.get_logger().info('Dummy PPE Publisher started')

    def publish_ppe_status(self):
        """Generate and publish random PPE status"""
        # Generate random status for each PPE item
        ppe_items = ['hardhat', 'beardnet', 'gloves', 'glasses', 'earplugs']
        status = []
        
        for item in ppe_items:
            # 50% chance of each item being detected
            detected = random.choice([True, False])
            status.append(f"{item}:{detected}")
        
        # Create message
        msg = String()
        msg.data = ', '.join(status)
        
        # Publish message
        self.publisher.publish(msg)
        self.get_logger().info(f'Published PPE status: {msg.data}')

def main(args=None):
    rclpy.init(args=args)
    node = DummyPPEPublisher()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()