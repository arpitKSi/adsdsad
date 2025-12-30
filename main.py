import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.flash_sinter_gui import FlashSinterGUI

def main():
    """Main entry point for the flash sintering application."""
    try:
        # Create and run the GUI
        app = FlashSinterGUI()
        app.run()
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 