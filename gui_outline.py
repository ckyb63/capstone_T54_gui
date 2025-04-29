import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGridLayout, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Basic dimensions
CAMERA_FEED_WIDTH = 400
CAMERA_FEED_HEIGHT = 300
BUTTON_WIDTH = 150
BUTTON_HEIGHT = 90

class MainWindowOutline(QMainWindow):
    """A simplified visual outline of the main application window."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GUI Outline")
        self.setMinimumSize(1024, 600)

        # Basic colors for differentiation (keeping border colors)
        self.dark_bg = "#A9A9A9"  # Dark Gray
        self.light_bg = "#E0E0E0" # Light Gray
        self.white_bg = "#FFFFFF" # White
        self.text_color = "#000000" # Black

        central_widget = QWidget()
        # Give central widget a light background for overall contrast
        central_widget.setStyleSheet(f"background-color: {self.light_bg};")
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        main_content = self._create_main_content_widget()
        main_layout.addWidget(main_content)

    def _create_main_content_widget(self):
        """Creates the main content widget holding header, status, camera/buttons."""
        main_content = QWidget()
        layout = QVBoxLayout(main_content)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)       

        layout.addWidget(self._create_header())
        layout.addWidget(self._create_status_frame())
        layout.addWidget(self._create_camera_button_section(), 1)

        main_content.setStyleSheet(f"QWidget {{ border: 1px solid blue; background-color: {self.dark_bg}; }}")
        return main_content

    def _create_header(self):
        """Creates the header layout outline."""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 10)

        help_button = QPushButton("Help")
        help_button.setFixedSize(100, 40)
        help_button.setStyleSheet(f"background-color: {self.white_bg}; border: 1px solid gray; color: {self.text_color};")

        title = QLabel("PPE Vending Machine")
        title.setFont(QFont('Arial', 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("border: 1px dashed gray;")

        settings_button = QPushButton("Settings")
        settings_button.setFixedSize(100, 40)
        settings_button.setStyleSheet(f"background-color: {self.white_bg}; border: 1px solid gray; color: {self.text_color};")

        layout.addWidget(help_button)
        layout.addStretch(1)
        layout.addWidget(title)
        layout.addStretch(1)
        layout.addWidget(settings_button)

        header_widget = QWidget()
        header_widget.setLayout(layout)
        header_widget.setStyleSheet(f"QWidget {{ border: 1px solid green; background-color: {self.light_bg}; }}")
        return header_widget

    def _create_status_frame(self):
        """Creates the status frame outline."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        frame.setStyleSheet(f"background-color: {self.light_bg}; border: 1px solid black; border-radius: 5px; padding: 5px;")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 5, 10, 5)

        gate_status = QLabel("Gate Status")
        gate_status.setFont(QFont('Arial', 14))
        gate_status.setStyleSheet(f"border: 1px dashed gray; padding: 5px; background-color: {self.white_bg}; color: {self.text_color};")

        dispensing_status = QLabel("Dispensing Status")
        dispensing_status.setFont(QFont('Arial', 14))
        dispensing_status.setStyleSheet(f"border: 1px dashed gray; padding: 5px; background-color: {self.white_bg}; color: {self.text_color};")

        layout.addWidget(gate_status)
        layout.addStretch(1)
        layout.addWidget(dispensing_status)
        return frame

    def _create_camera_button_section(self):
        """Creates the horizontal layout outline for camera and buttons."""
        layout = QHBoxLayout()
        layout.setSpacing(20)

        camera_feed = QLabel("Camera Feed")
        camera_feed.setMinimumSize(CAMERA_FEED_WIDTH, CAMERA_FEED_HEIGHT)
        camera_feed.setStyleSheet(f"background-color: {self.light_bg}; color: {self.text_color}; border: 1px solid black; border-radius: 5px;")
        camera_feed.setAlignment(Qt.AlignCenter)

        button_grid_widget = self._create_button_grid()

        layout.addWidget(camera_feed, 2)
        layout.addWidget(button_grid_widget, 1)

        section_widget = QWidget()
        section_widget.setLayout(layout)
        section_widget.setStyleSheet(f"QWidget {{ border: 1px solid red; background-color: {self.dark_bg}; }}")
        return section_widget

    def _create_button_grid(self):
        """Creates the widget containing the grid of placeholder buttons."""
        container = QWidget()
        container.setStyleSheet(f"background-color: {self.white_bg}; border: 1px solid purple; border-radius: 5px;")
        container_layout = QVBoxLayout(container)
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)

        buttons_config = [
            ("Hard Hat", 0, 0), ("Vest", 0, 1),
            ("Gloves", 1, 0), ("Glasses", 1, 1),
            ("Ear Plugs", 2, 0), ("OVERRIDE", 2, 1)
        ]

        for label, row, col in buttons_config:
            button = QPushButton(label)
            button.setFixedSize(BUTTON_WIDTH, BUTTON_HEIGHT)
            button.setStyleSheet(f"background-color: {self.white_bg}; color: {self.text_color}; border: 1px solid black; border-radius: 8px; font-weight: bold;")
            grid_layout.addWidget(button, row, col)

        container_layout.addStretch(1)
        container_layout.addLayout(grid_layout)
        container_layout.addStretch(1)
        return container

if __name__ == '__main__':
    app = QApplication(sys.argv)
    outline_window = MainWindowOutline()
    outline_window.show()
    sys.exit(app.exec()) 