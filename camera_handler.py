import cv2
import streamlit as st
from yolo_detector import YOLODetector

class CameraHandler:
    def __init__(self):
        self.camera = None
        self.detector = YOLODetector()
        self.detection_enabled = False
        
        # Initialize camera
        if 'camera' not in st.session_state:
            st.session_state.camera = cv2.VideoCapture(0)
            self.camera = st.session_state.camera
        else:
            self.camera = st.session_state.camera

    def release(self):
        """Release camera resources"""
        try:
            if self.camera is not None:
                self.camera.release()
                self.camera = None
            if 'camera' in st.session_state:
                del st.session_state.camera
        except Exception as e:
            st.error(f"Error releasing camera: {e}")

    def enable_detection(self, enabled=True):
        """Enable or disable YOLO detection"""
        self.detection_enabled = enabled

    def get_frame(self):
        """Get a single frame from the camera"""
        if self.camera is None or not self.camera.isOpened():
            return None

        ret, frame = self.camera.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if self.detection_enabled:
                frame = self.detector.process_frame(frame)
            return frame
        return None

    def display_feed(self, video_placeholder):
        """Display the camera feed in the given placeholder"""
        frame = self.get_frame()
        if frame is not None:
            video_placeholder.image(frame, use_container_width=True)
            
            if self.detection_enabled:
                detections = self.detector.get_detections()
                if detections:
                    st.write("Detections:", detections)