from tkinter import *
from tkinter import ttk
import cv2
from PIL import Image, ImageTk
import sys
import os
import time
import logging
from tkinter import filedialog
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import tkinter.messagebox as messagebox
# Queue removed - using arrays for better real-time plotting performance
import threading
import serial
from serial.tools import list_ports

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import flash control modules
from controllers.main_controller import MainController
from utils.logger import setup_logger
from config.settings import PLOTTING_CONFIG

class FlashSinterGUI:
    def __init__(self):
        """Initialize the GUI."""
        self.root = Tk()
        self.setup_window()
        self.setup_controller()
        self.create_gui_elements()
       
        # Initialize serial connection
        self.arduino = None
        self.setup_serial()
       
        # Data queues no longer needed - using arrays for better performance
       
        # Initialize timers
        self.control_timer = None
        self.data_timer = None
        self.display_timer = None
        self.is_plotting = False
       
        # Initialize timers with optimized periods for smooth plotting
        self.control_period = 50   # 50ms for control
        self.data_period = 50      # 50ms for data acquisition (20 Hz)  
        self.display_period = 100  # 100ms for display updates (10 Hz)
       
        # Data storage for smooth plotting
        self.voltage_data = []
        self.current_data = []
        self.time_data = []
        self.max_data_points = PLOTTING_CONFIG["max_data_points"]
        
        # Plot smoothing parameters
        self.smoothing_window = PLOTTING_CONFIG["smoothing_window"]
        self.plot_update_counter = 0
        
        # Compressed timeline parameters
        self.focus_window = PLOTTING_CONFIG["focus_window_seconds"]
        self.compression_ratio = PLOTTING_CONFIG["compression_ratio"]
        self.compression_exponent = PLOTTING_CONFIG["compression_exponent"]
       
        # Initialize sliding stage state
        self.is_stage_running = False
        
        # Initialize data file path
        self.data_filepath = None
        
        # Initialize hold time
        self.hold_time = 60.0  # Default hold time in seconds
       
        # Calculate initial voltage and current based on default parameters
        elec_d = 0.4  # cm
        width = 1.6   # mm
        thickness = 1.0  # mm
        e_field = 30.0  # V/cm
        curr_dens = 100.0  # mA/mm^2
        hold_time = 60.0  # s (NEW: Default hold time)
       
        # Calculate voltage and current
        voltage = e_field * elec_d
        current = curr_dens * width * thickness
       
        # Set initial voltage and current in entries
        self.voltage_entry.delete(0, END)
        self.voltage_entry.insert(0, f"{voltage:.2f}")
        self.current_entry.delete(0, END)
        self.current_entry.insert(0, f"{current:.2f}")
       
        # Update controller with initial values
        self.controller.update_parameters(
            electrical_distance=elec_d,
            width=width,
            thickness=thickness,
            electric_field=e_field,
            current_density=curr_dens
        )
       
        self.logger.info(f"Initial parameters set: {elec_d}, {width}, {thickness}, {e_field}, {curr_dens}, Hold Time: {hold_time}s")
        self.logger.info(f"Initial voltage: {voltage:.2f}V, current: {current:.2f}mA")
       
                # Set up cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
       
    def setup_window(self):
        # Get screen width and height
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()-60
       
        # Set the window size dynamically
        self.root.geometry(f"{self.screen_width}x{self.screen_height}")
        self.root.title("Flash Sinter Control System - Professional")
        self.root.resizable(TRUE, TRUE)
        self.root.minsize(1200, 800)
        self.root.maxsize(self.screen_width, self.screen_height)
        # Modern professional color scheme
        self.root.configure(bg="#f8f9fa")  # Light gray background
       
        # Calculate coordinates
        self.calculate_coordinates()
       
    def setup_controller(self):
        self.controller = MainController()
        self.logger = setup_logger(__name__)
       
    def calculate_coordinates(self):
        # Base design dimensions
        base_design_width = 1440
        base_design_height = 900
        self.width_factor = self.screen_width / base_design_width
        self.height_factor = self.screen_height / base_design_height
       
        # Modern layout with better proportions
        self.boarder_X = round(20 * self.width_factor)
        self.boarder_Y = round(20 * self.height_factor)
       
        # Start button - expanded to fill space with constraint frame
        self.Start_GUI_W = round(120 * self.width_factor)  # Keep original width
        self.Start_GUI_H = round(160 * self.height_factor)  # Match constraint frame height
       
        # Constraint frame - top section (optimally compressed for content visibility)
        self.constraint_frame_X = round(160 * self.width_factor)
        self.constraint_frame_Y = round(20 * self.height_factor)
        self.constraint_frame_W = round(580 * self.width_factor)  # Adjusted from 560 to 580 for better visibility
        self.constraint_frame_H = round(160 * self.height_factor)
        self.constraint_frame_Top = 15
        self.constraint_frame_Left = 15
        self.constraint_frame_sub_W = round((self.constraint_frame_W-100)/5)  # Adjusted spacing for better fit
        self.constraint_frame_sub_H = round((self.constraint_frame_H-40)/3)
       
        # Indicator frame - left middle
        self.indicator_frame_X = round(20 * self.width_factor)
        self.indicator_frame_Y = round(200 * self.height_factor)
        self.indicator_frame_W = round(300 * self.width_factor)
        self.indicator_frame_H = round(140 * self.height_factor)
       
        # Voltage and current control frame - center middle (optimally compressed for content visibility)
        self.voltage_current_frame_X = round(340 * self.width_factor)
        self.voltage_current_frame_Y = round(200 * self.height_factor)
        self.voltage_current_frame_W = round(380 * self.width_factor)  # Optimized from 400 to 380 for balanced compression
        self.voltage_current_frame_H = round(140 * self.height_factor)
        self.voltage_current_frame_Top = 15
        self.voltage_current_frame_Left = 15
        self.voltage_current_frame_sub_W = round((self.voltage_current_frame_W-80)/4)  # Adjusted spacing for content fit
        self.voltage_current_frame_sub_H = round((self.voltage_current_frame_H-40)/3)
       
        # Voltage and current plot frame - extended to use available space
        self.voltage_current_plot_frame_X = round(20 * self.width_factor)
        self.voltage_current_plot_frame_Y = round(360 * self.height_factor)
        self.voltage_current_plot_frame_W = round(700 * self.width_factor)  # Extended from 650 to 700
        self.voltage_current_plot_frame_H = round(500 * self.height_factor)
       

       
        # Image acquisition frame - right side (properly positioned for optimized layout)
        self.image_acquisition_frame_X = round(750 * self.width_factor)  # Adjusted from 740 to 750 for better spacing
        self.image_acquisition_frame_Y = round(20 * self.height_factor)
        self.image_acquisition_frame_W = round(660 * self.width_factor)  # Adjusted from 670 to 660 for balanced layout
        self.image_acquisition_frame_H = round(400 * self.height_factor)
       
       
       
        # MERGED RIGHT PANEL - Magnetics panel with induction graph (properly aligned)
        self.merged_right_panel_X = round(750 * self.width_factor)  # Aligned with camera panel
        self.merged_right_panel_Y = round(440 * self.height_factor)
        self.merged_right_panel_W = round(660 * self.width_factor)  # Matched to camera panel width
        self.merged_right_panel_H = round(420 * self.height_factor)
       
    def create_frame(self, parent, x, y, width, height, bg_color="#ffffff", border_color="#e9ecef", border_width=1):
        """Create a modern styled frame with subtle borders."""
        frame = Frame(parent, bg=bg_color, highlightbackground=border_color,
                     highlightthickness=border_width, relief="flat")
        frame.place(x=x, y=y, width=width, height=height)
        return frame
       
    def create_label(self, parent, x, y, text, font_size=12, bg_color="#ffffff", text_color="#2c3e50", font_weight="normal", width=None, anchor="w"):
        """Create a modern styled label."""
        font_family = "Segoe UI" if font_weight == "bold" else "Segoe UI"
        label = Label(parent, text=text, font=(font_family, font_size, font_weight),
                     bg=bg_color, fg=text_color, anchor=anchor)
        if width:
            label.place(x=x, y=y, width=width)
        else:
            label.place(x=x, y=y)
        return label
       
    def create_button(self, parent, x, y, text, width, height, bg_color="#3498db", fg_color="#ffffff",
                     font_size=11, relief="flat", command=None, hover_color="#2980b9"):
        """Create a modern flat button with professional styling."""
        button = Button(parent, text=text, bg=bg_color, fg=fg_color,
                       font=("Segoe UI", font_size, "normal"), anchor=CENTER, relief=relief,
                       borderwidth=0, command=command, cursor="hand2")
        button.place(x=x, y=y, width=width, height=height)
       
        # Add hover effects
        def on_enter(e):
            button.configure(bg=hover_color)
        def on_leave(e):
            button.configure(bg=bg_color)
       
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
        return button
       
    def create_entry(self, parent, x, y, width, height, bg_color="#f8f9fa", font_size=11, border_color="#ced4da"):
        """Create a modern styled entry field."""
        def validate_float(P):
            if P == "":
                return True
            try:
                float(P)
                return True
            except ValueError:
                return False

        vcmd = (self.root.register(validate_float), '%P')
        entry = Entry(parent, bg=bg_color, font=("Segoe UI", font_size),
                     validate="key", validatecommand=vcmd, relief="flat",
                     highlightbackground=border_color, highlightthickness=1,
                     bd=1, fg="#2c3e50", justify="center")
        entry.place(x=x, y=y, width=width, height=height)
        return entry
       
    def create_combobox(self, parent, x, y, width, height, values, font_size=11):
        """Create a modern styled combobox."""
        combobox = ttk.Combobox(parent, values=values, font=("Segoe UI", font_size),
                               state="readonly", width=int(width/10))  # Approximate width conversion
        combobox.place(x=x, y=y, width=width, height=height)
        return combobox
       
    def create_neumorphic_button(self, parent, x, y, text, width, height, bg_color="#e0e5ec", 
                                fg_color="#333333", font_size=14, command=None):
        """Create a neumorphic style button with soft shadows and depth."""
        # Create shadow frame (appears behind and slightly offset)
        shadow_frame = Frame(parent, bg="#babecc", highlightthickness=0)
        shadow_frame.place(x=x+3, y=y+3, width=width, height=height)
        
        # Create highlight frame (appears behind and slightly offset in opposite direction)
        highlight_frame = Frame(parent, bg="#ffffff", highlightthickness=0)
        highlight_frame.place(x=x-2, y=y-2, width=width, height=height)
        
        # Create the main button container frame
        button_frame = Frame(parent, bg=bg_color, highlightthickness=0)
        button_frame.place(x=x, y=y, width=width, height=height)
        
        # Create the actual button with neumorphic styling
        button = Button(
            button_frame,
            text=text,
            font=("Arial", font_size, "bold"),
            bg=bg_color,
            fg=fg_color,
            activebackground="#d1d9e6",
            activeforeground=fg_color,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            command=command
        )
        button.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Store references for later color changes
        button.shadow_frame = shadow_frame
        button.highlight_frame = highlight_frame
        button.button_frame = button_frame
        button.default_bg = bg_color
        
        # Add neumorphic hover effects
        def on_enter_neuro(e):
            button.configure(bg="#d1d9e6")
            button_frame.configure(bg="#d1d9e6")
            
        def on_leave_neuro(e):
            button.configure(bg=bg_color)
            button_frame.configure(bg=bg_color)
            
        button.bind("<Enter>", on_enter_neuro)
        button.bind("<Leave>", on_leave_neuro)
        
        return button
    
    def set_parameter_buttons_state(self, enabled):
        """Enable or disable the Apply Parameters and Change Condition buttons."""
        try:
            # Define disabled and enabled colors
            disabled_bg = "#f5f5f5"  # Light gray
            disabled_fg = "#9e9e9e"  # Gray text
            enabled_bg = "#e8f5e8"   # Light green
            enabled_fg = "#28a745"   # Green text
            
            if enabled:
                # Enable Apply Parameters button
                self.send_limits_button.configure(
                    state="normal",
                    bg=enabled_bg,
                    fg=enabled_fg
                )
                self.send_limits_button.button_frame.configure(bg=enabled_bg)
                
                # Enable Change Condition button
                self.change_condition_button.configure(
                    state="normal",
                    bg=enabled_bg,
                    fg=enabled_fg
                )
                self.change_condition_button.button_frame.configure(bg=enabled_bg)
                
                self.logger.info("Apply Parameters and Change Condition buttons enabled")
            else:
                # Disable Apply Parameters button
                self.send_limits_button.configure(
                    state="disabled",
                    bg=disabled_bg,
                    fg=disabled_fg
                )
                self.send_limits_button.button_frame.configure(bg=disabled_bg)
                
                # Disable Change Condition button
                self.change_condition_button.configure(
                    state="disabled",
                    bg=disabled_bg,
                    fg=disabled_fg
                )
                self.change_condition_button.button_frame.configure(bg=disabled_bg)
                
                self.logger.info("Apply Parameters and Change Condition buttons disabled")
                
        except Exception as e:
            self.logger.error(f"Error setting parameter button states: {str(e)}")
       
    def toggle_start_button(self):
        """Toggle neumorphic start button between inactive and active states."""
        try:
            if not self.start_button_active:
                # First click: Ask for file saving location, then change to active state
                self.select_save_file()
                
                if hasattr(self, 'data_filepath') and self.data_filepath:
                    # File was selected, proceed with activation
                    # Change to active neumorphic state (light green background)
                    active_color = "#d4f6d4"  # Light green background
                    self.Start_GUI_button.configure(bg=active_color, fg="#28a745")  # Green text
                    self.Start_GUI_button.button_frame.configure(bg=active_color)
                    self.Start_GUI_button.configure(text="Active")
                   
                    # Update hover effects for active state
                    def on_enter_active(e):
                        self.Start_GUI_button.configure(bg="#c3f0c3")  # Slightly darker light green on hover
                        self.Start_GUI_button.button_frame.configure(bg="#c3f0c3")
                    def on_leave_active(e):
                        self.Start_GUI_button.configure(bg=active_color)
                        self.Start_GUI_button.button_frame.configure(bg=active_color)
                   
                    # Remove old bindings and add new ones
                    self.Start_GUI_button.unbind("<Enter>")
                    self.Start_GUI_button.unbind("<Leave>")
                    self.Start_GUI_button.bind("<Enter>", on_enter_active)
                    self.Start_GUI_button.bind("<Leave>", on_leave_active)
                   
                    self.start_button_active = True
                    # Enable parameter buttons when start button is activated
                    self.set_parameter_buttons_state(True)
                    self.logger.info("Neumorphic start button activated")
                    self.logger.info(f"Data will be saved to: {self.data_filepath}")
                else:
                    # File selection was cancelled, don't activate button
                    self.logger.info("Start button activation cancelled - no file selected")
                    return
            else:
                # Already active: change back to inactive state
                inactive_color = "#e0e5ec"
                self.Start_GUI_button.configure(bg=inactive_color, fg="#333333")  # Default dark text
                self.Start_GUI_button.button_frame.configure(bg=inactive_color)
                self.Start_GUI_button.configure(text="Start")
               
                # Update hover effects for inactive state
                def on_enter_inactive(e):
                    self.Start_GUI_button.configure(bg="#d1d9e6")
                    self.Start_GUI_button.button_frame.configure(bg="#d1d9e6")
                def on_leave_inactive(e):
                    self.Start_GUI_button.configure(bg=inactive_color)
                    self.Start_GUI_button.button_frame.configure(bg=inactive_color)
               
                # Remove old bindings and add new ones
                self.Start_GUI_button.unbind("<Enter>")
                self.Start_GUI_button.unbind("<Leave>")
                self.Start_GUI_button.bind("<Enter>", on_enter_inactive)
                self.Start_GUI_button.bind("<Leave>", on_leave_inactive)
               
                self.start_button_active = False
                # Disable parameter buttons when start button is deactivated
                self.set_parameter_buttons_state(False)
                self.logger.info("Neumorphic start button deactivated")
           
            # Execute the original start functionality
            self.read_entries()
           
        except Exception as e:
            self.logger.error(f"Error toggling neumorphic start button: {str(e)}")

    def select_save_file(self):
        """Open file dialog to select where to save experiment data."""
        try:
            # Create data directory if it doesn't exist
            os.makedirs("data", exist_ok=True)
           
            # Get timestamp for default filename
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            default_filename = f"experiment_data_{timestamp}.txt"
           
            # Open file dialog to choose save location
            self.data_filepath = filedialog.asksaveasfilename(
                initialdir="data",
                initialfile=default_filename,
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Save Experiment Data As"
            )
           
            if self.data_filepath:
                self.logger.info(f"Selected file for saving: {self.data_filepath}")
                messagebox.showinfo("File Selected", f"Data will be saved to:\n{os.path.basename(self.data_filepath)}")
            else:
                self.logger.info("File selection cancelled by user")
                
        except Exception as e:
            self.logger.error(f"Error selecting save file: {e}")
            self.data_filepath = None

    def read_entries(self):
        try:
            elec_d = float(self.Elec_D_entry.get())
            width = float(self.width_entry.get())
            thickness = float(self.Thickness_entry.get())
            e_field = float(self.E_Field_entry.get())
            curr_dens = float(self.Curr_Dens_entry.get())
            hold_time = float(self.Hold_Time_entry.get())  # NEW: Read Hold Time
           
            # Calculate voltage and current
            voltage = e_field * elec_d
            current = curr_dens * width * thickness
           
            # Update voltage and current entries
            self.voltage_entry.delete(0, END)
            self.voltage_entry.insert(0, f"{voltage:.2f}")
            self.current_entry.delete(0, END)
            self.current_entry.insert(0, f"{current:.2f}")
           
            # Update controller with new values including hold time
            self.controller.update_parameters(
                electrical_distance=elec_d,
                width=width,
                thickness=thickness,
                electric_field=e_field,
                current_density=curr_dens
            )
            
            # Store hold time for use in experiment
            self.hold_time = hold_time
            # Update controller's hold time
            self.controller.update_hold_time(hold_time)
           
            self.logger.info(f"Updated parameters: {elec_d}, {width}, {thickness}, {e_field}, {curr_dens}, Hold Time: {hold_time}s")
            self.logger.info(f"Calculated voltage: {voltage:.2f}V, current: {current:.2f}mA")
        except ValueError as e:
            self.logger.error(f"Invalid input: {str(e)}")

    def load_usb_camera(self):
        try:
            self.cap = cv2.VideoCapture(0)  # 0 is the default camera
            # Set initial camera properties
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
           
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
           
            # Log actual camera settings
            self.logger.info(f"Camera properties: FPS={actual_fps}, Resolution={int(actual_width)}x{int(actual_height)}")
           
            frame = self.image_acquisition_frame
            self.is_recording = False
            self.video_writer = None

            def update_frame():
                ret, img_frame = self.cap.read()
                if ret:
                    # Save frame if recording
                    if self.is_recording and self.video_writer is not None:
                        self.video_writer.write(img_frame)
                   
                    img_frame = cv2.cvtColor(img_frame, cv2.COLOR_BGR2RGB)
                    img_frame = cv2.convertScaleAbs(img_frame, alpha=1.2, beta=10)
                    img = Image.fromarray(img_frame)
                   
                    # Fill entire video display area - cover black background completely
                    available_width = self.image_acquisition_frame_W - 20  # Match video_area_width
                    available_height = self.image_acquisition_frame_H - 60  # Match video_area_height
                   
                    # Calculate aspect ratios
                    camera_aspect = actual_width / actual_height
                    display_aspect = available_width / available_height
                   
                    # Fill entire area (crop if necessary to cover all black background)
                    if camera_aspect > display_aspect:
                        # Camera is wider - fit to height and crop sides
                        target_height = available_height
                        target_width = int(target_height * camera_aspect)
                    else:
                        # Camera is taller - fit to width and crop top/bottom
                        target_width = available_width
                        target_height = int(target_width / camera_aspect)
                   
                    # Resize image to fill the display area completely
                    img = img.resize((target_width, target_height), Image.LANCZOS)
                    imgtk = ImageTk.PhotoImage(image=img)
                    self.camera_label.imgtk = imgtk
                    self.camera_label.configure(image=imgtk)
               
                self.camera_label.after(33, update_frame)

            # Place camera label to fill entire video display frame - covers black background
            self.camera_label = Label(self.video_display_frame, bg="#000000")
            self.camera_label.place(x=0, y=0, width=self.image_acquisition_frame_W - 20,
                                   height=self.image_acquisition_frame_H - 60)  # Fill entire video area
            update_frame()
            self.logger.info(f"Camera initialized successfully with FPS: {actual_fps}, Resolution: {actual_width}x{actual_height}")
        except Exception as e:
            self.logger.error(f"Failed to initialize camera: {str(e)}")
           
    def stop_usb_camera(self):
        try:
            # Stop recording if active
            if self.is_recording:
                self.stop_recording()
           
            if hasattr(self, 'cap') and self.cap is not None:
                self.cap.release()
                self.cap = None
            if hasattr(self, 'camera_label') and self.camera_label:
                self.camera_label.config(image='')
                self.camera_label.destroy()  # Properly remove the label
                self.camera_label = None
            self.logger.info("Camera stopped successfully")
        except Exception as e:
            self.logger.error(f"Failed to stop camera: {str(e)}")
           
    def toggle_camera(self):
        """Toggle camera between green loading and red unloading states with hover effects."""
        try:
            if not self.is_camera_loaded:
                # Load camera and switch to red unloading state
                self.load_usb_camera()
               
                # Update to unload state (red neumorphic)
                self.is_camera_loaded = True
                red_color = "#ffe8e8"  # Light red background
                self.camera_toggle_button.configure(
                    text="Unloading",
                    bg=red_color,
                    fg="#dc2626"  # Red text
                )
                self.camera_toggle_button.button_frame.configure(bg=red_color)
                
                # Update hover effects for red state
                def on_enter_red(e):
                    hover_red = "#ffd6d6"
                    self.camera_toggle_button.configure(bg=hover_red)
                    self.camera_toggle_button.button_frame.configure(bg=hover_red)
                def on_leave_red(e):
                    self.camera_toggle_button.configure(bg=red_color)
                    self.camera_toggle_button.button_frame.configure(bg=red_color)
                
                # Remove old bindings and add new ones
                self.camera_toggle_button.unbind("<Enter>")
                self.camera_toggle_button.unbind("<Leave>")
                self.camera_toggle_button.bind("<Enter>", on_enter_red)
                self.camera_toggle_button.bind("<Leave>", on_leave_red)
                
                self.logger.info("Camera loaded successfully - button changed to red")
               
            else:
                # Stop camera and switch back to green loading state
                self.stop_usb_camera()
               
                # Update to load state (green neumorphic)
                self.is_camera_loaded = False
                green_color = "#e8f5e8"  # Light green background
                self.camera_toggle_button.configure(
                    text="Loading",
                    bg=green_color,
                    fg="#28a745"  # Green text
                )
                self.camera_toggle_button.button_frame.configure(bg=green_color)
                
                # Update hover effects for green state
                def on_enter_green(e):
                    hover_green = "#d4f6d4"
                    self.camera_toggle_button.configure(bg=hover_green)
                    self.camera_toggle_button.button_frame.configure(bg=hover_green)
                def on_leave_green(e):
                    self.camera_toggle_button.configure(bg=green_color)
                    self.camera_toggle_button.button_frame.configure(bg=green_color)
                
                # Remove old bindings and add new ones
                self.camera_toggle_button.unbind("<Enter>")
                self.camera_toggle_button.unbind("<Leave>")
                self.camera_toggle_button.bind("<Enter>", on_enter_green)
                self.camera_toggle_button.bind("<Leave>", on_leave_green)
                
                self.logger.info("Camera stopped successfully - button changed to green")
               
        except Exception as e:
            # Reset to green loading state on error (neumorphic)
            self.is_camera_loaded = False
            green_color = "#e8f5e8"  # Light green background
            self.camera_toggle_button.configure(
                text="Loading",
                bg=green_color,
                fg="#28a745"  # Green text
            )
            self.camera_toggle_button.button_frame.configure(bg=green_color)
            
            # Reset hover effects for green state
            def on_enter_green(e):
                hover_green = "#d4f6d4"
                self.camera_toggle_button.configure(bg=hover_green)
                self.camera_toggle_button.button_frame.configure(bg=hover_green)
            def on_leave_green(e):
                self.camera_toggle_button.configure(bg=green_color)
                self.camera_toggle_button.button_frame.configure(bg=green_color)
            
            self.camera_toggle_button.unbind("<Enter>")
            self.camera_toggle_button.unbind("<Leave>")
            self.camera_toggle_button.bind("<Enter>", on_enter_green)
            self.camera_toggle_button.bind("<Leave>", on_leave_green)
            
            self.logger.error(f"Error toggling camera: {str(e)}")
           
    def create_gui_elements(self):
        # Create neumorphic start button with modern styling
        self.start_button_active = False  # Track button state
        self.Start_GUI_button = self.create_neumorphic_button(
            self.root, self.boarder_X, self.boarder_Y,
            "Start", self.Start_GUI_W, self.Start_GUI_H,
            bg_color="#e0e5ec", fg_color="#333333", font_size=14,
            command=self.toggle_start_button
        )
       
        # Create constraint frame with modern styling
        self.constraint_frame = self.create_frame(
            self.root, self.constraint_frame_X, self.constraint_frame_Y,
            self.constraint_frame_W, self.constraint_frame_H,
            bg_color="#ffffff", border_color="#304166", border_width=2
        )
       
        # Create voltage-current plot frame
        self.voltage_current_plot_frame = self.create_frame(
            self.root, self.voltage_current_plot_frame_X,
            self.voltage_current_plot_frame_Y + 50,  # Move down by 50 pixels
            self.voltage_current_plot_frame_W,
            self.voltage_current_plot_frame_H - 50  # Reduce height to accommodate buttons
        )
       
        # Create matplotlib figure for voltage-current plot (more square format)
        self.fig, self.ax = plt.subplots(figsize=(6, 5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.voltage_current_plot_frame)
        self.canvas.get_tk_widget().pack(fill=BOTH, expand=True)
       
        # Add plot controls in a separate frame above the plot
        self.plot_controls_frame = self.create_frame(
            self.root,  # Changed parent to root
            self.voltage_current_plot_frame_X,
            self.voltage_current_plot_frame_Y,
            self.voltage_current_plot_frame_W,
            50  # Fixed height for controls
        )
       
        # Add button to control frame
        self.start_plot_button = self.create_neumorphic_button(
            self.plot_controls_frame, 10, 10, "Start Acquisition",
            120, 30, bg_color="#e8f5e8", fg_color="#28a745",
            font_size=11, command=self.toggle_plotting
        )
       
        # Initialize plot with professional formatting
        self.setup_professional_plot()
        
        # Initialize empty line objects for smooth updates
        self.line_voltage, = self.ax.plot([], [], 'b-', label='Voltage (V)', linewidth=0.5, antialiased=True)
        self.line_current, = self.ax2.plot([], [], 'r-', label='Current (mA)', linewidth=0.5, antialiased=True)
       
        # Constraint frame header and components
        self.constraint_label = self.create_label(self.constraint_frame, self.constraint_frame_Left,
                                                self.constraint_frame_Top, "Sample Parameters", 16,
                                                "#ffffff", "#2c3e50", "bold")
       
        # Calculate compressed dimensions for 6 input boxes
        compressed_sub_W = round((self.constraint_frame_W - 120) / 6)  # Reduced spacing for 6 boxes
        spacing_between_boxes = 8  # Reduced spacing between boxes
        
        # Create all the entry fields and labels for constraints (compressed layout)
        self.Elec_D_label = self.create_label(self.constraint_frame, self.constraint_frame_Left,
                                            self.constraint_frame_sub_H+20, "Length\n(cm)",
                                            10, "#ffffff", "#7f8c8d", "normal",
                                            compressed_sub_W, "center")
        self.Elec_D_entry = self.create_entry(self.constraint_frame, self.constraint_frame_Left,
                                            self.constraint_frame_H-self.constraint_frame_Top-self.constraint_frame_sub_H,
                                            compressed_sub_W, self.constraint_frame_sub_H)
        self.Elec_D_entry.insert(0, "0.4")  # Default value
       
        self.width_label = self.create_label(self.constraint_frame,
                                           self.constraint_frame_Left+compressed_sub_W+spacing_between_boxes,
                                           self.constraint_frame_sub_H+20, "Width\n(mm)", 10,
                                           "#ffffff", "#7f8c8d", "normal",
                                           compressed_sub_W, "center")
        self.width_entry = self.create_entry(self.constraint_frame,
                                           self.constraint_frame_Left+compressed_sub_W+spacing_between_boxes,
                                           self.constraint_frame_H-self.constraint_frame_Top-self.constraint_frame_sub_H,
                                           compressed_sub_W, self.constraint_frame_sub_H)
        self.width_entry.insert(0, "1.6")  # Default value
       
        self.Thickness_label = self.create_label(self.constraint_frame,
                                               self.constraint_frame_Left+2*compressed_sub_W+2*spacing_between_boxes,
                                               self.constraint_frame_sub_H+20, "Thickness\n(mm)",
                                               10, "#ffffff", "#7f8c8d", "normal",
                                               compressed_sub_W, "center")
        self.Thickness_entry = self.create_entry(self.constraint_frame,
                                               self.constraint_frame_Left+2*compressed_sub_W+2*spacing_between_boxes,
                                               self.constraint_frame_H-self.constraint_frame_Top-self.constraint_frame_sub_H,
                                               compressed_sub_W, self.constraint_frame_sub_H)
        self.Thickness_entry.insert(0, "1.0")  # Default value
       
        self.E_Field_label = self.create_label(self.constraint_frame,
                                             self.constraint_frame_Left+3*compressed_sub_W+3*spacing_between_boxes,
                                             self.constraint_frame_sub_H+20, "Electric Field\n(V/cm)",
                                             10, "#ffffff", "#7f8c8d", "normal",
                                             compressed_sub_W, "center")
        self.E_Field_entry = self.create_entry(self.constraint_frame,
                                             self.constraint_frame_Left+3*compressed_sub_W+3*spacing_between_boxes,
                                             self.constraint_frame_H-self.constraint_frame_Top-self.constraint_frame_sub_H,
                                             compressed_sub_W, self.constraint_frame_sub_H)
        self.E_Field_entry.insert(0, "30.0")  # Default value
       
        self.Curr_Dens_label = self.create_label(self.constraint_frame,
                                               self.constraint_frame_Left+4*compressed_sub_W+4*spacing_between_boxes,
                                               self.constraint_frame_sub_H+20, "Current Density\n(mA/mm²)",
                                               10, "#ffffff", "#7f8c8d", "normal",
                                               compressed_sub_W, "center")
        self.Curr_Dens_entry = self.create_entry(self.constraint_frame,
                                               self.constraint_frame_Left+4*compressed_sub_W+4*spacing_between_boxes,
                                               self.constraint_frame_H-self.constraint_frame_Top-self.constraint_frame_sub_H,
                                               compressed_sub_W, self.constraint_frame_sub_H)
        self.Curr_Dens_entry.insert(0, "100.0")  # Default value
        
        # NEW: Hold Time input box
        self.Hold_Time_label = self.create_label(self.constraint_frame,
                                                self.constraint_frame_Left+5*compressed_sub_W+5*spacing_between_boxes,
                                                self.constraint_frame_sub_H+20, "Hold Time\n(s)",
                                                10, "#ffffff", "#7f8c8d", "normal",
                                                compressed_sub_W, "center")
        self.Hold_Time_entry = self.create_entry(self.constraint_frame,
                                                self.constraint_frame_Left+5*compressed_sub_W+5*spacing_between_boxes,
                                                self.constraint_frame_H-self.constraint_frame_Top-self.constraint_frame_sub_H,
                                                compressed_sub_W, self.constraint_frame_sub_H)
        self.Hold_Time_entry.insert(0, "60.0")  # Default value
       
        # Apply Parameters button (positioned at the far right side of the frame)
        button_width = 140  # Increased width to fit "Apply Parameters" text properly
        button_x = self.constraint_frame_W - button_width - 15  # 15px margin from right edge
        self.send_limits_button = self.create_neumorphic_button(self.constraint_frame,
                                                   button_x,
                                                   self.constraint_frame_Top+5, "Apply Parameters",
                                                   button_width, self.constraint_frame_sub_H,
                                                   bg_color="#e8f5e8", fg_color="#28a745", font_size=11, command=self.read_entries)

        # Sliding stage frame and its components - Modern sliding stage control panel
        self.indication_frame = self.create_frame(self.root, self.indicator_frame_X,
                                                self.indicator_frame_Y, self.indicator_frame_W,
                                                self.indicator_frame_H,
                                                bg_color="#ffffff", border_color="#b3d9ff", border_width=1)
       
        # Calculate responsive dimensions based on panel size
        panel_width = self.indicator_frame_W - 20  # Total usable width (10px margin each side)
        panel_height = self.indicator_frame_H - 20  # Total usable height (10px margin each side)
       
        # Define element dimensions that scale with panel
        element_height = 32  # Moderately sized buttons - reduced from 40
        spacing_x = 3  # Minimal spacing between elements
       
        # Calculate vertical positions for better distribution
        input_section_height = int(panel_height * 0.5)  # 50% for inputs
        button_section_height = int(panel_height * 0.5)  # 50% for buttons
       
        # Calculate widths for each element
        position_width = int(panel_width * 0.35)  # 35% for position input (increased)
        com_width = int(panel_width * 0.32)      # 32% for COM port (decreased)
        refresh_width = int(panel_width * 0.28)   # 28% for refresh button (slightly increased)
       
        # Input section positioning - increased vertical spacing for better heading visibility
        input_y_start = 25  # Increased top margin to shift row downward
        input_entry_y = input_y_start + 25  # Increased spacing between label and input for better visibility
       
        # Position (mm) input box (left side)
        self.stage_input1_label = self.create_label(
            self.indication_frame, 10, input_y_start,
            "Speed (rpm):", 11,  # Changed to rpm and increased font size
            "#ffffff", "#2c3e50", "bold"
        )
        self.stage_input1_entry = self.create_entry(
            self.indication_frame, 10, input_entry_y,
            position_width, element_height
        )
        self.stage_input1_entry.insert(0, "0.0")
       
        # COM Port Selection (middle)
        com_x = 10 + position_width + spacing_x
        self.stage_input2_label = self.create_label(
            self.indication_frame, com_x, input_y_start,
            "COM Port:", 11,  # Increased font size to match Speed rpm
            "#ffffff", "#2c3e50", "bold", anchor="center"  # Centered alignment
        )
        
        # Create COM port combobox
        available_ports = self.get_available_ports()
        self.stage_input2_combobox = self.create_combobox(
            self.indication_frame, com_x, input_entry_y,
            com_width, element_height, available_ports
        )
        if available_ports:
            self.stage_input2_combobox.set(available_ports[0])
        else:
            self.stage_input2_combobox.set("Not Available")

        # Refresh button (right side)
        refresh_x = com_x + com_width + spacing_x
        self.refresh_com_button = self.create_neumorphic_button(
            self.indication_frame, refresh_x, input_entry_y,
            "Refresh", refresh_width, element_height,
            bg_color="#f0f2f5", fg_color="#304166",
            font_size=9, command=self.refresh_com_ports
        )

        # Button section positioning (bottom half of panel)
        button_y_position = input_section_height + 25  # Shifted buttons down even more
       
        # Calculate button widths for equal spacing
        button_width = (panel_width - 20) // 3  # Divide available width by 3 buttons
        button_spacing = 8  # Reduced spacing between buttons for better fit
       
        # Start button (left side)
        self.stage_start_button = self.create_neumorphic_button(
            self.indication_frame, 10, button_y_position,
            "Start", button_width, element_height,
            bg_color="#f0f2f5", fg_color="#304166",
            font_size=12, command=self.toggle_sliding_stage
        )
       
        # Loading button (middle)
        loading_x = 10 + button_width + button_spacing
        self.stage_loading_button = self.create_neumorphic_button(
            self.indication_frame, loading_x, button_y_position,
            "Unloading", button_width, element_height,
            bg_color="#ffe8e8", fg_color="#dc2626", font_size=12,
            command=self.run_loading
        )
       
        # Unloading button (right side)
        unloading_x = loading_x + button_width + button_spacing
        self.stage_unloading_button = self.create_neumorphic_button(
            self.indication_frame, unloading_x, button_y_position,
            "Loading", button_width, element_height,
            bg_color="#e8f5e8", fg_color="#28a745", font_size=12,
            command=self.run_unloading
        )

        # Voltage and current limit frame - Professional limit control interface
        self.voltage_current_frame = self.create_frame(self.root, self.voltage_current_frame_X,
                                                      self.voltage_current_frame_Y,
                                                      self.voltage_current_frame_W,
                                                      self.voltage_current_frame_H,
                                                      bg_color="#ffffff", border_color="#2759cd", border_width=2)
        self.voltage_current_label = self.create_label(self.voltage_current_frame,
                                                     self.voltage_current_frame_Left,
                                                     self.voltage_current_frame_Top,
                                                     "Current and Voltage Limit", 14,
                                                     "#ffffff", "#2c3e50", "bold")

        # Create voltage and current entries with modern styling
        self.voltage_label = self.create_label(self.voltage_current_frame,
                                             self.voltage_current_frame_Left,
                                             self.voltage_current_frame_Top+self.voltage_current_frame_sub_H,
                                             "Voltage\n(V)", 11, "#ffffff", "#7f8c8d", anchor="center")
        self.voltage_entry = self.create_entry(self.voltage_current_frame,
                                             self.voltage_current_frame_Left,
                                             self.voltage_current_frame_H-self.voltage_current_frame_Top-self.voltage_current_frame_sub_H,
                                             self.voltage_current_frame_sub_W,
                                             self.voltage_current_frame_sub_H)

        self.current_label = self.create_label(self.voltage_current_frame,
                                             self.voltage_current_frame_Left+self.voltage_current_frame_sub_W+15,
                                             self.voltage_current_frame_Top+self.voltage_current_frame_sub_H,
                                             "Current\n(mA)", 11, "#ffffff", "#7f8c8d", anchor="center")
        self.current_entry = self.create_entry(self.voltage_current_frame,
                                             self.voltage_current_frame_Left+self.voltage_current_frame_sub_W+15,
                                             self.voltage_current_frame_H-self.voltage_current_frame_Top-self.voltage_current_frame_sub_H,
                                             self.voltage_current_frame_sub_W,
                                             self.voltage_current_frame_sub_H)

        self.current_rate_label = self.create_label(self.voltage_current_frame,
                                                  self.voltage_current_frame_Left+2*self.voltage_current_frame_sub_W+30,
                                                  self.voltage_current_frame_Top+self.voltage_current_frame_sub_H,
                                                  "Ramp Rate\n(mA/s)", 11, "#ffffff", "#7f8c8d", anchor="center")
        self.current_rate_entry = self.create_entry(self.voltage_current_frame,
                                                  self.voltage_current_frame_Left+2*self.voltage_current_frame_sub_W+30,
                                                  self.voltage_current_frame_H-self.voltage_current_frame_Top-self.voltage_current_frame_sub_H,
                                                  self.voltage_current_frame_sub_W,
                                                  self.voltage_current_frame_sub_H)


        
        # Create action button matching input box dimensions
        self.change_condition_button = self.create_neumorphic_button(self.voltage_current_frame,
                                                        self.voltage_current_frame_Left+3*self.voltage_current_frame_sub_W+45,
                                                        self.voltage_current_frame_H-self.voltage_current_frame_Top-self.voltage_current_frame_sub_H,
                                                        "Change\nCondition",
                                                        self.voltage_current_frame_sub_W,
                                                        self.voltage_current_frame_sub_H,
                                                        bg_color="#e8f5e8", fg_color="#28a745",
                                                        font_size=9, command=self.change_conditions)

        # Image acquisition frame - Professional camera control interface with proper rectangular shape
        self.image_acquisition_frame = self.create_frame(self.root,
                                                       self.image_acquisition_frame_X,
                                                       self.image_acquisition_frame_Y,
                                                       self.image_acquisition_frame_W,
                                                       self.image_acquisition_frame_H,
                                                       bg_color="#ffffff", border_color="#d7d2cb", border_width=2)
       
        # Create video display area with proper rectangular boundaries
        video_area_x = 10
        video_area_y = 10
        video_area_width = self.image_acquisition_frame_W - 20  # 10px margin on each side
        video_area_height = self.image_acquisition_frame_H - 60  # Reserve 50px for buttons at bottom
       
        self.video_display_frame = self.create_frame(self.image_acquisition_frame,
                                                   video_area_x, video_area_y,
                                                   video_area_width, video_area_height,
                                                   bg_color="#000000", border_color="#cccccc", border_width=1)

        # Add single camera toggle button at the bottom with proper spacing
        self.is_camera_loaded = False  # Track camera state
        button_y_position = self.image_acquisition_frame_H - 45  # 5px from bottom

        self.camera_toggle_button = self.create_neumorphic_button(self.image_acquisition_frame, 10,
                                                      button_y_position,
                                                      "Loading", 140, 35, bg_color="#e8f5e8", 
                                                      fg_color="#28a745", font_size=12, command=self.toggle_camera)

        self.Save_video_button = self.create_neumorphic_button(
            self.image_acquisition_frame,
            160,
            button_y_position,
            "Save Video", 120, 35, bg_color="#e8f0ff", fg_color="#2759cd", font_size=12, command=self.save_video
        )

        # MAGNETICS PANEL - Induction vs Time Graph
        self.merged_right_panel = self.create_frame(self.root,
                                                   self.merged_right_panel_X,
                                                   self.merged_right_panel_Y,
                                                   self.merged_right_panel_W,
                                                   self.merged_right_panel_H,
                                                   bg_color="#ffffff", border_color="#b3d9ff", border_width=2)
       
        # Create matplotlib figure for induction vs time plot
        self.induction_fig, self.induction_ax = plt.subplots(figsize=(8, 4))
        self.induction_canvas = FigureCanvasTkAgg(self.induction_fig, master=self.merged_right_panel)
        self.induction_canvas.get_tk_widget().pack(fill=BOTH, expand=True)
       
        # Initialize induction plot
        self.induction_ax.set_xlabel('Time (s)')
        self.induction_ax.set_ylabel('Induction (mT)')
       
        # Enhanced grid configuration for induction plot
        self.induction_ax.grid(True, which='major', color='#d5d5d5', linestyle='-', linewidth=0.8, alpha=0.7)
        self.induction_ax.grid(True, which='minor', color='#e8e8e8', linestyle=':', linewidth=0.5, alpha=0.5)
        self.induction_ax.minorticks_on()  # Enable minor ticks for finer grid
       
        # Configure tick parameters for closer spacing
        self.induction_ax.tick_params(which='major', length=6, width=1.2, color='#666666')
        self.induction_ax.tick_params(which='minor', length=3, width=0.8, color='#999999')
       
        # Set custom tick locators for finer control
        from matplotlib.ticker import AutoMinorLocator
        self.induction_ax.xaxis.set_minor_locator(AutoMinorLocator(5))  # 5 minor ticks between major ticks
        self.induction_ax.yaxis.set_minor_locator(AutoMinorLocator(5))  # 5 minor ticks between major ticks
       
        # Initialize empty plot line
        self.line_induction, = self.induction_ax.plot([], [], 'g-', linewidth=0.5)
       
        # Set default axis limits
        self.induction_ax.set_xlim(0, 1)
        self.induction_ax.set_ylim(0, 1)
       
        # Initialize data storage for induction plotting
        self.induction_data = []
        
        # Initially disable Apply Parameters and Change Condition buttons
        self.set_parameter_buttons_state(False)
       
    def setup_serial(self):
        """Initialize serial connection to Arduino."""
        try:
            # Get the selected COM port from the combobox
            selected_port = self.stage_input2_combobox.get()
            if selected_port == "Not Available":
                self.logger.error("No COM ports available")
                return
                
            self.arduino = serial.Serial(port=selected_port, baudrate=9600, timeout=1)
            time.sleep(2)  # wait for Arduino to initialize
            self.logger.info(f"Serial connection established with Arduino on {selected_port}")
        except serial.SerialException as e:
            self.arduino = None
            self.logger.error(f"Could not open COM port: {str(e)}")

    def get_available_ports(self):
        """Get list of available COM ports."""
        ports = list(list_ports.comports())
        if not ports:
            return ["Not Available"]
        return [port.device for port in ports]

    def refresh_com_ports(self):
        """Refresh the list of available COM ports."""
        available_ports = self.get_available_ports()
        self.stage_input2_combobox['values'] = available_ports
        if available_ports:
            self.stage_input2_combobox.set(available_ports[0])
        else:
            self.stage_input2_combobox.set("Not Available")
        self.logger.info(f"COM ports refreshed: {available_ports}")

    def send_command(self, cmd):
        """Send command to Arduino."""
        if self.arduino:
            try:
                self.arduino.write((cmd + '\n').encode())
                response = self.arduino.readline().decode().strip()
                self.logger.info(f"Arduino response: {response}")
                return response
            except Exception as e:
                self.logger.error(f"Error sending command to Arduino: {str(e)}")
                return None
        else:
            self.logger.error("Serial not connected")
            return None

    def toggle_stage_direction(self):
        """Toggle the sliding stage direction between loading and unloading."""
        try:
            if self.is_forward_direction:
                # Currently loading, change to unloading
                self.is_forward_direction = False
                self.stage_direction_button.configure(
                    text="Unloading",
                    bg="#dc2626",  # Using red for unloading
                    activebackground="#b91c1c"
                )
                self.send_command("REV")  # Send reverse command to Arduino
                self.logger.info("Sliding stage direction set to unloading")
            else:
                # Currently unloading, change to loading
                self.is_forward_direction = True
                self.stage_direction_button.configure(
                    text="Loading",
                    bg="#8b5cf6",  # Using purple for loading
                    activebackground="#7c3aed"
                )
                self.send_command("FWD")  # Send forward command to Arduino
                self.logger.info("Sliding stage direction set to loading")
               
        except Exception as e:
            self.logger.error(f"Error toggling stage direction: {e}")

    def toggle_sliding_stage(self):
        """Toggle the sliding stage between start and stop states."""
        try:
            if self.is_stage_running:
                # Currently running, so stop it
                self.is_stage_running = False
                self.stage_start_button.configure(
                    text="Start",
                    bg="#304166",  # Using dark navy for start
                    activebackground="#263552"
                )
                self.send_command("STOP")  # Send stop command to Arduino
                self.logger.info("Sliding stage stopped")
            else:
                # Currently stopped, so start it
                # First check if we have a valid COM port connection
                if not self.arduino:
                    self.setup_serial()
                    if not self.arduino:
                        messagebox.showerror("Error", "No valid COM port connection available")
                        return
                
                self.is_stage_running = True
                self.stage_start_button.configure(
                    text="Stop",
                    bg="#ee4932",  # Using red for stop
                    activebackground="#d9412c"
                )
                # Get RPM from entry and send it
                rpm = self.stage_input1_entry.get()
                if rpm.isdigit():
                    self.send_command(f"RPM:{rpm}")
                self.logger.info("Sliding stage started")
               
        except Exception as e:
            self.logger.error(f"Error toggling sliding stage: {e}")

    def on_closing(self):
        """Clean up resources when closing the application."""
        try:
            if self.arduino:
                self.send_command("STOP")  # Stop motor before closing
                self.arduino.close()
            if hasattr(self, 'controller'):
                self.controller.cleanup()
            if hasattr(self, 'cap') and self.cap is not None:
                self.cap.release()
            self.root.destroy()
            self.logger.info("Application closed and resources cleaned up")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
            self.root.destroy()

    def save_video(self):
        try:
            if hasattr(self, 'cap') and self.cap is not None:
                # Create videos directory if it doesn't exist
                videos_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'videos')
                if not os.path.exists(videos_dir):
                    os.makedirs(videos_dir)
               
                # Get current timestamp for default filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                default_filename = f"video_{timestamp}.avi"
               
                # Open file dialog to choose save location
                filename = filedialog.asksaveasfilename(
                    initialdir=videos_dir,
                    initialfile=default_filename,
                    defaultextension=".avi",
                    filetypes=[("AVI files", "*.avi"), ("All files", "*.*")],
                    title="Save Video As"
                )
               
                if filename:  # If user didn't cancel the dialog
                    # Get video properties
                    width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = int(self.cap.get(cv2.CAP_PROP_FPS))
                   
                    # Create VideoWriter object
                    fourcc = cv2.VideoWriter_fourcc(*'XVID')
                    self.video_writer = cv2.VideoWriter(filename, fourcc, fps, (width, height))
                   
                    # Start recording
                    self.is_recording = True
                    self.logger.info(f"Started recording video to {filename}")
                   
                    # Update button state
                    self.Save_video_button.configure(text="Stop Recording", bg="#DB4761",
                                                   command=self.stop_recording)
        except Exception as e:
            self.logger.error(f"Failed to start video recording: {str(e)}")

    def stop_recording(self):
        try:
            if hasattr(self, 'video_writer') and self.video_writer is not None:
                self.video_writer.release()
                self.video_writer = None
                self.is_recording = False
                self.logger.info("Video recording stopped")
               
                # Reset button state
                self.Save_video_button.configure(text="Save Video", bg="#12BC95",
                                               command=self.save_video)
        except Exception as e:
            self.logger.error(f"Failed to stop video recording: {str(e)}")

    def toggle_plotting(self):
        """Toggle data acquisition and plotting."""
        if not self.is_plotting:
            try:
                # Check if a file has been selected (from Start button)
                if not hasattr(self, 'data_filepath') or not self.data_filepath:
                    messagebox.showerror("Error", "Please click the Start button first to select a save file.")
                    return
                
                # Get voltage and current limits from entries
                voltage_limit = float(self.voltage_entry.get())
                current_limit = float(self.current_entry.get())
                
                # Get hold time from entry (with default fallback)
                try:
                    hold_time = float(self.Hold_Time_entry.get())
                except (ValueError, AttributeError):
                    hold_time = 60.0  # Default fallback
                    self.logger.warning(f"Using default hold time: {hold_time}s")
               
                # Validate inputs
                if voltage_limit <= 0 or current_limit <= 0:
                    raise ValueError("Voltage and current limits must be positive")
                    
                if hold_time <= 0:
                    raise ValueError("Hold time must be positive")
               
                # Update controller with hold time before starting
                self.controller.update_hold_time(hold_time)
                self.controller.device_controller.hold_time_limit = hold_time
                
                # Start the process with specified limits (set outputs on hardware)
                # This will now raise RuntimeError if devices are not connected
                self.controller.device_controller.start_process(voltage_limit, current_limit)
                self.logger.info(f"Started process with V={voltage_limit}V, I={current_limit}mA, Hold Time={hold_time}s")
               
                # Initialize data storage and start time
                self.voltage_data = []
                self.current_data = []
                self.time_data = []
                self.start_time = time.time()
               
                # Open the pre-selected file and write header
                self.data_file = open(self.data_filepath, 'w')
                self.data_file.write("Time(s)\tVoltage(V)\tCurrent(mA)\n")
                self.logger.info(f"Started saving data to {self.data_filepath}")
               
                # Start data acquisition
                self.is_plotting = True
                self.start_plot_button.configure(text="Stop")
                self.start_data_acquisition()
               
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
            except RuntimeError as e:
                # Device connection error - show specific warning
                error_msg = str(e)
                if "DAQ not connected" in error_msg:
                    messagebox.showerror("DAQ Connection Error", 
                                       "DAQ device is not connected or not available.\n\n"
                                       "Please check:\n"
                                       "• DAQ hardware is connected\n"
                                       "• NI-DAQmx drivers are installed\n"
                                       "• Device is recognized by system\n\n"
                                       f"Details: {error_msg}")
                elif "Keithley not connected" in error_msg:
                    messagebox.showerror("Keithley Connection Error", 
                                       "Keithley instrument is not connected or not available.\n\n"
                                       "Please check:\n"
                                       "• Keithley hardware is connected\n"
                                       "• VISA drivers are installed\n"
                                       "• USB/Serial cable connection\n"
                                       "• Device is recognized by system\n\n"
                                       f"Details: {error_msg}")
                else:
                    messagebox.showerror("Device Connection Error", 
                                       "Hardware devices are not connected or not available.\n\n"
                                       "Please check device connections and try again.\n\n"
                                       f"Details: {error_msg}")
                self.logger.error(f"Device connection error prevented start: {error_msg}")
                return
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start data acquisition: {str(e)}")
                return
        else:
            # Stop data acquisition
            self.stop_data_acquisition()

    def update_cv_cc_display(self):
        """Update the CV/CC mode display based on power supply status."""
        try:
            if hasattr(self.controller.device_controller, 'get_power_supply_status'):
                status = self.controller.device_controller.get_power_supply_status()
                mode = status.get('mode', 'Unknown')
                
                if mode == "CV":
                    self.logger.info("Power supply in CV Mode")
                elif mode == "CC":
                    self.logger.info("Power supply in CC Mode")
                    # Log the transition for user awareness
                    if status.get('voltage_before_cc'):
                        voltage_drop = status['voltage_before_cc'] - (self.voltage_data[-1] if self.voltage_data else 0)
                        self.logger.info(f"CC Mode: Voltage dropped by {voltage_drop:.1f}V")
                else:
                    self.logger.info("Power supply mode: Unknown")
                    
        except Exception as e:
            self.logger.error(f"Error updating CV/CC display: {e}")

    def setup_professional_plot(self):
        """Setup professional-quality plot formatting like MATLAB."""
        # Clear any existing content
        self.ax.clear()
        
        # Set up primary axis (voltage)
        self.ax.set_xlabel('Time (s)', fontsize=10, fontweight='bold')
        self.ax.set_ylabel('Voltage (V)', fontsize=10, fontweight='bold', color='blue')
        self.ax.tick_params(axis='y', labelcolor='blue', labelsize=9)
        self.ax.tick_params(axis='x', labelsize=9)
        
        # Create secondary Y-axis for current with proper formatting
        self.ax2 = self.ax.twinx()
        self.ax2.set_ylabel('Current (mA)', fontsize=10, fontweight='bold', color='red')
        self.ax2.tick_params(axis='y', labelcolor='red', labelsize=9)
        
        # Professional grid configuration
        self.ax.grid(True, which='major', color='#d0d0d0', linestyle='-', linewidth=0.5, alpha=0.8)
        self.ax.grid(True, which='minor', color='#e0e0e0', linestyle=':', linewidth=0.3, alpha=0.6)
        self.ax.minorticks_on()
        
        # Set up tick locators for clean axis labels
        from matplotlib.ticker import MaxNLocator, AutoMinorLocator
        self.ax.xaxis.set_major_locator(MaxNLocator(nbins=8))
        self.ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
        self.ax2.yaxis.set_major_locator(MaxNLocator(nbins=6))
        
        # Minor tick locators
        self.ax.xaxis.set_minor_locator(AutoMinorLocator(5))
        self.ax.yaxis.set_minor_locator(AutoMinorLocator(4))
        self.ax2.yaxis.set_minor_locator(AutoMinorLocator(4))
        
        # Set initial axis limits - always start from 0
        self.ax.set_xlim(0, 10)  # Will expand as needed
        self.ax.set_ylim(0, 100)
        self.ax2.set_ylim(0, 100)
        
        # Enable interactive features
        self.ax.margins(x=0.01, y=0.05)
        self.ax2.margins(y=0.05)
        
        # Add legend
        lines1, labels1 = self.ax.get_legend_handles_labels()
        lines2, labels2 = self.ax2.get_legend_handles_labels()
        self.ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=8)
        
        # Tight layout for better appearance
        self.fig.tight_layout()

    def compress_timeline_data(self, time_data, voltage_data, current_data, focus_window=None):
        """
        Compress timeline to show all data from 0 with recent data having higher resolution.
        
        Args:
            time_data: Original time data
            voltage_data: Original voltage data  
            current_data: Original current data
            focus_window: Time window (seconds) for high-resolution recent data (uses config if None)
        
        Returns:
            tuple: (compressed_time, compressed_voltage, compressed_current)
        """
        if len(time_data) < 2:
            return time_data, voltage_data, current_data
            
        # Use configured focus window if not specified
        if focus_window is None:
            focus_window = self.focus_window
            
        current_time = time_data[-1]
        
        # If total time is less than focus window, no compression needed
        if current_time <= focus_window:
            return time_data, voltage_data, current_data
        
        # Split data into two parts: recent (high-res) and historical (compressed)
        recent_start_time = current_time - focus_window
        
        # Find split index
        split_idx = 0
        for i, t in enumerate(time_data):
            if t >= recent_start_time:
                split_idx = i
                break
        
        # Recent data (last 30 seconds) - keep full resolution
        recent_time = time_data[split_idx:]
        recent_voltage = voltage_data[split_idx:]
        recent_current = current_data[split_idx:]
        
        # Historical data - compress logarithmically
        if split_idx > 0:
            historical_time = time_data[:split_idx]
            historical_voltage = voltage_data[:split_idx]
            historical_current = current_data[:split_idx]
            
            # Compress historical data to fit in first 70% of plot width
            compressed_historical_time = []
            compressed_historical_voltage = []
            compressed_historical_current = []
            
            # Use logarithmic compression for historical data
            hist_duration = recent_start_time  # Duration of historical data
            target_duration = focus_window * self.compression_ratio  # Compress based on config
            
            compression_factor = target_duration / hist_duration if hist_duration > 0 else 1
            
            for i, t in enumerate(historical_time):
                # Apply logarithmic compression using configurable exponent
                normalized_t = t / hist_duration  # 0 to 1
                compressed_t = target_duration * (normalized_t ** self.compression_exponent)
                
                compressed_historical_time.append(compressed_t)
                compressed_historical_voltage.append(historical_voltage[i])
                compressed_historical_current.append(historical_current[i])
            
            # Shift recent data to start after compressed historical data
            recent_offset = target_duration
            shifted_recent_time = [t - recent_start_time + recent_offset for t in recent_time]
            
            # Combine compressed historical and shifted recent data
            final_time = compressed_historical_time + shifted_recent_time
            final_voltage = compressed_historical_voltage + recent_voltage
            final_current = compressed_historical_current + recent_current
            
        else:
            # No historical data, just use recent data
            final_time = recent_time
            final_voltage = recent_voltage  
            final_current = recent_current
        
        return final_time, final_voltage, final_current

    def smooth_data(self, data, window_size=5):
        """Apply moving average smoothing to data."""
        if len(data) < window_size:
            return data
        
        smoothed = []
        for i in range(len(data)):
            start = max(0, i - window_size // 2)
            end = min(len(data), i + window_size // 2 + 1)
            smoothed.append(np.mean(data[start:end]))
        return smoothed

    def start_data_acquisition(self):
        """Start optimized data acquisition with smooth plotting."""
        try:
            # Check if experiment was stopped due to hold time
            if hasattr(self.controller.device_controller, 'experiment_stopped_by_hold_time') and \
               self.controller.device_controller.experiment_stopped_by_hold_time:
                self.logger.info("Experiment automatically stopped due to hold time limit reached")
                
                # Check if video recording is active and stop it
                video_was_recording = hasattr(self, 'is_recording') and self.is_recording
                if video_was_recording:
                    self.logger.info("Stopping video recording due to automatic experiment termination")
                    self.stop_recording()
                
                # Stop GUI data acquisition (same as clicking stop button)
                self.stop_data_acquisition()
                
                # Show notification to user with appropriate message
                message = (f"Experiment automatically stopped after CV→CC transition hold time was reached.\n\n"
                          f"Data has been saved to: {os.path.basename(self.data_filepath) if self.data_filepath else 'file'}")
                
                if video_was_recording:
                    message += "\n\nVideo recording has been stopped and saved."
                
                messagebox.showinfo("Experiment Complete", message)
                return
            
            # Get measurements from device controller
            voltage, current, _ = self.controller.device_controller.get_measurements()
           
            # Skip if readings are invalid
            if voltage is None or current is None:
                self.logger.warning("Skipping invalid readings")
                if self.is_plotting:
                    self.data_timer = self.root.after(self.data_period, self.start_data_acquisition)
                return
           
            current_time = time.time() - self.start_time
           
            # Add initial point at (0,0) for both voltage and current if this is the first data point
            if len(self.time_data) == 0:
                # Add starting point at time=0 with values=0 for clean origin connection
                self.voltage_data.append(0.0)
                self.current_data.append(0.0)
                self.time_data.append(0.0)
                self.logger.info("Added initial origin point (0,0) for clean graph start")
           
            # Store data in arrays with size management
            self.voltage_data.append(voltage)
            self.current_data.append(current)
            self.time_data.append(current_time)
            
            # Limit data size for performance
            if len(self.voltage_data) > self.max_data_points:
                # Keep the origin point (first point) and remove from middle
                if len(self.voltage_data) > 1:
                    self.voltage_data.pop(1)  # Remove second point to preserve origin
                    self.current_data.pop(1)
                    self.time_data.pop(1)
           
            # Update CV/CC mode display
            self.update_cv_cc_display()
            
            # IMPORTANT: Update stage management for hold time functionality
            # This ensures CV→CC transition detection and hold time logic runs
            if hasattr(self.controller.device_controller, 'update_stage'):
                try:
                    # Get hold time from entry field
                    hold_time = float(self.Hold_Time_entry.get()) if hasattr(self, 'Hold_Time_entry') else self.hold_time
                    # Get the current limit that was set at experiment start
                    current_limit = float(self.current_entry.get()) if hasattr(self, 'current_entry') else 100.0
                    
                    # Log current stage and transition info for debugging
                    stage = getattr(self.controller.device_controller, 'current_stage', 'Unknown')
                    power_mode = getattr(self.controller.device_controller, 'power_supply_mode', 'Unknown')
                    current_percent = (current / current_limit * 100) if current_limit > 0 else 0
                    
                    # Only log occasionally to avoid spam
                    if hasattr(self, 'debug_log_counter'):
                        self.debug_log_counter += 1
                    else:
                        self.debug_log_counter = 0
                        
                    if self.debug_log_counter % 50 == 0:  # Log every 5 seconds (50 * 100ms)
                        self.logger.info(f"Stage: {stage}, Power Mode: {power_mode}, Current: {current:.1f}mA ({current_percent:.1f}% of {current_limit:.1f}mA), Hold Time: {hold_time}s")
                    
                    # Call stage update with proper parameters
                    self.controller.device_controller.update_stage(
                        dwell_time=0,  # Not used during acquisition
                        hold_current=60,  # Not used for hold time limit
                        current_limit=current_limit,  # Use the set current limit
                        hold_time=hold_time,  # Use the hold time from GUI
                        target_temperature=None
                    )
                except Exception as stage_error:
                    self.logger.debug(f"Stage update error: {stage_error}")
           
            # Save data to file (skip the artificial origin point)
            if len(self.time_data) > 1:  # Only save real measurements, not the origin point
                self.data_file.write(f"{current_time:.3f}\t{voltage:.3f}\t{current:.3f}\n")
                self.data_file.flush()
           
            # Update plot every few data points for smooth animation
            self.plot_update_counter += 1
            if self.plot_update_counter >= 2:  # Update plot every 2 data points (100ms)
                self.update_smooth_plot()
                self.plot_update_counter = 0
           
            # Schedule next data acquisition
            if self.is_plotting:
                self.data_timer = self.root.after(self.data_period, self.start_data_acquisition)
           
        except Exception as e:
            self.logger.error(f"Error in data acquisition: {e}")
            self.stop_data_acquisition()

    def update_smooth_plot(self):
        """Update plot with compressed timeline showing all data from 0."""
        try:
            if len(self.time_data) < 2:
                return
                
            # Apply smoothing to reduce noise
            smooth_voltage = self.smooth_data(self.voltage_data, self.smoothing_window)
            smooth_current = self.smooth_data(self.current_data, self.smoothing_window)
            
            # Apply timeline compression using configured parameters
            compressed_time, compressed_voltage, compressed_current = self.compress_timeline_data(
                self.time_data, smooth_voltage, smooth_current
            )
            
            # Apply curve interpolation for smooth plotting lines
            if len(compressed_time) >= 3:  # Need at least 3 points for interpolation
                from scipy.interpolate import interp1d
                
                # Create interpolation functions
                try:
                    # Generate more points for smooth curves
                    num_smooth_points = min(len(compressed_time) * 3, 1000)  # Increase point density
                    time_smooth = np.linspace(compressed_time[0], compressed_time[-1], num_smooth_points)
                    
                    # Create cubic spline interpolation for smooth curves
                    voltage_interp = interp1d(compressed_time, compressed_voltage, kind='cubic', 
                                            bounds_error=False, fill_value='extrapolate')
                    current_interp = interp1d(compressed_time, compressed_current, kind='cubic', 
                                            bounds_error=False, fill_value='extrapolate')
                    
                    # Generate smooth interpolated data
                    voltage_smooth = voltage_interp(time_smooth)
                    current_smooth = current_interp(time_smooth)
                    
                    # Update line data with smooth interpolated curves
                    self.line_voltage.set_data(time_smooth, voltage_smooth)
                    self.line_current.set_data(time_smooth, current_smooth)
                    
                except Exception as interp_error:
                    # Fall back to original data if interpolation fails
                    self.line_voltage.set_data(compressed_time, compressed_voltage)
                    self.line_current.set_data(compressed_time, compressed_current)
            else:
                # Not enough points for interpolation, use original data
                self.line_voltage.set_data(compressed_time, compressed_voltage)
                self.line_current.set_data(compressed_time, compressed_current)
            
            # Add visual separator between compressed and recent data
            self.add_timeline_separator()
            
            # Dynamic axis scaling
            if len(compressed_time) > 1:
                # X-axis: Always start from 0, end at current compressed time
                x_max = max(compressed_time) if compressed_time else 10
                self.ax.set_xlim(0, x_max * 1.05)  # 5% padding on right
                
                # Voltage axis: auto-scale with padding
                if len(compressed_voltage) > 0:
                    v_min, v_max = min(compressed_voltage), max(compressed_voltage)
                    v_range = v_max - v_min
                    padding = max(v_range * 0.1, 1.0)  # 10% padding or minimum 1V
                    self.ax.set_ylim(v_min - padding, v_max + padding)
                
                # Current axis: auto-scale with padding  
                if len(compressed_current) > 0:
                    c_min, c_max = min(compressed_current), max(compressed_current)
                    c_range = c_max - c_min
                    padding = max(c_range * 0.1, 1.0)  # 10% padding or minimum 1mA
                    self.ax2.set_ylim(c_min - padding, c_max + padding)
            
            # Optimized canvas update
            self.canvas.draw_idle()  # Use draw_idle for better performance
            
        except Exception as e:
            self.logger.error(f"Error updating compressed timeline plot: {e}")

    def add_timeline_separator(self):
        """Add visual separator between compressed historical and recent data."""
        try:
            if len(self.time_data) < 2 or not PLOTTING_CONFIG["show_timeline_separator"]:
                return
                
            current_time = self.time_data[-1]
            
            # Only add separator if we have enough data for compression
            if current_time > self.focus_window:
                separator_x = self.focus_window * self.compression_ratio  # Position where recent data starts
                
                # Remove any existing separator lines
                for line in self.ax.lines[:]:
                    if hasattr(line, '_separator_line'):
                        line.remove()
                
                # Add new separator line
                y_min, y_max = self.ax.get_ylim()
                separator_line = self.ax.axvline(x=separator_x, color='gray', 
                                               linestyle='--', alpha=0.5, linewidth=1)
                separator_line._separator_line = True  # Mark as separator line
                
                # Add text annotation
                self.ax.text(separator_x + 1, y_max * 0.95, 'Recent Data →', 
                           fontsize=8, color='gray', alpha=0.7)
                self.ax.text(separator_x - 1, y_max * 0.95, '← Compressed', 
                           fontsize=8, color='gray', alpha=0.7, ha='right')
                
        except Exception as e:
            self.logger.error(f"Error adding timeline separator: {e}")

    def add_condition_change_marker(self, new_voltage, new_current):
        """Add visual marker on the plot to show where conditions were changed."""
        try:
            if len(self.time_data) < 1:
                return
                
            # Get current time for marker position
            current_time = self.time_data[-1]
            
            # Apply timeline compression to get the correct x-position
            compressed_time, _, _ = self.compress_timeline_data(
                self.time_data, self.voltage_data, self.current_data
            )
            marker_x = compressed_time[-1] if compressed_time else current_time
            
            # Get current axis limits
            y_min, y_max = self.ax.get_ylim()
            y2_min, y2_max = self.ax2.get_ylim()
            
            # Add vertical line marker
            marker_line = self.ax.axvline(x=marker_x, color='orange', 
                                        linestyle=':', alpha=0.8, linewidth=2)
            marker_line._condition_change_marker = True  # Mark as condition change line
            
            # Add text annotation
            annotation_text = f'Conditions Changed\nV: {new_voltage:.0f}V, I: {new_current:.0f}mA'
            self.ax.text(marker_x + 1, y_max * 0.85, annotation_text, 
                       fontsize=8, color='orange', fontweight='bold',
                       bbox=dict(boxstyle="round,pad=0.3", facecolor='white', 
                               edgecolor='orange', alpha=0.8))
            
            # Force immediate canvas update to show the marker
            self.canvas.draw_idle()
            
            self.logger.info(f"Added condition change marker at time {current_time:.1f}s")
            
        except Exception as e:
            self.logger.error(f"Error adding condition change marker: {e}")

    def clear_plot(self):
        """Clear the plot data and reset the display."""
        try:
            # Clear all data arrays
            self.voltage_data = []
            self.current_data = []
            self.time_data = []
            
            # Reset plot update counter
            self.plot_update_counter = 0
           
            # Remove any existing condition change markers
            for line in self.ax.lines[:]:
                if hasattr(line, '_condition_change_marker'):
                    line.remove()
            
            # Remove any existing text annotations
            for text in self.ax.texts[:]:
                if 'Conditions Changed' in text.get_text():
                    text.remove()
           
            # Reinitialize professional plot
            self.setup_professional_plot()
            
            # Reinitialize line objects
            self.line_voltage, = self.ax.plot([], [], 'b-', label='Voltage (V)', linewidth=0.5, antialiased=True)
            self.line_current, = self.ax2.plot([], [], 'r-', label='Current (mA)', linewidth=0.5, antialiased=True)
           
            # Update the canvas
            self.canvas.draw()
           
            self.logger.info("Plot cleared and reinitialized with compressed timeline")
           
        except Exception as e:
            self.logger.error(f"Error clearing plot: {e}")
       
    def cleanup(self):
        """Clean up resources when closing the GUI."""
        try:
            if self.is_plotting:
                self.toggle_plotting()  # Stop data acquisition
            self.controller.device_controller.cleanup()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def save_experiment_data(self):
        """Save experiment data to a text file."""
        try:
            # Create filename with timestamp
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"experiment_data_{timestamp}.txt"
           
            # Get save path from settings
            save_path = os.path.join("data", filename)
           
            # Create data directory if it doesn't exist
            os.makedirs("data", exist_ok=True)
           
            # Write data to file
            with open(save_path, 'w') as f:
                # Write header
                f.write("Time(s)\tVoltage(V)\tCurrent(mA)\n")
               
                # Write data points (every 0.5 seconds)
                for i in range(0, len(self.voltage_data), 5):  # 5 samples = 0.5s (100ms interval)
                    if i < len(self.voltage_data):
                        time_val = i * 0.1  # Convert sample index to time
                        f.write(f"{time_val:.1f}\t{self.voltage_data[i]:.2f}\t{self.current_data[i]:.2f}\n")
           
            self.logger.info(f"Experiment data saved to {save_path}")
            messagebox.showinfo("Save Data", f"Experiment data saved to {save_path}")
           
        except Exception as e:
            self.logger.error(f"Error saving experiment data: {e}")
            messagebox.showerror("Save Error", f"Failed to save experiment data: {str(e)}")

    def stop_data_acquisition(self):
        """Stop data acquisition and close data file."""
        self.is_plotting = False
        self.start_plot_button.configure(text="Start Acquisition")
       
        # Cancel all timers
        if self.control_timer:
            self.root.after_cancel(self.control_timer)
            self.control_timer = None
        if self.data_timer:
            self.root.after_cancel(self.data_timer)
            self.data_timer = None
        if self.display_timer:
            self.root.after_cancel(self.display_timer)
            self.display_timer = None
       
        # Clear data arrays
        self.voltage_data = []
        self.current_data = []
        self.time_data = []
        
        # Reset file path so user needs to select file for next experiment
        self.data_filepath = None
        
        # Reset Start button to neumorphic inactive state since file selection is cleared
        if hasattr(self, 'start_button_active') and self.start_button_active:
            inactive_color = "#e0e5ec"
            self.Start_GUI_button.configure(bg=inactive_color, fg="#333333")  # Default neumorphic colors
            self.Start_GUI_button.button_frame.configure(bg=inactive_color)
            self.Start_GUI_button.configure(text="Start")
            
            # Update hover effects for inactive neumorphic state
            def on_enter_inactive(e):
                self.Start_GUI_button.configure(bg="#d1d9e6")
                self.Start_GUI_button.button_frame.configure(bg="#d1d9e6")
            def on_leave_inactive(e):
                self.Start_GUI_button.configure(bg=inactive_color)
                self.Start_GUI_button.button_frame.configure(bg=inactive_color)
           
            # Remove old bindings and add new ones
            self.Start_GUI_button.unbind("<Enter>")
            self.Start_GUI_button.unbind("<Leave>")
            self.Start_GUI_button.bind("<Enter>", on_enter_inactive)
            self.Start_GUI_button.bind("<Leave>", on_leave_inactive)
           
            self.start_button_active = False
            # Disable parameter buttons when start button is deactivated
            self.set_parameter_buttons_state(False)
            self.logger.info("Neumorphic start button reset to inactive state - acquisition stopped")
       
        # Stop the process (set outputs to zero)
        try:
            self.controller.device_controller.stop_process()
            self.logger.info("Stopped process")
           
            # Close data file if it's open
            if hasattr(self, 'data_file') and self.data_file:
                self.data_file.close()
                self.logger.info(f"Closed data file: {self.data_filepath}")
                messagebox.showinfo("Save Data", f"Experiment data saved to {self.data_filepath}")
           
        except Exception as e:
            self.logger.error(f"Failed to stop process: {str(e)}")

    def export_plot_data(self):
        """Export the current plot data to a CSV file."""
        try:
            # Get data from arrays
            time_list = self.time_data.copy()
            voltage_list = self.voltage_data.copy()
            current_list = self.current_data.copy()
           
            if not time_list:
                messagebox.showwarning("No Data", "No data available to export.")
                return
           
            # Create timestamp for filename
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            default_filename = f"plot_data_{timestamp}.csv"
           
            # Open file dialog
            filepath = filedialog.asksaveasfilename(
                initialdir="data",
                initialfile=default_filename,
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Export Plot Data"
            )
           
            if filepath:
                # Write data to CSV
                with open(filepath, 'w', newline='') as f:
                    f.write("Time(s),Voltage(V),Current(mA)\n")
                    for t, v, c in zip(time_list, voltage_list, current_list):
                        f.write(f"{t:.3f},{v:.3f},{c:.3f}\n")
               
                self.logger.info(f"Data exported to {filepath}")
                messagebox.showinfo("Success", "Data exported successfully!")
               
        except Exception as e:
            self.logger.error(f"Error exporting data: {e}")
            messagebox.showerror("Error", f"Failed to export data: {str(e)}")

    def create_conditions_panel(self, parent, x, y):
        """Create the conditions panel with input fields and buttons."""
        # Create frame
        frame = self.create_frame(parent, x, y, 300, 200, "Conditions")
       
        # Sample parameters
        self.create_label(frame, 10, 10, "Electrical Distance (mm):", 12)
        self.elec_dist_entry = self.create_entry(frame, 150, 10, "0.4", 12)
       
        self.create_label(frame, 10, 40, "Sample Width (mm):", 12)
        self.width_entry = self.create_entry(frame, 150, 40, "1.6", 12)
       
        self.create_label(frame, 10, 70, "Sample Thickness (mm):", 12)
        self.thickness_entry = self.create_entry(frame, 150, 70, "1.0", 12)
       
        self.create_label(frame, 10, 100, "Electric Field (V/mm):", 12)
        self.field_entry = self.create_entry(frame, 150, 100, "30.0", 12)
       
        self.create_label(frame, 10, 130, "Current Density (mA/mm²):", 12)
        self.density_entry = self.create_entry(frame, 150, 130, "100.0", 12)
       
        # Send Limits button
        self.send_limits_btn = self.create_button(frame, 10, 160, "Send Limits", 12, self.send_limits)
       
        return frame

    def send_limits(self):
        """Calculate and send voltage/current limits to devices and apply them immediately."""
        try:
            # Get values from entries
            elec_dist = float(self.elec_dist_entry.get())
            width = float(self.width_entry.get())
            thickness = float(self.thickness_entry.get())
            field = float(self.field_entry.get())
            density = float(self.density_entry.get())
           
            # Calculate limits
            voltage, current = self.controller.device_controller.calculate_limits_from_parameters(
                elec_dist, width, thickness, field, density
            )
            
            # Store old values for logging
            old_voltage, old_current, _ = self.controller.device_controller.get_measurements()
           
            # Set limits on devices
            if self.controller.device_controller.set_voltage_current_limits(voltage, current):
                # Update voltage and current entry fields with calculated values
                self.voltage_entry.delete(0, END)
                self.voltage_entry.insert(0, f"{voltage:.2f}")
                self.current_entry.delete(0, END)
                self.current_entry.insert(0, f"{current:.2f}")
                
                # IMMEDIATELY apply the new voltage/current values
                self.controller.device_controller.set_voltage_current_limits(voltage, current)
                self.controller.device_controller.apply_voltage_current_limits()
                
                # Reset CV/CC tracking for the new conditions
                self.controller.device_controller.reset_cv_cc_tracking()
                
                # Add change marker to data file and plot if acquisition is active
                if self.is_plotting:
                    if hasattr(self, 'data_file') and self.data_file:
                        current_time = time.time() - self.start_time
                        self.data_file.write(f"# LIMITS CALCULATED AND APPLIED at {current_time:.3f}s: V={old_voltage:.2f}→{voltage:.2f}V, I={old_current:.2f}→{current:.2f}mA\n")
                        self.data_file.flush()
                    
                    # Add visual marker on the plot
                    self.add_condition_change_marker(voltage, current)
                
                self.logger.info(f"Calculated and applied new limits:")
                self.logger.info(f"  Voltage: {old_voltage:.2f}V → {voltage:.2f}V")
                self.logger.info(f"  Current: {old_current:.2f}mA → {current:.2f}mA")
                self.logger.info(f"  From parameters: E={field}V/mm, J={density}mA/mm², d={elec_dist}mm")
                
            else:
                self.logger.error("Failed to set voltage/current limits")
               
        except ValueError as e:
            self.logger.error(f"Invalid input values: {e}")
        except Exception as e:
            self.logger.error(f"Error sending limits: {e}")

    def change_conditions(self):
        """Change voltage and current limits and immediately apply them during acquisition."""
        try:
            voltage = float(self.voltage_entry.get())
            current = float(self.current_entry.get())
           
            # Validate input ranges
            if not (0 <= voltage <= 300):
                raise ValueError("Voltage must be between 0 and 300V")
            if not (0 <= current <= 2000):
                raise ValueError("Current must be between 0 and 2000mA")
               
            # Store the old values for logging
            old_voltage, old_current, _ = self.controller.device_controller.get_measurements()
            
            # 1. Set new limits on the controller
            if self.controller.device_controller.set_voltage_current_limits(voltage, current):
                # 2. IMMEDIATELY apply the new voltage/current values
                self.controller.device_controller.apply_voltage_current_limits()
                
                # 3. Update GUI entry displays to reflect the new values
                # Values are already updated in the entry fields since user typed them
                
                # 4. Reset CV/CC tracking for the new conditions
                self.controller.device_controller.reset_cv_cc_tracking()
                
                # 5. Add change marker to data file and plot if acquisition is active
                if self.is_plotting:
                    if hasattr(self, 'data_file') and self.data_file:
                        current_time = time.time() - self.start_time
                        self.data_file.write(f"# CONDITIONS CHANGED at {current_time:.3f}s: V={old_voltage:.2f}→{voltage:.2f}V, I={old_current:.2f}→{current:.2f}mA\n")
                        self.data_file.flush()
                    
                    # Add visual marker on the plot
                    self.add_condition_change_marker(voltage, current)
                
                # 6. Log the change for debugging
                self.logger.info(f"Conditions changed and applied immediately:")
                self.logger.info(f"  Voltage: {old_voltage:.2f}V → {voltage:.2f}V")
                self.logger.info(f"  Current: {old_current:.2f}mA → {current:.2f}mA")
                self.logger.info(f"  Graph will show new values immediately")
                
                # 7. Show success message
                messagebox.showinfo("Change Conditions", 
                                  f"Conditions updated and applied immediately!\n"
                                  f"Voltage: {old_voltage:.1f}V → {voltage:.1f}V\n"
                                  f"Current: {old_current:.1f}mA → {current:.1f}mA\n"
                                  f"Graph is now showing new values.")
            else:
                raise RuntimeError("Failed to set voltage/current limits on device")
                
        except ValueError as e:
            self.logger.error(f"Invalid input values: {str(e)}")
            messagebox.showerror("Change Conditions Error", str(e))
        except Exception as e:
            self.logger.error(f"Failed to change conditions: {str(e)}")
            messagebox.showerror("Change Conditions Error", str(e))

    def run_loading(self):
        """Send the forward (loading) command to Arduino."""
        self.send_command("FWD")
        self.logger.info("Loading (forward) command sent")

    def run_unloading(self):
        """Send the reverse (unloading) command to Arduino."""
        self.send_command("REV")
        self.logger.info("Unloading (reverse) command sent")

    def run(self):
        """Start the GUI main loop."""
        try:
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"Error in main loop: {str(e)}")
            self.on_closing()

if __name__ == "__main__":
    app = FlashSinterGUI()
    app.run() 