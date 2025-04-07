# Import required libraries
import time
import threading
import cv2
import ultralytics
from ultralytics import YOLO

# Load the trained model
model = YOLO(r'C:\Users\maxch\Documents\Purdue Files\2024 Fall\ENGT 480\GitHub\capstone_T54_gui\new_backup_gui_win\best.pt')

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
        callback: Function to call with detection results
    """
    # Initialize detection states dictionary for mock data
    mock_detection_states = {
        'hardhat': True,  # Set all to True for mock data
        'glasses': True,
        'beardnet': True,
        'earplugs': True,
        'gloves': True
    }
    
    try:
        # Check if we should use mock data or real camera
        USE_MOCK_DATA = False  # Set to False to use real camera detection
        
        if USE_MOCK_DATA:
            print("Using mock detection data instead of camera.")
            # Signal that camera is not available but provide mock data
            callback(None)  # First signal that camera is not available
            
            # Then start sending mock detection data periodically
            while True:
                callback(mock_detection_states)
                time.sleep(0.5)  # Update every half second
            return
        
        # Signal that we're starting camera detection
        print("Starting camera detection with OpenCV approach...")
        callback(None)  # Signal that camera is initializing
        
        # Try to open the camera
        try:
            cap = cv2.VideoCapture(1)  # Try camera index 1 (external webcam)
            if not cap.isOpened():
                cap = cv2.VideoCapture(0)  # Try camera index 0 (built-in webcam)
                
            if not cap.isOpened():
                print("Error: Could not open webcam. Using mock detection data.")
                callback(None)  # Signal that camera is not available
                
                # Use mock data instead
                while True:
                    callback(mock_detection_states)
                    time.sleep(0.5)  # Update every half second
                return
        except Exception as cam_error:
            print(f"Error accessing camera: {cam_error}")
            callback(None)  # Signal that camera is not available
            
            # Use mock data instead
            while True:
                callback(mock_detection_states)
                time.sleep(0.5)  # Update every half second
            return
            
        print("Camera opened successfully. Starting detection.")
        callback(True)  # Signal that camera is available
        
        # Run continuous detection on camera frames
        while True:
            # Read a frame from the camera
            ret, frame = cap.read()
            if not ret:
                print("Error reading frame from camera.")
                break
                
            # Initialize detection states for this frame
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
                    # Get the class index and name
                    class_index = int(box.cls)
                    class_name = model.names[class_index].lower()
                    print(f"Detected class: {class_name}")
                    
                    if class_name in CLASS_TO_BUTTON_MAP:
                        button_key = CLASS_TO_BUTTON_MAP[class_name]
                        print(f"Mapping {class_name} to button key: {button_key}")
                        detection_states[button_key] = True
                    else:
                        print(f"Warning: No mapping found for class {class_name}")
            
            # Display the frame with detection results
            if len(results) > 0:
                # Get the annotated frame from the results
                annotated_frame = results[0].plot()
                cv2.imshow("Detection Results", annotated_frame)
            else:
                cv2.imshow("Detection Results", frame)
                
            # Send the current detection states to the GUI
            print(f"Sending detection states to GUI: {detection_states}")
            callback(detection_states)
            
            # Check for key press to exit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
            # Short delay to prevent excessive CPU usage
            time.sleep(0.1)
            
        # Clean up
        cap.release()
        cv2.destroyAllWindows()
        
    except Exception as e:
        print(f"Error in detection thread: {str(e)}")
        callback(None)  # Signal that camera is not available
        
        # Fall back to mock data
        try:
            while True:
                callback(mock_detection_states)
                time.sleep(0.5)
        except:
            pass