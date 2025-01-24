import cv2
import streamlit as st
from yolo_detector import YOLODetector
import threading
import time

class CameraHandler:
    def __init__(self):
        self.cap = None
        self.frame = None
        self.running = False
        self.thread = None
        self.detector = YOLODetector()
        self.detection_enabled = False
        print("CameraHandler initialized")

    def start(self):
        """Start camera capture"""
        try:
            print("Attempting to start camera...")
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("Failed to open camera")
                return False
            
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            print("Camera opened successfully")
            self.running = True
            self.thread = threading.Thread(target=self._update_frame, daemon=True)
            self.thread.start()
            return True
            
        except Exception as e:
            print(f"Camera start error: {e}")
            self.running = False
            return False

    def _update_frame(self):
        """Continuously update frame in background"""
        print("Frame update thread started")
        while self.running:
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    if self.detection_enabled:
                        frame = self.process_frame(frame)
                    self.frame = frame
            time.sleep(0.033)  # ~30 FPS

    def stop(self):
        """Stop camera capture"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.cap:
            self.cap.release()
        self.cap = None
        self.frame = None

    def enable_detection(self, enabled=True):
        """Enable or disable YOLO detection"""
        self.detection_enabled = enabled

    def process_frame(self, frame):
        """Process a frame with YOLO detection if enabled"""
        if self.detection_enabled:
            frame = self.detector.process_frame(frame)
            # Show detections if any
            detections = self.detector.get_detections()
            if detections:
                st.write("Detections:", detections)
        return frame

    def display_feed(self, placeholder):
        """Display the current frame"""
        if self.frame is not None:
            try:
                # Convert BGR to RGB for Streamlit
                frame_rgb = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
                # Display the frame
                placeholder.image(frame_rgb, channels="RGB", use_container_width=True)
                return True
            except Exception as e:
                print(f"Error displaying frame: {e}")
        return False