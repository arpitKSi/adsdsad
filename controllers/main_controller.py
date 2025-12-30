"""Main controller for the flash sintering system.
"""
from .device_controller import DeviceController
from .timer_manager import TimerManager
from config.settings import TIMER_PERIODS, STAGES

class MainController:
    """Main controller coordinating all system components.
    """
    def __init__(self):
        """Initialize main controller."""
        self.device_controller = DeviceController()
        self.timer_manager = TimerManager()
        
        # Pass timer manager reference to device controller for advanced timer control
        self.device_controller.timer_manager = self.timer_manager
        
        self.setup_timers()
        
        # Experiment parameters
        self.dwell_time = 300
        self.hold_current = 60
        self.current_limit = 60
        self.target_temperature = None
        self.hold_time = 60  # NEW: Hold time limit in seconds

    def setup_timers(self):
        """Set up all system timers."""
        # Control timer for experiment stages
        self.timer_manager.add_timer(
            "control",
            TIMER_PERIODS["control"],
            self.control_timer_callback
        )

        # Data acquisition timer
        self.timer_manager.add_timer(
            "data",
            TIMER_PERIODS["data_standard"],
            self.data_timer_callback
        )

        # Display update timer
        self.timer_manager.add_timer(
            "display",
            TIMER_PERIODS["display_standard"],
            self.display_timer_callback
        )

        # Temperature reading timer
        self.timer_manager.add_timer(
            "temperature",
            TIMER_PERIODS["temperature"],
            self.temperature_timer_callback
        )

    def start_experiment(self, voltage, current, dwell_time, hold_current, hold_time, target_temperature=None):
        """Start the flash sintering experiment.
        Args:
            voltage (float): Target voltage in volts
            current (float): Target current in milliamps
            dwell_time (float): Dwell time in seconds
            hold_current (float): Hold time in seconds
            hold_time (float): Hold time limit in seconds
            target_temperature (float): Target temperature before starting (optional)
        """
        # Store experiment parameters
        self.dwell_time = dwell_time
        self.hold_current = hold_current
        self.current_limit = current
        self.hold_time = hold_time  # NEW: Store hold time
        self.target_temperature = target_temperature
        
        self.device_controller.start_process(voltage, current)
        self.timer_manager.start_all()

    def stop_experiment(self):
        """Stop the flash sintering experiment."""
        self.device_controller.stop_process()
        self.timer_manager.stop_all()

    def control_timer_callback(self):
        """Callback for control timer with enhanced stage management."""
        if self.device_controller.is_running:
            self.device_controller.update_stage(
                dwell_time=self.dwell_time,
                hold_current=self.hold_current,
                current_limit=self.current_limit,
                hold_time=self.hold_time,
                target_temperature=self.target_temperature
            )

    def data_timer_callback(self):
        """Callback for data acquisition timer."""
        if self.device_controller.is_running:
            voltage, current, temperature = self.device_controller.get_measurements()
            # Update data storage/logging here

    def display_timer_callback(self):
        """Callback for display update timer."""
        if self.device_controller.is_running:
            voltage, current, temperature = self.device_controller.get_measurements()
            # Update GUI display here

    def temperature_timer_callback(self):
        """Callback for temperature reading timer."""
        if self.device_controller.is_running:
            _, _, temperature = self.device_controller.get_measurements()
            # Update temperature display here

    def update_timer_periods(self, stage):
        """Update timer periods based on experiment stage.
        Args:
            stage (int): Current experiment stage
        """
        if stage == STAGES["FLASH"]:
            self.timer_manager.update_period("data", TIMER_PERIODS["data_flash"])
            self.timer_manager.update_period("display", TIMER_PERIODS["display_flash"])
        else:
            self.timer_manager.update_period("data", TIMER_PERIODS["data_standard"])
            self.timer_manager.update_period("display", TIMER_PERIODS["display_standard"])

    def cleanup(self):
        """Clean up system resources."""
        self.stop_experiment()
        self.device_controller.cleanup()

    def update_parameters(self, electrical_distance, width, thickness, electric_field, current_density):
        """Update experiment parameters.
        Args:
            electrical_distance (float): Electrical distance in cm
            width (float): Sample width in mm
            thickness (float): Sample thickness in mm
            electric_field (float): Electric field in V/cm
            current_density (float): Current density in mA/mm²
        """
        voltage = electric_field * electrical_distance
        current = current_density * width * thickness
        self.device_controller.set_voltage_current_limits(voltage, current) 
        
    def update_hold_time(self, hold_time):
        """Update hold time parameter.
        Args:
            hold_time (float): Hold time limit in seconds
        """
        self.hold_time = hold_time 