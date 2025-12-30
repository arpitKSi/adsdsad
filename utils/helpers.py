"""Helper functions for the flash sintering control system.
"""
import time
from datetime import datetime
import os

def current_time_seconds():
    """Return the current time in seconds since the start of the day.
    """
    now = datetime.now()
    return now.hour * 3600 + now.minute * 60 + now.second + now.microsecond/1000000

def elapsed_time(start_time):
    """Calculate elapsed time from start time.
    """
    return time.time() - start_time

def create_directory_if_not_exists(path):
    """Create directory if it doesn't exist.
    """
    if not os.path.exists(path):
        os.makedirs(path)

def get_save_filename(base_path, prefix="experiment", extension=".mat"):
    """Generate a unique filename based on timestamp.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(base_path, f"{prefix}_{timestamp}{extension}")

def calculate_voltage_from_field(field_strength, electrode_distance):
    """Calculate required voltage from electric field strength and electrode distance.
    """
    # E = V/d => V = E*d
    # field_strength in V/cm, electrode_distance in cm, result in V
    return field_strength * electrode_distance

def calculate_current_from_density(current_density, sample_width, sample_thickness):
    """Calculate required current from current density and sample dimensions.
    """
    # J = I/A => I = J*A
    # current_density in mA/mm^2, dimensions in mm, result in mA
    return current_density * (sample_width * sample_thickness)

def clip_value(value, min_val, max_val):
    """Clip a value between min and max.
    """
    return max(min_val, min(max_val, value)) 