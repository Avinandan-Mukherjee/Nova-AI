import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QSizePolicy, QHBoxLayout
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QColor
import pyqtgraph as pg
import psutil
import time
import numpy as np

# Configure pyqtgraph settings for a sci-fi white-on-black theme
pg.setConfigOption('background', 'k')  # Black background
pg.setConfigOption('foreground', 'w')  # White foreground
pg.setConfigOption('antialias', True)  # Enable antialiasing for smoother lines

class SystemMonitorWidget(QWidget):
    def __init__(self, parent=None):
        super(SystemMonitorWidget, self).__init__(parent)
        self.setObjectName("systemMonitor")
        
        # Set up layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)  # Reduce margins for square layout
        layout.setSpacing(2)  # Reduce spacing for tighter layout
        
        # Set widget styling
        self.setStyleSheet("""
            #systemMonitor {
                background-color: rgba(0, 0, 0, 0);
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            QLabel {
                color: white;
                font-family: Consolas, 'Courier New', monospace;
            }
        """)
        
        # Create title
        title = QLabel("SYSTEM VITALS")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Consolas", 9, QFont.Bold))  # Slightly smaller font
        title.setStyleSheet("color: white; margin-bottom: 2px")
        layout.addWidget(title)
        
        # Create metrics display
        self.metrics_layout = QHBoxLayout()
        self.metrics_layout.setSpacing(5)
        
        # CPU usage
        self.cpu_label = QLabel("CPU: 0%")
        self.cpu_label.setStyleSheet("color: white; font-size: 8pt")  # Smaller font
        self.cpu_label.setAlignment(Qt.AlignCenter)
        self.metrics_layout.addWidget(self.cpu_label)
        
        # RAM usage
        self.ram_label = QLabel("RAM: 0%")
        self.ram_label.setStyleSheet("color: white; font-size: 8pt")  # Smaller font
        self.ram_label.setAlignment(Qt.AlignCenter)
        self.metrics_layout.addWidget(self.ram_label)
        
        # Network usage
        self.net_label = QLabel("NET: 0 KB/s")
        self.net_label.setStyleSheet("color: white; font-size: 8pt")  # Smaller font
        self.net_label.setAlignment(Qt.AlignCenter)
        self.metrics_layout.addWidget(self.net_label)
        
        layout.addLayout(self.metrics_layout)
        
        # Create graphs container
        self.graphs_container = QWidget()
        graphs_layout = QVBoxLayout(self.graphs_container)
        graphs_layout.setContentsMargins(0, 0, 0, 0)
        graphs_layout.setSpacing(2)  # Reduce spacing for tighter layout
        
        # CPU graph
        self.cpu_plot = pg.PlotWidget()
        self.cpu_plot.setBackground('k')
        self.cpu_plot.setMinimumHeight(40)  # Adjusted for square layout
        self.cpu_plot.setMaximumHeight(60)  # Adjusted for square layout
        self.cpu_plot.showAxis('left', False)
        self.cpu_plot.showAxis('bottom', False)
        self.cpu_plot.setXRange(0, 100, padding=0)
        self.cpu_plot.setYRange(0, 100, padding=0)
        self.cpu_plot.setMouseEnabled(x=False, y=False)
        self.cpu_plot.setMenuEnabled(False)
        
        # Add grid to CPU graph
        self.cpu_plot.showGrid(x=True, y=True, alpha=0.3)
        
        # RAM graph
        self.ram_plot = pg.PlotWidget()
        self.ram_plot.setBackground('k')
        self.ram_plot.setMinimumHeight(40)  # Adjusted for square layout
        self.ram_plot.setMaximumHeight(60)  # Adjusted for square layout
        self.ram_plot.showAxis('left', False)
        self.ram_plot.showAxis('bottom', False)
        self.ram_plot.setXRange(0, 100, padding=0)
        self.ram_plot.setYRange(0, 100, padding=0)
        self.ram_plot.setMouseEnabled(x=False, y=False)
        self.ram_plot.setMenuEnabled(False)
        
        # Add grid to RAM graph
        self.ram_plot.showGrid(x=True, y=True, alpha=0.3)
        
        # Network graph
        self.net_plot = pg.PlotWidget()
        self.net_plot.setBackground('k')
        self.net_plot.setMinimumHeight(40)  # Adjusted for square layout
        self.net_plot.setMaximumHeight(60)  # Adjusted for square layout
        self.net_plot.showAxis('left', False)
        self.net_plot.showAxis('bottom', False)
        self.net_plot.setXRange(0, 100, padding=0)
        self.net_plot.setMouseEnabled(x=False, y=False)
        self.net_plot.setMenuEnabled(False)
        
        # Add grid to network graph
        self.net_plot.showGrid(x=True, y=True, alpha=0.3)
        
        # Add plots to layout with labels
        cpu_container = QWidget()
        cpu_layout = QVBoxLayout(cpu_container)
        cpu_layout.setContentsMargins(0, 0, 0, 0)
        cpu_layout.setSpacing(0)
        
        cpu_header = QLabel("CPU")
        cpu_header.setAlignment(Qt.AlignCenter)
        cpu_header.setStyleSheet("color: white; font-size: 9px")
        cpu_layout.addWidget(cpu_header)
        cpu_layout.addWidget(self.cpu_plot)
        
        ram_container = QWidget()
        ram_layout = QVBoxLayout(ram_container)
        ram_layout.setContentsMargins(0, 0, 0, 0)
        ram_layout.setSpacing(0)
        
        ram_header = QLabel("RAM")
        ram_header.setAlignment(Qt.AlignCenter)
        ram_header.setStyleSheet("color: white; font-size: 9px")
        ram_layout.addWidget(ram_header)
        ram_layout.addWidget(self.ram_plot)
        
        net_container = QWidget()
        net_layout = QVBoxLayout(net_container)
        net_layout.setContentsMargins(0, 0, 0, 0)
        net_layout.setSpacing(0)
        
        net_header = QLabel("NETWORK")
        net_header.setAlignment(Qt.AlignCenter)
        net_header.setStyleSheet("color: white; font-size: 9px")
        net_layout.addWidget(net_header)
        net_layout.addWidget(self.net_plot)
        
        # Add all graphs to the container
        graphs_layout.addWidget(cpu_container)
        graphs_layout.addWidget(ram_container)
        graphs_layout.addWidget(net_container)
        
        # Add graphs container to main layout
        layout.addWidget(self.graphs_container)
        
        # Initialize data
        self.cpu_data = np.zeros(100)
        self.ram_data = np.zeros(100)
        self.net_data = np.zeros(100)
        
        # Create plot curves with white pens
        cpu_pen = pg.mkPen(color=(255, 255, 255), width=2)
        ram_pen = pg.mkPen(color=(255, 255, 255), width=2)
        net_pen = pg.mkPen(color=(255, 255, 255), width=2)
        
        self.cpu_curve = self.cpu_plot.plot(self.cpu_data, pen=cpu_pen)
        self.ram_curve = self.ram_plot.plot(self.ram_data, pen=ram_pen)
        self.net_curve = self.net_plot.plot(self.net_data, pen=net_pen)
        
        # Initialize network monitoring variables
        self.last_net_io = psutil.net_io_counters()
        self.last_net_time = time.time()
        self.max_net_speed = 100  # Initial max speed in KB/s
        
        # Set up timer for updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)  # Update every second
        
        # Ensure graphs are always visible
        self.graphs_container.setVisible(True)
    
    def update_stats(self):
        # Update CPU usage
        cpu_percent = psutil.cpu_percent()
        self.cpu_data = np.roll(self.cpu_data, -1)
        self.cpu_data[-1] = cpu_percent
        self.cpu_curve.setData(self.cpu_data)
        self.cpu_label.setText(f"CPU: {cpu_percent:.1f}%")
        
        # Update RAM usage
        ram = psutil.virtual_memory()
        ram_percent = ram.percent
        self.ram_data = np.roll(self.ram_data, -1)
        self.ram_data[-1] = ram_percent
        self.ram_curve.setData(self.ram_data)
        self.ram_label.setText(f"RAM: {ram_percent:.1f}%")
        
        # Update network usage
        current_net_io = psutil.net_io_counters()
        current_time = time.time()
        
        # Calculate network speed
        time_elapsed = current_time - self.last_net_time
        bytes_sent = current_net_io.bytes_sent - self.last_net_io.bytes_sent
        bytes_recv = current_net_io.bytes_recv - self.last_net_io.bytes_recv
        
        # Calculate speed in KB/s
        net_speed = (bytes_sent + bytes_recv) / (1024 * time_elapsed)
        
        # Dynamically adjust the scale if needed
        if net_speed > self.max_net_speed:
            self.max_net_speed = max(net_speed * 1.2, 100)  # Increase by 20% with a minimum of 100 KB/s
            self.net_plot.setYRange(0, self.max_net_speed, padding=0)
        
        # Update network data
        self.net_data = np.roll(self.net_data, -1)
        self.net_data[-1] = net_speed
        self.net_curve.setData(self.net_data)
        
        # Format display based on speed
        if net_speed < 1000:
            self.net_label.setText(f"NET: {net_speed:.1f} KB/s")
        else:
            self.net_label.setText(f"NET: {net_speed/1024:.2f} MB/s")
        
        # Update last values
        self.last_net_io = current_net_io
        self.last_net_time = current_time
    
    # Methods for updating individual metrics (used by InitialScreen)
    def update_cpu(self, cpu_percent):
        """Update only the CPU data"""
        self.cpu_data = np.roll(self.cpu_data, -1)
        self.cpu_data[-1] = cpu_percent
        self.cpu_curve.setData(self.cpu_data)
        self.cpu_label.setText(f"CPU: {cpu_percent:.1f}%")
    
    def update_ram(self, ram_percent):
        """Update only the RAM data"""
        self.ram_data = np.roll(self.ram_data, -1)
        self.ram_data[-1] = ram_percent
        self.ram_curve.setData(self.ram_data)
        self.ram_label.setText(f"RAM: {ram_percent:.1f}%")
    
    def update_net(self, net_speed):
        """Update only the network data"""
        # Dynamically adjust the scale if needed
        if net_speed > self.max_net_speed:
            self.max_net_speed = max(net_speed * 1.2, 100)  # Increase by 20% with a minimum of 100 KB/s
            self.net_plot.setYRange(0, self.max_net_speed, padding=0)
        
        # Update network data
        self.net_data = np.roll(self.net_data, -1)
        self.net_data[-1] = net_speed
        self.net_curve.setData(self.net_data)
        
        # Format display based on speed
        if net_speed < 1000:
            self.net_label.setText(f"NET: {net_speed:.1f} KB/s")
        else:
            self.net_label.setText(f"NET: {net_speed/1024:.2f} MB/s")
    
    # For compatibility with existing code that might call these methods
    def toggle_visibility(self):
        pass  # No-op since graphs are always visible
        
    def is_visible(self):
        return True  # Always return True since graphs are always visible

# For testing the widget standalone
if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = SystemMonitorWidget()
    widget.show()
    sys.exit(app.exec_()) 