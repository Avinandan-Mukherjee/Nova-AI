from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QStackedWidget, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QLabel, QSizePolicy, QGraphicsItem, QScrollArea, QLineEdit, QGridLayout, QDialog
from PyQt5.QtGui import QIcon, QPainter, QMovie, QColor, QTextCharFormat, QFont, QPixmap, QTextBlockFormat
from PyQt5.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve, QVariantAnimation, QAbstractAnimation
from dotenv import dotenv_values
import sys
import os
import psutil
import time
import json
import pyqtgraph as pg
import numpy as np

# Try to import set_key, but don't fail if it's not available
try:
    from dotenv import set_key
    HAS_SET_KEY = True
except ImportError:
    HAS_SET_KEY = False
    print("[Warning] python-dotenv set_key function not available. Username changes will not be saved.")

# We'll use this variable to store the reference to Main module's Username
# It will be set from Main.py after it imports this module
main_username_ref = None

from Backend.Model import FirstLayerDMM
from Backend.RealtimeSearchEngine import RealtimeSearchEngine
from Backend.Chatbot import ChatBot
from Backend.TextToSpeech import TextToSpeech
from Frontend.SystemMonitor import SystemMonitorWidget

env_vars = dotenv_values(".env")
Assistantname = env_vars.get("Assistantname")
Username = env_vars.get("Username")
current_dir = os.getcwd()
old_chat_message = ""
TempDirPath = os.path.join(current_dir, "Frontend", "Files")
GraphicsDirPath = os.path.join(current_dir, "Frontend", "Graphics")

def calculate_16_9_dimensions(width=None, height=None):
    """Calculate dimensions to maintain 16:9 aspect ratio"""
    if width:
        return width, int(width * 9 / 16)
    elif height:
        return int(height * 16 / 9), height
    else:
        # Default size if neither width nor height is provided
        return 1280, 720

def AnswerModifier(Answer):
    lines = Answer.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    modified_answer = '\n'.join(non_empty_lines)
    return modified_answer

def QueryModifier(Query):
    new_query = Query.lower().strip()
    query_words = new_query.split()
    question_words = ["how", "what", "who", "where", "when", "why", "which", "whose", "whom", "can you", "what's", "where's", "how's", "can you"]
    
    if any(word + " " in new_query for word in question_words):
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "."
        else:
            new_query += "?"
    else:
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "."
        else:
            new_query += "."
    return new_query.capitalize()

def SetMicrophoneStatus(Command):
    mic_file_path = os.path.join(TempDirPath, "Mic.data")
    with open(mic_file_path, "w", encoding='utf-8') as file:
        file.write(Command)

def GetMicrophoneStatus():
    mic_file_path = os.path.join(TempDirPath, "Mic.data")
    with open(mic_file_path, "r", encoding='utf-8') as file:
        Status = file.read()
    return Status

def SetAssistantStatus(Status):
    status_file_path = os.path.join(TempDirPath, "Status.data")
    with open(status_file_path, "w", encoding='utf-8') as file:
        file.write(Status)

def GetAssistantStatus():
    status_file_path = os.path.join(TempDirPath, "Status.data")
    with open(status_file_path, "r", encoding='utf-8') as file:
        Status = file.read()
    return Status

def StyleAssistantStatus(status_text):
    """Apply color styling to assistant status messages with visual indicators"""
    if "Listening" in status_text:
        return f'<span style="color: #4B89DC; font-weight: bold">● {status_text}</span>'
    elif "Processing" in status_text:
        return f'<span style="color: #E67E22; font-weight: bold">◆ {status_text}</span>'
    elif "Searching" in status_text:
        return f'<span style="color: #8E44AD; font-weight: bold">◉ {status_text}</span>'
    elif "Answering" in status_text:
        return f'<span style="color: #27AE60; font-weight: bold">◇ {status_text}</span>'
    elif "Available" in status_text:
        return f'<span style="color: #BDC3C7">○ {status_text}</span>'
    elif "Error" in status_text:
        return f'<span style="color: #E74C3C; font-weight: bold">⚠ {status_text}</span>'
    else:
        return f'<span style="color: #FFFFFF">■ {status_text}</span>'

def MicButtonInitialed():
    SetMicrophoneStatus("False")

def MicButtonClosed():
    SetMicrophoneStatus("True")

def GraphicsDirectoryPath(Filename):
    return os.path.join(GraphicsDirPath, Filename)

def TempDirectoryPath(Filename):
    return os.path.join(TempDirPath, Filename)

def ShowTextToScreen(Text):
    responses_file_path = TempDirectoryPath('Responses.data')
    with open(responses_file_path, "w", encoding='utf-8') as file:
        file.write(Text)


class ChatSection(QWidget):
    
    def loadMessages(self):
        global old_chat_message

        # Load messages from Responses.data (User voice messages or Assistant responses)
        try:
            responses_file_path = TempDirectoryPath('Responses.data')
            with open(responses_file_path, "r", encoding='utf-8') as file:
                messages = file.read()

                if not messages or len(messages) <= 1:
                    pass # Nothing to process or file is empty/cleared
                elif str(old_chat_message) == str(messages):
                    pass # Message already processed
                else:
                    if messages.startswith(f"{Username}:"):
                        # Display user voice message
                        message_text = messages.replace(f"{Username}:", "").strip()
                        if message_text:
                            self.addMessage(message=message_text, is_user=True)
                            old_chat_message = messages # Update last processed message
                            # Ensure scrolling to latest message
                            self.scrollToBottom()
                            # DO NOT clear Responses.data here, wait for assistant response
                    
                    elif messages.startswith(f"{Assistantname}:"):
                        # Display assistant message
                        message_text = messages.replace(f"{Assistantname}:", "").strip()
                        if message_text: # Ensure non-empty message
                            self.addMessage(message=message_text, is_user=False)
                            old_chat_message = messages # Update last processed message
                            # Ensure scrolling to latest message
                            self.scrollToBottom()
                            # Clear the file ONLY after assistant message is displayed
                            try:
                                with open(responses_file_path, "w", encoding='utf-8') as f:
                                    f.write("")
                            except Exception as clear_e:
                                print(f"Error clearing Responses.data after assistant msg: {clear_e}")

        except FileNotFoundError:
            # Responses.data might not exist initially or after clearing
            pass 
        except Exception as e:
            print(f"Error reading Responses.data: {e}")
            # Attempt to clear file on error to prevent loops
            try:
                responses_file_path = TempDirectoryPath('Responses.data')
                with open(responses_file_path, "w", encoding='utf-8') as f:
                        f.write("")
            except Exception as clear_e:
                 print(f"Error clearing Responses.data on read error: {clear_e}")

        # Update mic button state based on Mic.data
        try:
            mic_file_path = TempDirectoryPath('Mic.data')
            with open(mic_file_path, "r", encoding='utf-8') as file:
                mic_status = file.read().strip()
                new_mic_state = (mic_status == "True")
                if self.mic_toggled != new_mic_state:
                    self.mic_toggled = new_mic_state
                    self.update_mic_icon()
        except Exception as e:
            print(f"Error reading Mic.data: {e}")
    
    def SpeechRecogText(self):
            status_file_path = os.path.join(TempDirPath, "Status.data")
            with open(status_file_path, "r", encoding='utf-8') as file:
                messages = file.read()
                self.label.setText(StyleAssistantStatus(messages))
    
    def createMessageBubble(self, message, is_user=False):
        # Create bubble container widget
        bubble = QWidget()
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(8, 8, 8, 8)
        
        # Create message label
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        # Set font size larger
        font = QFont()
        font.setPointSize(11)
        message_label.setFont(font)
        
        # Set max width to prevent extremely wide bubbles but make them larger
        message_label.setMaximumWidth(int(self.chat_scroll_area.width() * 0.8))
        
        # Style the message label based on sender
        if is_user:
            message_label.setStyleSheet("""
                background-color: #2D2D2D;
                color: #FFFFFF;
                border-radius: 18px;
                padding: 15px;
                margin: 8px;
                font-weight: 500;
            """)
            alignment = Qt.AlignRight
        else:
            message_label.setStyleSheet("""
                background-color: #3D3D3D;
                color: #FFFFFF;
                border-radius: 18px;
                padding: 15px;
                margin: 8px;
                font-weight: 500;
            """)
            alignment = Qt.AlignLeft
        
        bubble_layout.addWidget(message_label)
        bubble_layout.setAlignment(alignment)
        return bubble
    
    def addMessage(self, message, is_user=False):
        # Create and add a message bubble
        bubble = self.createMessageBubble(message, is_user)
        
        # Add bubble to the main layout with proper alignment
        row_layout = QHBoxLayout()
        if is_user:
            row_layout.addStretch()
            row_layout.addWidget(bubble)
        else:
            row_layout.addWidget(bubble)
            row_layout.addStretch()
        
        # Add to chat area
        self.chat_layout.addLayout(row_layout)
        
        # Auto-scroll to bottom
        self.scrollToBottom()
    
    def loadChatHistory(self):
        """Load and display all previous chat history from Chatlog.json"""
        try:
            # Path to the chat log file
            chat_log_path = os.path.join('Data', 'Chatlog.json')
            
            # Check if the file exists
            if not os.path.exists(chat_log_path):
                print(f"[Info] Chat history file not found: {chat_log_path}")
                return
                
            # Read the chat log file
            with open(chat_log_path, "r", encoding="utf-8") as file:
                chat_data = file.read()
                
            if not chat_data or len(chat_data) < 5:  # Empty or nearly empty file
                return
                
            # Parse the JSON data
            try:
                messages = json.loads(chat_data)
                print(f"[Info] Loaded {len(messages)} previous chat messages")
                
                # Add each message to the chat display
                for message in messages:
                    role = message.get("role", "")
                    content = message.get("content", "")
                    
                    if role == "user":
                        self.addMessage(content, is_user=True)
                    elif role == "assistant":
                        self.addMessage(content, is_user=False)
                
                print("[Info] Chat history loaded successfully")
            except json.JSONDecodeError as e:
                print(f"[Error] Failed to parse chat history JSON: {e}")
        except Exception as e:
            print(f"[Error] Error loading chat history: {e}")
    
    def scrollToBottom(self):
        # Scroll to the bottom of the chat area
        vbar = self.chat_scroll_area.verticalScrollBar()
        vbar.setValue(vbar.maximum())
        
    def load_icon(self, path, width=60, height=60):
        pixmap = QPixmap(path)
        new_pixmap = pixmap.scaled(width, height)
        self.mic_button.setIcon(QIcon(new_pixmap))
    
    def toggle_icon(self, event=None):
        self.mic_toggled = not self.mic_toggled
        self.update_mic_icon()
        
        if self.mic_toggled:
            # Activate microphone
            MicButtonClosed()
            SetAssistantStatus("Listening... ")
        else:
            # Deactivate microphone
            MicButtonInitialed()
            SetAssistantStatus("Available... ")

    def update_mic_icon(self):
        if self.mic_toggled:
            # Mic is ON: Disable text input and send button
            self.mic_button.setIcon(QIcon(GraphicsDirectoryPath('Mic_on.png')))
            self.text_input.setEnabled(False)
            self.send_button.setEnabled(False)
            self.text_input.setPlaceholderText("Turn off microphone to type...")
        else:
            # Mic is OFF: Enable text input and send button
            self.mic_button.setIcon(QIcon(GraphicsDirectoryPath('Mic_off.png')))
            self.text_input.setEnabled(True)
            self.send_button.setEnabled(True)
            self.text_input.setPlaceholderText("Type a message...")
            
        self.mic_button.setIconSize(QSize(24, 24))
        self.mic_button.setStyleSheet("""
            QPushButton {
                background-color: #3D3D3D;
                border: none;
                border-radius: 25px;
                padding: 12px;
                min-width: 50px;
                min-height: 50px;
            }
            QPushButton:hover {
                background-color: #4D4D4D;
            }
        """)

    def __init__(self):
        super().__init__() # Fixed: Use proper inheritance
        layout = QHBoxLayout(self)
        layout.setContentsMargins(-10, 40, 40, 100)
        layout.setSpacing(-100)
        
        # Create main layout container
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create scroll area for chat
        self.chat_scroll_area = QScrollArea()
        self.chat_scroll_area.setWidgetResizable(True)
        self.chat_scroll_area.setFrameStyle(QFrame.NoFrame)
        
        # Create widget to hold all chat messages
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setSpacing(10)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_layout.addStretch()
        
        # Set chat widget as the scroll area's widget
        self.chat_scroll_area.setWidget(self.chat_widget)
        
        # Style the scroll area
        self.chat_scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #000000;
                border: none;
            }
            QWidget {
                background-color: #000000;
            }
            QScrollBar:vertical {
                background-color: #000000;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #2D2D2D;
                min-height: 30px;
                border-radius: 6px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Create input area
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(10, 10, 10, 10)
        input_layout.setSpacing(10)
        
        # Create text input field
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Type a message...")
        self.text_input.returnPressed.connect(self.send_message)
        self.text_input.setStyleSheet("""
            QLineEdit {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border: none;
                border-radius: 25px;
                padding: 12px 20px;
                font-size: 14px;
                min-height: 50px;
            }
            QLineEdit:focus {
                border: 2px solid #3D3D3D;
            }
            QLineEdit:disabled {
                background-color: #202020; /* Darker background when disabled */
                color: #555555; /* Lighter text color when disabled */
            }
        """)
        
        # Create mic button
        self.mic_button = QPushButton()
        self.mic_button.setCursor(Qt.PointingHandCursor)
        self.mic_button.clicked.connect(self.toggle_icon)
        self.mic_button.setStyleSheet("""
            QPushButton {
                background-color: #3D3D3D;
                border: none;
                border-radius: 25px;
                padding: 12px;
                min-width: 50px;
                min-height: 50px;
            }
            QPushButton:hover {
                background-color: #4D4D4D;
            }
        """)
        
        # Create send button
        self.send_button = QPushButton()
        send_icon_path = GraphicsDirectoryPath('send.png')
        
        # Check if icon file exists
        if os.path.exists(send_icon_path):
            self.send_button.setIcon(QIcon(send_icon_path))
            self.send_button.setIconSize(QSize(24, 24))
        else:
            # Use text as fallback
            self.send_button.setText("➤")
            self.send_button.setFont(QFont("Arial", 14))
            
        self.send_button.setCursor(Qt.PointingHandCursor)
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #3D3D3D;
                border: none;
                border-radius: 25px;
                padding: 12px;
                min-width: 50px;
                min-height: 50px;
            }
            QPushButton:hover {
                background-color: #4D4D4D;
            }
            QPushButton:disabled {
                 background-color: #202020; /* Darker background when disabled */
                 /* Optionally, change icon color or opacity if needed */
            }
        """)
        
        # Initialize mic state and update UI elements (including disabling if needed)
        self.mic_toggled = (GetMicrophoneStatus() == "True") 
        self.update_mic_icon() # This will now also handle enabling/disabling input
        
        # Create status label
        self.label = QLabel("")
        self.label.setStyleSheet("""
            color: white; 
            font-size: 16px; 
            padding: 12px 20px; 
            border-radius: 20px; 
            background-color: rgba(45, 45, 45, 0.85);
            margin-right: 15px;
            margin-bottom: 5px;
            border: 1px solid rgba(70, 70, 70, 0.5);
        """)
        self.label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.label.setMaximumHeight(50)
        
        # Status container (to ensure proper alignment)
        status_container = QHBoxLayout()
        status_container.addStretch()
        status_container.addWidget(self.label)
        status_container.setContentsMargins(0, 0, 10, 8)
        
        # Add widgets to input layout
        input_layout.addWidget(self.text_input, 7)
        input_layout.addWidget(self.mic_button, 1)
        input_layout.addWidget(self.send_button, 1)
        
        # Add chat area, status indicator, and input area to main layout
        main_layout.addWidget(self.chat_scroll_area, 1)
        main_layout.addLayout(status_container)
        main_layout.addLayout(input_layout, 0)
        
        # Add main layout to the widget
        left_container = QWidget()
        left_container.setLayout(main_layout)
        left_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Add to the main layout
        layout.addWidget(left_container)
        
        # Create a container for the right side (GIF + system monitor)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(15)
        
        # SIMPLIFIED RIGHT SIDE LAYOUT
        
        # 1. TOP: Single CPU graph
        cpu_container = QWidget()
        cpu_container.setObjectName("cpuContainer")
        cpu_layout = QVBoxLayout(cpu_container)
        cpu_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create CPU Monitor with only CPU label visible
        self.cpu_monitor = SystemMonitorWidget()
        self.cpu_monitor.setFixedHeight(150)
        
        # Hide RAM and Network graphs - show only CPU graph
        self.cpu_monitor.ram_plot.setVisible(False)
        self.cpu_monitor.net_plot.setVisible(False)
        
        # Hide RAM and Network labels from SystemMonitorWidget
        for child in self.cpu_monitor.findChildren(QLabel):
            if "RAM" in child.text() or "NET" in child.text():
                child.setVisible(False)
            if child.text() == "SYSTEM VITALS":
                child.setText("CPU")
        
        # Make sure we have a prominent CPU title
        cpu_title = QLabel("CPU USAGE")
        cpu_title.setAlignment(Qt.AlignCenter)
        cpu_title.setStyleSheet("""
            color: white; 
            font-size: 16px; 
            font-weight: bold;
            margin-bottom: 5px;
        """)
        cpu_layout.addWidget(cpu_title, 0)
        cpu_layout.addWidget(self.cpu_monitor, 1)
        
        cpu_container.setStyleSheet("""
            #cpuContainer {
                background-color: rgba(0, 0, 0, 0.5);
                border-radius: 15px;
                border: none;
            }
        """)
        
        # 2. MIDDLE: GIF
        gif_container = QWidget()
        gif_container.setObjectName("gifContainer")
        gif_layout = QVBoxLayout(gif_container)
        gif_layout.setContentsMargins(10, 10, 10, 10)
        gif_layout.setAlignment(Qt.AlignCenter)
        
        # Create GIF label in the center
        self.gif_label = QLabel()
        self.gif_label.setStyleSheet("border: none; background-color: transparent")
        self.gif_label.setObjectName("gifLabel")
        movie = QMovie(GraphicsDirectoryPath('Jarvis.gif'))
        
        # Resize GIF for center placement - make it larger
        max_gif_size = 360  # Increased from 320 to 360
        movie.setScaledSize(QSize(max_gif_size, int(max_gif_size * 9 / 16)))  # 16:9 ratio
        
        self.gif_label.setAlignment(Qt.AlignCenter)
        self.gif_label.setMovie(movie)
        movie.start()
        
        gif_layout.addWidget(self.gif_label)
        
        gif_container.setStyleSheet("""
            #gifContainer {
                background-color: rgba(0, 0, 0, 0.4);
                border-radius: 15px;
            }
        """)
        
        # 3. BOTTOM: System Vitals text display
        vitals_container = QWidget()
        vitals_container.setObjectName("vitalsContainer")
        vitals_layout = QVBoxLayout(vitals_container)
        vitals_layout.setContentsMargins(20, 20, 20, 20)
        vitals_layout.setSpacing(12)
        
        # Add title
        vitals_title = QLabel("SYSTEM VITALS")
        vitals_title.setAlignment(Qt.AlignCenter)
        vitals_title.setStyleSheet("color: white; font-size: 16px;")
        vitals_layout.addWidget(vitals_title)
        
        # Create labels for each vital metric with clean, simple styling
        self.cpu_vital = QLabel("CPU: 0%")
        self.ram_vital = QLabel("RAM: 0%")
        self.net_vital = QLabel("NETWORK: 0 KB/s")
        self.disk_vital = QLabel("DISK: 0%")
        
        # Simple, clean style for all vitals labels - no backgrounds, just plain text
        vitals_style = "color: white; font-size: 15px;"
        
        # Set styles and add to layout
        self.cpu_vital.setStyleSheet(vitals_style)
        self.ram_vital.setStyleSheet(vitals_style)
        self.net_vital.setStyleSheet(vitals_style)
        self.disk_vital.setStyleSheet(vitals_style)
        
        vitals_layout.addWidget(self.cpu_vital)
        vitals_layout.addWidget(self.ram_vital)
        vitals_layout.addWidget(self.net_vital)
        vitals_layout.addWidget(self.disk_vital)
        
        vitals_container.setStyleSheet("""
            #vitalsContainer {
                background-color: #000000;
            }
        """)
        
        # Add all containers to right layout with proper proportions
        right_layout.addWidget(cpu_container, 1)
        right_layout.addWidget(gif_container, 2)
        right_layout.addWidget(vitals_container, 2)
        
        # Add right container to main layout (make it narrower)
        right_container.setFixedWidth(300)  # Fixed width makes chat area wider
        layout.addWidget(right_container)
        
        # Set up timer for updating messages and status
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.loadMessages) # Handles assistant responses and mic sync
        self.timer.timeout.connect(self.SpeechRecogText) # Handles status label
        self.timer.timeout.connect(self.update_vitals) # Updates vital statistics
        self.timer.start(100) # Check more frequently for smoother updates
        
        # Add fade-in animation for the GIF
        self.fade_in_animation = QVariantAnimation()
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)
        self.fade_in_animation.setDuration(1000)  # 1 second duration
        self.fade_in_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.fade_in_animation.valueChanged.connect(self.update_gif_opacity)
        
        # Start the animation after a short delay
        QTimer.singleShot(500, self.fade_in_animation.start)
        
        # Load previous chat history
        QTimer.singleShot(1000, self.loadChatHistory)
        
    def update_gif_opacity(self, opacity):
        """Update the opacity of the GIF label during animation"""
        # Opacity property not fully supported, use opacity effect instead
        self.gif_label.setStyleSheet("border: none; background-color: transparent")
    
    def send_message(self):
        message = self.text_input.text().strip()
        if message:
            # Add the message to the chat display immediately
            self.addMessage(message=message, is_user=True)

            # Write the raw query to Query.data for backend processing
            try:
                query_file_path = TempDirectoryPath('Query.data')
                with open(query_file_path, "w", encoding='utf-8') as file:
                    file.write(message)
            except Exception as e:
                 print(f"Error writing Query.data: {e}")

            # Clear the input field and refocus it
            self.text_input.clear()
            self.text_input.setFocus()

            # Set status to processing (backend will handle this)
            # SetAssistantStatus("Processing... ") # Let backend control status updates

    def update_vitals(self):
        """Update the vital statistics display"""
        # CPU
        cpu_percent = psutil.cpu_percent()
        self.cpu_vital.setText(f"CPU: {cpu_percent:.1f}%")
        
        # RAM
        ram = psutil.virtual_memory()
        ram_percent = ram.percent
        ram_total = ram.total / (1024 * 1024 * 1024)  # Convert to GB
        ram_used = ram.used / (1024 * 1024 * 1024)    # Convert to GB
        self.ram_vital.setText(f"RAM: {ram_percent:.1f}% ({ram_used:.1f}/{ram_total:.1f} GB)")
        
        # Network
        try:
            current_net_io = psutil.net_io_counters()
            current_time = time.time()
            
            # Initialize last values if not already
            if not hasattr(self, 'last_net_io'):
                self.last_net_io = current_net_io
                self.last_net_time = current_time
                net_speed = 0
            else:
                # Calculate network speed
                time_elapsed = current_time - self.last_net_time
                bytes_sent = current_net_io.bytes_sent - self.last_net_io.bytes_sent
                bytes_recv = current_net_io.bytes_recv - self.last_net_io.bytes_recv
                
                # Calculate speed in KB/s
                net_speed = (bytes_sent + bytes_recv) / (1024 * time_elapsed)
                
                # Update last values
                self.last_net_io = current_net_io
                self.last_net_time = current_time
            
            # Format display based on speed
            if net_speed < 1000:
                self.net_vital.setText(f"NETWORK: {net_speed:.1f} KB/s")
            else:
                self.net_vital.setText(f"NETWORK: {net_speed/1024:.2f} MB/s")
        except Exception as e:
            self.net_vital.setText("NETWORK: Error")
            print(f"Network monitoring error: {e}")
        
        # Disk
        try:
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_total = disk.total / (1024 * 1024 * 1024)  # Convert to GB
            disk_used = disk.used / (1024 * 1024 * 1024)    # Convert to GB
            self.disk_vital.setText(f"DISK: {disk_percent:.1f}% ({disk_used:.1f}/{disk_total:.1f} GB)")
        except Exception as e:
            self.disk_vital.setText("DISK: Error")
            print(f"Disk monitoring error: {e}")

class InitialScreen(QWidget):
        def __init__(self, parent = None):
            super().__init__(parent)
            # Get screen size
            desktop = QApplication.desktop()
            screen_width = desktop.screenGeometry().width()
            screen_height = desktop.screenGeometry().height()
            
            # Calculate 16:9 dimensions based on screen size
            window_width, window_height = calculate_16_9_dimensions(width=screen_width)
            if window_height > screen_height:
                window_width, window_height = calculate_16_9_dimensions(height=screen_height)
            
            # Create main layout
            main_layout = QGridLayout(self)
            main_layout.setContentsMargins(30, 30, 30, 30)
            main_layout.setSpacing(30)
            
            # Configure GIF in center
            center_container = QWidget()
            center_layout = QVBoxLayout(center_container)
            center_layout.setContentsMargins(20, 20, 20, 20)
            center_layout.setAlignment(Qt.AlignCenter)
            
            # GIF label
            gif_label = QLabel()
            movie = QMovie(GraphicsDirectoryPath('Jarvis.gif'))
            
            # Calculate good size for central GIF
            gif_width = int(window_width * 0.4)  # 40% of window width
            gif_height = int(gif_width * 9 / 16)  # Maintain 16:9 ratio
            movie.setScaledSize(QSize(gif_width, gif_height))
            
            gif_label.setMovie(movie)
            gif_label.setAlignment(Qt.AlignCenter)
            movie.start()
            
            # Status label below GIF
            self.status_label = QLabel()
            self.status_label.setStyleSheet("""
                color: white; 
                font-size: 16px; 
                padding: 10px 20px; 
                border-radius: 15px; 
                background-color: rgba(45, 45, 45, 0.85);
                border: 1px solid rgba(70, 70, 70, 0.5);
            """)
            self.status_label.setAlignment(Qt.AlignCenter)
            
            # Microphone button
            self.mic_label = QLabel()
            pixmap = QPixmap(GraphicsDirectoryPath('Mic_off.png'))  # Start with mic off by default
            new_pixmap = pixmap.scaled(60, 60)
            self.mic_label.setPixmap(new_pixmap)
            self.mic_label.setFixedSize(80, 80)
            self.mic_label.setAlignment(Qt.AlignCenter)
            self.toggled = False  # Start with mic off state
            self.mic_label.setCursor(Qt.PointingHandCursor)
            self.mic_label.mousePressEvent = self.toggle_icon
            
            # Add widgets to center container
            center_layout.addWidget(gif_label)
            center_layout.addWidget(self.status_label)
            center_layout.addWidget(self.mic_label, 0, Qt.AlignCenter)  # Center the mic button
            
            # Create four system monitor widgets for each corner
            
            # TOP-LEFT: CPU Monitor
            cpu_container = QWidget()
            cpu_container.setObjectName("cpuContainer")
            cpu_layout = QVBoxLayout(cpu_container)
            cpu_layout.setContentsMargins(15, 15, 15, 15)
            
            cpu_title = QLabel("CPU Usage")
            cpu_title.setAlignment(Qt.AlignCenter)
            cpu_title.setStyleSheet("color: white; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
            
            # Create SystemMonitorWidget with correct parameters
            self.cpu_monitor = SystemMonitorWidget()
            self.cpu_monitor.setFixedSize(250, 150)
            
            # Set CPU monitor color
            cpu_pen = pg.mkPen(color=(0, 255, 255), width=2)
            self.cpu_monitor.cpu_curve.setPen(cpu_pen)
            
            # Hide RAM and Network graphs - show only CPU graph
            self.cpu_monitor.ram_plot.setVisible(False)
            self.cpu_monitor.net_plot.setVisible(False)
            
            self.cpu_stat = QLabel("CPU: 0%")
            self.cpu_stat.setStyleSheet("""
                color: #00FFFF;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 14px;
                background-color: rgba(0, 0, 0, 0.6);
                border-radius: 5px;
                padding: 5px;
                margin-top: 5px;
            """)
            self.cpu_stat.setAlignment(Qt.AlignCenter)
            
            cpu_layout.addWidget(cpu_title)
            cpu_layout.addWidget(self.cpu_monitor)
            cpu_layout.addWidget(self.cpu_stat)
            
            cpu_container.setStyleSheet("""
                #cpuContainer {
                    background-color: rgba(0, 0, 0, 0.5);
                    border-radius: 15px;
                    border: 1px solid rgba(0, 255, 255, 0.3);
                }
            """)
            
            # TOP-RIGHT: RAM Monitor
            ram_container = QWidget()
            ram_container.setObjectName("ramContainer")
            ram_layout = QVBoxLayout(ram_container)
            ram_layout.setContentsMargins(15, 15, 15, 15)
            
            ram_title = QLabel("RAM Usage")
            ram_title.setAlignment(Qt.AlignCenter)
            ram_title.setStyleSheet("color: white; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
            
            self.ram_monitor = SystemMonitorWidget()
            self.ram_monitor.setFixedSize(250, 150)
            
            # Set RAM monitor color
            ram_pen = pg.mkPen(color=(0, 255, 0), width=2)
            self.ram_monitor.ram_curve.setPen(ram_pen)
            
            # Hide CPU and Network graphs - show only RAM graph
            self.ram_monitor.cpu_plot.setVisible(False)
            self.ram_monitor.net_plot.setVisible(False)
            
            self.ram_stat = QLabel("RAM: 0%")
            self.ram_stat.setStyleSheet("""
                color: #00FF00;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 14px;
                background-color: rgba(0, 0, 0, 0.6);
                border-radius: 5px;
                padding: 5px;
                margin-top: 5px;
            """)
            self.ram_stat.setAlignment(Qt.AlignCenter)
            
            ram_layout.addWidget(ram_title)
            ram_layout.addWidget(self.ram_monitor)
            ram_layout.addWidget(self.ram_stat)
            
            ram_container.setStyleSheet("""
                #ramContainer {
                    background-color: rgba(0, 0, 0, 0.5);
                    border-radius: 15px;
                    border: 1px solid rgba(0, 255, 0, 0.3);
                }
            """)
            
            # BOTTOM-LEFT: Network Monitor
            net_container = QWidget()
            net_container.setObjectName("netContainer")
            net_layout = QVBoxLayout(net_container)
            net_layout.setContentsMargins(15, 15, 15, 15)
            
            net_title = QLabel("Network Traffic")
            net_title.setAlignment(Qt.AlignCenter)
            net_title.setStyleSheet("color: white; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
            
            self.net_monitor = SystemMonitorWidget()
            self.net_monitor.setFixedSize(250, 150)
            
            # Set Network monitor color
            net_pen = pg.mkPen(color=(255, 0, 255), width=2)
            self.net_monitor.net_curve.setPen(net_pen)
            
            # Hide CPU and RAM graphs - show only Network graph
            self.net_monitor.cpu_plot.setVisible(False)
            self.net_monitor.ram_plot.setVisible(False)
            
            self.net_stat = QLabel("Network: 0 KB/s")
            self.net_stat.setStyleSheet("""
                color: #FF00FF;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 14px;
                background-color: rgba(0, 0, 0, 0.6);
                border-radius: 5px;
                padding: 5px;
                margin-top: 5px;
            """)
            self.net_stat.setAlignment(Qt.AlignCenter)
            
            net_layout.addWidget(net_title)
            net_layout.addWidget(self.net_monitor)
            net_layout.addWidget(self.net_stat)
            
            net_container.setStyleSheet("""
                #netContainer {
                    background-color: rgba(0, 0, 0, 0.5);
                    border-radius: 15px;
                    border: 1px solid rgba(255, 0, 255, 0.3);
                }
            """)
            
            # BOTTOM-RIGHT: Disk Monitor
            disk_container = QWidget()
            disk_container.setObjectName("diskContainer")
            disk_layout = QVBoxLayout(disk_container)
            disk_layout.setContentsMargins(15, 15, 15, 15)
            
            disk_title = QLabel("Disk Usage")
            disk_title.setAlignment(Qt.AlignCenter)
            disk_title.setStyleSheet("color: white; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
            
            # Create a new disk monitor widget
            self.disk_monitor = SystemMonitorWidget()
            self.disk_monitor.setFixedSize(250, 150)
            
            # Set Disk monitor color using CPU curve since we'll repurpose it
            disk_pen = pg.mkPen(color=(255, 255, 0), width=2)
            self.disk_monitor.cpu_curve.setPen(disk_pen)
            
            # Hide RAM and Network graphs - show only CPU graph (repurposed for disk)
            self.disk_monitor.ram_plot.setVisible(False)
            self.disk_monitor.net_plot.setVisible(False)
            
            self.disk_stat = QLabel("Disk: 0%")
            self.disk_stat.setStyleSheet("""
                color: #FFFF00;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 14px;
                background-color: rgba(0, 0, 0, 0.6);
                border-radius: 5px;
                padding: 5px;
                margin-top: 5px;
            """)
            self.disk_stat.setAlignment(Qt.AlignCenter)
            
            disk_layout.addWidget(disk_title)
            disk_layout.addWidget(self.disk_monitor)
            disk_layout.addWidget(self.disk_stat)
            
            disk_container.setStyleSheet("""
                #diskContainer {
                    background-color: rgba(0, 0, 0, 0.5);
                    border-radius: 15px;
                    border: 1px solid rgba(255, 255, 0, 0.3);
                }
            """)
            
            # Add all widgets to main grid layout
            main_layout.addWidget(cpu_container, 0, 0)   # Top-left
            main_layout.addWidget(ram_container, 0, 2)   # Top-right
            main_layout.addWidget(center_container, 0, 1, 2, 1)  # Center (spans 2 rows)
            main_layout.addWidget(net_container, 1, 0)   # Bottom-left
            main_layout.addWidget(disk_container, 1, 2)  # Bottom-right
            
            # Set column and row stretches for proper layout
            main_layout.setColumnStretch(0, 2)  # Left column
            main_layout.setColumnStretch(1, 3)  # Center column (wider)
            main_layout.setColumnStretch(2, 2)  # Right column
            main_layout.setRowStretch(0, 1)     # Top row
            main_layout.setRowStretch(1, 1)     # Bottom row
            
            # Set overall widget properties - ensure it fits on screen
            self.setFixedSize(min(window_width, screen_width - 50), min(window_height, screen_height - 50))
            self.setStyleSheet("background-color: black;")
            
            # Initialize network variables for calculations
            self.last_net_time = time.time()
            self.last_net_io = psutil.net_io_counters()
            
            # Timer for updates
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_stats)
            self.timer.timeout.connect(self.SpeechRecogText)
            self.timer.start(1000)  # Update every second

        def update_stats(self):
            """Update system stats"""
            # Update CPU stats
            cpu_percent = psutil.cpu_percent()
            self.cpu_stat.setText(f"CPU: {cpu_percent:.1f}%")
            
            # Update RAM stats
            ram = psutil.virtual_memory()
            ram_percent = ram.percent
            ram_total = ram.total / (1024 * 1024 * 1024)  # Convert to GB
            ram_used = ram.used / (1024 * 1024 * 1024)    # Convert to GB
            self.ram_stat.setText(f"RAM: {ram_percent:.1f}% ({ram_used:.1f}/{ram_total:.1f} GB)")
            
            # Update Network stats (calculate speed)
            current_time = time.time()
            time_elapsed = current_time - self.last_net_time
            
            current_net_io = psutil.net_io_counters()
            bytes_sent = current_net_io.bytes_sent - self.last_net_io.bytes_sent
            bytes_recv = current_net_io.bytes_recv - self.last_net_io.bytes_recv
            
            # Calculate speed in KB/s
            send_speed = bytes_sent / (1024 * time_elapsed)
            recv_speed = bytes_recv / (1024 * time_elapsed)
            total_speed = send_speed + recv_speed
            
            # Format display based on speed
            if total_speed < 1000:
                self.net_stat.setText(f"NETWORK: {total_speed:.1f} KB/s")
            else:
                self.net_stat.setText(f"NETWORK: {total_speed/1024:.2f} MB/s")
            
            # Update disk stats
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_total = disk.total / (1024 * 1024 * 1024)  # Convert to GB
            disk_used = disk.used / (1024 * 1024 * 1024)    # Convert to GB
            self.disk_stat.setText(f"DISK: {disk_percent:.1f}% ({disk_used:.1f}/{disk_total:.1f} GB)")
            
            # Update for next calculation
            self.last_net_time = current_time
            self.last_net_io = current_net_io
            
            # Update curve data for SystemMonitorWidgets
            self.cpu_monitor.update_cpu(cpu_percent)
            self.ram_monitor.update_ram(ram_percent)
            self.net_monitor.update_net(total_speed)
            self.disk_monitor.update_cpu(disk_percent)  # Using CPU curve for disk
            
            # Check mic status from file and sync the UI
            self.check_mic_status()
        
        def check_mic_status(self):
            """Check and sync mic status from Mic.data file"""
            try:
                mic_file_path = TempDirectoryPath('Mic.data')
                if os.path.exists(mic_file_path):
                    with open(mic_file_path, "r", encoding='utf-8') as file:
                        mic_status = file.read().strip()
                        file_mic_state = (mic_status == "True")
                        
                        # Only update the UI if the state is different
                        if self.toggled != file_mic_state:
                            self.toggled = file_mic_state
                            self.update_mic_icon()
            except Exception as e:
                print(f"[Error] Failed to read mic status in InitialScreen: {e}")
                
        def update_mic_icon(self):
            """Update the mic icon based on current toggled state"""
            if self.toggled:
                # Mic is ON
                pixmap = QPixmap(GraphicsDirectoryPath('Mic_on.png'))
            else:
                # Mic is OFF
                pixmap = QPixmap(GraphicsDirectoryPath('Mic_off.png'))
                
            self.mic_label.setPixmap(pixmap.scaled(60, 60))
        
        def SpeechRecogText(self):
            """Update the status label with the content from Status.data"""
            try:
                status_file_path = os.path.join(TempDirPath, "Status.data")
                if os.path.exists(status_file_path):
                    with open(status_file_path, "r", encoding='utf-8') as file:
                        status_text = file.read().strip()
                        if status_text:
                            self.status_label.setText(StyleAssistantStatus(status_text))
            except Exception as e:
                print(f"Error reading Status.data in InitialScreen: {e}")
        
        def toggle_icon(self, event=None):
            """Toggle microphone icon and state"""
            self.toggled = not self.toggled
            
            if self.toggled:
                # Mic ON
                pixmap = QPixmap(GraphicsDirectoryPath('Mic_on.png'))
                MicButtonClosed()
                SetAssistantStatus("Listening... ")
            else:
                # Mic OFF
                pixmap = QPixmap(GraphicsDirectoryPath('Mic_off.png'))
                MicButtonInitialed()
                SetAssistantStatus("Available... ")
                
            self.update_mic_icon()

class MessageScreen(QWidget):
    def __init__(self, parent = None):
            super().__init__(parent)
            # Get screen size
            desktop = QApplication.desktop()
            screen_width = desktop.screenGeometry().width()
            screen_height = desktop.screenGeometry().height()
            
            # Calculate 16:9 dimensions based on screen size
            window_width, window_height = calculate_16_9_dimensions(width=screen_width)
            if window_height > screen_height:
                window_width, window_height = calculate_16_9_dimensions(height=screen_height)
            
            layout = QVBoxLayout()
            label = QLabel("")
            layout.addWidget(label)
            chat_section = ChatSection()
            layout.addWidget(chat_section)
            
            self.setLayout(layout)
            self.setFixedSize(window_width, window_height)
            self.setStyleSheet("background-color: black;")

class CustomTopBar(QWidget):
        def __init__(self, parent, stacked_widget):
            super().__init__(parent)
            self.initUI()
            self.current_screen = None
            self.stacked_widget = stacked_widget

        def maximizeWindow(self):
            parent = self.parent()
            if parent and isinstance(parent, QWidget):
                if parent.isMaximized():
                    parent.showNormal()
                    # Restore to 16:9 ratio
                    desktop = QApplication.desktop()
                    screen_width = desktop.screenGeometry().width()
                    screen_height = desktop.screenGeometry().height()
                    window_width, window_height = calculate_16_9_dimensions(width=screen_width)
                    if window_height > screen_height:
                        window_width, window_height = calculate_16_9_dimensions(height=screen_height)
                    parent.setFixedSize(window_width, window_height)
                else:
                    parent.showMaximized()

        def minimizeWindow(self):
            parent = self.parent()
            if parent and isinstance(parent, QWidget):
                parent.showMinimized()

        def closeWindow(self):
            parent = self.parent()
            if parent and isinstance(parent, QWidget):
                parent.close()


        def initUI(self):
            self.setFixedHeight(50)
            layout = QHBoxLayout(self)
            layout.setAlignment(Qt.AlignRight)
            home_button = QPushButton()
            home_icon = QIcon(GraphicsDirectoryPath("Home.png"))
            home_button.setIcon(home_icon)
            home_button.setText(" Home")
            home_button.setStyleSheet("height:40px; line-height:40px; background-color:white; color: black")
            message_button = QPushButton()
            message_icon = QIcon(GraphicsDirectoryPath("Chats.png"))
            message_button.setIcon(message_icon)
            message_button.setText(" Chat")
            message_button.setStyleSheet("height:40px; line-height:40px; background-color:white; color: black")
            minimize_button = QPushButton()
            minimize_icon = QIcon(GraphicsDirectoryPath('Minimize2.png'))
            minimize_button.setIcon(minimize_icon)
            minimize_button.setStyleSheet("background-color:white")
            minimize_button.clicked.connect(self.minimizeWindow)
            self.maximize_button = QPushButton()
            self.maximize_icon = QIcon(GraphicsDirectoryPath('Maximize.png'))
            self.restore_icon = QIcon(GraphicsDirectoryPath('Minimize.png'))
            self.maximize_button.setIcon(self.maximize_icon)
            self.maximize_button.setFlat(True)
            self.maximize_button.setStyleSheet("background-color:white")
            self.maximize_button.clicked.connect(self.maximizeWindow)
            close_button = QPushButton()
            close_icon = QIcon(GraphicsDirectoryPath('Close.png'))
            close_button.setIcon(close_icon)
            close_button.setStyleSheet("background-color:white")
            close_button.clicked.connect(self.closeWindow)
            line_frame = QFrame()
            line_frame.setFixedHeight(1)
            line_frame.setFrameShape(QFrame.HLine)
            line_frame.setFrameShadow(QFrame.Sunken)
            line_frame.setStyleSheet("border-color: black;")
            title_label = QLabel(f"{str(Assistantname).capitalize()} AI")
            title_label.setStyleSheet("color: black; font-size: 18px; background-color: white")
            home_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
            message_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
            layout.addWidget(title_label)
            layout.addStretch(1)
            layout.addWidget(home_button)
            layout.addWidget(message_button)
            layout.addStretch(1)
            layout.addWidget(minimize_button)
            layout.addWidget(self.maximize_button)
            layout.addWidget(close_button)
            layout.addWidget(line_frame)
            self.draggable = True
            self.offset = None

        def paintEvent(self, event):
            painter = QPainter(self)
            painter.fillRect(self.rect(), Qt.white)
            super().paintEvent(event)

        def minimizeWindow(self):
            self.parent().showMinimized()

        def showMaximize(self):
            if self.parent().isMaximized():
                self.parent().showNormal()
                self.maximize_button.setIcon(self.maximize_icon)
                
                # Restore to 16:9 ratio
                desktop = QApplication.desktop()
                screen_width = desktop.screenGeometry().width()
                screen_height = desktop.screenGeometry().height()
                window_width, window_height = calculate_16_9_dimensions(width=screen_width)
                if window_height > screen_height:
                    window_width, window_height = calculate_16_9_dimensions(height=screen_height)
                self.parent().setFixedSize(window_width, window_height)
            else:
                self.parent().showMaximized()
                self.maximize_button.setIcon(self.restore_icon)
        
        def closeWindow(self):
            self.parent().close()

        def mousePressEvent(self, event):
            if self.draggable:
                self.offset = event.pos()

        def mouseMoveEvent(self, event):
            if self.draggable and self.offset:
                new_pos = event.globalPos() - self.offset
                self.parent().move(new_pos)

        def showMessageScreen(self):
            if self.current_screen is not None:
                self.current_screen.hide()

            message_screen = MessageScreen(self)
            layout = self.parent().layout()
            if layout is not None:
                layout.addWidget(message_screen)
            self.current_screen = message_screen

        def showInitialScreen(self):
            if self.current_screen is not None:
                self.current_screen.hide()

            initial_screen = InitialScreen(self)
            layout = self.parent().layout()
            if layout is not None:
                layout.addWidget(initial_screen)
            self.current_screen = initial_screen

class SetupScreen(QDialog):
    """First-time setup screen that asks for username"""
    def __init__(self, parent=None):
        super(SetupScreen, self).__init__(parent)
        self.setWindowTitle("NOVA Setup")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setStyleSheet("""
            QDialog {
                background-color: black;
                border: 1px solid #333333;
                border-radius: 10px;
            }
        """)
        
        # Calculate a good size for the setup window (smaller than main window)
        desktop = QApplication.desktop()
        screen_width = desktop.screenGeometry().width()
        screen_height = desktop.screenGeometry().height()
        
        # Define window dimensions - 50% of screen width, maintain aspect ratio
        window_width = int(screen_width * 0.5)
        window_height = int(window_width * 0.6)  # 10:6 aspect ratio
        
        # Set window size and position
        self.setFixedSize(window_width, window_height)
        self.move((screen_width - window_width) // 2, 
                 (screen_height - window_height) // 2)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)
        
        # Add welcome header
        header_label = QLabel("Welcome to NOVA AI")
        header_label.setStyleSheet("""
            color: white;
            font-size: 32px;
            font-weight: bold;
        """)
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        # Create a container for the central content
        central_container = QWidget()
        central_layout = QHBoxLayout(central_container)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(30)
        
        # Left side: GIF animation
        gif_container = QWidget()
        gif_layout = QVBoxLayout(gif_container)
        gif_layout.setContentsMargins(0, 0, 0, 0)
        gif_layout.setAlignment(Qt.AlignCenter)
        
        self.gif_label = QLabel()
        self.gif_label.setMinimumSize(300, 200)  # Force minimum size
        self.gif_label.setStyleSheet("background-color: transparent;")
        self.gif_label.setAlignment(Qt.AlignCenter)
        self.gif_label.setScaledContents(False)  # Let it scale properly
        
        # Use absolute path for the GIF to ensure it loads
        gif_path = GraphicsDirectoryPath('Jarvis.gif')
        print(f"[Info] Loading GIF from: {gif_path}")
        if not os.path.exists(gif_path):
            print(f"[Error] GIF file not found at: {gif_path}")
            # Try to find it in the current directory structure as fallback
            for root, dirs, files in os.walk("."):
                for file in files:
                    if file == "Jarvis.gif":
                        gif_path = os.path.join(root, file)
                        print(f"[Info] Found GIF at: {gif_path}")
                        break
                if os.path.exists(gif_path) and gif_path != GraphicsDirectoryPath('Jarvis.gif'):
                    break
        
        movie = QMovie(gif_path)
        # Set a fixed size for the movie that's large enough
        movie.setScaledSize(QSize(427, 240))
        self.gif_label.setMovie(movie)
        movie.start()
        
        gif_layout.addWidget(self.gif_label)
        gif_container.setStyleSheet("""
            background-color: rgba(0, 0, 0, 0.2);
            border-radius: 15px;
            padding: 10px;
        """)
        
        # Right side: form controls
        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(20)
        form_layout.setAlignment(Qt.AlignCenter)
        
        # Add description
        description = QLabel("Please enter your name to personalize your experience")
        description.setStyleSheet("""
            color: #DDDDDD;
            font-size: 16px;
        """)
        description.setAlignment(Qt.AlignCenter)
        description.setWordWrap(True)
        form_layout.addWidget(description)
        
        # Add input field
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Your Name")
        self.name_input.setStyleSheet("""
            QLineEdit {
                background-color: #2D2D2D;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 8px;
                font-size: 16px;
                margin-top: 0px;
            }
            QLineEdit:focus {
                border: 2px solid #3D8BFF;
            }
        """)
        self.name_input.setMinimumHeight(50)
        form_layout.addWidget(self.name_input)
        
        # Add Continue button
        self.continue_button = QPushButton("Continue")
        self.continue_button.setCursor(Qt.PointingHandCursor)
        self.continue_button.setStyleSheet("""
            QPushButton {
                background-color: #3D8BFF;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 7px;
                font-size: 16px;
                font-weight: bold;
                min-height: 50px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #5A9CFF;
            }
            QPushButton:pressed {
                background-color: #2D6BCC;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #AAAAAA;
            }
        """)
        self.continue_button.clicked.connect(self.save_username)
        # Initially enable the button - we'll disable it if empty
        self.continue_button.setEnabled(True)
        form_layout.addWidget(self.continue_button)
        
        # Error message placeholder
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #FF5555; font-size: 14px;")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setWordWrap(True)
        form_layout.addWidget(self.error_label)
        
        # Add spacer to push form to the center
        form_layout.addStretch()
        
        # Add the form container to the right side
        form_container.setStyleSheet("""
            background-color: rgba(0, 0, 0, 0.2);
            border-radius: 15px;
        """)
        
        # Add containers to the central layout
        central_layout.addWidget(gif_container, 1)  # 1 part for GIF
        central_layout.addWidget(form_container, 1)  # 1 part for form
        
        # Add the central container to the main layout
        layout.addWidget(central_container, 1)  # Give it stretch
        
        # Enable button state management
        self.name_input.textChanged.connect(self.update_button_state)
        
        # Set initial focus
        self.name_input.setFocus()
    
    def update_button_state(self):
        """Enable continue button only when text is entered"""
        self.continue_button.setEnabled(bool(self.name_input.text().strip()))
    
    def save_username(self):
        """Save the username to the .env file"""
        username = self.name_input.text().strip()
        if not username:
            return
            
        try:
            # If set_key is available, update the .env file
            if HAS_SET_KEY:
                env_path = ".env"
                set_key(env_path, "Username", username)
                print(f"[Info] Username saved: {username}")
            else:
                print(f"[Warning] Username not saved to .env (set_key not available): {username}")
                
            # Store username in a temporary file as a fallback
            try:
                os.makedirs(os.path.dirname(TempDirectoryPath('Username.data')), exist_ok=True)
                with open(TempDirectoryPath('Username.data'), "w", encoding='utf-8') as f:
                    f.write(username)
                print(f"[Info] Username saved to temporary file")
            except Exception as temp_e:
                print(f"[Warning] Failed to save username to temporary file: {temp_e}")
                
            # Close the dialog
            self.accept()
        except Exception as e:
            print(f"[Error] Failed to save username: {e}")
            # Show error message
            self.error_label.setText(f"Error: Could not save settings. Please try again.")

# Function to check if setup is needed
def check_first_run():
    """Check if this is the first run that needs setup"""
    env_vars = dotenv_values(".env")
    username = env_vars.get("Username", "").strip()
    return not username or username == "User"

# Function to run the setup screen if needed
def run_setup_if_needed(app):
    """Show setup screen if needed and return the result"""
    if check_first_run():
        setup_screen = SetupScreen()
        result = setup_screen.exec_()
        
        # If setup was completed successfully, reload environment vars
        if result == QDialog.Accepted:
            # Update global variables in Main module if a reference was provided
            if main_username_ref is not None:
                try:
                    # Reload env_vars
                    new_env_vars = dotenv_values(".env")
                    new_username = new_env_vars.get("Username", "")
                    
                    # Use the reference to update Main's Username
                    globals()[main_username_ref] = new_username
                    print(f"[Info] Updated Main module Username to: {new_username}")
                    
                    # Try to directly import and call Main's reload function
                    try:
                        import sys
                        if 'Main' in sys.modules:
                            # If Main is already imported, we can directly call its function
                            if hasattr(sys.modules['Main'], 'reload_user_info'):
                                sys.modules['Main'].reload_user_info()
                                print("[Info] Called Main.reload_user_info() successfully")
                    except Exception as import_e:
                        print(f"[Warning] Could not call Main.reload_user_info: {import_e}")
                except Exception as e:
                    print(f"[Error] Failed to update Username reference: {e}")
                    
            return True
        return False
    return True

# This will be called from Main.py to set up the reference to its Username variable
def register_main_username_ref(ref_name):
    """Register the name of the variable in Main that holds the Username"""
    global main_username_ref
    main_username_ref = ref_name
    print(f"[Info] Registered Main module Username reference: {ref_name}")

class MainWindow(QMainWindow):
    
    def __init__(self):
        super().__init__()
        
        # Check if first-time setup is needed
        if check_first_run():
            setup_screen = SetupScreen(self)
            result = setup_screen.exec_()
            if result != QDialog.Accepted:
                print("[Error] Setup was cancelled or failed")
                sys.exit(1)
        
        # Try to call Main's reload_user_info function to ensure username is updated
        try:
            import sys
            if 'Main' in sys.modules and hasattr(sys.modules['Main'], 'reload_user_info'):
                sys.modules['Main'].reload_user_info()
                print("[Info] Called Main.reload_user_info from MainWindow init")
        except Exception as e:
            print(f"[Warning] Could not call Main.reload_user_info from MainWindow: {e}")
        
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.initUI()

    def initUI(self):
        # Get screen size
        desktop = QApplication.desktop()
        screen_width = desktop.screenGeometry().width()
        screen_height = desktop.screenGeometry().height()
        
        # Calculate 16:9 dimensions based on screen size
        window_width, window_height = calculate_16_9_dimensions(width=screen_width)
        if window_height > screen_height:
            window_width, window_height = calculate_16_9_dimensions(height=screen_height)
        
        stacked_widget = QStackedWidget(self)
        initial_screen = InitialScreen()
        message_screen = MessageScreen()
        stacked_widget.addWidget(initial_screen)
        stacked_widget.addWidget(message_screen)
        
        # Set window size to maintain 16:9 aspect ratio
        self.setGeometry(
            (screen_width - window_width) // 2,  # Center horizontally
            (screen_height - window_height) // 2,  # Center vertically
            window_width, 
            window_height
        )
        
        self.setStyleSheet("background-color: black;")
        top_bar = CustomTopBar(self, stacked_widget)
        self.setMenuWidget(top_bar)
        self.setCentralWidget(stacked_widget)

def GraphicalUserInterface():
    app = QApplication(sys.argv)
    
    # Show setup screen if needed
    if not run_setup_if_needed(app):
        print("[Error] Setup was cancelled or failed")
        return
        
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    GraphicalUserInterface()