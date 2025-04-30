# Import required libraries
import time
import threading
import cv2
import ultralytics
from ultralytics import YOLO
import numpy as np
import sys
import platform
import subprocess
import re
import torch

# Load the trained model
# Make sure the model path is correct for your environment
# Consider making this path configurable or relative
MODEL_PATH = r'C:\Users\maxch\Documents\Purdue Files\2024 Fall\ENGT 480\GitHub\capstone_T54_gui\new_backup_gui_win\final.pt'
try:
    model = YOLO(MODEL_PATH)
    print(f"Successfully loaded YOLO model from: {MODEL_PATH}")
except Exception as e:
    print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print(f"ERROR loading YOLO model from {MODEL_PATH}: {e}")
    print(f"Ensure the path is correct and the model file exists.")
    print(f"Falling back to mock functionality if GUI requests.")
    print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    # Set model to None or a mock object if loading fails, 
    # so the DetectionThread can handle it gracefully.
    model = None 

# Mapping of model class names to GUI button keys
CLASS_TO_BUTTON_MAP = {
    'helmet': 'hardhat',
    'glasses': 'glasses',  # This maps the model's 'glasses' class to the GUI's 'glasses' button
    'safety glasses': 'glasses',  # This also maps 'safety glasses' class to the same button
    'safety_goggles': 'glasses',
    'beardnet': 'beardnet',
    'earplugs': 'earplugs',
    'gloves': 'gloves'
}

# Global variable to store detection results - Will be moved into DetectionThread
# latest_detection_results = None 
# last_annotated_frame = None

# Constants for optimization
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
DETECTION_INTERVAL = 5  # Only run detection every N frames (Increased from 5)
DISPLAY_FPS = 60 # Target FPS for camera reads/display attempts

def print_camera_info(cap, camera_index):
    """Print detailed information about the camera"""
    if not cap.isOpened():
        print(f"Camera {camera_index} failed to open")
        return False
        
    # Get camera properties
    props = {
        'WIDTH': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        'HEIGHT': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        'FPS': int(cap.get(cv2.CAP_PROP_FPS)),
        'FORMAT': int(cap.get(cv2.CAP_PROP_FORMAT)),
        'BACKEND': cap.getBackendName(),
        'BUFFER_SIZE': int(cap.get(cv2.CAP_PROP_BUFFERSIZE))
    }
    
    print(f"\nCamera {camera_index} Information:")
    print("------------------------")
    for prop, value in props.items():
        print(f"{prop}: {value}")
    print("------------------------\n")
    return True

def get_linux_cameras():
    """Get available video devices on Linux using v4l2-ctl"""
    try:
        # Run v4l2-ctl --list-devices and capture output
        result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("\nAvailable video devices:")
            print(result.stdout)
            
            # Parse the output to get device paths
            devices = []
            current_device = None
            
            for line in result.stdout.split('\n'):
                if line.strip():
                    if not line.startswith('\t'):
                        current_device = line.strip()
                    elif line.strip().startswith('/dev/video'):
                        devices.append({
                            'name': current_device,
                            'path': line.strip()
                        })
            
            return devices
    except Exception as e:
        print(f"Error getting camera list: {str(e)}")
    
    return []

def try_open_camera(cam_index, max_retries=5, retry_delay=2.0):
    """Try to open a camera with retries"""
    print(f"\nAttempting to open camera {cam_index} (max {max_retries} attempts)...")
    print(f"Operating System: {platform.system()}")
    
    device_path = None # Store device path if found
    if platform.system() != "Windows":
        # Get list of available cameras on Linux
        cameras = get_linux_cameras()
        print("\nDetected cameras:")
        for i, cam in enumerate(cameras):
            print(f"  {i}: Name: {cam['name']}, Path: {cam['path']}")
            # Try to match cam_index to the index in the path (e.g., /dev/video1 -> index 1)
            match = re.search(r'(\d+)$', cam['path'])
            if match and int(match.group(1)) == cam_index:
                 device_path = cam['path']
                 print(f"Found matching device path for index {cam_index}: {device_path}")
                 break
        if not device_path:
             print(f"Could not find specific device path for index {cam_index}, will try index directly.")


    # Different capture methods based on OS
    if platform.system() == "Windows":
        capture_method = cv2.CAP_DSHOW
    else:
        capture_method = cv2.CAP_V4L2
        # Construct GStreamer pipeline for Jetson-like environments
        gst_pipeline_format = (
            "nvv4l2camerasrc device=/dev/video{index} ! "
            "video/x-raw(memory:NVMM), format=UYVY, width=3840, height=2160 ! "
            "nvvidconv ! "
            "video/x-raw, format=BGRx, width={width}, height={height} ! " # Use configured dimensions
            "videoconvert ! "
            "video/x-raw, format=BGR ! appsink drop=true sync=false"
        )
        gst_pipeline = gst_pipeline_format.format(index=cam_index, width=FRAME_WIDTH, height=FRAME_HEIGHT)


    for attempt in range(max_retries):
        try:
            print(f"\nAttempt {attempt + 1}/{max_retries}...")
            
            cap = None # Initialize cap to None
            if platform.system() == "Windows":
                cap = cv2.VideoCapture(cam_index, capture_method)
            else:
                # 1. Try GStreamer pipeline first
                print(f"Trying GStreamer pipeline: {gst_pipeline}")
                cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

                # 2. If GStreamer fails, try the specific device path with V4L2
                if not cap or not cap.isOpened():
                    print("GStreamer failed.")
                    if device_path:
                        print(f"Trying specific device path with V4L2: {device_path}")
                        cap = cv2.VideoCapture(device_path, capture_method)

                # 3. If specific path failed or wasn't found, try the index with V4L2
                if not cap or not cap.isOpened():
                     print(f"Trying index {cam_index} with V4L2 backend...")
                     cap = cv2.VideoCapture(cam_index, capture_method)

                # 4. If V4L2 failed, try the index with the default backend
                if not cap or not cap.isOpened():
                    print(f"V4L2 failed, trying index {cam_index} with default backend...")
                    cap = cv2.VideoCapture(cam_index)
            
            # Give the camera more time to initialize
            print("Waiting for camera initialization...")
            time.sleep(retry_delay) # Reduced wait
            
            if cap.isOpened():
                print("Camera initially opened, attempting to configure...")
                
                # Try to set desired properties (resolution, FPS, buffer)
                print("\nRequesting camera properties:")
                props_to_set = {
                    'WIDTH': (cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH),
                    'HEIGHT': (cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT),
                    'FPS': (cv2.CAP_PROP_FPS, DISPLAY_FPS), # Request desired FPS
                    'BUFFERSIZE': (cv2.CAP_PROP_BUFFERSIZE, 1) # Keep buffer low for latency
                }
                
                for name, (prop, value) in props_to_set.items():
                    try:
                        original = cap.get(prop)
                        if cap.set(prop, value):
                            # Verify if it was actually set
                            actual = cap.get(prop)
                            print(f"  {name}: Requested={value}, Original={original}, Actual={actual}")
                        else:
                            print(f"  {name}: Failed to set (requested: {value})")
                    except Exception as e:
                        print(f"  Error setting {name}: {str(e)}")
                
                # Validate camera with multiple test reads
                print("\nValidating camera with test reads...")
                valid_reads = 0
                frames = []
                
                for i in range(5): # Reduced test reads but quicker
                    try:
                        ret, test_frame = cap.read()
                        if ret and test_frame is not None and test_frame.size > 0:
                            valid_reads += 1
                            frames.append(test_frame.shape)
                            # print(f"Test read {i+1}: Success (shape: {test_frame.shape})") # Less verbose
                        else:
                            print(f"Test read {i+1}: Failed (ret={ret}, frame_size={'None' if test_frame is None else test_frame.size})")
                        # time.sleep(0.2) # Removed sleep between reads for faster validation
                    except Exception as e:
                        print(f"Error during test read {i+1}: {str(e)}")
                
                print("\nValidation summary:")
                print(f"Valid reads: {valid_reads}/5")
                if frames:
                    # Show unique frame shapes observed
                    unique_shapes = set(frames)
                    print(f"Observed frame shapes: {unique_shapes}")
                
                # Accept if we get at least a few valid frames
                if valid_reads >= 2: # Adjusted threshold
                    print(f"Camera validated with {valid_reads}/5 successful test reads.")
                    
                    # Print final confirmed camera properties
                    print("\nFinal Confirmed Camera Properties:")
                    props_to_read = {
                        'FOURCC': cv2.CAP_PROP_FOURCC,
                        'FPS': cv2.CAP_PROP_FPS,
                        'WIDTH': cv2.CAP_PROP_FRAME_WIDTH,
                        'HEIGHT': cv2.CAP_PROP_FRAME_HEIGHT,
                        'BUFFERSIZE': cv2.CAP_PROP_BUFFERSIZE,
                         # Add more relevant properties if needed for debugging
                         # 'BRIGHTNESS': cv2.CAP_PROP_BRIGHTNESS,
                         # 'CONTRAST': cv2.CAP_PROP_CONTRAST,
                         # 'SATURATION': cv2.CAP_PROP_SATURATION,
                         # 'EXPOSURE': cv2.CAP_PROP_EXPOSURE,
                    }
                    for prop_name, prop_id in props_to_read.items():
                        try:
                            value = cap.get(prop_id)
                             # Decode FOURCC if possible
                            if prop_name == 'FOURCC' and value != -1:
                                 fourcc_str = "".join([chr((int(value) >> 8 * i) & 0xFF) for i in range(4)])
                                 print(f"  {prop_name}: {fourcc_str} ({value})")
                            else:
                                 print(f"  {prop_name}: {value}")
                        except:
                            print(f"  {prop_name}: Failed to read")
                    
                    return cap
                else:
                    print(f"Camera validation failed ({valid_reads}/5 valid frames)")
                    cap.release()
            else:
                print(f"Failed to open camera using current method.")
                if cap:
                    cap.release()
                    
        except Exception as e:
            print(f"Error on attempt {attempt + 1}: {str(e)}")
            if 'cap' in locals() and cap:
                cap.release()
        
        if attempt < max_retries - 1:
            print(f"Waiting {retry_delay} seconds before next attempt...")
            time.sleep(retry_delay)
    
    print(f"All attempts to open camera {cam_index} failed.")
    return None

# !!! Removed the _detection_worker function from here !!!
# It will become a method within the DetectionThread class in main_landscape.py

# --- Main Entry Point --- 
# This function now just returns the necessary constants/model
def run_detection():
    """
    Called by DetectionThread to get necessary components.
    Returns the YOLO model object and configuration constants.
    """
    config = {
        'model': model, # The loaded YOLO model (or None if failed)
        'frame_width': FRAME_WIDTH,
        'frame_height': FRAME_HEIGHT,
        'detection_interval': DETECTION_INTERVAL,
        'display_fps': DISPLAY_FPS,
        'class_map': CLASS_TO_BUTTON_MAP
    }
    print("run_detection called, returning model and config.")
    return config

# Keep standalone testing block if desired, but update it
if __name__ == '__main__':
     print("Capstone Model script run directly.")
     print("This script primarily provides camera functions and model loading.")
     print("The main detection loop logic is now intended to be within DetectionThread.")
     
     # Example: Test camera opening
     print("\nTesting camera opening...")
     test_cap = try_open_camera(1) # Try index 1
     if test_cap:
         print("Camera test successful (simulated or real)")
         # if isinstance(test_cap, cv2.VideoCapture): test_cap.release()
     else:
         print("Camera test failed.")
         
     # Example: Test model loading was successful
     config = run_detection()
     if config['model']:
         print("\nYOLO model appears to be loaded.")
     else:
         print("\nYOLO model failed to load or is None.")