#!/usr/bin/env python3
"""
Experimental PPE Vending Machine GUI Node
--------------------------------------
A resizable version of the PPE Vending Machine GUI that adapts layout based on window orientation.
Integrates with ROS2 for real-time PPE detection status and vending control.

Author: Max Chen
Version: 0.3.1
"""

import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QWidget, 
                            QGridLayout, QLabel, QVBoxLayout, QHBoxLayout,
                            QDialog, QTabWidget,
                            QFormLayout, QSpinBox, QDoubleSpinBox, QComboBox,
                            QTextEdit, QFrame)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QVariantAnimation, pyqtProperty
from PyQt5.QtGui import QFont, QColor
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool
import threading
import time
import os
import signal
from contextlib import contextmanager
import json
from datetime import datetime

@contextmanager
def ros_context():
    """Context manager for ROS initialization and shutdown"""
    try:
        rclpy.init()
        yield
    finally:
        try:
            rclpy.shutdown()
        except Exception:
            pass

class ROSNode(Node):
    def __init__(self):
        super().__init__('ppe_gui_node')
        
        # Create subscriber for PPE status
        self.subscription = self.create_subscription(
            String,
            'ppe_status',
            self.ppe_status_callback,
            10)
        
        # Create publisher for dispense requests
        self.dispense_publisher = self.create_publisher(
            String,
            'pleaseDispense',
            10)
            
        # Create publisher for gate status
        self.gate_publisher = self.create_publisher(
            Bool,
            'gate',
            10)
        
        # Reference to GUI (will be set later)
        self.gui = None
        
        self.get_logger().info('ROS Node initialized')

    def ppe_status_callback(self, msg):
        """Handle incoming PPE status messages"""
        if self.gui and not self.gui.is_shutting_down:
            # Use signal to update GUI
            self.gui.status_update_signal.emit(msg.data)
            self.get_logger().info(f'Received PPE status: {msg.data}')

    def publish_dispense_request(self, ppe_name):
        """Publish a request to dispense a PPE item"""
        msg = String()
        msg.data = ppe_name
        self.dispense_publisher.publish(msg)
        self.get_logger().info(f'Published dispense request for: {ppe_name}')

    def publish_gate_status(self, is_locked):
        """Publish safety gate status"""
        msg = Bool()
        msg.data = is_locked
        self.gate_publisher.publish(msg)
        self.get_logger().info(f'Published gate status: {"locked" if is_locked else "unlocked"}')

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("PPE Vending Machine Help")
        self.setModal(True)
        # Remove close button
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)
        
        # Create main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Title section
        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title_layout.setAlignment(Qt.AlignCenter)
        
        # Replace emoji with simple text
        help_icon = QLabel("?")  # Simple question mark
        help_icon.setFont(QFont('Arial', 48, QFont.Bold))
        help_icon.setStyleSheet(f"""
            QLabel {{
                color: {parent.colors.primary};
                background-color: {parent.colors.surface};
                border-radius: 40px;
                padding: 10px;
                min-width: 80px;
                min-height: 80px;
            }}
        """)
        help_icon.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(help_icon)
        
        title_text = QLabel("USER HELP GUIDE")
        title_text.setFont(QFont('Arial', 36, QFont.Bold))
        title_text.setStyleSheet(f"color: {parent.colors.primary};")
        title_layout.addWidget(title_text)
        
        layout.addWidget(title_widget)
        
        # Help text
        help_text = """
<h2>PPE Detection:</h2>
<ul style='font-size: 14pt;'>
<li>The camera will detect the presence of required PPE</li>
<li>Green buttons (O) indicate detected PPE</li>
<li>Red buttons (X) indicate missing PPE</li>
<li>The user may need to rotate head, look left and right, to fully detect all required PPE</li>
</ul>

<h2>Dispensing:</h2>
<ul style='font-size: 14pt;'>
<li>Click on the missing PPE button to dispense that item</li>
<li>The safety gate remains locked until all required PPE is detected</li>
</ul>

<h2>Safety Override:</h2>
<ul style='font-size: 14pt;'>
<li>Orange OVERRIDE button for emergency or administrative override</li>
<li>It will log the user and time of the override</li>
</ul>
"""
        text_label = QLabel(help_text)
        text_label.setTextFormat(Qt.RichText)
        text_label.setWordWrap(True)
        text_label.setStyleSheet(f"""
            QLabel {{
                background: {parent.colors.surface};
                color: {parent.colors.text};
                border-radius: 10px;
                padding: 20px;
                margin: 0 10px;
            }}
        """)
        layout.addWidget(text_label)
        
        # Remove accessibility toggle container and settings button
        # Add button container for accessibility and OK buttons
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setSpacing(40)
        
        # Accessibility toggle button with fixed width
        self.toggle_button = QPushButton("Accessibility O/X OFF" if not parent.accessibility_mode else "Accessibility O/X ON")
        self.toggle_button.setFont(QFont('Arial', 20, QFont.Bold))
        self.toggle_button.setFixedSize(400, 80)  # Fixed width and height
        self.toggle_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {parent.colors.success if parent.accessibility_mode else parent.colors.neutral};
                color: white;
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {parent.colors.success if parent.accessibility_mode else '#555'};
            }}
        """)
        self.toggle_button.clicked.connect(self.toggle_accessibility)
        
        # OK button
        ok_button = QPushButton("OK")
        ok_button.setFont(QFont('Arial', 20, QFont.Bold))
        # Calculate width based on text width plus padding
        text_width = ok_button.fontMetrics().boundingRect("OK").width()
        ok_button.setFixedSize(text_width + 40, 80)  # Add 40px padding (20px each side)
        ok_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {parent.colors.primary};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 0 20px;  /* Horizontal padding */
            }}
            QPushButton:hover {{
                background-color: {parent.colors.primary_dark};
            }}
        """)
        ok_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.toggle_button)
        button_layout.addWidget(ok_button)
        
        layout.addWidget(button_container)
        
        # Match parent window size exactly
        parent_geometry = parent.geometry()
        self.setGeometry(parent_geometry)
        
        # No need for manual positioning since we're matching parent exactly
        
        # Set dialog styling
        self.setStyleSheet(f"""
            QDialog {{
                background: {parent.colors.background};
            }}
            QLabel {{
                color: {parent.colors.text};
            }}
            QPushButton {{
                border-radius: 10px;
                margin: 0 40px;
            }}
        """)

    def toggle_accessibility(self):
        """Toggle accessibility mode"""
        self.parent.accessibility_mode = not self.parent.accessibility_mode
        self.toggle_button.setText("Accessibility O/X ON" if self.parent.accessibility_mode else "Accessibility O/X OFF")
        self.toggle_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.parent.colors.success if self.parent.accessibility_mode else self.parent.colors.neutral};
                color: white;
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {self.parent.colors.success if self.parent.accessibility_mode else '#555'};
            }}
        """)
        self.parent.update_status_displays()

    def show_settings(self):
        """Show the settings dialog"""
        if not hasattr(self, 'settings_dialog') or not self.settings_dialog:
            self.settings_dialog = SettingsDialog(self)
            # Remove all window decorations
            self.settings_dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        
        # Get current main window position and size
        main_pos = self.parent.geometry()
        
        # Move dialog to match main window exactly
        self.settings_dialog.setGeometry(
            main_pos.x(),
            main_pos.y(),
            main_pos.width(),
            main_pos.height()
        )
        self.settings_dialog.show()

class ColoredButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._color = "#ff6b6b"  # Default red
        self._animation = QVariantAnimation()
        self._animation.setDuration(300)  # 300ms transition
        self._animation.valueChanged.connect(self._updateStyleSheet)
        
    @pyqtProperty(str)
    def color(self):
        return self._color
        
    @color.setter
    def color(self, color):
        if self._color != color:
            self._animation.stop()
            self._animation.setStartValue(self._color)
            self._animation.setEndValue(color)
            self._animation.start()
            self._color = color
            
    def _updateStyleSheet(self, color):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self._darken(color)};
            }}
            QPushButton:pressed {{
                background-color: {self._darken(color, 0.2)};
            }}
        """)
        
    def _darken(self, color, factor=0.1):
        # Helper function to darken a color
        c = QColor(color)
        h, s, v, a = c.getHsv()
        return QColor.fromHsv(h, s, int(v * (1 - factor)), a).name()

class OverrideLogger:
    def __init__(self, log_file="override_log.json"):
        self.log_file = log_file
        self.logs = self._load_logs()
        
    def _load_logs(self):
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
        
    def log_override(self, reason=""):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "reason": reason
        }
        self.logs.append(log_entry)
        self._save_logs()
        
    def _save_logs(self):
        with open(self.log_file, 'w') as f:
            json.dump(self.logs, f, indent=2)
            
    def get_recent_logs(self, limit=10):
        return self.logs[-limit:]

class ColorScheme:
    def __init__(self, is_dark=False):
        self.is_dark = is_dark
        self.update_colors()
        
    def update_colors(self):
        if self.is_dark:
            self.background = "#1e1e1e"
            self.surface = "#2d2d2d"
            self.text = "#ffffff"
            self.text_secondary = "#aaaaaa"
            self.primary = "#007bff"
            self.primary_dark = "#0056b3"
            self.success = "#28a745"
            self.warning = "#ffc107"
            self.danger = "#dc3545"
            self.neutral = "#666666"
        else:
            self.background = "#ffffff"
            self.surface = "#f8f9fa"
            self.text = "#000000"
            self.text_secondary = "#666666"
            self.primary = "#007bff"
            self.primary_dark = "#0056b3"
            self.success = "#4caf50"
            self.warning = "#ff9800"
            self.danger = "#ff6b6b"
            self.neutral = "#666666"

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Settings")
        self.setModal(True)
        # Remove close button
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)
        
        # Create main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Title section
        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title_layout.setAlignment(Qt.AlignCenter)
        
        settings_icon = QLabel("⚙️")
        settings_icon.setObjectName("settings_icon")  # Set object name
        settings_icon.setFont(QFont('Arial', 48, QFont.Bold))
        settings_icon.setStyleSheet(f"""
            QLabel {{
                color: {parent.colors.primary};
                background-color: {parent.colors.surface};
                border-radius: 40px;
                padding: 10px;
                min-width: 80px;
                min-height: 80px;
            }}
        """)
        settings_icon.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(settings_icon)
        
        title_text = QLabel("SETTINGS")
        title_text.setFont(QFont('Arial', 36, QFont.Bold))
        title_text.setStyleSheet(f"color: {parent.colors.primary};")
        title_layout.addWidget(title_text)
        
        layout.addWidget(title_widget)
        
        # Create tabs
        tabs = QTabWidget()
        tabs.setFont(QFont('Arial', 12))
        tabs.addTab(self._create_colors_tab(), "Appearance")
        tabs.addTab(self._create_inventory_tab(), "Inventory")
        tabs.addTab(self._create_timing_tab(), "Timing")
        tabs.addTab(self._create_override_log_tab(), "Override Log")
        
        layout.addWidget(tabs)
        
        # Add save button that spans the width
        save_button = QPushButton("Save")
        save_button.setFont(QFont('Arial', 20, QFont.Bold))
        save_button.setMinimumHeight(80)
        save_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {parent.colors.primary};
                color: white;
                border: none;
                border-radius: 10px;
                margin: 0 40px;
            }}
            QPushButton:hover {{
                background-color: {parent.colors.primary_dark};
            }}
            QPushButton:pressed {{
                background-color: #004085;
            }}
        """)
        save_button.clicked.connect(self.accept)
        
        layout.addWidget(save_button)
        
        # Match parent window size exactly
        parent_geometry = parent.geometry()
        self.setGeometry(parent_geometry)
        
        # Store initial values for cancel
        self.initial_theme = parent.colors.is_dark
        self.initial_override_duration = parent.override_duration
        self.initial_cooldown = parent.dispense_cooldown
        self.initial_accessibility = parent.accessibility_mode
        
        # Set dialog styling
        self.setStyleSheet(f"""
            QDialog {{
                background: {parent.colors.background};
            }}
            QLabel {{
                color: {parent.colors.text};
            }}
            QWidget {{
                background-color: {parent.colors.background};
                color: {parent.colors.text};
            }}
            QTabWidget::pane {{
                border: 1px solid {parent.colors.neutral};
                background: {parent.colors.surface};
                border-radius: 5px;
            }}
            QTabBar::tab {{
                background: {parent.colors.surface};
                color: {parent.colors.text};
                padding: 10px 20px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }}
            QTabBar::tab:selected {{
                background: {parent.colors.primary};
                color: white;
            }}
            QTextEdit {{
                background-color: {parent.colors.surface};
                color: {parent.colors.text};
                border: 1px solid {parent.colors.neutral};
                border-radius: 5px;
                padding: 5px;
            }}
            QSpinBox, QDoubleSpinBox, QComboBox {{
                background-color: {parent.colors.surface};
                color: {parent.colors.text};
                border: 1px solid {parent.colors.neutral};
                border-radius: 5px;
                padding: 5px;
                min-height: 30px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: none;
                width: 20px;
                height: 20px;
                background: {parent.colors.primary};
                border-radius: 10px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {parent.colors.surface};
                color: {parent.colors.text};
                selection-background-color: {parent.colors.primary};
                selection-color: white;
                border: 1px solid {parent.colors.neutral};
            }}
        """)

    def _create_colors_tab(self):
        widget = QWidget()
        widget.setObjectName("colors_tab")
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignTop)
        layout.setSpacing(20)
        
        # Color scheme section
        scheme_label = QLabel("Color Scheme:")
        scheme_label.setFont(QFont('Arial', 16))
        layout.addWidget(scheme_label)
        
        self.color_scheme = QComboBox()
        self.color_scheme.setObjectName("color_scheme")
        self.color_scheme.setFont(QFont('Arial', 14))
        self.color_scheme.addItems(["Light", "Dark"])
        self.color_scheme.setCurrentText("Dark" if self.parent.colors.is_dark else "Light")
        self.color_scheme.currentTextChanged.connect(self.apply_theme_preview)
        layout.addWidget(self.color_scheme)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"background-color: {self.parent.colors.neutral};")
        layout.addWidget(separator)
        
        # Accessibility section
        access_label = QLabel("Accessibility:")
        access_label.setFont(QFont('Arial', 16))
        layout.addWidget(access_label)
        
        self.settings_toggle_button = QPushButton("Accessibility O/X OFF" if not self.parent.accessibility_mode else "Accessibility O/X ON")
        self.settings_toggle_button.setFont(QFont('Arial', 14, QFont.Bold))
        self.settings_toggle_button.setFixedHeight(50)
        self.settings_toggle_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.parent.colors.success if self.parent.accessibility_mode else self.parent.colors.neutral};
                color: white;
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {self.parent.colors.success if self.parent.accessibility_mode else '#555'};
            }}
        """)
        self.settings_toggle_button.clicked.connect(self.toggle_accessibility_settings)
        layout.addWidget(self.settings_toggle_button)
        
        layout.addStretch()
        return widget

    def _create_timing_tab(self):
        widget = QWidget()
        widget.setObjectName("timing_tab")
        layout = QFormLayout(widget)
        
        # Create spinboxes with labels
        override_label = QLabel("Override Duration (s):")
        override_label.setStyleSheet(f"color: {self.parent.colors.text};")
        self.override_duration_spin = QSpinBox()
        self.override_duration_spin.setObjectName("override_duration")
        self.override_duration_spin.setRange(5, 30)
        self.override_duration_spin.setValue(int(self.parent.override_duration))
        
        cooldown_label = QLabel("Cooldown Time (s):")
        cooldown_label.setStyleSheet(f"color: {self.parent.colors.text};")
        self.cooldown_time_spin = QDoubleSpinBox()
        self.cooldown_time_spin.setObjectName("cooldown_time")
        self.cooldown_time_spin.setRange(0.5, 5.0)
        self.cooldown_time_spin.setValue(self.parent.dispense_cooldown)
        
        status_label = QLabel("Status Message Duration (s):")
        status_label.setStyleSheet(f"color: {self.parent.colors.text};")
        self.status_duration_spin = QSpinBox()
        self.status_duration_spin.setObjectName("status_duration")
        self.status_duration_spin.setRange(1, 10)
        self.status_duration_spin.setValue(3)
        
        layout.addRow(override_label, self.override_duration_spin)
        layout.addRow(cooldown_label, self.cooldown_time_spin)
        layout.addRow(status_label, self.status_duration_spin)
        
        return widget

    def _create_inventory_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Add inventory tracking (placeholder)
        layout.addWidget(QLabel("Inventory tracking will be implemented here"))
        
        return widget
        
    def _create_override_log_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Show recent override logs
        log_text = QTextEdit()
        log_text.setReadOnly(True)
        log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.parent.colors.surface};
                color: {self.parent.colors.text};
                border: 1px solid {self.parent.colors.neutral};
                border-radius: 5px;
                padding: 10px;
                font-size: 12pt;
            }}
        """)
        
        recent_logs = self.parent.override_logger.get_recent_logs()
        log_text.setText("\n".join([
            f"{log['timestamp']}: {log['reason']}"
            for log in recent_logs
        ]))
        
        layout.addWidget(log_text)
        
        return widget

    def accept(self):
        """Apply settings before closing"""
        # Store current help dialog state
        had_help_open = False
        help_dialog_pos = None
        if hasattr(self.parent, 'help_dialog') and self.parent.help_dialog is not None:
            had_help_open = self.parent.help_dialog.isVisible()
            help_dialog_pos = self.parent.help_dialog.pos()
            self.parent.help_dialog.close()
            self.parent.help_dialog = None
        
        # Apply color scheme
        is_dark = self.color_scheme.currentText() == "Dark"
        theme_changed = is_dark != self.parent.colors.is_dark
        
        if theme_changed:
            self.parent.colors.is_dark = is_dark
            self.parent.colors.update_colors()
            self.parent.apply_theme()
        
        # Apply timing settings
        timing_tab = self.findChild(QWidget, "timing_tab")
        if timing_tab:
            override_duration = timing_tab.findChild(QSpinBox, "override_duration")
            cooldown_time = timing_tab.findChild(QDoubleSpinBox, "cooldown_time")
            status_duration = timing_tab.findChild(QSpinBox, "status_duration")
            
            if override_duration:
                self.parent.override_duration = float(override_duration.value())
            if cooldown_time:
                self.parent.dispense_cooldown = float(cooldown_time.value())
            if status_duration:
                self.parent.status_message_duration = float(status_duration.value())
        
        # Reopen help dialog if it was open
        if had_help_open:
            # Ensure old dialog is fully closed
            if self.parent.help_dialog:
                self.parent.help_dialog.close()
                self.parent.help_dialog = None
            
            # Create fresh dialog
            QTimer.singleShot(100, lambda: self.reopen_help_dialog(help_dialog_pos))
        
        super().accept()
    
    def reopen_help_dialog(self, pos=None):
        """Reopen help dialog with proper theme"""
        self.parent.help_dialog = HelpDialog(self.parent)
        if pos:
            self.parent.help_dialog.move(pos)
        self.parent.help_dialog.show()

    def reject(self):
        """Restore original values when canceling"""
        # Restore theme
        if self.parent.colors.is_dark != self.initial_theme:
            self.parent.colors.is_dark = self.initial_theme
            self.parent.colors.update_colors()
            self.parent.apply_theme()
        
        # Restore timing values
        self.parent.override_duration = self.initial_override_duration
        self.parent.dispense_cooldown = self.initial_cooldown
        
        # Restore accessibility mode
        if self.parent.accessibility_mode != self.initial_accessibility:
            self.parent.accessibility_mode = self.initial_accessibility
            self.parent.update_status_displays()
        
        super().reject()

    def save_settings(self):
        """Save settings and return to main view"""
        # Get settings content from the current widget
        settings_tabs = self.main_layout.itemAt(0).widget().findChild(QTabWidget)
        
        # Apply color scheme
        colors_tab = settings_tabs.findChild(QWidget, "colors_tab")
        if colors_tab:
            color_scheme = colors_tab.findChild(QComboBox, "color_scheme")
            if color_scheme:
                is_dark = color_scheme.currentText() == "Dark"
                if is_dark != self.colors.is_dark:
                    self.colors.is_dark = is_dark
                    self.colors.update_colors()
                    self.apply_theme()
        
        # Apply timing settings
        timing_tab = settings_tabs.findChild(QWidget, "timing_tab")
        if timing_tab:
            override_duration = timing_tab.findChild(QSpinBox, "override_duration")
            cooldown_time = timing_tab.findChild(QDoubleSpinBox, "cooldown_time")
            status_duration = timing_tab.findChild(QSpinBox, "status_duration")
            
            if override_duration:
                self.override_duration = float(override_duration.value())
            if cooldown_time:
                self.dispense_cooldown = float(cooldown_time.value())
            if status_duration:
                self.status_message_duration = float(status_duration.value())
        
        # Return to main view
        self.switchContent()

    def toggle_accessibility_settings(self):
        """Toggle accessibility mode from settings screen"""
        self.accessibility_mode = not self.accessibility_mode
        self.settings_toggle_button.setText("Accessibility O/X ON" if self.accessibility_mode else "Accessibility O/X OFF")
        self.settings_toggle_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors.success if self.accessibility_mode else self.colors.neutral};
                color: white;
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {self.colors.success if self.accessibility_mode else '#555'};
            }}
        """)
        self.update_status_displays()

    def apply_theme_preview(self):
        """Apply theme changes in real-time"""
        is_dark = self.color_scheme.currentText() == "Dark"
        if is_dark != self.colors.is_dark:
            self.colors.is_dark = is_dark
            self.colors.update_colors()
            self.apply_theme()

    def cancel_settings(self):
        """Cancel settings changes and return to main view"""
        # Restore theme
        if self.colors.is_dark != self.initial_settings['is_dark']:
            self.colors.is_dark = self.initial_settings['is_dark']
            self.colors.update_colors()
            self.apply_theme()
        
        # Restore timing values
        self.override_duration = self.initial_settings['override_duration']
        self.dispense_cooldown = self.initial_settings['dispense_cooldown']
        
        # Restore accessibility mode
        if self.accessibility_mode != self.initial_settings['accessibility_mode']:
            self.accessibility_mode = self.initial_settings['accessibility_mode']
            self.update_status_displays()
        
        # Return to main view
        self.switchContent()

class ExperimentalPPEVendingMachine(QMainWindow):
    # Add signals for thread-safe updates
    shutdown_signal = pyqtSignal()
    status_update_signal = pyqtSignal(str)
    gate_status_signal = pyqtSignal(bool)
    
    def __init__(self, ros_node):
        super().__init__()
        self.ros_node = ros_node
        self.is_shutting_down = False
        
        # Initialize override logger
        self.override_logger = OverrideLogger()
        
        # Initialize color scheme
        self.colors = ColorScheme()
        
        # Add accessibility setting
        self.accessibility_mode = False
        
        # Initialize PPE status
        self.ppe_status = {
            'hardhat': False,
            'beardnet': False,
            'gloves': False,
            'glasses': False,
            'earplugs': False
        }
        self.safety_gate_locked = True
        
        # Cooldown tracking
        self.last_dispense_time = 0
        self.dispense_cooldown = 1.0  # 1 second cooldown
        self.current_ppe = None  # Add this line
        
        # Create main widget and layout
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QVBoxLayout(self.main_widget)
        
        # Initialize resize timer
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.handleResize)
        
        # Initialize UI elements
        self.initUI()
        
        # Initialize timers after UI elements exist
        self.setupTimers()
        
        # Connect signals to slots
        self.status_update_signal.connect(self.handle_status_update)
        self.gate_status_signal.connect(self.handle_gate_status)
        
        # Enable mouse tracking
        self.setMouseTracking(True)
        self.centralWidget().setMouseTracking(True)
        
        # Set window properties
        self.setWindowTitle('PPE Vending Machine')
        self.setMinimumSize(300, 240)
        self.setFixedSize(600, 900)  # Set fixed size to match original GUI
        self.center()
        
        # Initial layout update
        self.updateLayout()
        
        # Show the window
        self.show()

    def setupTimers(self):
        """Initialize all timers"""
        # Override reset timer
        self.override_timer = QTimer()
        self.override_timer.timeout.connect(self.reset_override)
        self.override_timer.setSingleShot(True)
        self.override_duration = 10.0
        
        # Override countdown timer
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_timer.setInterval(1000)
        self.time_remaining = self.override_duration
        
        # Status update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status_displays)
        self.timer.start(100)
        
        # Status message timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.reset_status)
        self.status_timer.setSingleShot(True)
        
        # Dispense completion timer
        self.dispense_complete_timer = QTimer()
        self.dispense_complete_timer.setSingleShot(True)
        self.dispense_complete_timer.timeout.connect(self.show_dispense_complete)

    def center(self):
        """Center window on screen"""
        frame = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        center_point = QApplication.desktop().screenGeometry(screen).center()
        frame.moveCenter(center_point)
        self.move(frame.topLeft())

    def initUI(self):
        """Initialize UI elements"""
        # Create all widgets
        self.createTitleSection()
        self.createStatusSection()
        self.createCameraSection()
        self.createPPEGrid()
        
        # Window setup
        self.setWindowTitle('Experimental PPE Vending Machine')
        self.setMinimumSize(650, 900)  # Set minimum size same as starting size
        self.resize(650, 900)  # Set initial window size

    def createTitleSection(self):
        """Create title section"""
        self.title_widget = QWidget()
        header_layout = QHBoxLayout(self.title_widget)
        
        # Help button container with fixed size
        help_container = QWidget()
        help_container.setFixedSize(40, 40)
        help_layout = QHBoxLayout(help_container)
        help_layout.setContentsMargins(0, 0, 0, 0)
        
        # Help button (left)
        help_button = QPushButton("?")
        help_button.setFont(QFont('Arial', 16, QFont.Bold))
        help_button.setFixedSize(40, 40)
        help_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors.primary};
                color: white;
                border-radius: 20px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.colors.primary_dark};
            }}
        """)
        help_button.clicked.connect(self.show_help)
        help_layout.addWidget(help_button)
        
        header_layout.addWidget(help_container)
        
        # Add stretch before title for centering
        header_layout.addStretch(1)
        
        title = QLabel('PPE Vending Machine')
        title.setFont(QFont('Arial', 24, QFont.Bold))
        header_layout.addWidget(title)
        
        # Add stretch between title and settings button
        header_layout.addStretch(1)
        
        # Settings button (right)
        settings_button = QPushButton("⚙️")
        settings_button.setFont(QFont('Arial', 16, QFont.Bold))
        settings_button.setFixedSize(40, 40)
        settings_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors.primary};
                color: white;
                border-radius: 20px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.colors.primary_dark};
            }}
        """)
        settings_button.clicked.connect(self.show_settings)
        header_layout.addWidget(settings_button)

    def createStatusSection(self):
        """Create status section"""
        self.status_widget = QWidget()
        status_layout = QVBoxLayout(self.status_widget)
        
        # Status line widget (contains both gate status and status message)
        status_line = QWidget()
        status_layout_line = QHBoxLayout(status_line)
        
        # Gate status
        self.gate_status = QLabel('Gate LOCKED')
        self.gate_status.setFont(QFont('Arial', 20, QFont.Bold))
        self.gate_status.setStyleSheet(f"""
            QLabel {{
                color: {self.colors.danger};
                font-weight: bold;
                padding: 5px;
            }}
        """)
        status_layout_line.addWidget(self.gate_status)
        
        # Add stretch to push gate status and status label apart
        status_layout_line.addStretch(1)
        
        # Status message
        self.status_label = QLabel('Ready to dispense...')
        self.status_label.setFont(QFont('Arial', 18, QFont.Bold))
        self.status_label.setStyleSheet(f"color: {self.colors.text};")
        status_layout_line.addWidget(self.status_label)
        
        status_layout.addWidget(status_line)

    def createCameraSection(self):
        """Create camera feed section"""
        self.camera_widget = QWidget()
        camera_layout = QVBoxLayout(self.camera_widget)
        
        # Camera feed placeholder
        self.camera_placeholder = QLabel('Camera Feed Placeholder')
        self.camera_placeholder.setFont(QFont('Arial', 14))
        self.updateCameraPlaceholder()  # Initial styling
        self.camera_placeholder.setAlignment(Qt.AlignCenter)
        camera_layout.addWidget(self.camera_placeholder)

    def updateCameraPlaceholder(self):
        """Update camera placeholder styling based on theme"""
        self.camera_placeholder.setStyleSheet(f"""
            QLabel {{
                border: 2px dashed {self.colors.neutral};
                background: {self.colors.surface};
                color: {self.colors.text_secondary};
                min-height: 400px;
                padding: 10px;
            }}
        """)

    def createPPEGrid(self):
        """Create PPE buttons grid"""
        self.ppe_buttons = {}
        
        ppe_items = [
            ('Hard Hat', 'hardhat'),
            ('Beard Net', 'beardnet'),
            ('Gloves', 'gloves'),
            ('Safety Glasses', 'glasses'),
            ('Ear Plugs', 'earplugs'),
            ('OVERRIDE', 'override')
        ]
        
        for label, key in ppe_items:
            # Create container for button
            container = QWidget()
            layout = QHBoxLayout(container)
            
            # Create button
            button = ColoredButton(label)
            button.setFont(QFont('Arial', 16, QFont.Bold))
            button.setMinimumHeight(80)
            button.setStyleSheet("""
                QPushButton {
                    background-color: #ff6b6b;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                    padding: 10px;
                }
                QPushButton:hover {
                    background-color: #ff5252;
                }
                QPushButton:pressed {
                    background-color: #ff3838;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                }
            """)
            button.clicked.connect(lambda checked, k=key: self.on_ppe_button_click(k))
            
            # Add to layout
            layout.addWidget(button)
            
            self.ppe_buttons[key] = container

    def resizeEvent(self, event):
        """Handle window resize events"""
        super().resizeEvent(event)
        # Use timer to prevent too frequent updates
        self.resize_timer.start(100)

    def handleResize(self):
        """Update layout based on window size"""
        self.updateLayout()

    def updateLayout(self):
        """Update layout based on window size"""
        # Clear main layout while keeping widgets
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
        
        # Get current window dimensions
        width = self.width()
        height = self.height()
        
        if width > height:  # Landscape mode
            # Create landscape container
            landscape = QWidget()
            landscape_layout = QHBoxLayout(landscape)
            
            # Left panel
            left_widget = QWidget()
            left_layout = QVBoxLayout(left_widget)
            
            # Add widgets to left panel
            self.title_widget.show()
            self.status_widget.show()
            left_layout.addWidget(self.title_widget)
            left_layout.addWidget(self.status_widget)
            
            # Add button grid
            grid_widget = QWidget()
            grid = QGridLayout(grid_widget)
            positions = [
                ('hardhat', 0, 0), ('beardnet', 0, 1),
                ('glasses', 1, 0), ('earplugs', 1, 1),
                ('gloves', 2, 0), ('override', 2, 1)
            ]
            
            for key, row, col in positions:
                if key in self.ppe_buttons:
                    self.ppe_buttons[key].show()
                    grid.addWidget(self.ppe_buttons[key], row, col)
            
            left_layout.addWidget(grid_widget)
            
            # Right panel (camera)
            self.camera_widget.show()
            landscape_layout.addWidget(left_widget, 1)
            landscape_layout.addWidget(self.camera_widget, 2)
            
            self.main_layout.addWidget(landscape)
        else:
            # Portrait layout
            portrait = QWidget()
            layout = QVBoxLayout(portrait)
            
            # Add widgets
            self.title_widget.show()
            self.status_widget.show()
            self.camera_widget.show()
            layout.addWidget(self.title_widget)
            layout.addWidget(self.status_widget)
            layout.addWidget(self.camera_widget, 1)
            
            # Create button grid
            grid_widget = QWidget()
            grid = QGridLayout(grid_widget)
            positions = [
                ('hardhat', 0, 0), ('beardnet', 0, 1), ('gloves', 0, 2),
                ('glasses', 1, 0), ('earplugs', 1, 1), ('override', 1, 2)
            ]
            
            for key, row, col in positions:
                if key in self.ppe_buttons:
                    self.ppe_buttons[key].show()
                    grid.addWidget(self.ppe_buttons[key], row, col)
            
            layout.addWidget(grid_widget)
            
            self.main_layout.addWidget(portrait)
        
        # Force layout update
        self.main_layout.update()

    def confirm_override(self):
        """Show confirmation dialog for override"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Confirm Override")
        dialog.setModal(True)
        
        # Create main layout
        layout = QVBoxLayout(dialog)
        layout.setSpacing(20)
        
        # Warning icon and text
        warning_widget = QWidget()
        warning_layout = QHBoxLayout(warning_widget)
        warning_layout.setAlignment(Qt.AlignCenter)
        
        warning_icon = QLabel("⚠️")
        warning_icon.setFont(QFont('Arial', 48))
        warning_icon.setStyleSheet(f"color: {self.colors.warning};")
        warning_layout.addWidget(warning_icon)
        
        warning_text = QLabel("WARNING")
        warning_text.setFont(QFont('Arial', 36, QFont.Bold))
        warning_text.setStyleSheet(f"color: {self.colors.warning};")
        warning_layout.addWidget(warning_text)
        
        layout.addWidget(warning_widget)
        
        # Message text
        message = QLabel("Are you sure you want to override\nthe safety system?")
        message.setFont(QFont('Arial', 24))
        message.setAlignment(Qt.AlignCenter)
        message.setWordWrap(True)
        message.setStyleSheet(f"color: {self.colors.text};")
        
        info_text = QLabel("This will unlock the safety gate for 10 seconds.")
        info_text.setFont(QFont('Arial', 18))
        info_text.setAlignment(Qt.AlignCenter)
        info_text.setWordWrap(True)
        info_text.setStyleSheet(f"color: {self.colors.text_secondary};")
        
        # Add message and info text to layout
        layout.addWidget(message)
        layout.addWidget(info_text)
        
        # Form layout for dropdowns
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(15)
        
        # User dropdown
        user_combo = QComboBox()
        user_combo.setFont(QFont('Arial', 14))
        user_combo.addItems(["Select User", "Operator", "Supervisor", "Admin", "Maintenance"])
        user_combo.setCurrentText("Select User")
        user_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colors.surface};
                color: {self.colors.text};
                border: 1px solid {self.colors.neutral};
                border-radius: 5px;
                padding: 8px;
                min-width: 200px;
                min-height: 40px;
            }}
        """)
        
        # Reason dropdown
        reason_combo = QComboBox()
        reason_combo.setFont(QFont('Arial', 14))
        reason_combo.addItems([
            "Select Reason",
            "PPE Not Detected",
            "System Maintenance",
            "Emergency Override",
            "Admin Access",
            "Calibration Required"
        ])
        reason_combo.setCurrentText("Select Reason")
        reason_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colors.surface};
                color: {self.colors.text};
                border: 1px solid {self.colors.neutral};
                border-radius: 5px;
                padding: 8px;
                min-width: 200px;
                min-height: 40px;
            }}
        """)
        
        # Add dropdowns to form
        form_layout.addRow("User:", user_combo)
        form_layout.addRow("Reason:", reason_combo)
        
        # Style form labels
        for label in form_widget.findChildren(QLabel):
            label.setFont(QFont('Arial', 14))
            label.setStyleSheet(f"color: {self.colors.text};")
        
        layout.addWidget(form_widget)
        
        # Buttons
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setSpacing(20)
        
        no_button = QPushButton("NO")
        no_button.setFont(QFont('Arial', 20, QFont.Bold))
        no_button.setMinimumSize(200, 80)
        no_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors.neutral};
                color: white;
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: #555;
            }}
            QPushButton:pressed {{
                background-color: #444;
            }}
        """)
        no_button.clicked.connect(dialog.reject)
        
        yes_button = QPushButton("YES")
        yes_button.setFont(QFont('Arial', 20, QFont.Bold))
        yes_button.setMinimumSize(200, 80)
        yes_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors.warning};
                color: white;
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: #f57c00;
            }}
            QPushButton:pressed {{
                background-color: #ef6c00;
            }}
        """)
        
        # Custom accept handler to validate selections
        def handle_accept():
            if user_combo.currentText() == "Select User":
                self.show_status("Please select a user", "red")
                return
            if reason_combo.currentText() == "Select Reason":
                self.show_status("Please select a reason", "red")
                return
            # Log the override with user and reason
            self.override_logger.log_override(f"User: {user_combo.currentText()} - Reason: {reason_combo.currentText()}")
            dialog.accept()
        
        yes_button.clicked.connect(handle_accept)
        
        button_layout.addWidget(no_button)
        button_layout.addWidget(yes_button)
        
        layout.addWidget(button_widget)
        
        # Set dialog size and styling
        dialog.setStyleSheet(f"""
            QDialog {{
                background: {self.colors.background};
                min-width: 600px;
                min-height: 500px;
            }}
            QLabel {{
                color: {self.colors.text};
            }}
        """)
        
        # Center the dialog on the parent window
        parent_geometry = self.geometry()
        dialog_width = 600
        dialog_height = 500
        
        x = parent_geometry.x() + (parent_geometry.width() - dialog_width) // 2
        y = parent_geometry.y() + (parent_geometry.height() - dialog_height) // 2
        
        dialog.setGeometry(x, y, dialog_width, dialog_height)
        
        return dialog.exec_() == QDialog.Accepted

    def on_ppe_button_click(self, ppe_name):
        """Handle PPE button clicks"""
        current_time = time.time()
        
        if ppe_name == 'override':
            if not self.confirm_override():
                return
            
            # Log the override
            self.override_logger.log_override("Manual override activated")
            
            for ppe in self.ppe_status:
                self.ppe_status[ppe] = True
            self.safety_gate_locked = False
            
            self.ros_node.publish_dispense_request('OVERRIDE')
            self.ros_node.publish_gate_status(self.safety_gate_locked)
            
            self.ppe_buttons['override'].setEnabled(False)
            self.override_timer.start(int(self.override_duration * 1000))
            
            self.time_remaining = self.override_duration
            self.update_countdown()
            self.countdown_timer.start()
            
            self.show_status(f"Override activated for {int(self.override_duration)}s!", "orange")
            
        else:
            if current_time - self.last_dispense_time < self.dispense_cooldown:
                remaining = round(self.dispense_cooldown - (current_time - self.last_dispense_time), 1)
                self.show_status(f"Please wait {remaining}s before next request", "red")
                return
            
            # Store current PPE for dispense completion message
            self.current_ppe = ppe_name
            
            # Show requesting status instead of dispensing
            self.show_status(f"Requesting {ppe_name.title()}...", "blue")
            
            self.ros_node.publish_dispense_request(ppe_name)
            self.ros_node.publish_gate_status(self.safety_gate_locked)
            
            self.last_dispense_time = current_time
            
            # Disable button during cooldown
            button = self.ppe_buttons[ppe_name].layout().itemAt(0).widget()
            button.setEnabled(False)
            
            # Set timer to re-enable button and show completion message
            QTimer.singleShot(int(self.dispense_cooldown * 1000), 
                            lambda: self.handle_dispense_complete(ppe_name))
        
        self.update_safety_gate()
        self.update_status_displays()

    def handle_dispense_complete(self, ppe_name):
        """Handle completion of dispense action"""
        # Re-enable button
        button = self.ppe_buttons[ppe_name].layout().itemAt(0).widget()
        button.setEnabled(True)
        
        # Show completion message
        self.show_status(f"{ppe_name.title()} Dispensed!", "green")
        
        # Start auto-reset timer
        self.status_timer.start(3000)

    def update_countdown(self):
        """Update the override countdown display"""
        self.time_remaining -= 1
        if self.time_remaining > 0:
            self.show_status(f"Override active: {int(self.time_remaining)}s", "orange")
        else:
            self.countdown_timer.stop()
            self.reset_override()

    def reset_override(self):
        """Reset system after override period"""
        for ppe in self.ppe_status:
            self.ppe_status[ppe] = False
        
        self.safety_gate_locked = True
        self.ros_node.publish_gate_status(self.safety_gate_locked)
        self.ppe_buttons['override'].setEnabled(True)
        
        self.countdown_timer.stop()
        
        self.show_status("Override period ended", "blue")
        # Start auto-reset timer to return to ready state
        self.status_timer.start(3000)
        
        self.update_status_displays()

    def show_status(self, message, color="black"):
        """Show status message with color and auto-reset"""
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"""
            color: {color};
            font-weight: bold;
        """)
        
        # Cancel any pending auto-reset
        self.status_timer.stop()
        
        # Only start auto-reset timer for regular status messages
        if ("Override" not in message and 
            "Requesting" not in message and
            "Dispensed" not in message):
            self.status_timer.start(1500)

    def reset_status(self):
        """Reset status message to default"""
        self.status_label.setText('Ready to dispense...')  # No "Status: " prefix
        self.status_label.setStyleSheet("color: black;")

    def update_safety_gate(self):
        """Update safety gate based on PPE detection"""
        previous_state = self.safety_gate_locked
        self.safety_gate_locked = not all(self.ppe_status.values())
        
        if previous_state != self.safety_gate_locked:
            # Emit signal instead of directly publishing
            self.gate_status_signal.emit(self.safety_gate_locked)

    def parse_ppe_status(self, status_str):
        """Parse PPE status string into dictionary - called from ROS thread"""
        # Emit signal instead of directly updating GUI
        self.status_update_signal.emit(status_str)

    def handle_status_update(self, status_str):
        """Handle PPE status updates in the Qt thread"""
        try:
            status_parts = status_str.split(',')
            for part in status_parts:
                name, value = part.strip().split(':')
                bool_value = value.strip().lower() == 'true'
                if name.strip() in self.ppe_status:
                    self.ppe_status[name.strip()] = bool_value
            
            self.update_safety_gate()
            self.update_status_displays()
            self.show_status("PPE status updated", "green")
        except Exception as e:
            self.ros_node.get_logger().error(f'Error parsing PPE status: {e}')
            self.show_status("Error updating PPE status", "red")

    def handle_gate_status(self, is_locked):
        """Handle gate status updates in the Qt thread"""
        if not self.is_shutting_down:
            self.ros_node.publish_gate_status(is_locked)

    def cleanup(self):
        """Clean up timers from the Qt thread"""
        if not self.is_shutting_down:
            self.is_shutting_down = True
            self.timer.stop()
            self.override_timer.stop()
            self.countdown_timer.stop()
            self.status_timer.stop()
            self.dispense_complete_timer.stop()
            QApplication.processEvents()

    def closeEvent(self, event):
        """Handle window close event"""
        self.cleanup()
        event.accept()

    def update_status_displays(self):
        """Update all status displays"""
        if self.is_shutting_down:
            return
            
        try:
            # Update button colors and indicators
            for ppe, status in self.ppe_status.items():
                if ppe in self.ppe_buttons:
                    button = self.ppe_buttons[ppe].layout().itemAt(0).widget()
                    
                    # Update button text with O/X indicator when in accessibility mode
                    base_text = button.text().split('\n')[0]  # Get original label
                    if self.accessibility_mode:
                        button.setText(f"{base_text}\n{'O' if status else 'X'}")
                    else:
                        button.setText(base_text)
                    
                    # Update button color
                    if status:
                        button.setStyleSheet("""
                            QPushButton {
                                background-color: #4caf50;
                                color: white;
                                border: none;
                                border-radius: 5px;
                                font-weight: bold;
                                padding: 10px;
                            }
                            QPushButton:hover {
                                background-color: #45a049;
                            }
                            QPushButton:pressed {
                                background-color: #3d8b40;
                            }
                            QPushButton:disabled {
                                background-color: #cccccc;
                            }
                        """)
                    else:
                        button.setStyleSheet("""
                            QPushButton {
                                background-color: #ff6b6b;
                                color: white;
                                border: none;
                                border-radius: 5px;
                                font-weight: bold;
                                padding: 10px;
                            }
                            QPushButton:hover {
                                background-color: #ff5252;
                            }
                            QPushButton:pressed {
                                background-color: #ff3838;
                            }
                            QPushButton:disabled {
                                background-color: #cccccc;
                            }
                        """)
            
            # Special styling for override button
            if 'override' in self.ppe_buttons:
                override_button = self.ppe_buttons['override'].layout().itemAt(0).widget()
                override_button.setStyleSheet("""
                    QPushButton {
                        background-color: #ff9800;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        font-weight: bold;
                        padding: 10px;
                    }
                    QPushButton:hover {
                        background-color: #f57c00;
                    }
                    QPushButton:pressed {
                        background-color: #ef6c00;
                    }
                    QPushButton:disabled {
                        background-color: #cccccc;
                    }
                """)
            
            # Update gate status
            self.gate_status.setText('Gate LOCKED' if self.safety_gate_locked else 'Gate UNLOCKED')
            self.gate_status.setStyleSheet(f"""
                QLabel {{
                    color: {'red' if self.safety_gate_locked else 'green'};
                    font-weight: bold;
                    padding: 5px;
                    font-size: 20pt;
                }}
            """)
        except Exception as e:
            if not self.is_shutting_down:
                print(f"Error updating status displays: {e}")

    def show_help(self):
        """Switch to help content"""
        self.switchContent('help')

    def show_settings(self):
        """Switch to settings content"""
        self.switchContent('settings')

    def switchContent(self, content_type=None):
        """Switch main window content between main GUI, help, and settings"""
        # Clear the main layout first
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
        
        if content_type == 'help':
            # Create new help content each time
            help_content = self.createHelpContent()
            help_content.setFixedSize(self.size())
            self.main_layout.addWidget(help_content)
            
        elif content_type == 'settings':
            # Create new settings content each time
            settings_content = self.createSettingsContent()
            settings_content.setFixedSize(self.size())
            self.main_layout.addWidget(settings_content)
            
        else:  # Main GUI
            # Show main content widgets
            self.title_widget.show()
            self.status_widget.show()
            self.camera_widget.show()
            
            # Add widgets to layout based on orientation
            if self.width() > self.height():  # Landscape
                h_layout = QHBoxLayout()
                left_layout = QVBoxLayout()
                left_layout.addWidget(self.title_widget)
                left_layout.addWidget(self.status_widget)
                
                # Add button grid
                grid_widget = QWidget()
                grid = QGridLayout(grid_widget)
                positions = [
                    ('hardhat', 0, 0), ('beardnet', 0, 1),
                    ('glasses', 1, 0), ('earplugs', 1, 1),
                    ('gloves', 2, 0), ('override', 2, 1)
                ]
                
                for key, row, col in positions:
                    if key in self.ppe_buttons:
                        self.ppe_buttons[key].show()
                        grid.addWidget(self.ppe_buttons[key], row, col)
                
                left_widget = QWidget()
                left_widget.setLayout(left_layout)
                left_layout.addWidget(grid_widget)
                
                h_layout.addWidget(left_widget, 1)
                h_layout.addWidget(self.camera_widget, 2)
                
                container = QWidget()
                container.setLayout(h_layout)
                self.main_layout.addWidget(container)
            else:  # Portrait
                container = QWidget()
                layout = QVBoxLayout(container)
                
                layout.addWidget(self.title_widget)
                layout.addWidget(self.status_widget)
                layout.addWidget(self.camera_widget, 1)
                
                # Add button grid
                grid_widget = QWidget()
                grid = QGridLayout(grid_widget)
                positions = [
                    ('hardhat', 0, 0), ('beardnet', 0, 1), ('gloves', 0, 2),
                    ('glasses', 1, 0), ('earplugs', 1, 1), ('override', 1, 2)
                ]
                
                for key, row, col in positions:
                    if key in self.ppe_buttons:
                        self.ppe_buttons[key].show()
                        grid.addWidget(self.ppe_buttons[key], row, col)
                
                layout.addWidget(grid_widget)
                
                self.main_layout.addWidget(container)
        
        # Force layout update
        self.main_layout.update()

    def createHelpContent(self):
        """Create help content widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Title section
        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title_layout.setAlignment(Qt.AlignCenter)
        
        # Help icon and title (centered)
        help_icon = QLabel("?")
        help_icon.setFont(QFont('Arial', 48, QFont.Bold))
        help_icon.setStyleSheet(f"""
            QLabel {{
                color: {self.colors.primary};
                background-color: {self.colors.surface};
                border-radius: 40px;
                padding: 10px;
                min-width: 80px;
                min-height: 80px;
            }}
        """)
        help_icon.setAlignment(Qt.AlignCenter)
        
        title_text = QLabel("HELP GUIDE")
        title_text.setFont(QFont('Arial', 36, QFont.Bold))
        title_text.setStyleSheet(f"color: {self.colors.primary};")
        
        # Add to title layout (centered)
        title_layout.addWidget(help_icon)
        title_layout.addWidget(title_text)
        
        layout.addWidget(title_widget)
        
        # Help content
        help_text = """
        <h2>Operation:</h2>
        <ul style='font-size: 14pt;'>
        <li>The system detects required PPE items</li>
        <li>Green buttons indicate detected PPE</li>
        <li>Red buttons indicate missing PPE</li>
        <li>The user may need to rotate head to fully detect all required PPE</li>
        </ul>

        <h2>Dispensing:</h2>
        <ul style='font-size: 14pt;'>
        <li>Click any PPE button to dispense that item</li>
        <li>There is a 1 second cooldown between dispense requests</li>
        <li>The safety gate remains locked until all required PPE is detected</li>
        </ul>

        <h2>Safety Override:</h2>
        <ul style='font-size: 14pt;'>
        <li>Orange OVERRIDE button for emergency or administrative override only</li>
        <li>Override unlocks the gate for 10 seconds</li>
        </ul>
        """
        text_label = QLabel(help_text)
        text_label.setTextFormat(Qt.RichText)
        text_label.setWordWrap(True)
        text_label.setStyleSheet(f"""
            QLabel {{
                background: {self.colors.surface};
                color: {self.colors.text};
                border-radius: 10px;
                padding: 20px;
                margin: 0 10px;
            }}
        """)
        layout.addWidget(text_label)
        
        # Button container
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setSpacing(40)  # Increase spacing between buttons
        
        # Accessibility toggle button with fixed width
        self.help_toggle_button = QPushButton("Accessibility O/X OFF" if not self.accessibility_mode else "Accessibility O/X ON")
        self.help_toggle_button.setFont(QFont('Arial', 20, QFont.Bold))
        self.help_toggle_button.setFixedSize(400, 80)
        self.help_toggle_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors.success if self.accessibility_mode else self.colors.neutral};
                color: white;
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {self.colors.success if self.accessibility_mode else '#555'};
            }}
        """)
        self.help_toggle_button.clicked.connect(self.toggle_accessibility_help)
        
        # OK button
        ok_button = QPushButton("OK")
        ok_button.setFont(QFont('Arial', 20, QFont.Bold))
        # Calculate width based on text width plus padding
        text_width = ok_button.fontMetrics().boundingRect("OK").width()
        ok_button.setFixedSize(text_width + 40, 80)  # Add 40px padding (20px each side)
        ok_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors.primary};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 0 20px;  /* Horizontal padding */
            }}
            QPushButton:hover {{
                background-color: {self.colors.primary_dark};
            }}
        """)
        ok_button.clicked.connect(lambda: self.switchContent())
        
        button_layout.addWidget(self.help_toggle_button)
        button_layout.addWidget(ok_button)
        layout.addWidget(button_container)
        
        # Set widget styling
        widget.setStyleSheet(f"""
            QWidget {{
                background-color: {self.colors.background};
                color: {self.colors.text};
            }}
        """)
        
        return widget

    def toggle_accessibility_help(self):
        """Toggle accessibility mode from help screen"""
        self.accessibility_mode = not self.accessibility_mode
        self.help_toggle_button.setText("Accessibility O/X ON" if self.accessibility_mode else "Accessibility O/X OFF")
        self.help_toggle_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors.success if self.accessibility_mode else self.colors.neutral};
                color: white;
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {self.colors.success if self.accessibility_mode else '#555'};
            }}
        """)
        self.update_status_displays()

    def createSettingsContent(self):
        """Create settings content widget"""
        # Store initial values when creating settings
        self.initial_settings = {
            'is_dark': self.colors.is_dark,
            'override_duration': self.override_duration,
            'dispense_cooldown': self.dispense_cooldown,
            'accessibility_mode': self.accessibility_mode
        }
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        # Remove all margins to ensure full coverage
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create main content widget with proper margins
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)
        
        # Title section
        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title_layout.setAlignment(Qt.AlignCenter)
        
        settings_icon = QLabel("⚙️")
        settings_icon.setFont(QFont('Arial', 48, QFont.Bold))
        settings_icon.setStyleSheet(f"""
            QLabel {{
                color: {self.colors.primary};
                background-color: {self.colors.surface};
                border-radius: 40px;
                padding: 10px;
                min-width: 80px;
                min-height: 80px;
            }}
        """)
        settings_icon.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(settings_icon)
        
        title_text = QLabel("SETTINGS")
        title_text.setFont(QFont('Arial', 36, QFont.Bold))
        title_text.setStyleSheet(f"color: {self.colors.primary};")
        title_layout.addWidget(title_text)
        
        content_layout.addWidget(title_widget)
        
        # Create tabs
        tabs = QTabWidget()
        tabs.setFont(QFont('Arial', 12))
        tabs.addTab(self._create_colors_tab(), "Appearance")
        tabs.addTab(self._create_inventory_tab(), "Inventory")
        tabs.addTab(self._create_timing_tab(), "Timing")
        tabs.addTab(self._create_override_log_tab(), "Override Log")
        
        content_layout.addWidget(tabs)
        
        # Button container
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setSpacing(40)
        
        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.setFont(QFont('Arial', 20, QFont.Bold))
        cancel_button.setFixedSize(200, 80)  # Match OK button size from help
        cancel_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors.neutral};
                color: white;
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: #555;
            }}
        """)
        cancel_button.clicked.connect(self.cancel_settings)
        
        # Save button
        save_button = QPushButton("Save")
        save_button.setFont(QFont('Arial', 20, QFont.Bold))
        save_button.setFixedSize(200, 80)  # Match OK button size from help
        save_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors.primary};
                color: white;
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {self.colors.primary_dark};
            }}
        """)
        save_button.clicked.connect(self.save_settings)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(save_button)
        content_layout.addWidget(button_container)
        
        # Add the content widget to the main layout
        layout.addWidget(content_widget)
        
        # Set widget styling
        widget.setStyleSheet(f"""
            QWidget {{
                background-color: {self.colors.background};
                color: {self.colors.text};
            }}
        """)
        
        return widget

    def save_settings(self):
        """Save settings and return to main view"""
        # Get settings content from the current widget
        settings_tabs = self.main_layout.itemAt(0).widget().findChild(QTabWidget)
        
        # Apply color scheme
        colors_tab = settings_tabs.findChild(QWidget, "colors_tab")
        if colors_tab:
            color_scheme = colors_tab.findChild(QComboBox, "color_scheme")
            if color_scheme:
                is_dark = color_scheme.currentText() == "Dark"
                if is_dark != self.colors.is_dark:
                    self.colors.is_dark = is_dark
                    self.colors.update_colors()
                    self.apply_theme()
        
        # Apply timing settings
        timing_tab = settings_tabs.findChild(QWidget, "timing_tab")
        if timing_tab:
            override_duration = timing_tab.findChild(QSpinBox, "override_duration")
            cooldown_time = timing_tab.findChild(QDoubleSpinBox, "cooldown_time")
            status_duration = timing_tab.findChild(QSpinBox, "status_duration")
            
            if override_duration:
                self.override_duration = float(override_duration.value())
            if cooldown_time:
                self.dispense_cooldown = float(cooldown_time.value())
            if status_duration:
                self.status_message_duration = float(status_duration.value())
        
        # Return to main view
        self.switchContent()

    def show_dispense_complete(self):
        """Show dispense completion message"""
        if hasattr(self, 'current_ppe'):
            self.show_status(f"{self.current_ppe.title()} Dispensed!", "green")
            # Start auto-reset timer after showing dispensed message
            self.status_timer.start(3000)

    def apply_theme(self):
        """Apply current color scheme to all widgets"""
        # Apply to main window
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.colors.background};
            }}
            QLabel {{
                color: {self.colors.text};
            }}
            QWidget {{
                background-color: {self.colors.background};
                color: {self.colors.text};
            }}
        """)
        
        # Update status label colors
        self.status_label.setStyleSheet(f"color: {self.colors.text};")
        
        # Update gate status colors
        if self.safety_gate_locked:
            self.gate_status.setStyleSheet(f"color: {self.colors.danger};")
        else:
            self.gate_status.setStyleSheet(f"color: {self.colors.success};")
        
        # Update camera placeholder
        self.updateCameraPlaceholder()
        
        # Force update of all buttons
        self.update_status_displays()

    def _create_colors_tab(self):
        widget = QWidget()
        widget.setObjectName("colors_tab")
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignTop)
        layout.setSpacing(20)
        
        # Color scheme section
        scheme_label = QLabel("Color Scheme:")
        scheme_label.setFont(QFont('Arial', 16))
        layout.addWidget(scheme_label)
        
        self.color_scheme = QComboBox()
        self.color_scheme.setObjectName("color_scheme")
        self.color_scheme.setFont(QFont('Arial', 14))
        self.color_scheme.addItems(["Light", "Dark"])
        self.color_scheme.setCurrentText("Dark" if self.colors.is_dark else "Light")
        self.color_scheme.currentTextChanged.connect(self.apply_theme_preview)
        layout.addWidget(self.color_scheme)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"background-color: {self.colors.neutral};")
        layout.addWidget(separator)
        
        # Accessibility section
        access_label = QLabel("Accessibility:")
        access_label.setFont(QFont('Arial', 16))
        layout.addWidget(access_label)
        
        self.settings_toggle_button = QPushButton("Accessibility O/X OFF" if not self.accessibility_mode else "Accessibility O/X ON")
        self.settings_toggle_button.setFont(QFont('Arial', 14, QFont.Bold))
        self.settings_toggle_button.setFixedHeight(50)
        self.settings_toggle_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors.success if self.accessibility_mode else self.colors.neutral};
                color: white;
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {self.colors.success if self.accessibility_mode else '#555'};
            }}
        """)
        self.settings_toggle_button.clicked.connect(self.toggle_accessibility_settings)
        layout.addWidget(self.settings_toggle_button)
        
        layout.addStretch()
        return widget

    def _create_timing_tab(self):
        widget = QWidget()
        widget.setObjectName("timing_tab")
        layout = QFormLayout(widget)
        
        # Create spinboxes with labels
        override_label = QLabel("Override Duration (s):")
        override_label.setStyleSheet(f"color: {self.colors.text};")
        self.override_duration_spin = QSpinBox()
        self.override_duration_spin.setObjectName("override_duration")
        self.override_duration_spin.setRange(5, 30)
        self.override_duration_spin.setValue(int(self.override_duration))
        
        cooldown_label = QLabel("Cooldown Time (s):")
        cooldown_label.setStyleSheet(f"color: {self.colors.text};")
        self.cooldown_time_spin = QDoubleSpinBox()
        self.cooldown_time_spin.setObjectName("cooldown_time")
        self.cooldown_time_spin.setRange(0.5, 5.0)
        self.cooldown_time_spin.setValue(self.dispense_cooldown)
        
        status_label = QLabel("Status Message Duration (s):")
        status_label.setStyleSheet(f"color: {self.colors.text};")
        self.status_duration_spin = QSpinBox()
        self.status_duration_spin.setObjectName("status_duration")
        self.status_duration_spin.setRange(1, 10)
        self.status_duration_spin.setValue(3)
        
        layout.addRow(override_label, self.override_duration_spin)
        layout.addRow(cooldown_label, self.cooldown_time_spin)
        layout.addRow(status_label, self.status_duration_spin)
        
        return widget

    def _create_inventory_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Add inventory tracking (placeholder)
        layout.addWidget(QLabel("Inventory tracking will be implemented here"))
        
        return widget
        
    def _create_override_log_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Show recent override logs
        log_text = QTextEdit()
        log_text.setReadOnly(True)
        log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.colors.surface};
                color: {self.colors.text};
                border: 1px solid {self.colors.neutral};
                border-radius: 5px;
                padding: 10px;
                font-size: 12pt;
            }}
        """)
        
        recent_logs = self.override_logger.get_recent_logs()
        log_text.setText("\n".join([
            f"{log['timestamp']}: {log['reason']}"
            for log in recent_logs
        ]))
        
        layout.addWidget(log_text)
        
        return widget

    def toggle_accessibility_settings(self):
        """Toggle accessibility mode from settings screen"""
        self.accessibility_mode = not self.accessibility_mode
        self.settings_toggle_button.setText("Accessibility O/X ON" if self.accessibility_mode else "Accessibility O/X OFF")
        self.settings_toggle_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors.success if self.accessibility_mode else self.colors.neutral};
                color: white;
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {self.colors.success if self.accessibility_mode else '#555'};
            }}
        """)
        self.update_status_displays()

    def apply_theme_preview(self):
        """Apply theme changes in real-time"""
        is_dark = self.color_scheme.currentText() == "Dark"
        if is_dark != self.colors.is_dark:
            self.colors.is_dark = is_dark
            self.colors.update_colors()
            self.apply_theme()

    def cancel_settings(self):
        """Cancel settings changes and return to main view"""
        # Restore theme
        if self.colors.is_dark != self.initial_settings['is_dark']:
            self.colors.is_dark = self.initial_settings['is_dark']
            self.colors.update_colors()
            self.apply_theme()
        
        # Restore timing values
        self.override_duration = self.initial_settings['override_duration']
        self.dispense_cooldown = self.initial_settings['dispense_cooldown']
        
        # Restore accessibility mode
        if self.accessibility_mode != self.initial_settings['accessibility_mode']:
            self.accessibility_mode = self.initial_settings['accessibility_mode']
            self.update_status_displays()
        
        # Return to main view
        self.switchContent()

def main():
    with ros_context():
        ros_node = ROSNode()
        
        os.environ['XDG_RUNTIME_DIR'] = '/tmp/runtime-dir'
        app = QApplication(sys.argv)
        
        # Create and show the main window
        gui = ExperimentalPPEVendingMachine(ros_node)
        gui.show()  # Make sure window is shown
        
        ros_node.gui = gui
        
        def spin_ros():
            try:
                while not gui.is_shutting_down:
                    if rclpy.ok():
                        rclpy.spin_once(ros_node, timeout_sec=0.1)
                    else:
                        break
            except Exception as e:
                if not gui.is_shutting_down:
                    print(f"ROS thread error: {e}")
        
        ros_thread = threading.Thread(target=spin_ros, daemon=True)
        ros_thread.start()
        
        def shutdown():
            if not gui.is_shutting_down:
                gui.is_shutting_down = True
                gui.cleanup()
                if rclpy.ok():
                    ros_node.destroy_node()
        
        def signal_handler(signum, frame):
            shutdown()
            app.quit()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            exit_code = app.exec_()
        except KeyboardInterrupt:
            shutdown()
            exit_code = 0
        except Exception as e:
            print(f"Error in main loop: {e}")
            shutdown()
            exit_code = 1
        finally:
            shutdown()
            sys.exit(exit_code)

if __name__ == '__main__':
    main() 