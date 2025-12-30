"""Controller for hardware devices (DAQ, Keithley).
"""
import numpy as np
import time
from utils.logger import setup_logger
from config.settings import (DAQ_DEVICE, AI_CHANNELS,
                           KEITHLEY_RESOURCE, DAQ_RATE,
                           VOLTAGE_SCALE_OUTPUT, CURRENT_SCALE,
                           TIMER_PERIODS, STAGES, COLORS, STAGE_TIMER_CONFIGS)
from .daq_keithley_controller import DAQController

import sys

# Check device availability without simulation fallbacks
if sys.platform == 'darwin':
    NIDAQMX_AVAILABLE = False
    PYVISA_AVAILABLE = False
    print("macOS detected - hardware drivers not available")
else:
    try:
        import nidaqmx
        from nidaqmx.constants import AcquisitionType
        NIDAQMX_AVAILABLE = True
    except ImportError:
        NIDAQMX_AVAILABLE = False
        print("WARNING: nidaqmx not available.")

    try:
        import pyvisa
        PYVISA_AVAILABLE = True
    except ImportError:
        PYVISA_AVAILABLE = False
        print("WARNING: pyvisa not available.")

class DeviceController:
    """Controller for hardware devices (DAQ, Keithley).
    """
    def __init__(self):
        """Initialize device controller.
        """
        self.logger = setup_logger(__name__)
        self.daq_controller = DAQController()
        self.is_running = False

        # Initialize device attributes
        self.ai_task = None
        self.ao_task = None
        self.keithley = None

        # Experiment state
        self.current_stage = STAGES["DWELL"]
        self.sub_stage = 0  # Add sub-staging like MATLAB's 'k' variable
        self.start_time = 0
        self.flash_start_time = 0
        self.hold_start_time = 0
        self.stage_2_time = 0  # Time when stage 2 (flash) started
        self.temperature_reached = False  # Track if target temperature reached
        
        # Power supply CV/CC mode tracking
        self.power_supply_mode = "CV"  # Start in Constant Voltage mode
        self.cv_cc_transition_time = None
        self.voltage_before_cc = None
        self.current_limit_reached = False
        
        # Last values for continuity
        self.last_voltage = 0
        self.last_current = 0
        self.last_temperature = 0

        # Initialize voltage and current limits (not applied until start_process)
        self.voltage_limit = 0
        self.current_limit = 0

        # Hold time control
        self.hold_time_limit = 60  # Default hold time limit in seconds
        self.hold_elapsed_time = 0  # Track elapsed time during hold stage
        
        # Flag to indicate if experiment was stopped due to hold time
        self.experiment_stopped_by_hold_time = False

        # Initialize devices
        self.initialize_devices()

    def check_device_connections(self):
        """Check the status of all devices.
        Returns:
            dict: Dictionary with device connection status
        """
        status = {
            "DAQ": {"connected": False, "device": None, "error": None},
            "Keithley": {"connected": False, "device": None, "error": None}
        }
        
        # Check DAQ connection
        if NIDAQMX_AVAILABLE:
            try:
                system = nidaqmx.system.System.local()
                devices = system.devices
                
                if DAQ_DEVICE in [device.name for device in devices]:
                    status["DAQ"]["connected"] = True
                    status["DAQ"]["device"] = DAQ_DEVICE
                    self.logger.info(f"DAQ: Connected to {DAQ_DEVICE}")
                else:
                    status["DAQ"]["error"] = f"Device {DAQ_DEVICE} not found"
                    self.logger.error(f"DAQ: Device {DAQ_DEVICE} not found")
                    
            except Exception as e:
                status["DAQ"]["error"] = str(e)
                self.logger.error(f"DAQ: Error checking connection - {e}")
        else:
            status["DAQ"]["error"] = "nidaqmx not available"

        # Check Keithley connection
        if PYVISA_AVAILABLE:
            try:
                rm = pyvisa.ResourceManager()
                resources = rm.list_resources()
                
                if KEITHLEY_RESOURCE in resources:
                    status["Keithley"]["connected"] = True
                    status["Keithley"]["device"] = KEITHLEY_RESOURCE
                    self.logger.info(f"Keithley: Connected to {KEITHLEY_RESOURCE}")
                else:
                    available_devices = ', '.join(resources) if resources else 'None'
                    status["Keithley"]["error"] = f"Device {KEITHLEY_RESOURCE} not found. Available devices: ({available_devices})"
                    self.logger.error(f"Keithley: Device {KEITHLEY_RESOURCE} not found. Available devices: ({available_devices})")
                    
            except Exception as e:
                status["Keithley"]["error"] = str(e)
                self.logger.error(f"Keithley: Error checking connection - {e}")
        else:
            status["Keithley"]["error"] = "pyvisa not available"

        return status

    def initialize_devices(self):
        """Initialize DAQ and Keithley devices.
        """
        # First check device connections
        device_status = self.check_device_connections()

        if not device_status["DAQ"]["connected"]:
            self.logger.error("DAQ not available - cannot initialize")
            return

        # Initialize DAQ for analog input
        try:
            self.ai_task = nidaqmx.Task()
            # Add analog input channels
            for name, channel in AI_CHANNELS.items():
                self.ai_task.ai_channels.add_ai_voltage_chan(
                    f"{DAQ_DEVICE}/ai{channel}",
                    terminal_config=nidaqmx.constants.TerminalConfiguration.RSE,
                    min_val=-5.0, max_val=5.0
                )
            # Configure timing
            self.ai_task.timing.cfg_samp_clk_timing(
                rate=DAQ_RATE,
                sample_mode=AcquisitionType.FINITE,
                samps_per_chan=2
            )
            self.logger.info("DAQ analog input initialized")

            # Initialize DAQ for analog output
            self.ao_task = nidaqmx.Task()
            # Add analog output channels
            self.ao_task.ao_channels.add_ao_voltage_chan(
                f"{DAQ_DEVICE}/ao0:1",
                min_val=0, max_val=5.0
            )
            # Set initial output to zero
            self.ao_task.write([0, 0])
            self.logger.info("DAQ analog output initialized")

        except Exception as e:
            self.logger.error(f"Error initializing DAQ: {e}")
            self.ai_task = None
            self.ao_task = None

        # Initialize Keithley if available
        if device_status["Keithley"]["connected"]:
            try:
                rm = pyvisa.ResourceManager()
                self.keithley = rm.open_resource(KEITHLEY_RESOURCE)
                self.logger.info(f"Connected to Keithley: {self.keithley.query('*IDN?')}")
            except Exception as e:
                self.logger.error(f"Error connecting to Keithley: {e}")
                self.keithley = None
        else:
            self.logger.error("Keithley not available - cannot initialize")

    def cleanup(self):
        """Clean up device connections.
        """
        try:
            if self.ai_task:
                self.ai_task.close()
            if self.ao_task:
                # Set outputs to zero before closing
                self.ao_task.write([0, 0])
                self.ao_task.close()
            if self.keithley:
                self.keithley.close()
            self.logger.info("Device connections closed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def read_analog_inputs(self):
        """Read all analog inputs.
        """
        if not NIDAQMX_AVAILABLE or not self.ai_task:
            # No simulation - return None to indicate device not available
            return None

        try:
            # Start the task
            self.ai_task.start()
            # Read 2 samples and take the average
            data = self.ai_task.read(number_of_samples_per_channel=2)
            # Stop the task
            self.ai_task.stop()
            # Return average of the 2 samples
            return np.mean(data, axis=0)
        except Exception as e:
            self.logger.error(f"Error reading analog inputs: {e}")
            return None

    def read_keithley_measurements(self):
        """Read both voltage and current from Keithley.
        Returns:
            tuple: (voltage, current) in volts and milliamps, or (None, None) if not available
        """
        if not PYVISA_AVAILABLE or not self.keithley:
            # No simulation - return None to indicate device not available
            return None, None

        try:
            # Check Keithley status before reading
            if not self.daq_controller.check_keithley_status():
                self.logger.warning("Keithley status check failed, attempting to reconfigure")
                if not self.daq_controller.configure_keithley_current():
                    raise RuntimeError("Failed to reconfigure Keithley")
            
            # Read voltage
            self.keithley.write('MEAS:VOLT:DC?')
            voltage = float(self.keithley.read())
            
            # Read current using improved method
            current_ua, measurement_time = self.daq_controller.read_keithley_current()
            current = current_ua / 1000.0  # Convert µA to mA
            
            self.logger.debug(f"Keithley readings - V: {voltage:.2f}V, I: {current:.2f}mA (Measurement time: {measurement_time:.3f}s)")
            return voltage, current
        except Exception as e:
            self.logger.error(f"Error reading Keithley measurements: {e}")
            # Try to recover by reconfiguring
            try:
                self.daq_controller.configure_keithley_current()
            except Exception as reconf_error:
                self.logger.error(f"Failed to recover Keithley: {reconf_error}")
            return None, None

    def read_sample_voltage(self, daq_range=5.0, actual_range=300.0):
        """
        Reads voltage measurement across the sample using DAQ
        Args:
            daq_range (float): The input range of the DAQ in Volts (e.g., 5.0 for ±5V)
            actual_range (float): The actual voltage range across the sample (e.g., 300.0 for 300V)
        Returns:
            float: voltage in Volts
        """
        try:
            with nidaqmx.Task() as task:
                task.ai_channels.add_ai_voltage_chan(
                    physical_channel="Dev1/ai1",  # Using ai1 for voltage measurement
                    terminal_config=nidaqmx.constants.TerminalConfiguration.RSE,
                    min_val=-daq_range,
                    max_val=daq_range
                )
                task.timing.cfg_samp_clk_timing(
                    rate=1000,
                    sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                    samps_per_chan=2
                )
                voltage_raw = task.read(number_of_samples_per_channel=2)
                voltage_mean = sum(voltage_raw) / len(voltage_raw)
                voltage = (actual_range / daq_range) * voltage_mean
                self.logger.debug(f"[DAQ] Raw: {voltage_raw}, Mean: {voltage_mean:.4f} V, Scaled: {voltage:.2f} V")
                return voltage
        except Exception as e:
            self.logger.error(f"Error during voltage measurement: {str(e)}")
            return None

    def get_measurements(self):
        """Get current measurements from both DAQ and Keithley.
        Returns:
            tuple: (voltage, current, temperature) in volts, milliamps, and celsius
        """
        try:          
            # Read voltage from DAQ using improved method
            voltage = self.read_sample_voltage_improved(daq_range=5.0, actual_range=300.0)
            
            # Read current from Keithley using improved method
            current, _ = self.read_keithley_current_improved()  # Unpack tuple, ignore measurement time
            
            # Read temperature (not implemented yet)
            temperature = self.last_temperature
            
            return voltage, current, temperature
            
        except Exception as e:
            self.logger.error(f"Error getting measurements: {e}")
            return None, None, None

    def read_sample_voltage_improved(self, daq_range=5.0, actual_range=300.0):
        """
        Reads voltage measurement across the sample using improved DAQ method
        
        Args:
            daq_range (float): The input range of the DAQ in Volts (e.g., 5.0 for ±5V)
            actual_range (float): The actual voltage range across the sample (e.g., 300.0 for 300V)

        Returns:
            float: voltage in Volts
        """
        try:
            # Create DAQ task for analog input
            with nidaqmx.Task() as task:
                # Add analog input channel for voltage measurement
                task.ai_channels.add_ai_voltage_chan(
                    physical_channel="Dev1/ai1",  # Using ai1 for voltage measurement
                    terminal_config=nidaqmx.constants.TerminalConfiguration.RSE,  # Referenced Single-Ended
                    min_val=-daq_range,
                    max_val=daq_range
                )
                
                # Configure timing
                task.timing.cfg_samp_clk_timing(
                    rate=1000,
                    sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                    samps_per_chan=2  # Minimum 2 samples
                )
                
                # Read voltage from DAQ (returns a list of 2 samples)
                voltage_raw = task.read(number_of_samples_per_channel=2)
                voltage_mean = sum(voltage_raw) / len(voltage_raw)
                # Apply scaling
                voltage = (actual_range / daq_range) * voltage_mean
                
                self.logger.debug(f"[DAQ] Raw: {voltage_raw}, Mean: {voltage_mean:.4f} V, Scaled: {voltage:.2f} V")
                return voltage
            
        except Exception as e:
            self.logger.error(f"Error during voltage measurement: {str(e)}")
            return 0.0  # Return default value instead of raising

    def read_keithley_current_improved(self):
        """
        Reads current measurement from Keithley instrument using improved method
        
        Returns:
            tuple: (current in milliamps, measurement_time in seconds) or (None, None) if not available
        """
        try:
            if not PYVISA_AVAILABLE or not self.keithley:
                self.logger.error("Keithley not available")
                return None, None

            # Check Keithley status before reading
            if not self.daq_controller.check_keithley_status():
                self.logger.warning("Keithley status check failed, attempting to reconfigure")
                if not self.daq_controller.configure_keithley_current():
                    raise RuntimeError("Failed to reconfigure Keithley")

            # Use the improved method from DAQController
            current_ua, measurement_time = self.daq_controller.read_keithley_current()
            current_ma = current_ua / 1000.0  # Convert µA to mA
            
            self.logger.debug(f"[Keithley] Current: {current_ma:.3f} mA (Measurement time: {measurement_time:.3f}s)")
            return current_ma, measurement_time
            
        except Exception as e:
            self.logger.error(f"Error reading Keithley current: {e}")
            # Try to recover by reconfiguring
            try:
                self.daq_controller.configure_keithley_current()
            except Exception as reconf_error:
                self.logger.error(f"Failed to recover Keithley: {reconf_error}")
            return None, None

    def set_outputs(self, voltage, current):
        """Set voltage and current outputs.
        Args:
            voltage (float): Voltage in volts
            current (float): Current in milliamps
        """
        try:
            # Use the DAQ controller's consistent scaling method
            self.daq_controller.set_outputs(voltage, current)
            self.logger.debug(f"Set DAQ outputs - V: {voltage:.2f}V, I: {current:.2f}mA")
            
            # Set Keithley outputs
            if PYVISA_AVAILABLE and self.keithley:
                self.keithley.write(f'SOUR:VOLT {voltage}')
                self.keithley.write(f'SOUR:CURR {current/1000.0}')  # Convert mA to A
                self.logger.debug(f"Set Keithley outputs - V: {voltage:.2f}V, I: {current:.2f}mA")
            
        except Exception as e:
            self.logger.error(f"Error setting outputs: {e}")
            raise

    def start_process(self, voltage, current):
        """Start the flash sintering process.
        Args:
            voltage (float): Target voltage in volts
            current (float): Target current in milliamps
        """
        # Check device connections before starting
        device_status = self.check_device_connections()
        
        if not device_status["DAQ"]["connected"]:
            raise RuntimeError(f"DAQ not connected: {device_status['DAQ']['error']}")
            
        if not device_status["Keithley"]["connected"]:
            raise RuntimeError(f"Keithley not connected: {device_status['Keithley']['error']}")
        
        try:
            self.logger.info("Starting process")
            self.is_running = True
            self.start_time = time.time()
            self.current_stage = STAGES["DWELL"]
            
            # Reset CV/CC tracking for new experiment
            self.reset_cv_cc_tracking()
            
            # Reset hold time flag for new experiment
            self.experiment_stopped_by_hold_time = False
            
            # Set the voltage and current limits and apply them
            self.set_voltage_current_limits(voltage, current)
            self.apply_voltage_current_limits()
            self.logger.info(f"Process started - V: {voltage}V, I: {current}mA (CV mode)")
        except Exception as e:
            self.logger.error(f"Error starting process: {e}")
            self.is_running = False
            raise

    def stop_process(self):
        """Stop the flash sintering process.
        """
        try:
            self.logger.info("Stopping process")
            self.is_running = False
            self.set_outputs(0, 0)
        except Exception as e:
            self.logger.error(f"Error stopping process: {e}")

    def update_stage(self, dwell_time, hold_current, current_limit, hold_time, target_temperature=None):
        """Update the experiment stage based on current conditions.
        Enhanced to match MATLAB implementation with sub-staging and hold time control.
        Args:
            dwell_time (float): Dwell time in seconds
            hold_current (float): Hold time in seconds
            current_limit (float): Current limit in mA
            hold_time (float): Hold time limit in seconds
            target_temperature (float): Target temperature for starting (optional)
        """
        if not self.is_running:
            return

        current_time = time.time() - self.start_time
        voltage, current, temperature = self.get_measurements()

        # Detect CV/CC power supply mode transitions
        if voltage is not None and current is not None:
            cv_cc_transition = self._detect_cv_cc_transition(voltage, current, current_limit)
            
            # Log power supply mode for debugging
            if cv_cc_transition:
                self.logger.debug(f"Power supply mode: {self.power_supply_mode}")

        # Stage 0: DWELL (j=0 in MATLAB)
        if self.current_stage == STAGES["DWELL"]:
            # Wait for target temperature if specified (MATLAB behavior)
            if target_temperature and not self.temperature_reached:
                if temperature and temperature >= target_temperature:
                    self.temperature_reached = True
                    self.logger.info(f"Target temperature {target_temperature}°C reached")
                else:
                    return  # Stay in dwell until temperature reached
            
            # Check if dwell time has passed
            if current_time > dwell_time:
                self.current_stage = STAGES["INCUBATION"]
                self.sub_stage = 0
                self.logger.info("Entering incubation stage (j=1)")
                # Trigger timer period changes for incubation
                self._update_timer_periods_for_stage(STAGES["INCUBATION"])

        # Stage 1: INCUBATION (j=1 in MATLAB)
        elif self.current_stage == STAGES["INCUBATION"]:
            # Flash onset is triggered by CV→CC transition (more accurate than arbitrary threshold)
            if (self.power_supply_mode == "CC" and 
                self.cv_cc_transition_time and 
                time.time() - self.cv_cc_transition_time < 1.0):  # Recent transition
                
                self.current_stage = STAGES["FLASH"]
                self.flash_start_time = time.time()
                self.stage_2_time = time.time()
                self.sub_stage = 0
                self.logger.info("Entering flash stage (j=2) - triggered by CV→CC transition")
                self.logger.info(f"Flash onset: V dropped from {self.voltage_before_cc:.2f}V to {voltage:.2f}V")
                self.logger.info(f"Flash start time set: {self.flash_start_time}")
                # Change to flash timer periods
                self._update_timer_periods_for_stage(STAGES["FLASH"])
            
            # Fallback: traditional current threshold method
            elif current and current > 0.9 * current_limit:
                self.current_stage = STAGES["FLASH"]
                self.flash_start_time = time.time()
                self.stage_2_time = time.time()
                self.sub_stage = 0
                self.logger.info("Entering flash stage (j=2) - traditional current threshold")
                self.logger.info(f"Flash start time set: {self.flash_start_time}")
                # Change to flash timer periods
                self._update_timer_periods_for_stage(STAGES["FLASH"])

        # Stage 2: FLASH (j=2 in MATLAB)
        elif self.current_stage == STAGES["FLASH"]:
            # Debug logging every 2 seconds
            if not hasattr(self, 'last_flash_log_time'):
                self.last_flash_log_time = time.time()
            elif time.time() - self.last_flash_log_time >= 2.0:
                flash_elapsed = time.time() - self.flash_start_time if self.flash_start_time else 0
                self.logger.info(f"FLASH stage: elapsed {flash_elapsed:.1f}s, mode {self.power_supply_mode}, current {current:.1f}mA ({current/current_limit*100:.1f}%)")
                self.last_flash_log_time = time.time()
            
            # Hold stage when current stabilizes at limit (CC mode established)
            if (self.power_supply_mode == "CC" and 
                self.current_limit_reached and
                current and current >= 0.95 * current_limit):
                
                self.current_stage = STAGES["HOLD"]
                self.hold_start_time = time.time()
                self.sub_stage = 0
                self.logger.info("Entering hold stage (j=3) - CC mode stabilized")
                self.logger.info(f"Current stabilized at {current:.2f}mA in CC mode")
                flash_elapsed = time.time() - self.flash_start_time
                self.logger.info(f"Flash stage completed in {flash_elapsed:.2f}s")
                self.logger.info(f"Starting hold time countdown: {hold_time}s limit")
                # Keep flash timer periods during hold

        # Stage 3: HOLD (j=3 in MATLAB)
        elif self.current_stage == STAGES["HOLD"]:
            # Update hold time limit and track elapsed time since flash started
            self.hold_time_limit = hold_time
            
            # Safety check: if flash_start_time wasn't set, use hold_start_time as fallback
            if not hasattr(self, 'flash_start_time') or self.flash_start_time is None:
                self.logger.warning("flash_start_time not set, using hold_start_time as fallback")
                self.flash_start_time = self.hold_start_time
            
            self.hold_elapsed_time = time.time() - self.flash_start_time  # Time since flash start, not hold start
            
            # Debug logging every 2 seconds
            if not hasattr(self, 'last_hold_log_time'):
                self.last_hold_log_time = time.time()
            elif time.time() - self.last_hold_log_time >= 2.0:
                self.logger.info(f"HOLD stage: elapsed {self.hold_elapsed_time:.1f}s / {self.hold_time_limit:.1f}s limit")
                self.last_hold_log_time = time.time()
            
            # Check if hold time limit has been reached
            if self.hold_elapsed_time >= self.hold_time_limit:
                self.logger.info(f"Hold time limit reached ({self.hold_time_limit}s). Stopping experiment automatically.")
                self.logger.info(f"Hold elapsed time: {self.hold_elapsed_time:.2f}s")
                self.logger.info("CV→CC transition hold time completed - experiment terminating as requested")
                
                # Automatically stop the experiment by setting voltage and current to zero
                self.set_outputs(0, 0)
                self.stop_process()
                # Set a flag to indicate experiment was stopped due to hold time
                self.experiment_stopped_by_hold_time = True
                return
            
            hold_elapsed = time.time() - self.hold_start_time
            
            # Sub-staging within HOLD (like MATLAB's k variable)
            if hold_elapsed > 30 and self.sub_stage == 0:
                self.sub_stage = 1
                self.logger.info("Entering hold sub-stage (k=1)")
                # Change to extended hold timer periods
                self._update_timer_periods_for_substage(self.sub_stage)
            
            # Check if hold time is complete (this is the old logic, now superseded by hold time limit above)
            # if hold_elapsed > hold_current:
            #     self.current_stage = STAGES["SHUTDOWN"]
            #     self.logger.info("Entering shutdown stage (j=4)")
            #     # Schedule extended data acquisition (like MATLAB's 10 sec more)
            #     self._schedule_extended_acquisition(10.0)

        # Stage 4: SHUTDOWN (j=4 in MATLAB)
        elif self.current_stage == STAGES["SHUTDOWN"]:
            # Extended data acquisition for 10 more seconds (MATLAB behavior)
            shutdown_elapsed = time.time() - self.hold_start_time
            if shutdown_elapsed > hold_current + 10:  # 10 sec after hold ends
                self.logger.info("Extended acquisition complete, stopping process")
                self.stop_process()

    def _update_timer_periods_for_stage(self, stage):
        """Update timer periods based on experiment stage.
        Matches MATLAB's complex timer management.
        Args:
            stage (int): Current experiment stage
        """
        if not hasattr(self, 'timer_manager'):
            return
            
        # Map stage number to stage name
        stage_names = {v: k for k, v in STAGES.items()}
        stage_name = stage_names.get(stage, "DWELL")
        
        # Get timer configuration for this stage
        if stage_name in STAGE_TIMER_CONFIGS:
            config = STAGE_TIMER_CONFIGS[stage_name]
            
            # Update each timer period based on stage configuration
            for timer_name, period_key in config.items():
                if period_key in TIMER_PERIODS and timer_name in self.timer_manager.timers:
                    new_period = TIMER_PERIODS[period_key]
                    self.timer_manager.update_period(timer_name, new_period)
                    self.logger.debug(f"Updated {timer_name} timer to {new_period}s for stage {stage_name}")
        
        self.logger.debug(f"Updated timer periods for stage {stage_name} ({stage})")

    def _update_timer_periods_for_substage(self, sub_stage):
        """Update timer periods for sub-stages within main stages.
        Matches MATLAB's k-variable based timer changes.
        Args:
            sub_stage (int): Current sub-stage
        """
        if not hasattr(self, 'timer_manager'):
            return
            
        if sub_stage == 1 and self.current_stage == STAGES["HOLD"]:
            # Extended hold period adjustments (like MATLAB k=1)
            # Use HOLD_EXTENDED configuration for different image acquisition rates
            if "HOLD_EXTENDED" in STAGE_TIMER_CONFIGS:
                config = STAGE_TIMER_CONFIGS["HOLD_EXTENDED"]
                
                for timer_name, period_key in config.items():
                    if period_key in TIMER_PERIODS and timer_name in self.timer_manager.timers:
                        new_period = TIMER_PERIODS[period_key]
                        self.timer_manager.update_period(timer_name, new_period)
                        self.logger.debug(f"Updated {timer_name} timer to {new_period}s for extended hold")
        
        self.logger.debug(f"Updated timer periods for sub-stage {sub_stage}")

    def _schedule_extended_acquisition(self, duration):
        """Schedule extended data acquisition after main process.
        Matches MATLAB's behavior of acquiring data for 10 more seconds.
        Args:
            duration (float): Duration in seconds for extended acquisition
        """
        self.logger.info(f"Scheduling extended data acquisition for {duration} seconds")
        # This would continue data acquisition without voltage/current output

    def set_voltage_current_limits(self, voltage, current):
        """Set voltage and current limits for the devices WITHOUT applying them.
        This method only stores the limits. Use apply_voltage_current_limits() to actually apply them.
        Args:
            voltage (float): Voltage in volts
            current (float): Current in milliamps
        """
        try:
            # Store limits without applying them
            self.voltage_limit = voltage
            self.current_limit = current
            self.logger.info(f"Set voltage limit to {voltage}V, current limit to {current}mA (not applied yet)")
            
            # Update last values for tracking
            self.last_voltage = voltage
            self.last_current = current
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting voltage/current limits: {e}")
            return False

    def apply_voltage_current_limits(self):
        """Apply the previously set voltage and current limits to the devices.
        This should only be called when starting acquisition.
        """
        try:
            if not hasattr(self, 'voltage_limit') or not hasattr(self, 'current_limit'):
                self.logger.warning("No voltage/current limits set to apply")
                return False
                
            # Use the DAQ controller's consistent scaling method
            self.daq_controller.set_outputs(self.voltage_limit, self.current_limit)
            self.logger.info(f"Applied voltage limit: {self.voltage_limit}V, current limit: {self.current_limit}mA")
            
            # Set current limit on Keithley
            if PYVISA_AVAILABLE and self.keithley:
                # Convert mA to A for Keithley
                current_amps = self.current_limit / 1000.0
                self.keithley.write(f'CURR {current_amps}')
                self.logger.info(f"Applied current limit to Keithley: {self.current_limit}mA ({current_amps}A)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error applying voltage/current limits: {e}")
            return False

    def calculate_limits_from_parameters(self, elec_dist, sample_width, sample_thickness, elec_field, current_density):
        """Calculate voltage and current limits from sample parameters.
        Args:
            elec_dist (float): Electrical distance in mm
            sample_width (float): Sample width in mm
            sample_thickness (float): Sample thickness in mm
            elec_field (float): Electric field in V/mm
            current_density (float): Current density in mA/mm²
        Returns:
            tuple: (voltage, current) in volts and milliamps
        """
        try:
            # Calculate voltage needed (V = E * d)
            voltage = elec_field * elec_dist
            
            # Calculate current needed (I = J * A)
            area = sample_width * sample_thickness  # mm²
            current = current_density * area  # mA
            
            self.logger.info(f"Calculated limits - Voltage: {voltage}V, Current: {current}mA")
            return voltage, current
            
        except Exception as e:
            self.logger.error(f"Error calculating limits: {e}")
            return 0, 0

    def _detect_cv_cc_transition(self, voltage, current, current_limit):
        """Detect CV/CC mode transitions in the power supply.
        
        This is critical for flash sintering because:
        - CV Mode: Power supply maintains set voltage, current varies with resistance
        - CC Mode: When current hits limit, voltage drops to maintain constant current
        
        Args:
            voltage (float): Current voltage reading
            current (float): Current reading  
            current_limit (float): Set current limit
        """
        cv_cc_threshold = 0.95  # 95% of current limit indicates CC mode entry
        
        # Detect CV → CC transition
        if (self.power_supply_mode == "CV" and 
            current >= cv_cc_threshold * current_limit):
            
            self.power_supply_mode = "CC"
            self.cv_cc_transition_time = time.time()
            self.voltage_before_cc = voltage
            self.current_limit_reached = True
            
            self.logger.info(f"Power supply CV→CC transition detected!")
            self.logger.info(f"Voltage before CC: {self.voltage_before_cc:.2f}V")
            self.logger.info(f"Current at transition: {current:.2f}mA")
            
            return True  # Transition occurred
            
        # Detect CC → CV transition (if current drops significantly)
        elif (self.power_supply_mode == "CC" and 
              current < 0.8 * current_limit):
            
            self.power_supply_mode = "CV"
            self.current_limit_reached = False
            
            self.logger.info(f"Power supply CC→CV transition detected!")
            self.logger.info(f"Current dropped to: {current:.2f}mA")
            
            return True  # Transition occurred
            
        return False  # No transition 

    def get_power_supply_status(self):
        """Get current power supply mode and status.
        
        Returns:
            dict: Power supply status information
        """
        status = {
            "mode": self.power_supply_mode,
            "cv_cc_transition_time": self.cv_cc_transition_time,
            "voltage_before_cc": self.voltage_before_cc,
            "current_limit_reached": self.current_limit_reached,
            "time_in_cc_mode": None
        }
        
        if self.cv_cc_transition_time:
            status["time_in_cc_mode"] = time.time() - self.cv_cc_transition_time
            
        return status

    def reset_cv_cc_tracking(self):
        """Reset CV/CC mode tracking for new experiment."""
        self.power_supply_mode = "CV"
        self.cv_cc_transition_time = None
        self.voltage_before_cc = None
        self.current_limit_reached = False
        self.logger.info("Reset CV/CC tracking - starting in CV mode")

    def test_current_scaling(self, test_current=160):
        """Test current scaling to verify it matches MATLAB behavior.
        Args:
            test_current (float): Test current in mA (default 160mA)
        Returns:
            dict: Scaling test results
        """
        try:
            # Calculate expected output voltage for current limit
            # MATLAB formula: current * 5/2000
            matlab_expected = test_current * 5 / 2000
            
            # Python formula: current / (CURRENT_SCALE * 1000)
            python_result = test_current / (CURRENT_SCALE * 1000)
            
            # Test voltage scaling too
            test_voltage = 150  # 150V
            matlab_voltage_expected = test_voltage * 5 / 300
            python_voltage_result = test_voltage / VOLTAGE_SCALE_OUTPUT
            
            results = {
                "current_mA": test_current,
                "matlab_current_output_V": matlab_expected,
                "python_current_output_V": python_result,
                "current_scaling_match": abs(matlab_expected - python_result) < 0.001,
                "voltage_V": test_voltage,
                "matlab_voltage_output_V": matlab_voltage_expected,
                "python_voltage_output_V": python_voltage_result,
                "voltage_scaling_match": abs(matlab_voltage_expected - python_voltage_result) < 0.001
            }
            
            self.logger.info(f"Current scaling test results: {results}")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in scaling test: {e}")
            return None 