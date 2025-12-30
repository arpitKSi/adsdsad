# Flash Sintering Control System

A comprehensive Python implementation of a flash sintering control system, converted from MATLAB. This system provides precise control over the flash sintering process with real-time monitoring and data acquisition capabilities.

## Features

- Real-time control of voltage and current
- Temperature monitoring and control
- Data acquisition and storage
- State machine for process control
- GUI interface for monitoring and control
- Support for National Instruments DAQ and Keithley instruments
- PID control for current regulation
- Data logging and visualization

## Requirements

- Python 3.8 or higher
- National Instruments DAQ hardware (optional, simulation mode available)
- Keithley source meter (optional, simulation mode available)
- Required Python packages (see requirements.txt)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd flash-control
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the application:
```bash
python main.py
```

2. Configure experiment parameters in the GUI
3. Start the experiment
4. Monitor the process in real-time
5. Data is automatically saved to the data directory

## Directory Structure

```
flash_control/
├── main.py              # Main entry point
├── gui/                 # PyQt-based user interface
├── controllers/         # Core logic and device control
├── config/             # Configuration settings
└── utils/              # Utility functions and logging
```

## Configuration

The system can be configured through the `config/settings.py` file. Key settings include:

- DAQ device configuration
- Keithley instrument settings
- PID controller parameters
- Timer periods
- File paths
- Default experiment parameters

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Original MATLAB implementation
- National Instruments for DAQ support
- Keithley for instrument support 