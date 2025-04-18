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

# Load the trained model
model = YOLO(r'C:\Users\maxch\Documents\Purdue Files\2024 Fall\ENGT 480\GitHub\capstone_T54_gui\new_backup_gui_win\14_Apr.pt')

# Mapping of model class names to GUI button keys
CLASS_TO_BUTTON_MAP = {
    'helmet': 'hardhat',
    'glasses': 'glasses',  # This maps the model's 'glasses' class to the GUI's 'glasses' button
    'safety glasses': 'glasses',  # This also maps 'safety glasses' class to the same button
    'beardnet': 'beardnet',
    'earplugs': 'earplugs',
    'gloves': 'gloves'
}

# Global variable to store detection results
latest_detection_results = None
last_annotated_frame = None  # Add this line to store the last annotated frame

# Constants for optimization
FRAME_WIDTH = 640  # Reduced resolution
FRAME_HEIGHT = 480
DETECTION_INTERVAL = 5  # Only run detection every N frames
DISPLAY_FPS = 30  # Target FPS for display updates

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
    
    if platform.system() != "Windows":
        # Get list of available cameras on Linux
        cameras = get_linux_cameras()
        print("\nDetected cameras:")
        for cam in cameras:
            print(f"Name: {cam['name']}")
            print(f"Path: {cam['path']}")
    
    # Different capture methods based on OS
    if platform.system() == "Windows":
        capture_method = cv2.CAP_DSHOW
    else:
        capture_method = cv2.CAP_V4L2
        
    for attempt in range(max_retries):
        try:
            print(f"\nAttempt {attempt + 1}/{max_retries}...")
            
            if platform.system() == "Windows":
                cap = cv2.VideoCapture(cam_index, capture_method)
            else:
                # For Linux, try both the index and the direct device path
                device_path = f"/dev/video{cam_index}"
                print(f"Trying direct device path: {device_path}")
                cap = cv2.VideoCapture(device_path, capture_method)
                
                if not cap.isOpened():
                    print(f"Direct path failed, trying index {cam_index}")
                    cap = cv2.VideoCapture(cam_index, capture_method)
                
                if not cap.isOpened():
                    print("V4L2 failed, trying default capture method...")
                    cap = cv2.VideoCapture(cam_index)
            
            # Give the camera more time to initialize
            print("Waiting for camera initialization...")
            time.sleep(retry_delay * 2)  # Double the delay
            
            if cap.isOpened():
                print("Camera initially opened, attempting to configure...")
                
                # Set camera properties based on OS
                if platform.system() != "Windows":
                    try:
                        # First try to get current format
                        current_fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
                        print(f"Current format: {current_fourcc}")
                        
                        # Try different formats if needed
                        formats_to_try = [
                            ('M', 'J', 'P', 'G'),  # MJPG
                            ('Y', 'U', 'Y', 'V'),  # YUYV
                            None  # Try with default format
                        ]
                        
                        success = False
                        for fmt in formats_to_try:
                            try:
                                if fmt is None:
                                    print("Trying with default format")
                                    success = True
                                    break
                                    
                                fourcc = cv2.VideoWriter_fourcc(*fmt)
                                print(f"Trying format: {''.join(fmt)}")
                                if cap.set(cv2.CAP_PROP_FOURCC, fourcc):
                                    print(f"Successfully set format to {''.join(fmt)}")
                                    success = True
                                    break
                            except Exception as e:
                                print(f"Failed to set format {''.join(fmt) if fmt else 'default'}: {str(e)}")
                        
                        # Try to set other properties
                        print("\nSetting camera properties:")
                        props = {
                            'FPS': (cv2.CAP_PROP_FPS, 30),
                            'WIDTH': (cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH),
                            'HEIGHT': (cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT),
                            'BUFFERSIZE': (cv2.CAP_PROP_BUFFERSIZE, 1)
                        }
                        
                        for name, (prop, value) in props.items():
                            try:
                                original = cap.get(prop)
                                if cap.set(prop, value):
                                    actual = cap.get(prop)
                                    print(f"{name}: Original={original}, Requested={value}, Actual={actual}")
                                else:
                                    print(f"Failed to set {name}")
                            except Exception as e:
                                print(f"Error setting {name}: {str(e)}")
                        
                    except Exception as e:
                        print(f"Error during camera configuration: {str(e)}")
                        print("Continuing with default settings")
                
                # Validate camera with multiple test reads
                print(f"\nValidating camera with test reads...")
                valid_reads = 0
                frames = []
                
                for i in range(10):  # Increased test reads
                    try:
                        ret, test_frame = cap.read()
                        if ret and test_frame is not None and test_frame.size > 0:
                            valid_reads += 1
                            frames.append(test_frame.shape)
                            print(f"Test read {i+1}: Success (shape: {test_frame.shape})")
                        else:
                            print(f"Test read {i+1}: Failed (ret={ret}, frame={'None' if test_frame is None else test_frame.size})")
                        time.sleep(0.2)  # Longer delay between reads
                    except Exception as e:
                        print(f"Error during test read {i+1}: {str(e)}")
                
                print(f"\nValidation summary:")
                print(f"Valid reads: {valid_reads}/10")
                if frames:
                    print(f"Frame sizes: {frames}")
                
                # More lenient validation - accept if we get any valid frames
                if valid_reads > 0:
                    print(f"Camera validated with {valid_reads}/10 successful test reads")
                    
                    # Print final camera properties
                    props = {
                        'FOURCC': cv2.CAP_PROP_FOURCC,
                        'FPS': cv2.CAP_PROP_FPS,
                        'WIDTH': cv2.CAP_PROP_FRAME_WIDTH,
                        'HEIGHT': cv2.CAP_PROP_FRAME_HEIGHT,
                        'BRIGHTNESS': cv2.CAP_PROP_BRIGHTNESS,
                        'CONTRAST': cv2.CAP_PROP_CONTRAST,
                        'SATURATION': cv2.CAP_PROP_SATURATION,
                        'HUE': cv2.CAP_PROP_HUE,
                        'GAIN': cv2.CAP_PROP_GAIN,
                        'EXPOSURE': cv2.CAP_PROP_EXPOSURE,
                        'BUFFERSIZE': cv2.CAP_PROP_BUFFERSIZE
                    }
                    print("\nFinal Camera Properties:")
                    for prop_name, prop_id in props.items():
                        try:
                            value = cap.get(prop_id)
                            print(f"{prop_name}: {value}")
                        except:
                            print(f"{prop_name}: Failed to read")
                    
                    return cap
                else:
                    print(f"Camera validation failed (no valid frames)")
                    cap.release()
            else:
                print(f"Failed to open camera {cam_index}")
                if cap:
                    cap.release()
                    
        except Exception as e:
            print(f"Error on attempt {attempt + 1}: {str(e)}")
            if 'cap' in locals() and cap:
                cap.release()
        
        if attempt < max_retries - 1:
            print(f"Waiting {retry_delay} seconds before next attempt...")
            time.sleep(retry_delay)
    
    return None

def run_detection(callback):
    """
    Run continuous detection on webcam feed and report PPE detection status.
    
    Args:
        callback: A function that will be called with detection results.
                 The callback receives a dictionary with detection states.
    """
    # Initialize detection thread
    detection_thread = threading.Thread(target=_detection_worker, args=(callback,))
    detection_thread.daemon = True  # Thread will exit when main program exits
    detection_thread.start()
    
    return detection_thread

def _detection_worker(callback):
    """
    Worker function that runs in a separate thread to perform continuous detection.
    
    Args:
        callback: Function to call with detection results and frame
    """
    global last_annotated_frame  # Add this line
    mock_detection_states = {
        'hardhat': True,
        'glasses': True,
        'beardnet': True,
        'earplugs': True,
        'gloves': True
    }
    
    try:
        USE_MOCK_DATA = False
        
        if USE_MOCK_DATA:
            print("Using mock detection data instead of camera.")
            callback(None, None)
            while True:
                callback(mock_detection_states, None)
                time.sleep(1.0 / DISPLAY_FPS)
            return
        
        print("\nInitializing camera detection system...")
        print("----------------------------------------")
        callback(None, None)
        
        if platform.system() != "Windows":
            # Try video1 first since that's where the USB camera is
            print("\nTrying primary USB camera at /dev/video1...")
            cap = try_open_camera(1, max_retries=3, retry_delay=2.0)
            
            # If that fails, try video2
            if cap is None:
                print("\nTrying secondary USB camera at /dev/video2...")
                cap = try_open_camera(2, max_retries=2, retry_delay=2.0)
            
            # Last resort, try video0
            if cap is None:
                print("\nTrying fallback camera at /dev/video0...")
                cap = try_open_camera(0, max_retries=2, retry_delay=2.0)
        else:
            # Windows camera initialization remains the same
            print("\nTrying to open external camera...")
            cap = try_open_camera(1, max_retries=5, retry_delay=2.0)
            
            if cap is None:
                print("\nExternal camera failed, trying built-in camera...")
                cap = try_open_camera(0, max_retries=3, retry_delay=1.0)
        
        if cap is None:
            print("\nFailed to initialize any camera. Using mock data.")
            callback(None, None)
            while True:
                callback(mock_detection_states, None)
                time.sleep(1.0 / DISPLAY_FPS)
            return
            
        # Camera opened successfully, now set properties
        print("\nSetting camera properties:")
        
        # Store original properties for comparison
        orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        orig_fps = int(cap.get(cv2.CAP_PROP_FPS))
        
        print(f"Original camera properties: {orig_width}x{orig_height} @ {orig_fps}fps")
        
        print(f"Setting resolution to {FRAME_WIDTH}x{FRAME_HEIGHT}")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        
        print(f"Setting FPS to {DISPLAY_FPS}")
        cap.set(cv2.CAP_PROP_FPS, DISPLAY_FPS)
        
        print("Setting buffer size to 1")
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Verify if properties were actually set
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = int(cap.get(cv2.CAP_PROP_FPS))
        
        print(f"\nActual camera properties after setting:")
        print(f"Resolution: {actual_width}x{actual_height} (requested: {FRAME_WIDTH}x{FRAME_HEIGHT})")
        print(f"FPS: {actual_fps} (requested: {DISPLAY_FPS})")
        
        # Test frame capture with retries
        print("\nValidating camera with test captures:")
        test_frame = None
        valid_frames = 0
        
        for i in range(5):
            ret, frame = cap.read()
            if ret and frame is not None and frame.size > 0:
                test_frame = frame
                valid_frames += 1
                print(f"Test capture {i+1}: Success (shape: {frame.shape})")
            else:
                print(f"Test capture {i+1}: Failed")
            time.sleep(0.1)
        
        if valid_frames < 3:
            print(f"Camera validation failed ({valid_frames}/5 successful captures)")
            cap.release()
            callback(None, None)
            while True:
                callback(mock_detection_states, None)
                time.sleep(1.0 / DISPLAY_FPS)
            return

        print(f"\nCamera validated with {valid_frames}/5 successful captures")
        print("Starting detection loop...")
        callback(True, None)
        
        frame_count = 0
        last_detection_states = None
        last_detection_time = time.time()
        fps_start_time = time.time()
        fps_frame_count = 0
        
        while True:
            frame_start_time = time.time()
            
            ret, frame = cap.read()
            if not ret:
                print("Error reading frame from camera, retrying...")
                time.sleep(0.5)  # Add small delay before retry
                continue  # Try to read the next frame instead of breaking
            
            frame_count += 1
            fps_frame_count += 1
            
            # Calculate and print FPS every second
            if time.time() - fps_start_time >= 1.0:
                current_fps = fps_frame_count / (time.time() - fps_start_time)
                print(f"Current FPS: {current_fps:.2f}")
                fps_frame_count = 0
                fps_start_time = time.time()
            
            display_frame = frame.copy()
            
            # Only run detection every DETECTION_INTERVAL frames
            if frame_count % DETECTION_INTERVAL == 0:
                detection_start_time = time.time()
                detection_states = {
                    'hardhat': False,
                    'glasses': False,
                    'beardnet': False,
                    'earplugs': False,
                    'gloves': False
                }
                
                # Run detection on the frame
                results = model.predict(frame, conf=0.5, verbose=False)
                
                # Process detection results
                if results and len(results) > 0:
                    result = results[0]
                    
                    # Process each detected object
                    for box in result.boxes:
                        class_index = int(box.cls)
                        class_name = model.names[class_index].lower()
                        conf = float(box.conf)
                        
                        if class_name in CLASS_TO_BUTTON_MAP:
                            button_key = CLASS_TO_BUTTON_MAP[class_name]
                            detection_states[button_key] = True
                            print(f"Detected {class_name} with confidence {conf:.2f}")
                    
                    # Get the annotated frame with bounding boxes using YOLO's plot
                    display_frame = results[0].plot(
                        conf=True,      # Show confidence scores
                        labels=True,    # Show class labels
                        boxes=True,     # Show bounding boxes
                        line_width=2,   # Thicker box lines
                        font_size=18,   # Larger font
                        pil=False       # Use cv2 instead of PIL for drawing
                    )
                    last_annotated_frame = display_frame.copy()  # Store the annotated frame
                    print(f"Generated annotated frame with boxes: shape={display_frame.shape}")
                else:
                    display_frame = frame.copy()
                    last_annotated_frame = None  # Clear the stored frame if no detections
                    print("No detections in this frame")
                
                detection_time = time.time() - detection_start_time
                print(f"Detection time: {detection_time:.3f}s")
                
                last_detection_states = detection_states
                last_detection_time = time.time()
            else:
                # For frames between detections, use the last annotated frame if available
                display_frame = last_annotated_frame if last_annotated_frame is not None else frame.copy()
                detection_states = last_detection_states if last_detection_states else mock_detection_states
            
            # Convert BGR to RGB for Qt display
            display_frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            
            # Send the current detection states and frame to the GUI
            callback(detection_states, display_frame_rgb)
            
            # Calculate and maintain target frame rate
            frame_time = time.time() - frame_start_time
            sleep_time = max(0, (1.0 / DISPLAY_FPS) - frame_time)
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        print("\nCleaning up camera resources...")
        cap.release()
        cv2.destroyAllWindows()
        print("Camera cleanup complete.")
        
    except Exception as e:
        print(f"\nCritical error in detection thread:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback
        print("Traceback:")
        traceback.print_exc()
        
        print("\nFalling back to mock data due to error.")
        callback(None, None)
        
        try:
            while True:
                callback(mock_detection_states, None)
                time.sleep(1.0 / DISPLAY_FPS)
        except:
            print("Mock data loop interrupted.")