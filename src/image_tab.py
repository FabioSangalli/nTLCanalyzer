"""
Image analysis tab module for the TLC analyzer application.

This module implements the ImageTab class which handles image loading,
adjustment, and profile line creation.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import os
import traceback

from src.utils import generate_unique_id, get_color_for_line
from src.image_processing import load_image, adjust_image

class ImageTab(ttk.Frame):
    """
    Class for the image analysis tab.
    
    This class manages:
    - Image loading
    - Profile line creation
    - Image adjustments
    """
    def __init__(self, parent, app):
        """
        Initialize a new image tab.
        
        Args:
            parent: Parent widget
            app: Main application instance
        """
        super().__init__(parent)
        
        self.app = app
        self.image = None
        self.orig_image = None
        self.adjusted_image = None
        self.profile_lines = {}
        self.current_line_id = None
        self.active_color = '#555555'
        self.brightness = 0
        self.contrast = 1
        self.file_path = ""
        self.band_width = 5
        
        # Split into left (image) and right (controls) panels
        self.paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left panel for image
        image_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(image_frame, weight=3)
        
        # Right panel for controls
        control_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(control_frame, weight=1)
        
        # Image toolbar
        toolbar_frame = ttk.Frame(image_frame)
        toolbar_frame.pack(fill=tk.X, pady=(0, 10))
        
        # File operations
        select_btn = ttk.Button(toolbar_frame, text="Open Image", 
                               bootstyle="primary",
                               command=self.select_image)
        select_btn.pack(side=tk.LEFT, padx=5, pady=3)
        
        # Line operations
        new_line_btn = ttk.Button(toolbar_frame, text="New Line", 
                                bootstyle="success",
                                command=self.new_profile_line)
        new_line_btn.pack(side=tk.LEFT, padx=5, pady=3)
        
        delete_line_btn = ttk.Button(toolbar_frame, text="Delete Line", 
                                    bootstyle="danger",
                                    command=self.delete_profile_line)
        delete_line_btn.pack(side=tk.LEFT, padx=5, pady=3)
        
        # Image display area
        self.image_display_frame = ttk.Frame(image_frame)
        self.image_display_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a figure for the image
        self.image_fig, self.image_ax = plt.subplots(figsize=(6, 6))
        self.image_ax.set_title("Select an image and click to add points")
        self.image_ax.set_xticks([])
        self.image_ax.set_yticks([])
        
        # Info display at the bottom of the image
        self.info_ax = self.image_fig.add_axes([0.12, 0.01, 0.76, 0.03])
        self.info_ax.set_axis_off()
        self.info_text = self.info_ax.text(0.5, 0.5, "", ha='center', va='center', 
                                          fontsize=9, bbox=dict(facecolor='white', alpha=0.7))
        
        # Embed the matplotlib figure
        self.image_canvas = FigureCanvasTkAgg(self.image_fig, master=self.image_display_frame)
        self.image_canvas.draw()
        self.image_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add toolbar
        self.toolbar = NavigationToolbar2Tk(self.image_canvas, self.image_display_frame)
        self.toolbar.update()
        
        # Connect events
        self.image_canvas.mpl_connect('button_press_event', self.on_image_click)
        self.image_canvas.mpl_connect('key_press_event', self.on_image_key)
        self.image_canvas.mpl_connect('motion_notify_event', self.on_image_motion)
        
        # Control panel - Image Adjustments
        adjust_frame = ttk.LabelFrame(control_frame, text="Image Adjustments")
        adjust_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Brightness
        ttk.Label(adjust_frame, text="Brightness:").pack(anchor=tk.W, padx=5, pady=2)
        
        bright_frame = ttk.Frame(adjust_frame)
        bright_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.brightness_var = tk.DoubleVar(value=0.0)
        bright_scale = ttk.Scale(bright_frame, from_=-1.0, to=1.0, variable=self.brightness_var,
                                orient=tk.HORIZONTAL, length=150, 
                                command=self.on_adjust_image)
        bright_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        bright_label = ttk.Label(bright_frame, textvariable=self.brightness_var, width=4)
        bright_label.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Contrast
        ttk.Label(adjust_frame, text="Contrast:").pack(anchor=tk.W, padx=5, pady=2)
        
        contrast_frame = ttk.Frame(adjust_frame)
        contrast_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.contrast_var = tk.DoubleVar(value=1.0)
        contrast_scale = ttk.Scale(contrast_frame, from_=0.5, to=2.0, variable=self.contrast_var,
                                  orient=tk.HORIZONTAL, length=150, 
                                  command=self.on_adjust_image)
        contrast_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        contrast_label = ttk.Label(contrast_frame, textvariable=self.contrast_var, width=4)
        contrast_label.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Reset button
        reset_adjust_btn = ttk.Button(adjust_frame, text="Reset Adjustments", 
                                    command=self.reset_image_adjustments)
        reset_adjust_btn.pack(fill=tk.X, padx=5, pady=5)
        
        # Set default band width
        self.band_width_var = tk.IntVar(value=5)
        
        # Action buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        extract_btn = ttk.Button(btn_frame, text="Create Chromatogram", 
                               command=self.create_chromatogram)
        extract_btn.pack(fill=tk.X, pady=5)
    
    def select_image(self):
        """Open file dialog to select an image"""
        file_path = filedialog.askopenfilename(
            title="Select Chromatogram Image",
            filetypes=(
                ("Image files", "*.jpg *.jpeg *.png *.tif *.tiff *.bmp"),
                ("All files", "*.*")
            )
        )
        
        if not file_path:
            return
        
        # Load image
        try:
            self.orig_image, self.image = load_image(file_path)
            self.file_path = file_path
            
            # Reset data
            self.profile_lines = {}
            self.current_line_id = None
            
            # Create first line automatically
            self.new_profile_line()
            
            # Apply any brightness/contrast adjustments
            self.adjust_image()
            
            # Update display
            self.update_image_display()
            
            # Update status
            self.app.set_status(f"Loaded image: {os.path.basename(file_path)}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {str(e)}")
            traceback.print_exc()
    
    def on_adjust_image(self, event=None):
        """Handle brightness/contrast slider changes"""
        self.adjust_image()
        self.update_image_display()
    
    def adjust_image(self):
        """Apply brightness and contrast adjustments to the image"""
        if self.orig_image is None:
            return
            
        # Get current values
        brightness = self.brightness_var.get()
        contrast = self.contrast_var.get()
        
        # Store current values as instance variables for reference
        self.brightness = brightness
        self.contrast = contrast
        
        # Apply adjustments
        self.image = adjust_image(self.orig_image, brightness, contrast)
    
    def reset_image_adjustments(self):
        """Reset brightness and contrast to default values"""
        self.brightness_var.set(0.0)
        self.contrast_var.set(1.0)
        
        # Apply reset
        if self.orig_image is not None:
            self.image = self.orig_image.copy()
            self.update_image_display()
    
    def new_profile_line(self):
        """Create a new profile line"""
        if self.image is None:
            messagebox.showinfo("Info", "Please select an image first")
            return
        
        # Generate a unique ID for this line
        line_id = generate_unique_id()
        color = get_color_for_line(len(self.profile_lines))
        
        # Deactivate current active line
        if self.current_line_id:
            self.profile_lines[self.current_line_id]['active'] = False
        
        # Create the new line
        self.profile_lines[line_id] = {
            'points': [],
            'color': color,
            'active': True  # New line is active
        }
        
        self.current_line_id = line_id
        self.active_color = color
        
        # Update display
        self.update_image_display()
        
        # Update status
        self.app.set_status(f"New line created. Click to add points.")
    
    def delete_profile_line(self):
        """Delete the active profile line"""
        if not self.current_line_id:
            messagebox.showinfo("Info", "No active line to delete")
            return
                
        # Remove the line
        if self.current_line_id in self.profile_lines:
            del self.profile_lines[self.current_line_id]
                
            # If we have other lines, make one active
            if self.profile_lines:
                self.current_line_id = list(self.profile_lines.keys())[0]
                self.profile_lines[self.current_line_id]['active'] = True
                self.active_color = self.profile_lines[self.current_line_id]['color']
            else:
                self.current_line_id = None
                    
            # Update display
            self.update_image_display()
            self.app.set_status("Line deleted")
    
    def on_image_click(self, event):
        """Handle clicks on the image"""
        # Only respond to clicks within the axes
        if event.xdata is None or event.ydata is None or event.inaxes != self.image_ax:
            return
        
        # Only allow clicks if we have an image and active line
        if self.image is None:
            messagebox.showinfo("Info", "Please select an image first")
            return
            
        if not self.current_line_id:
            messagebox.showinfo("Info", "Please create a new line first")
            return
        
        # Add the point to active line
        self.profile_lines[self.current_line_id]['points'].append((event.xdata, event.ydata))
        
        # Update display
        self.update_image_display()
        
        # Update status
        points_count = len(self.profile_lines[self.current_line_id]['points'])
        self.app.set_status(f"{points_count} points selected for current line")
    
    def on_image_key(self, event):
        """Handle key presses on the image"""
        # Check for Ctrl+Z to undo last point
        if event.key == 'ctrl+z':
            if self.current_line_id and self.profile_lines[self.current_line_id]['points']:
                # Remove the last point
                self.profile_lines[self.current_line_id]['points'].pop()
                
                # Update display
                self.update_image_display()
                
                # Update status
                points_count = len(self.profile_lines[self.current_line_id]['points'])
                self.app.set_status(f"Removed last point. {points_count} points remaining.")
    
    def on_image_motion(self, event):
        """Handle mouse movement over the image"""
        if event.inaxes != self.image_ax or self.image is None:
            self.info_text.set_text("")
            self.image_canvas.draw_idle()
            return
            
        # Get image info at the cursor position
        x, y = int(event.xdata), int(event.ydata)
        
        # Check if coordinates are within image bounds
        if 0 <= x < self.image.shape[1] and 0 <= y < self.image.shape[0]:
            # Get pixel value (RGB or grayscale)
            if len(self.image.shape) == 3:
                r, g, b = self.image[y, x]
                value_str = f"RGB: ({r}, {g}, {b})"
            else:
                value = self.image[y, x]
                value_str = f"Value: {value}"
                
            info = f"Position: ({x}, {y})  {value_str}"
            self.info_text.set_text(info)
            self.image_canvas.draw_idle()
    
    def update_image_display(self):
        """Update the image display with current lines"""
        # Clear the plot
        self.image_ax.clear()
        
        # Show the image
        if self.image is not None:
            self.image_ax.imshow(self.image)
            self.image_ax.set_title("Click to add points along the chromatogram")
            self.image_ax.set_xticks([])
            self.image_ax.set_yticks([])
        
        # Plot all lines
        for line_id, line_data in self.profile_lines.items():
            points = line_data['points']
            color = line_data['color']
            is_active = line_data['active']
            
            if len(points) > 0:
                points_array = np.array(points)
                
                # Different style for active line
                style = '-' if is_active else '--'
                linewidth = 2 if is_active else 1
                
                # Plot line
                self.image_ax.plot(points_array[:, 0], points_array[:, 1], 
                                 marker='o', linestyle=style, color=color, 
                                 linewidth=linewidth, markersize=4)
                
                # Show band width for active line
                if is_active and len(points) > 1:
                    self.show_band_width(points_array, color)
        
        # Update canvas
        self.image_canvas.draw()
    
    def show_band_width(self, points, color):
        """Visualize the band width for averaging"""
        if len(points) < 2:
            return
            
        band_width = self.band_width_var.get()
        
        # Only draw for segments
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i+1]
            
            # Vector from p1 to p2
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            
            # Perpendicular vector (normalized)
            length = np.sqrt(dx*dx + dy*dy)
            if length > 0:
                nx = -dy / length
                ny = dx / length
                
                # Scale by band width
                nx *= band_width / 2
                ny *= band_width / 2
                
                # Draw the band outline
                alpha = 0.2
                
                # Create band polygon
                x = [p1[0] - nx, p1[0] + nx, p2[0] + nx, p2[0] - nx]
                y = [p1[1] - ny, p1[1] + ny, p2[1] + ny, p2[1] - ny]
                self.image_ax.fill(x, y, color=color, alpha=alpha)
    
    def create_chromatogram(self):
        """Create a new chromatogram tab using the current active line"""
        # Check if we have an image
        if self.image is None:
            messagebox.showinfo("Info", "Please select an image first")
            return
            
        # Check if we have an active line with enough points
        if not self.current_line_id or len(self.profile_lines[self.current_line_id]['points']) < 2:
            messagebox.showinfo("Info", "Please add at least 2 points to the active line")
            return
            
        # Get data for the active line
        points = self.profile_lines[self.current_line_id]['points']
        color = self.profile_lines[self.current_line_id]['color']
        band_width = self.band_width_var.get()
        
        # Create a new chromatogram tab with this data
        tab_id = self.app.create_new_chromatogram_tab(
            image=self.image, 
            profile_points=points,
            line_color=color
        )
        
        # Set band width
        self.app.tabs[tab_id].band_width = band_width
        
        # Set tab title if we have a file path
        if self.file_path:
            title = f"{os.path.basename(self.file_path)} - Line {tab_id}"
            self.app.set_tab_title(tab_id, title)
        
        # Update status
        self.app.set_status(f"Created new chromatogram tab for the active line")
