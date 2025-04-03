#Import required libraries
import ultralytics
from ultralytics import YOLO
import cv2
import numpy as np

def run_detection(callback):
    """
    Run computer vision detection and call the callback function with detection results
    Args:
        callback: Function to call with detection results (dict of button_key -> bool)
    """
    #Load the trained model
    model = YOLO(r'C:\Users\maxch\Documents\Purdue Files\2024 Fall\ENGT 480\GitHub\capstone_T54_gui\new_backup_gui_win\best.pt')
    
    # Initialize video capture
    cap = cv2.VideoCapture(0)
    
    # Report initial camera status
    if not cap.isOpened():
        callback(None)  # Signal camera failure
        return
    
    # Create a named window for the video feed
    cv2.namedWindow('PPE Detection', cv2.WINDOW_NORMAL)
    
    # Initialize detection states
    detection_states = {
        'hardhat': False,
        'glasses': False,
        'beardnet': False,
        'gloves': False,
        'earplugs': False
    }
    
    while True:
        # Read frame from camera
        ret, frame = cap.read()
        if not ret:
            callback(None)  # Signal camera failure
            break
            
        # Make prediction on the frame
        results = model.track(frame, show=False, tracker="bytetrack.yaml")
        
        # Process detections
        for result in results:
            #For each frame
            for box in result.boxes:
                #Get the class index and name
                class_index = int(box.cls)
                class_name = model.names[class_index].lower()
                
                # Map detected class to button key
                button_key = None
                if class_name == 'helmet' or class_name == 'hardhat':
                    button_key = 'hardhat'
                elif class_name == 'glasses':  # Map regular glasses to safety glasses
                    button_key = 'glasses'
                elif class_name == 'beard net':
                    button_key = 'beardnet'
                elif class_name == 'gloves':
                    button_key = 'gloves'
                elif class_name == 'ear plugs':
                    button_key = 'earplugs'
                
                # Update detection state if a valid button key was found
                if button_key:
                    detection_states[button_key] = True
        
        # Call the callback with current detection states
        callback(detection_states)
        
        # Reset detection states for next frame
        detection_states = {k: False for k in detection_states}
        
        # Draw detections on frame
        annotated_frame = results[0].plot()
        
        # Show the frame
        cv2.imshow('PPE Detection', annotated_frame)
        
        # Break loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Clean up
    cap.release()
    cv2.destroyAllWindows()

'''
#Initialize detection flags
helmet_detected = False
vest_detected = False

#Iterate over the results (each corresponds to a processed frame)
for result in results:
    #For each frame
    for box in result.boxes:
        #Get the class index and name
        class_index = int(box.cls)
        class_name = model.names[class_index].lower()

        #Check if the detected class is 'helmet' or 'vest'
        if class_name == 'helmet':
            helmet_detected = True
        elif class_name == 'vest':
            vest_detected = True

        #Break early if both detections are found
        if helmet_detected and vest_detected:
            break
    if helmet_detected and vest_detected:
        break

#Print the final detection status
print(f"Helmet: {helmet_detected}, Vest: {vest_detected}")
'''