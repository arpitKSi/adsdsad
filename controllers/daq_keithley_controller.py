"""Controller for DAQ and Keithley instruments."""
import sys
import time
from utils.logger import setup_logger
from config.settings import (DAQ_DEVICE, AI_CHANNELS,
                           KEITHLEY_RESOURCE, DAQ_RATE, DAQ_BUFFER_SIZE,
                           VOLTAGE_SCALE_OUTPUT, VOLTAGE_SCALE_INPUT, CURRENT_SCALE)

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

class DAQController:
    """Controller for DAQ and Keithley instruments."""
    def __init__(self):
        """Initialize the controller."""
        self.logger = setup_logger(__name__)
        self.ai_task = None
        self.ao_task = None
        self.keithley = None
        self.initialize_devices()

    def initialize_devices(self):
        """Initialize DAQ and Keithley devices."""
        # Initialize DAQ
        if NIDAQMX_AVAILABLE:
            try:
                # Initialize DAQ for analog input
                self.ai_task = nidaqmx.Task()
                for name, channel in AI_CHANNELS.items():
                    self.ai_task.ai_channels.add_ai_voltage_chan(
                        f"{DAQ_DEVICE}/ai{channel}",
                        terminal_config=nidaqmx.constants.TerminalConfiguration.RSE,
                        min_val=-5.0, max_val=5.0
                    )
                self.ai_task.timing.cfg_samp_clk_timing(
                    rate=DAQ_RATE,
                    sample_mode=AcquisitionType.FINITE,
                    samps_per_chan=DAQ_BUFFER_SIZE
                )
                self.logger.info("NI-DAQ tasks initialized successfully")

                # Initialize DAQ for analog output
                self.ao_task = nidaqmx.Task()
                self.ao_task.ao_channels.add_ao_voltage_chan(
                    f"{DAQ_DEVICE}/ao0:1",
                    min_val=0, max_val=5.0
                )
                self.ao_task.write([0, 0])
            except Exception as e:
                self.logger.error(f"Error initializing DAQ: {e}")
                self.ai_task = None
                self.ao_task = None

        # Initialize Keithley
        if PYVISA_AVAILABLE:
            try:
                rm = pyvisa.ResourceManager()
                self.keithley = rm.open_resource(KEITHLEY_RESOURCE)
                
                # Configure Keithley for current measurement
                if not self.configure_keithley_current():
                    raise RuntimeError("Failed to configure Keithley")
                
                self.logger.info("Keithley instrument initialized successfully")
            except Exception as e:
                self.logger.error(f"Error initializing Keithley: {e}")
                self.keithley = None

    def get_measurements(self):
        """Get voltage and current measurements from DAQ with validation."""
        try:
            if not NIDAQMX_AVAILABLE or not self.ai_task:
                self.logger.error("DAQ not available or task not initialized")
                return None, None
            
            # Read with timeout and error checking
            data = self.ai_task.read(number_of_samples_per_channel=1, timeout=1.0)
            
            if data is None or len(data) < 2:
                self.logger.error("Invalid data received from DAQ")
                return None, None
            
            # Validate raw readings are within expected range (0-5V)
            raw_voltage = data[0][0]
            raw_current = data[0][1]
            
            if not (0 <= raw_voltage <= 5) or not (0 <= raw_current <= 5):
                self.logger.error(f"Raw readings out of range - V: {raw_voltage}V, I: {raw_current}V")
                return None, None
            
            # Scale the readings using correct scaling factors
            voltage = raw_voltage * VOLTAGE_SCALE_INPUT  # 0-5V → 0-300V
            current = raw_current * (CURRENT_SCALE * 1000)  # 0-5V → 0-2000mA
            
            # Validate scaled readings
            if not (0 <= voltage <= 300) or not (0 <= current <= 2000):
                self.logger.error(f"Scaled readings out of range - V: {voltage}V, I: {current}mA")
                return None, None
            
            self.logger.debug(f"Read measurements - V: {voltage:.2f}V, I: {current:.2f}mA")
            return voltage, current
                
        except Exception as e:
            self.logger.error(f"Error reading measurements: {str(e)}")
            return None, None

    def set_outputs(self, voltage, current):
        """Set voltage and current outputs.
        
        Args:
            voltage (float): Voltage in volts
            current (float): Current in milliamps
        """
        if not NIDAQMX_AVAILABLE or not self.ao_task:
            raise RuntimeError("DAQ not available - cannot set outputs")
            
        try:
            # Validate input ranges
            if not (0 <= voltage <= 300):
                raise ValueError(f"Voltage {voltage}V exceeds 0-300V range")
            if not (0 <= current <= 2000):
                raise ValueError(f"Current {current}mA exceeds 0-2000mA range")

            # Scale the outputs using correct scaling factors
            voltage_scaled = voltage / VOLTAGE_SCALE_OUTPUT  # Scale to 0-5V range
            current_scaled = current / (CURRENT_SCALE * 1000)  # Scale to 0-5V range
            
            # Verify scaling matches MATLAB: voltage*5/300, current*5/2000
            matlab_voltage_scaled = voltage * 5 / 300
            matlab_current_scaled = current * 5 / 2000
            
            # Correct channel order: [voltage, current]
            self.ao_task.write([voltage_scaled, current_scaled])
            self.logger.debug(f"Set DAQ outputs - V: {voltage:.2f}V->({voltage_scaled:.3f}V), I: {current:.2f}mA->({current_scaled:.3f}V)")
            self.logger.debug(f"MATLAB equivalent would be: V->({matlab_voltage_scaled:.3f}V), I->({matlab_current_scaled:.3f}V)")
            
            # Verify scaling accuracy
            if abs(voltage_scaled - matlab_voltage_scaled) > 0.001:
                self.logger.warning(f"Voltage scaling mismatch! Python: {voltage_scaled:.3f}V vs MATLAB: {matlab_voltage_scaled:.3f}V")
            if abs(current_scaled - matlab_current_scaled) > 0.001:
                self.logger.warning(f"Current scaling mismatch! Python: {current_scaled:.3f}V vs MATLAB: {matlab_current_scaled:.3f}V")
        except Exception as e:
            self.logger.error(f"Error setting outputs: {e}")
            raise

    def cleanup(self):
        """Clean up device connections."""
        if self.ai_task:
            self.ai_task.close()
        if self.ao_task:
            self.ao_task.write([0, 0])
            self.ao_task.close()
        if self.keithley:
            self.keithley.close()
        self.logger.info("Device connections closed")

    def check_keithley_status(self):
        """Check Keithley status and clear any errors.
        Returns:
            bool: True if status is OK, False if there was an error
        """
        if not PYVISA_AVAILABLE or not self.keithley:
            return False

        try:
            # Check for errors
            self.keithley.write('*ESR?')
            esr = int(self.keithley.read())
            
            if esr != 0:
                # Get error message
                self.keithley.write('SYST:ERR?')
                error_msg = self.keithley.read().strip()
                self.logger.warning(f"Keithley error detected: {error_msg}")
                
                # Clear status and reset
                self.keithley.write('*CLS')  # Clear status
                self.keithley.write('*RST')  # Reset to default settings
                
                # Reconfigure for current measurement
                self.configure_keithley_current()
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking Keithley status: {e}")
            return False

    def configure_keithley_current(self):
        """Configure Keithley for current measurement."""
        if not PYVISA_AVAILABLE or not self.keithley:
            return False

        try:
            # Configure Keithley for current measurement
            self.keithley.write('*RST')  # Reset to default settings
            self.keithley.write('CONF:CURR:DC')  # Configure for DC current measurement
            self.keithley.write('SENS:CURR:NPLC 0.1')  # Reduced integration time for faster readings
            self.keithley.write('SENS:CURR:RANG:AUTO ON')  # Enable auto-ranging
            self.keithley.write('SENS:CURR:AVER:COUNT 5')  # Reduced averaging count
            self.keithley.write('SENS:CURR:AVER:TCON REP')  # Set averaging type to repeating
            self.keithley.write('SENS:CURR:AVER ON')  # Turn on averaging
            
            # Verify configuration
            self.keithley.write('CONF?')
            config = self.keithley.read().strip()
            if 'CURR:DC' not in config:
                raise ValueError(f"Invalid Keithley configuration: {config}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error configuring Keithley: {e}")
            return False

    def read_keithley_current(self):
        """
        Reads current measurement from Keithley instrument with optimized settings and error handling
        
        Returns:
            tuple: (current in microamperes, measurement_time in seconds) or (None, None) if not available
        """
        if not PYVISA_AVAILABLE or not self.keithley:
            self.logger.error("Keithley not available")
            return None, None

        try:
            start_time = time.time()
            
            # Check status and reconfigure if needed
            if not self.check_keithley_status():
                self.logger.warning("Keithley status check failed, attempting to reconfigure")
                if not self.configure_keithley_current():
                    raise RuntimeError("Failed to reconfigure Keithley")
            
            # Read current from Keithley using MEASure command
            self.keithley.write('MEAS:CURR?')
            current = float(self.keithley.read()) * 1e6  # Convert to microamperes
            
            end_time = time.time()
            measurement_time = end_time - start_time
            
            self.logger.debug(f"Keithley current reading: {current:.10f} µA (Measurement time: {measurement_time:.3f}s)")
            return current, measurement_time
            
        except Exception as e:
            self.logger.error(f"Error reading Keithley current: {e}")
            # Try to recover by reconfiguring
            try:
                self.configure_keithley_current()
            except Exception as reconf_error:
                self.logger.error(f"Failed to recover Keithley: {reconf_error}")
            return None, None 