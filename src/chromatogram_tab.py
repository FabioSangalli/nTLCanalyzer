"""
Chromatogram tab module for the TLC analyzer application.

This module implements the ChromatogramTab class which represents a single
analysis tab in the application.
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
import pandas as pd

from src.utils import generate_unique_id, get_color_for_line, calculate_area
from src.image_processing import extract_profile
from numba import njit
from scipy.signal import savgol_filter
from src.peak_analysis import apply_savitzky_golay, apply_gaussian_smooth, detect_peaks
from src.integration import manual_integration
from src.fitting import fit_mecozzi_to_peak, mecozzi_a

class ChromatogramTab(ttk.Frame):
    """
    Class for individual chromatogram analysis tabs.
    
    This class manages:
    - Profile extraction
    - Peak detection
    - Integration
    - Curve fitting
    """
    def __init__(self, parent, app, tab_id):
        """
        Initialize a new chromatogram tab.
        
        Args:
            parent: Parent widget
            app: Main application instance
            tab_id: Unique ID for this tab
        """
        super().__init__(parent)
        
        self.app = app
        self.tab_id = tab_id
        self.image = None
        self.profile_points = []
        self.line_color = '#555555'
        self.band_width = 5
        self.results_data = {}
        self.file_path = ""
        self.peaks = {}
        self.integrations = {}
        self.mecozzi_fits = {}
        
        # Create the layout
        # Split horizontally
        paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left panel for chromatogram
        self.chrom_frame = ttk.Frame(paned_window)
        paned_window.add(self.chrom_frame, weight=3)
        
        # Right panel for controls
        control_frame = ttk.Frame(paned_window)
        paned_window.add(control_frame, weight=1)
        
        # Create chromatogram figure
        self.chrom_fig = plt.figure(figsize=(8, 5))
        self.chrom_ax = self.chrom_fig.add_subplot(111)
        self.chrom_ax.set_title("Chromatogram")
        self.chrom_ax.set_xlabel("Distance (pixels)")
        self.chrom_ax.set_ylabel("Intensity")
        
        # Add cursor info display with Tufte-inspired styling
        from src.utils import COLORS
        from src.themes import get_theme_style
        theme_style = get_theme_style(self.app.theme)
        self.cursor_annotation = self.chrom_ax.annotate('', xy=(0, 0), xytext=(10, 10),
                                                    textcoords='offset points',
                                                    bbox=dict(boxstyle='round,pad=0.5', fc=COLORS[theme_style]['annotation'], alpha=0.5),
                                                    fontsize=8)
        self.cursor_annotation.set_visible(False)
        
        # Add selection rectangle for area selection with Tufte-inspired styling
        self.selection_rect = plt.Rectangle((0, 0), 0, 0, edgecolor=COLORS[theme_style]['accent'], facecolor=COLORS[theme_style]['selection'], alpha=0.2)
        self.chrom_ax.add_patch(self.selection_rect)
        self.selection_rect.set_visible(False)
        
        self.chrom_fig.tight_layout()
        
        self.chrom_canvas = FigureCanvasTkAgg(self.chrom_fig, master=self.chrom_frame)
        self.chrom_canvas.draw()
        self.chrom_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Connect events
        self.chrom_canvas.mpl_connect('motion_notify_event', self.on_chrom_motion)
        self.chrom_canvas.mpl_connect('button_press_event', self.on_chrom_click)
        self.chrom_canvas.mpl_connect('button_release_event', self.on_chrom_release)
        
        # Add toolbar
        self.chrom_toolbar = NavigationToolbar2Tk(self.chrom_canvas, self.chrom_frame)
        self.chrom_toolbar.update()
        
        # Create a notebook for the analysis controls
        control_notebook = ttk.Notebook(control_frame)
        control_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs for different controls
        filter_tab = ttk.Frame(control_notebook)
        peak_tab = ttk.Frame(control_notebook)
        fit_tab = ttk.Frame(control_notebook)
        
        control_notebook.add(filter_tab, text="Filters")
        control_notebook.add(peak_tab, text="Peaks")
        control_notebook.add(fit_tab, text="Fitting")
        
        # Filters tab
        filter_frame = ttk.LabelFrame(filter_tab, text="Signal Processing")
        filter_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Invert values option (default to True)
        self.invert_var = tk.BooleanVar(value=True)
        invert_check = ttk.Checkbutton(filter_frame, text="Invert Values", 
                                     variable=self.invert_var,
                                     command=lambda: self.apply_filters() if self.results_data else None)
        invert_check.pack(anchor=tk.W, padx=5, pady=5)
        
        # Savitzky-Golay filter
        ttk.Label(filter_frame, text="Window Size:").pack(anchor=tk.W, padx=5, pady=2)
        
        window_frame = ttk.Frame(filter_frame)
        window_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.window_size_var = tk.IntVar(value=15)
        window_scale = ttk.Scale(window_frame, from_=5, to=201, variable=self.window_size_var,
                               orient=tk.HORIZONTAL, length=150,
                               command=lambda e: self.apply_filters() if self.results_data else None)
        window_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        window_label = ttk.Label(window_frame, textvariable=self.window_size_var, width=3)
        window_label.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Polynomial order
        ttk.Label(filter_frame, text="Polynomial Order:").pack(anchor=tk.W, padx=5, pady=2)
        
        poly_frame = ttk.Frame(filter_frame)
        poly_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.poly_order_var = tk.IntVar(value=3)
        poly_scale = ttk.Scale(poly_frame, from_=1, to=9, variable=self.poly_order_var,
                             orient=tk.HORIZONTAL, length=150,
                             command=lambda e: self.apply_filters() if self.results_data else None)
        poly_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        poly_label = ttk.Label(poly_frame, textvariable=self.poly_order_var, width=3)
        poly_label.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Smoothing
        ttk.Label(filter_frame, text="Smoothing:").pack(anchor=tk.W, padx=5, pady=2)
        
        smooth_frame = ttk.Frame(filter_frame)
        smooth_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.smooth_var = tk.DoubleVar(value=0.0)
        smooth_scale = ttk.Scale(smooth_frame, from_=0.0, to=20.0, variable=self.smooth_var,
                               orient=tk.HORIZONTAL, length=150,
                               command=lambda e: self.apply_filters() if self.results_data else None)
        smooth_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        smooth_label = ttk.Label(smooth_frame, textvariable=self.smooth_var, width=3)
        smooth_label.pack(side=tk.RIGHT, padx=(5, 0))
        
        # No Apply button needed as filters apply automatically
        
        # Peak detection tab
        peak_frame = ttk.LabelFrame(peak_tab, text="Peak Detection")
        peak_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Peak height threshold
        ttk.Label(peak_frame, text="Height Threshold:").pack(anchor=tk.W, padx=5, pady=2)
        
        height_frame = ttk.Frame(peak_frame)
        height_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.peak_height_var = tk.DoubleVar(value=0.5)
        height_scale = ttk.Scale(height_frame, from_=0.0, to=1.0, variable=self.peak_height_var,
                               orient=tk.HORIZONTAL, length=150)
        height_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        height_label = ttk.Label(height_frame, textvariable=self.peak_height_var, width=3)
        height_label.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Peak distance
        ttk.Label(peak_frame, text="Minimum Distance:").pack(anchor=tk.W, padx=5, pady=2)
        
        distance_frame = ttk.Frame(peak_frame)
        distance_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.peak_distance_var = tk.IntVar(value=20)
        distance_scale = ttk.Scale(distance_frame, from_=5, to=100, variable=self.peak_distance_var,
                                 orient=tk.HORIZONTAL, length=150)
        distance_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        distance_label = ttk.Label(distance_frame, textvariable=self.peak_distance_var, width=3)
        distance_label.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Peak width (for integration)
        ttk.Label(peak_frame, text="Peak Width %:").pack(anchor=tk.W, padx=5, pady=2)
        
        width_frame = ttk.Frame(peak_frame)
        width_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.peak_width_var = tk.IntVar(value=20)  # Default to 20% of height
        width_scale = ttk.Scale(width_frame, from_=5, to=90, variable=self.peak_width_var,
                              orient=tk.HORIZONTAL, length=150)
        width_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        width_label = ttk.Label(width_frame, textvariable=self.peak_width_var, width=3)
        width_label.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Peak detection buttons
        peak_btn_frame = ttk.Frame(peak_frame)
        peak_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        detect_btn = ttk.Button(peak_btn_frame, text="Detect Peaks", 
                              command=self.detect_peaks)
        detect_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        
        clear_btn = ttk.Button(peak_btn_frame, text="Clear Peaks", 
                             command=self.clear_peaks)
        clear_btn.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(2, 0))
        
        # Integration frame
        integration_frame = ttk.LabelFrame(peak_tab, text="Integration")
        integration_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Option to hide integration instructions
        self.hide_integration_instructions = tk.BooleanVar(value=False)
        hide_instructions_check = ttk.Checkbutton(integration_frame, 
                                                text="Hide integration instructions", 
                                                variable=self.hide_integration_instructions)
        hide_instructions_check.pack(anchor=tk.W, padx=5, pady=5)
        
        # Manual integration mode
        self.integration_mode = tk.StringVar(value="manual")
        
        # Integration buttons
        int_btn_frame = ttk.Frame(integration_frame)
        int_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.manual_int_btn = ttk.Button(int_btn_frame, text="Manual Integration", 
                                      command=self.enable_manual_integration)
        self.manual_int_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        
        clear_int_btn = ttk.Button(int_btn_frame, text="Clear Integrations", 
                                 command=self.clear_integrations)
        clear_int_btn.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(2, 0))
        
        # Fitting tab - moved to top
        mecozzi_frame = ttk.LabelFrame(fit_tab, text="Mecozzi Fitting")
        mecozzi_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # No peak selection mode or fit selected peak button
        
        # Fit all button
        fit_all_btn = ttk.Button(mecozzi_frame, text="Fit All Peaks", 
                               command=self.fit_all_peaks)
        fit_all_btn.pack(fill=tk.X, padx=5, pady=5)
        
        # Integrate fitted peaks button
        integrate_fits_btn = ttk.Button(mecozzi_frame, text="Integrate Fitted Peaks", 
                                      command=self.integrate_fitted_peaks)
        integrate_fits_btn.pack(fill=tk.X, padx=5, pady=5)
        
        # Results display
        result_frame = ttk.LabelFrame(fit_tab, text="Results")
        result_frame.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)
        
        # Create a text widget for results with scrollbar
        result_scroll = ttk.Scrollbar(result_frame)
        result_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.result_text = tk.Text(result_frame, height=10, width=30, font=('Times New Roman', 9),
                                 yscrollcommand=result_scroll.set)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        result_scroll.config(command=self.result_text.yview)
        
        # File operations
        file_frame = ttk.Frame(control_frame)
        file_frame.pack(fill=tk.X, padx=10, pady=10, side=tk.BOTTOM)
        
        save_btn = ttk.Button(file_frame, text="Save Data", 
                            command=self.save_data)
        save_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        
        open_btn = ttk.Button(file_frame, text="Open Data", 
                            command=self.open_data)
        open_btn.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(2, 0))
    
    def set_image_data(self, image, profile_points, line_color):
        """
        Set the image and profile data for this tab.
        
        Args:
            image (ndarray): The image data
            profile_points (list): List of points defining the profile line
            line_color (str): Color for the profile line
        """
        self.image = image
        self.profile_points = profile_points
        self.line_color = line_color
        
        # Create a unique ID for this line
        line_id = generate_unique_id()
        
        # Add a single line to our results data
        self.results_data = {
            line_id: {
                'distances': np.array([]),  # Will be filled during extraction
                'raw_intensities': np.array([]),  # Will be filled during extraction
                'filtered': np.array([]),  # Will be filled during extraction
                'color': line_color
            }
        }
    
    def extract_and_analyze(self):
        """Extract profile and analyze it"""
        # Check if we have an image and profile points
        if self.image is None or not self.profile_points:
            messagebox.showinfo("Info", "No image or profile data available")
            return
        
        # Get a unique line ID (should be only one in this tab)
        line_id = next(iter(self.results_data))
        
        # Extract profile
        distances, intensities = extract_profile(self.image, self.profile_points, self.band_width)
        
        # Store raw data
        self.results_data[line_id]['distances'] = distances
        self.results_data[line_id]['raw_intensities'] = intensities
        self.results_data[line_id]['filtered'] = intensities.copy()  # Will be updated by apply_filters
        
        # Apply filters
        self.apply_filters()
        
        # Update display
        self.update_chromatogram_display()
        
        # Update status
        self.app.set_status("Extraction complete. Use peak detection tools for analysis.")
    
    def apply_filters(self):
        """Apply filters to the extracted profile"""
        if not self.results_data:
            return
            
        # Get filter parameters
        window_size = self.window_size_var.get()
        if window_size % 2 == 0:
            window_size += 1  # Ensure odd
            
        poly_order = self.poly_order_var.get()
        smooth_sigma = self.smooth_var.get()
        invert = self.invert_var.get()
        
        # Apply to each profile (should be only one in this tab)
        for line_id, data in self.results_data.items():
            intensities = data['raw_intensities']
            
            # Invert if needed
            if invert:
                filtered = np.max(intensities) - intensities
            else:
                filtered = intensities.copy()
            
            # Apply SG filter if we have enough points
            if len(filtered) > window_size:
                try:
                    filtered = apply_savitzky_golay(filtered, window_size, poly_order)
                except Exception as e:
                    messagebox.showerror("Filter Error", 
                                       f"Error applying Savitzky-Golay filter:\n{str(e)}\n"
                                       f"Try reducing window size or polynomial order.")
                    return
                
            # Apply additional smoothing if requested
            if smooth_sigma > 0:
                filtered = apply_gaussian_smooth(filtered, smooth_sigma)
                
            # Update filtered data
            data['filtered'] = filtered
            
        # Update chromatogram display
        self.update_chromatogram_display()
        
        # Clear peaks and integrations when filters change
        self.peaks = {}
        self.integrations = {}
        self.mecozzi_fits = {}
    
    def update_chromatogram_display(self):
        """Update the chromatogram display"""
        if not self.results_data:
            return
            
        # Clear the plot
        self.chrom_ax.clear()
        
        # Setup chromatogram plot
        self.chrom_ax.set_title("Chromatogram")
        self.chrom_ax.set_xlabel("Distance (pixels)")
        self.chrom_ax.set_ylabel("Intensity")
        
        # Plot chromatogram (should be only one in this tab)
        for line_id, data in self.results_data.items():
            if len(data['distances']) == 0 or len(data['filtered']) == 0:
                continue
                
            distances = data['distances']
            filtered = data['filtered']
            color = data['color']
            
            # Plot the chromatogram
            self.chrom_ax.plot(distances, filtered, color=color, linewidth=1.5)
            
            # Plot any detected peaks
            if line_id in self.peaks:
                peak_indices = self.peaks[line_id]
                peak_x = distances[peak_indices]
                peak_y = filtered[peak_indices]
                
                self.chrom_ax.plot(peak_x, peak_y, 'o', color='#D62728', markersize=5)
                
                # Number the peaks
                for j, (x, y) in enumerate(zip(peak_x, peak_y)):
                    self.chrom_ax.text(x, y + 5, f"{j+1}", ha='center', va='bottom', 
                                     fontsize=8, color='#D62728')
            
            # Plot any integrations with distinct colors
            if line_id in self.integrations:
                for j, (start_idx, end_idx) in enumerate(self.integrations[line_id]):
                    # Get x range
                    x_range = distances[start_idx:end_idx]
                    y_range = filtered[start_idx:end_idx]
                    
                    # Calculate baseline (straight line between start and end points)
                    baseline = np.linspace(filtered[start_idx], filtered[end_idx], len(x_range))
                    
                    # Use a different color for each integration
                    integration_color = plt.cm.tab10(j % 10)
                    
                    # Fill the area only above baseline
                    self.chrom_ax.fill_between(x_range, baseline, y_range, 
                                             where=(y_range > baseline), 
                                             alpha=0.3, color=integration_color)
                    
                    # Draw baseline
                    self.chrom_ax.plot(x_range, baseline, '-', color=integration_color, linewidth=1, alpha=0.7)
                    
                    # Add a label with the area
                    area = calculate_area(y_range - baseline, x_range)
                    mid_x = np.mean(x_range)
                    max_y = np.max(y_range)
                    
                    self.chrom_ax.text(mid_x, max_y * 0.8, f"A{j+1}: {area:.1f}", 
                                      ha='center', va='center', fontsize=8, color=integration_color,
                                      bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
        
        # Plot any Mecozzi fits
        for line_id in self.mecozzi_fits:
            if line_id in self.results_data:  # Make sure we have data for this line
                for i, fit_data in enumerate(self.mecozzi_fits[line_id]):
                    # Plot the fitted curve
                    x_fit = fit_data['x_fit']
                    y_fit = fit_data['y_fit']
                    
                    self.chrom_ax.plot(x_fit, y_fit, '--', color='#FF7F0E', linewidth=1.5)
                    
                    # Label with peak number if it's associated with a detected peak
                    if 'peak_idx' in fit_data:
                        peak_idx = fit_data['peak_idx']
                        fitted_center = fit_data['params'][1]  # center parameter
                        
                        # Add label at the peak center
                        self.chrom_ax.text(fitted_center, y_fit.max() + 10, 
                                         f"F{i+1}", ha='center', va='bottom',
                                         fontsize=8, color='#FF7F0E')
        
        # Add the cursor annotation and selection rectangle back
        self.chrom_ax.add_artist(self.cursor_annotation)
        self.chrom_ax.add_patch(self.selection_rect)
        
        # Update the results text with a summary
        self.update_results_text()
        
        # Tighten layout and draw
        self.chrom_fig.tight_layout()
        self.chrom_canvas.draw()
    
    def on_chrom_motion(self, event):
        """Handle mouse movement over the chromatogram"""
        if not event.inaxes or event.inaxes != self.chrom_ax or not self.results_data:
            self.cursor_annotation.set_visible(False)
            self.chrom_canvas.draw_idle()
            return
            
        # Get x and y data
        line_id = next(iter(self.results_data))
        distances = self.results_data[line_id]['distances']
        intensities = self.results_data[line_id]['filtered']
        
        if len(distances) == 0 or len(intensities) == 0:
            return
            
        # Find closest x point
        x = event.xdata
        idx = np.argmin(np.abs(distances - x))
        
        if idx >= 0 and idx < len(distances):
            # Update annotation with position and value
            self.cursor_annotation.xy = (distances[idx], intensities[idx])
            self.cursor_annotation.set_text(f"x: {distances[idx]:.1f}\ny: {intensities[idx]:.1f}")
            self.cursor_annotation.set_visible(True)
            
            # Update selection rectangle if we're in the middle of a selection
            if hasattr(self, 'selection_start') and self.selection_start is not None:
                start_x = self.selection_start
                end_x = x
                
                # Get the indices for the range
                start_idx = np.argmin(np.abs(distances - start_x))
                end_idx = np.argmin(np.abs(distances - end_x))
                
                # Ensure start is before end
                if start_idx > end_idx:
                    start_idx, end_idx = end_idx, start_idx
                
                # Get the y range
                y_min = np.min(intensities[start_idx:end_idx+1])
                y_max = np.max(intensities[start_idx:end_idx+1])
                
                # Add some padding
                y_range = y_max - y_min
                y_min -= y_range * 0.1
                y_max += y_range * 0.1
                
                # Update the rectangle
                width = distances[end_idx] - distances[start_idx]
                height = y_max - y_min
                self.selection_rect.set_xy((distances[start_idx], y_min))
                self.selection_rect.set_width(width)
                self.selection_rect.set_height(height)
                self.selection_rect.set_visible(True)
                
                # Calculate area
                y_vals = intensities[start_idx:end_idx+1]
                x_vals = distances[start_idx:end_idx+1]
                
                # Create baseline between endpoints
                baseline = np.linspace(intensities[start_idx], intensities[end_idx], len(x_vals))
                
                # Calculate area above baseline
                area = calculate_area(y_vals - baseline, x_vals)
                
                # Update status
                self.app.set_status(f"Selection: x=[{distances[start_idx]:.1f}, {distances[end_idx]:.1f}], Area={area:.1f}")
            
            self.chrom_canvas.draw_idle()
    
    def on_chrom_click(self, event):
        """Handle mouse click on the chromatogram"""
        if not event.inaxes or event.inaxes != self.chrom_ax or not self.results_data:
            return
            
        # Start a selection
        self.selection_start = event.xdata
        
        # Clear any previous selection
        self.selection_rect.set_visible(False)
        self.chrom_canvas.draw_idle()
    
    def on_chrom_release(self, event):
        """Handle mouse release on the chromatogram"""
        if not event.inaxes or event.inaxes != self.chrom_ax or not self.results_data:
            return
            
        # End selection
        if hasattr(self, 'selection_start') and self.selection_start is not None:
            # Get current line data
            line_id = next(iter(self.results_data))
            distances = self.results_data[line_id]['distances']
            filtered = self.results_data[line_id]['filtered']
            
            if len(distances) == 0 or len(filtered) == 0:
                return
                
            # Get the selection bounds
            start_x = self.selection_start
            end_x = event.xdata
            
            # Get the indices for the range
            start_idx = np.argmin(np.abs(distances - start_x))
            end_idx = np.argmin(np.abs(distances - end_x))
            
            # Ensure start is before end
            if start_idx > end_idx:
                start_idx, end_idx = end_idx, start_idx
                
            # Add to integrations if we're in manual integration mode
            if hasattr(self, 'manual_integration_active') and self.manual_integration_active:
                if line_id not in self.integrations:
                    self.integrations[line_id] = []
                    
                self.integrations[line_id].append((start_idx, end_idx))
                
                # Calculate and display area
                x_range = distances[start_idx:end_idx]
                y_range = filtered[start_idx:end_idx]
                baseline = np.linspace(filtered[start_idx], filtered[end_idx], len(x_range))
                area = calculate_area(y_range - baseline, x_range)
                
                self.app.set_status(f"Integrated area: {area:.2f}")
                
                # Hide selection rectangle and update display
                self.selection_rect.set_visible(False)
                self.update_chromatogram_display()
            
            # Reset selection start
            self.selection_start = None
    
    def update_results_text(self):
        """Update the results text widget with current data"""
        self.result_text.delete(1.0, tk.END)
        
        if not self.results_data:
            self.result_text.insert(tk.END, "No data to display.")
            return
            
        # Show data for the line
        line_id = next(iter(self.results_data))
        self.result_text.insert(tk.END, "Chromatogram Analysis:\n")
        self.result_text.insert(tk.END, "------------------\n")
        
        # Show peak information
        if line_id in self.peaks:
            peak_indices = self.peaks[line_id]
            distances = self.results_data[line_id]['distances']
            intensities = self.results_data[line_id]['filtered']
            
            self.result_text.insert(tk.END, "Detected Peaks:\n")
            
            for j, peak_idx in enumerate(peak_indices):
                peak_x = distances[peak_idx]
                peak_y = intensities[peak_idx]
                
                self.result_text.insert(tk.END, f"  Peak {j+1}:\n")
                self.result_text.insert(tk.END, f"    Position: {peak_x:.1f}\n")
                self.result_text.insert(tk.END, f"    Intensity: {peak_y:.1f}\n")
                
                # Show integration if available
                if line_id in self.integrations:
                    for k, (start_idx, end_idx) in enumerate(self.integrations[line_id]):
                        # Check if this integration contains this peak
                        if start_idx <= peak_idx <= end_idx:
                            x_range = distances[start_idx:end_idx]
                            y_range = intensities[start_idx:end_idx]
                            
                            # Calculate baseline
                            baseline = np.linspace(intensities[start_idx], intensities[end_idx], len(x_range))
                            
                            area = calculate_area(y_range - baseline, x_range)
                            self.result_text.insert(tk.END, f"    Area (A{k+1}): {area:.1f}\n")
                
                # Show Mecozzi fit if available
                if line_id in self.mecozzi_fits:
                    for i, fit_data in enumerate(self.mecozzi_fits[line_id]):
                        if 'peak_idx' in fit_data and fit_data['peak_idx'] == peak_idx:
                            h, c, w, a = fit_data['params']
                            self.result_text.insert(tk.END, f"    Mecozzi Fit (F{i+1}):\n")
                            self.result_text.insert(tk.END, f"      Height: {h:.2f}\n")
                            self.result_text.insert(tk.END, f"      Center: {c:.2f}\n")
                            self.result_text.insert(tk.END, f"      HWHM: {w:.2f}\n")
                            self.result_text.insert(tk.END, f"      Asymmetry: {a:.2f}\n")
                            self.result_text.insert(tk.END, f"      Area: {fit_data['area']:.2f}\n")
                
                self.result_text.insert(tk.END, "\n")
        else:
            self.result_text.insert(tk.END, "No peaks detected.\n")
            self.result_text.insert(tk.END, "Use the peak detection tools to analyze the chromatogram.\n\n")
            
        # Show all integrations
        if line_id in self.integrations and self.integrations[line_id]:
            distances = self.results_data[line_id]['distances']
            intensities = self.results_data[line_id]['filtered']
            
            self.result_text.insert(tk.END, "All Integrations:\n")
            
            for k, (start_idx, end_idx) in enumerate(self.integrations[line_id]):
                x_range = distances[start_idx:end_idx]
                y_range = intensities[start_idx:end_idx]
                
                # Calculate baseline
                baseline = np.linspace(intensities[start_idx], intensities[end_idx], len(x_range))
                
                area = calculate_area(y_range - baseline, x_range)
                self.result_text.insert(tk.END, f"  Integration A{k+1}:\n")
                self.result_text.insert(tk.END, f"    Start: {distances[start_idx]:.1f}\n")
                self.result_text.insert(tk.END, f"    End: {distances[end_idx]:.1f}\n")
                self.result_text.insert(tk.END, f"    Area: {area:.1f}\n\n")
    
    def detect_peaks(self):
        """Detect peaks in the chromatogram"""
        if not self.results_data:
            messagebox.showinfo("Info", "No data to analyze. Extract profiles first.")
            return
            
        # Get peak detection parameters
        height_threshold = self.peak_height_var.get()
        distance = self.peak_distance_var.get()
        
        # Detect peaks
        line_id = next(iter(self.results_data))
        filtered = self.results_data[line_id]['filtered']
        
        if len(filtered) == 0:
            return
            
        # Find peaks
        try:
            peak_indices = detect_peaks(filtered, height_threshold, distance, prominence=10, width=3)
            
            # Store the peaks
            self.peaks[line_id] = peak_indices
        except Exception as e:
            messagebox.showerror("Error", f"Failed to detect peaks: {str(e)}")
            return
        
        # Update the display
        self.update_chromatogram_display()
        
        # Update status
        self.app.set_status(f"Detected {len(peak_indices)} peaks")
    
    def clear_peaks(self):
        """Clear detected peaks"""
        self.peaks = {}
        self.update_chromatogram_display()
        self.app.set_status("Peaks cleared")
    
    def enable_manual_integration(self):
        """Enable manual integration mode"""
        # Check if we should show instructions
        if not hasattr(self, 'hide_integration_instructions') or not self.hide_integration_instructions.get():
            messagebox.showinfo("Manual Integration", 
                              "Click and drag to select a region to integrate.\n"
                              "The area between the selected points above the baseline will be integrated.\n"
                              "You can select multiple regions for integration.")
        
        # Set manual integration mode
        self.manual_integration_active = True
        self.manual_int_btn.config(text="Exit Integration Mode")
        self.manual_int_btn.config(command=self.disable_manual_integration)
        
        # Update status
        self.app.set_status("Manual integration mode enabled. Click and drag to select regions.")
    
    def disable_manual_integration(self):
        """Disable manual integration mode"""
        self.manual_integration_active = False
        self.manual_int_btn.config(text="Manual Integration")
        self.manual_int_btn.config(command=self.enable_manual_integration)
        
        # Update status
        self.app.set_status("Manual integration mode disabled.")
    
    def clear_integrations(self):
        """Clear all integrations"""
        self.integrations = {}
        self.update_chromatogram_display()
        self.app.set_status("Integrations cleared")
    
    def fit_mecozzi(self):
        """Fit all peaks with Mecozzi function"""
        # Just call fit_all_peaks since we removed the individual peak fitting option
        self.fit_all_peaks()
    
    def on_peak_select(self, event):
        """Handle peak selection for fitting"""
        if event.inaxes != self.chrom_ax:
            return
            
        # Get line data
        line_id = next(iter(self.results_data))
        if line_id not in self.peaks or not self.peaks[line_id].size:
            return
            
        distances = self.results_data[line_id]['distances']
        peak_indices = self.peaks[line_id]
        
        # Find closest peak
        closest_peak_idx = None
        closest_distance = float('inf')
        
        for peak_idx in peak_indices:
            peak_x = distances[peak_idx]
            distance = abs(peak_x - event.xdata)
            
            if distance < closest_distance:
                closest_distance = distance
                closest_peak_idx = peak_idx
        
        # Check if we found a peak close enough
        if closest_peak_idx is not None and closest_distance < 20:
            # Fit the peak
            self.fit_peak(line_id, closest_peak_idx)
            
            # Disconnect events
            self.chrom_canvas.mpl_disconnect(self.peak_select_cid)
            self.chrom_canvas.mpl_disconnect(self.peak_key_cid)
    
    def on_peak_key(self, event):
        """Handle key press for peak selection"""
        if event.key == 'escape':
            # Disconnect events
            self.chrom_canvas.mpl_disconnect(self.peak_select_cid)
            self.chrom_canvas.mpl_disconnect(self.peak_key_cid)
            
            self.app.set_status("Peak selection cancelled")
    
    def fit_peak(self, line_id, peak_idx):
        """Fit Mecozzi function to the selected peak"""
        distances = self.results_data[line_id]['distances']
        intensities = self.results_data[line_id]['filtered']
        
        try:
            # Fit the peak
            fit_result = fit_mecozzi_to_peak(distances, intensities, peak_idx)
            
            # Store the fit
            if line_id not in self.mecozzi_fits:
                self.mecozzi_fits[line_id] = []
                
            self.mecozzi_fits[line_id].append(fit_result)
            
            # Update display
            self.update_chromatogram_display()
            
            # Update status
            center = fit_result['params'][1]
            self.app.set_status(f"Fitted peak at position {center:.1f}")
            
        except Exception as e:
            messagebox.showerror("Fitting Error", f"Failed to fit Mecozzi function:\n{str(e)}")
            traceback.print_exc()
    
    def fit_all_peaks(self):
        """Fit all detected peaks with Mecozzi function"""
        if not self.results_data or not self.peaks:
            messagebox.showinfo("Info", "No peaks to fit. Detect peaks first.")
            return
        
        # Clear previous fits
        self.mecozzi_fits = {}
        
        # Get line data (should be only one in this tab)
        line_id = next(iter(self.results_data))
        if line_id not in self.peaks or not self.peaks[line_id].size:
            return
            
        # Initialize fits list for this line
        self.mecozzi_fits[line_id] = []
        
        # Fit each peak
        total_fits = 0
        for peak_idx in self.peaks[line_id]:
            try:
                fit_result = fit_mecozzi_to_peak(
                    self.results_data[line_id]['distances'], 
                    self.results_data[line_id]['filtered'], 
                    peak_idx
                )
                self.mecozzi_fits[line_id].append(fit_result)
                total_fits += 1
            except Exception as e:
                print(f"Error fitting peak at index {peak_idx}: {str(e)}")
                
        # Update display
        self.update_chromatogram_display()
        
        # Update status
        self.app.set_status(f"Fitted {total_fits} peaks")
    
    def integrate_fitted_peaks(self):
        """Integrate areas under Mecozzi fitted peaks"""
        if not self.results_data or not self.mecozzi_fits:
            messagebox.showinfo("Info", "No fitted peaks to integrate. Fit peaks first.")
            return
        
        # Show the areas in the result text
        self.result_text.insert(tk.END, "\nFitted Peak Areas:\n")
        self.result_text.insert(tk.END, "------------------\n")
        
        # Process each line (should be only one in this tab)
        for line_id, fit_list in self.mecozzi_fits.items():
            if not fit_list:
                continue
                
            for j, fit_data in enumerate(fit_list):
                area = fit_data['area']
                center = fit_data['params'][1]
                self.result_text.insert(tk.END, f"  Fit {j+1} (x={center:.1f}): {area:.2f}\n")
            
        self.app.set_status("Integrated fitted peaks")
    
    def save_data(self):
        """Save data to CSV"""
        if not self.results_data:
            messagebox.showinfo("Info", "No data to save")
            return
            
        # Open save dialog
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
            title="Save Data"
        )
        
        if not file_path:
            return
            
        try:
            # Create a DataFrame
            data_dict = {}
            line_id = next(iter(self.results_data))
            data = self.results_data[line_id]
            
            # Distance and intensities
            data_dict['Distance'] = data['distances']
            data_dict['Raw_Intensity'] = data['raw_intensities']
            data_dict['Filtered_Intensity'] = data['filtered']
            
            # Add peak information
            if line_id in self.peaks:
                peak_indices = self.peaks[line_id]
                peak_series = np.zeros_like(data['distances'])
                peak_series[peak_indices] = data['filtered'][peak_indices]
                data_dict['Peaks'] = peak_series
                
                # Add peak positions and heights as separate columns
                peak_x = data['distances'][peak_indices]
                peak_y = data['filtered'][peak_indices]
                
                for i, (x, y) in enumerate(zip(peak_x, peak_y)):
                    data_dict[f'Peak_{i+1}_Position'] = x
                    data_dict[f'Peak_{i+1}_Height'] = y
            
            # Add integration information with separate columns for each integration
            if line_id in self.integrations:
                for i, (start_idx, end_idx) in enumerate(self.integrations[line_id]):
                    # Create an integration mask
                    integration_series = np.zeros_like(data['distances'])
                    integration_series[start_idx:end_idx] = 1
                    data_dict[f'Integration_{i+1}'] = integration_series
                    
                    # Add integration boundaries
                    data_dict[f'Integration_{i+1}_Start'] = data['distances'][start_idx]
                    data_dict[f'Integration_{i+1}_End'] = data['distances'][end_idx]
                    
                    # Add integration area
                    x_range = data['distances'][start_idx:end_idx]
                    y_range = data['filtered'][start_idx:end_idx]
                    baseline = np.linspace(data['filtered'][start_idx], data['filtered'][end_idx], len(x_range))
                    area = calculate_area(y_range - baseline, x_range)
                    data_dict[f'Integration_{i+1}_Area'] = area
            
            # Add Mecozzi fits
            if line_id in self.mecozzi_fits:
                for i, fit_data in enumerate(self.mecozzi_fits[line_id]):
                    # Resample fit to match original distances
                    fit_y = mecozzi_a(data['distances'], *fit_data['params'])
                    data_dict[f'Fit_{i+1}'] = fit_y
                    
                    # Add fit parameters
                    h, c, w, a = fit_data['params']
                    data_dict[f'Fit_{i+1}_Height'] = h
                    data_dict[f'Fit_{i+1}_Center'] = c
                    data_dict[f'Fit_{i+1}_HWHM'] = w
                    data_dict[f'Fit_{i+1}_Asymmetry'] = a
                    data_dict[f'Fit_{i+1}_Area'] = fit_data['area']
            
            # Create and save DataFrame
            df = pd.DataFrame(data_dict)
            df.to_csv(file_path, index=False)
            
            # Update status
            self.app.set_status(f"Data saved to {os.path.basename(file_path)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save data: {str(e)}")
            traceback.print_exc()
    
    def open_data(self):
        """Open previously saved data"""
        # Open file dialog
        file_path = filedialog.askopenfilename(
            defaultextension=".csv",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
            title="Open Data"
        )
        
        if not file_path:
            return
            
        try:
            # Read the CSV
            df = pd.read_csv(file_path)
            
            # Check if it has the expected format
            if 'Distance' not in df.columns or 'Filtered_Intensity' not in df.columns:
                messagebox.showerror("Error", "Invalid file format. Missing required columns.")
                return
            
            # Reset data
            line_id = generate_unique_id()
            self.results_data = {
                line_id: {
                    'distances': df['Distance'].values,
                    'raw_intensities': df['Raw_Intensity'].values if 'Raw_Intensity' in df.columns else df['Filtered_Intensity'].values,
                    'filtered': df['Filtered_Intensity'].values,
                    'color': self.line_color
                }
            }
            
            # Reset peaks, integrations, and fits
            self.peaks = {}
            self.integrations = {}
            self.mecozzi_fits = {}
            
            # Load peak data
            if 'Peaks' in df.columns:
                peak_indices = np.where(df['Peaks'] > 0)[0]
                if peak_indices.size:
                    self.peaks[line_id] = peak_indices
            
            # Load integration data
            integration_cols = [col for col in df.columns if col.startswith('Integration_') and col.endswith('_Start')]
            for col in integration_cols:
                idx = col.split('_')[1]  # Get the integration number
                
                # Check if we have the corresponding end column
                end_col = f'Integration_{idx}_End'
                if end_col in df.columns:
                    # Find the indices
                    start_point = df[col].iloc[0]
                    end_point = df[end_col].iloc[0]
                    
                    # Convert points to indices
                    start_idx = np.argmin(np.abs(df['Distance'].values - start_point))
                    end_idx = np.argmin(np.abs(df['Distance'].values - end_point))
                    
                    # Add the integration
                    if line_id not in self.integrations:
                        self.integrations[line_id] = []
                    self.integrations[line_id].append((start_idx, end_idx))
            
            # Load fit data
            fit_cols = [col for col in df.columns if col.startswith('Fit_') and col.endswith('_Height')]
            for col in fit_cols:
                idx = col.split('_')[1]  # Get the fit number
                
                # Check if we have all parameters
                param_cols = [
                    f'Fit_{idx}_Height',
                    f'Fit_{idx}_Center',
                    f'Fit_{idx}_HWHM',
                    f'Fit_{idx}_Asymmetry'
                ]
                
                if all(pc in df.columns for pc in param_cols):
                    # Get parameters
                    h = df[f'Fit_{idx}_Height'].iloc[0]
                    c = df[f'Fit_{idx}_Center'].iloc[0]
                    w = df[f'Fit_{idx}_HWHM'].iloc[0]
                    a = df[f'Fit_{idx}_Asymmetry'].iloc[0]
                    
                    # Get area if available
                    area_col = f'Fit_{idx}_Area'
                    if area_col in df.columns:
                        area = df[area_col].iloc[0]
                    else:
                        # Calculate area
                        x_fit = np.linspace(c - 5*w, c + 5*w, 500)
                        y_fit = mecozzi_a(x_fit, h, c, w, a)
                        area = calculate_area(y_fit, x_fit)
                    
                    # Create fit data
                    x_fit = np.linspace(c - 5*w, c + 5*w, 500)
                    y_fit = mecozzi_a(x_fit, h, c, w, a)
                    
                    # Add the fit
                    if line_id not in self.mecozzi_fits:
                        self.mecozzi_fits[line_id] = []
                    
                    self.mecozzi_fits[line_id].append({
                        'x_fit': x_fit,
                        'y_fit': y_fit,
                        'params': [h, c, w, a],
                        'area': area
                    })
            
            # Update display
            self.update_chromatogram_display()
            
            # Set file path
            self.file_path = file_path
            
            # Update status
            self.app.set_status(f"Data loaded from {os.path.basename(file_path)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open data: {str(e)}")
            traceback.print_exc()