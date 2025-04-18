import cv2


class CameraDriver:
    def __init__(self):       
        # Initialize OpenCV bridge
        
        # Initialize camera (assuming a USB camera for now)
        device_index = "/dev/video0"

        gst_pipeline = (
            f"nvv4l2camerasrc device={device_index} ! "
            "video/x-raw(memory:NVMM), format=UYVY, width=3840, height=2160 ! "
            "nvvidconv ! "
            "video/x-raw, format=BGRx, width=1920, height=1080 ! "
            "videoconvert ! "
            "video/x-raw, format=BGR ! appsink drop=true sync=false"
        )

        # Open video stream
        self.cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
    def display_stream(self):
        while True:
            # Capture frame-by-frame
            ret, frame = self.cap.read()

            if not ret:
                print("Error: Failed to grab frame.")
                break

            # Display the resulting frame
            cv2.imshow("Camera Stream", frame)

            # Break the loop when the user presses 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # Release the capture and close any open windows
        self.cap.release()
        cv2.destroyAllWindows()

    

if __name__ == "__main__":
    camera_driver = CameraDriver()
    camera_driver.display_stream()