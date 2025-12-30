"""Configuration settings for the flash sintering control system.
"""

# DAQ Configuration
DAQ_DEVICE = "Dev1"  # NI DAQ device name
DAQ_RATE = 1000  # Sampling rate in Hz
DAQ_BUFFER_SIZE = 1000  # Buffer size for DAQ

# Analog Input Channels
AI_CHANNELS = {
    "sample_voltage": 0,    # AI0: Voltage across the sample
    "shunt_voltage": 1,     # AI1: Voltage across shunt resistor (for current)
    "reference": 2,         # AI2: Reference voltage
    "auxiliary": 3          # AI3: Auxiliary input
}

# Analog Output Channels
AO_CHANNELS = {
    "voltage_control": 0,   # AO0: Controls voltage applied to sample
    "current_control": 1    # AO1: Controls current limit
}

# Keithley Configuration
KEITHLEY_RESOURCE = "USB0::0x05E6::0x6500::04645387::INSTR"  # VISA resource name

# Timer Periods (seconds) - Enhanced to match MATLAB implementation
TIMER_PERIODS = {
    # Control and core timers
    "control": 0.1,              # Control timer period (matches MATLAB)
    "temperature": 1.0,          # Temperature reading timer
    
    # Data acquisition timers (matches MATLAB edit11/edit12)
    "data_standard": 0.1,        # Data acquisition timer (dwell/incubation stages, j=0,1)
    "data_flash": 0.01,          # Data acquisition timer (flash/hold stages, j=2,3)
    
    # Display update timers (matches MATLAB edit15/edit16)
    "display_standard": 0.5,     # Display update timer (dwell/incubation stages)
    "display_flash": 0.1,        # Display update timer (flash/hold stages)
    
    # Image saving timers (matches MATLAB edit39/edit40/edit53)
    "save_image_standard": 1.0,  # Image saving timer (dwell/incubation stages)
    "save_image_flash": 0.1,     # Image saving timer (flash/hold stages)
    "save_image_extended": 0.05, # Image saving timer (extended hold sub-stage, k=1)
    
    # Image display timers (matches MATLAB edit41/edit42/edit54)
    "show_image_standard": 1.0,  # Image display timer (dwell/incubation stages)
    "show_image_flash": 0.1,     # Image display timer (flash/hold stages)
    "show_image_extended": 0.05  # Image display timer (extended hold sub-stage, k=1)
}

# Stage-specific timer configurations (like MATLAB's dynamic timer switching)
STAGE_TIMER_CONFIGS = {
    "DWELL": {
        "data": "data_standard",
        "display": "display_standard", 
        "save_image": "save_image_standard",
        "show_image": "show_image_standard"
    },
    "INCUBATION": {
        "data": "data_standard",
        "display": "display_standard",
        "save_image": "save_image_standard", 
        "show_image": "show_image_standard"
    },
    "FLASH": {
        "data": "data_flash",
        "display": "display_flash",
        "save_image": "save_image_flash",
        "show_image": "show_image_flash"
    },
    "HOLD": {
        "data": "data_flash",
        "display": "display_flash",
        "save_image": "save_image_flash",
        "show_image": "show_image_flash"
    },
    "HOLD_EXTENDED": {  # Sub-stage after 30 seconds in hold (k=1)
        "data": "data_flash",
        "display": "display_flash", 
        "save_image": "save_image_extended",
        "show_image": "show_image_extended"
    }
}

# File Paths
DEFAULT_SAVE_PATH = "data/"
DEFAULT_VIDEO_PATH = "videos/"

# Camera Settings
CAMERA_EXPOSURE = 0.01  # Default exposure time (seconds)

# Voltage/Current Scaling Factors (Sorensen DLM 300-2 specifications)
VOLTAGE_SCALE_OUTPUT = 60    # 300V/5V = 60V per volt (matches MATLAB: voltage * 5/300)
VOLTAGE_SCALE_INPUT = 60
CURRENT_SCALE = 0.4          # 2A/5V = 0.4A per volt (matches MATLAB: current * 5/2000)
MONITOR_RANGE = 5            # 0-5V monitor output range

# Current limit scaling: current_mA / (CURRENT_SCALE * 1000) = current_mA / 400
# Example: 160mA -> 160/400 = 0.4V (same as MATLAB: 160 * 5/2000 = 0.4V)

# Backward compatibility - use output scaling as default
VOLTAGE_SCALE = VOLTAGE_SCALE_OUTPUT

# Plotting Configuration for Smooth Real-time Performance
PLOTTING_CONFIG = {
    # Data acquisition rates (Hz)
    "data_acquisition_rate": 20,    # 20 Hz = 50ms intervals
    "plot_update_rate": 10,         # 10 Hz = 100ms plot updates
    
    # Data management
    "max_data_points": 2000,        # Maximum points to store (100 seconds at 20 Hz)
    "plot_window_seconds": 30,      # Time window to display (seconds)
    
    # Compressed Timeline Settings
    "enable_compressed_timeline": True,  # Enable compressed timeline view
    "focus_window_seconds": 30,          # High-resolution recent data window
    "compression_ratio": 0.7,            # Ratio of plot width for compressed data (0.7 = 70%)
    "compression_exponent": 0.3,         # Logarithmic compression factor (lower = more compression)
    "show_timeline_separator": True,     # Show visual separator between compressed/recent
    
    # Smoothing parameters
    "smoothing_window": 5,          # Moving average window size
    "enable_smoothing": True,       # Enable data smoothing
    
    # Axis formatting
    "voltage_axis_color": "blue",
    "current_axis_color": "red", 
    "grid_major_alpha": 0.8,
    "grid_minor_alpha": 0.6,
    
    # Performance optimizations
    "use_antialiasing": True,       # Enable line antialiasing
    "use_draw_idle": True,          # Use optimized canvas updates
    "axis_auto_scale": True,        # Enable dynamic axis scaling
    "axis_padding_percent": 10      # Padding around data (percentage)
}

# Default Experiment Parameters
DEFAULT_PARAMS = {
    "dwell_time": 300,        # Seconds
    "voltage": 100,           # Volts
    "current": 60,            # mA
    "shutdown_time": 0,       # Seconds after experiment start
    "hold_current": 60,       # Seconds to hold after flash
    "target_temperature": 500  # Celsius
}

# GUI Colors
COLORS = {
    "active": "#00E600",    # Green for active elements
    "inactive": "#E60000",  # Red for inactive elements
    "neutral": "#E6E6E6"    # Gray for neutral elements
}

# Experiment Stages
STAGES = {
    "DWELL": 0,
    "INCUBATION": 1,
    "FLASH": 2,
    "HOLD": 3,
    "SHUTDOWN": 4
} 