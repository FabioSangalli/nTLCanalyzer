"""
Comparison tab module for the TLC analyzer application.

This module implements the ComparisonTab class which allows the 
comparison of multiple chromatograms from different analysis tabs.
"""

import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import os

class ComparisonTab(ttk.Frame):
    """
    Class for comparing multiple chromatograms.
    
    This class allows the visualization of multiple chromatograms from 
    different tabs in a single plot for easy comparison.
    """
    def __init__(self, parent, app):
        """
        Initialize a new comparison tab.
        
        Args:
            parent: Parent widget
            app: Main application instance
        """
        super().__init__(parent)
        
        self.app = app
        
        # Create a paned window
        self.paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left panel for chromatogram
        self.chrom_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.chrom_frame, weight=3)
        
        # Right panel for controls
        control_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(control_frame, weight=1)
        
        # Create chromatogram figure
        self.chrom_fig, self.chrom_ax = plt.subplots(figsize=(8, 5))
        self.chrom_ax.set_title("Chromatogram Comparison")
        self.chrom_ax.set_xlabel("Distance (pixels)")
        self.chrom_ax.set_ylabel("Intensity")
        
        self.chrom_canvas = FigureCanvasTkAgg(self.chrom_fig, master=self.chrom_frame)
        self.chrom_canvas.draw()
        self.chrom_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add toolbar
        chrom_toolbar = NavigationToolbar2Tk(self.chrom_canvas, self.chrom_frame)
        chrom_toolbar.update()
        
        # Controls for chromatogram selection
        select_frame = ttk.LabelFrame(control_frame, text="Select Chromatograms")
        select_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a scrolled frame for checkboxes
        checkbox_canvas = tk.Canvas(select_frame)
        scrollbar = ttk.Scrollbar(select_frame, orient="vertical", command=checkbox_canvas.yview)
        
        self.checkbox_frame = ttk.Frame(checkbox_canvas)
        
        self.checkbox_frame.bind(
            "<Configure>",
            lambda e: checkbox_canvas.configure(scrollregion=checkbox_canvas.bbox("all"))
        )
        
        checkbox_canvas.create_window((0, 0), window=self.checkbox_frame, anchor="nw")
        checkbox_canvas.configure(yscrollcommand=scrollbar.set)
        
        checkbox_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Button to refresh the comparison
        refresh_btn = ttk.Button(control_frame, text="Refresh Comparison", 
                               command=lambda: self.update_comparison_display(self.app.tabs))
        refresh_btn.pack(fill=tk.X, padx=10, pady=10)
        
        # Button to save comparison as image
        save_btn = ttk.Button(control_frame, text="Save Comparison", 
                            command=self.save_comparison)
        save_btn.pack(fill=tk.X, padx=10, pady=5)
        
        # Button to save comparison data
        save_data_btn = ttk.Button(control_frame, text="Save Comparison Data", 
                                 command=self.save_comparison_data)
        save_data_btn.pack(fill=tk.X, padx=10, pady=5)
        
        # Dictionary to store checkbox variables
        self.chromatogram_vars = {}
    
    def update_comparison_display(self, tabs):
        """
        Update the comparison display with chromatograms from the specified tabs.
        
        Args:
            tabs (dict): Dictionary of tab IDs to tab objects
        """
        # Clear checkboxes
        for widget in self.checkbox_frame.winfo_children():
            widget.destroy()
            
        self.chromatogram_vars = {}
        
        # Add checkboxes for each chromatogram
        row = 0
        for tab_id, tab in tabs.items():
            if hasattr(tab, 'results_data') and tab.results_data:
                for line_id, data in tab.results_data.items():
                    var = tk.BooleanVar(value=True)
                    self.chromatogram_vars[(tab_id, line_id)] = var
                    
                    # Create checkbox with descriptive label
                    if hasattr(tab, 'file_path') and tab.file_path:
                        label = f"Tab {tab_id}: {os.path.basename(tab.file_path)}"
                    else:
                        label = f"Tab {tab_id}: Line {row+1}"
                        
                    cb = ttk.Checkbutton(self.checkbox_frame, text=label, variable=var,
                                       command=self.refresh_plot)
                    cb.grid(row=row, column=0, sticky="w", padx=5, pady=2)
                    row += 1
        
        # Refresh the plot
        self.refresh_plot()
    
    def refresh_plot(self):
        """Refresh the comparison plot based on selected chromatograms."""
        # Clear the plot
        self.chrom_ax.clear()
        
        # Set up the axes
        self.chrom_ax.set_title("Chromatogram Comparison")
        self.chrom_ax.set_xlabel("Distance (pixels)")
        self.chrom_ax.set_ylabel("Intensity")
        
        # Plot each selected chromatogram
        has_data = False
        
        for (tab_id, line_id), var in self.chromatogram_vars.items():
            if var.get() and tab_id in self.app.tabs:
                tab = self.app.tabs[tab_id]
                
                if line_id in tab.results_data:
                    has_data = True
                    data = tab.results_data[line_id]
                    
                    distances = data['distances']
                    filtered = data['filtered']
                    color = data['color']
                    
                    # Get line label
                    if hasattr(tab, 'file_path') and tab.file_path:
                        label = f"{os.path.basename(tab.file_path)} - Tab {tab_id}"
                    else:
                        label = f"Tab {tab_id}"
                        
                    # Plot the chromatogram
                    self.chrom_ax.plot(distances, filtered, color=color, linewidth=1.5, 
                                      label=label)
                    
                    # Plot peaks if available
                    if hasattr(tab, 'peaks') and line_id in tab.peaks:
                        peak_indices = tab.peaks[line_id]
                        peak_x = distances[peak_indices]
                        peak_y = filtered[peak_indices]
                        
                        self.chrom_ax.plot(peak_x, peak_y, 'o', color='#D62728', markersize=4)
        
        # Add legend if we have data
        if has_data:
            self.chrom_ax.legend(loc='best')
        else:
            self.chrom_ax.text(0.5, 0.5, "No chromatograms selected", 
                              ha='center', va='center', transform=self.chrom_ax.transAxes)
        
        # Redraw
        self.chrom_fig.tight_layout()
        self.chrom_canvas.draw()
    
    def save_comparison(self):
        """Save the comparison plot as an image."""
        # Open save dialog
        file_path = tk.filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=(
                ("PNG Image", "*.png"),
                ("JPEG Image", "*.jpg"),
                ("PDF Document", "*.pdf"),
                ("SVG Image", "*.svg"),
                ("All files", "*.*")
            ),
            title="Save Comparison Plot"
        )
        
        if not file_path:
            return
            
        try:
            # Apply tight layout before saving
            self.chrom_fig.tight_layout()
            
            # Save figure
            self.chrom_fig.savefig(file_path, dpi=300, bbox_inches='tight')
            
            # Update status
            self.app.set_status(f"Comparison plot saved as {os.path.basename(file_path)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save plot: {str(e)}")
    
    def save_comparison_data(self):
        """Save the comparison data to CSV."""
        # Open save dialog
        file_path = tk.filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
            title="Save Comparison Data"
        )
        
        if not file_path:
            return
            
        try:
            # Create a DataFrame with a common distance column
            data_dict = {}
            max_length = 0
            
            # Find the maximum length for padding
            for (tab_id, line_id), var in self.chromatogram_vars.items():
                if var.get() and tab_id in self.app.tabs:
                    tab = self.app.tabs[tab_id]
                    
                    if line_id in tab.results_data:
                        length = len(tab.results_data[line_id]['distances'])
                        max_length = max(max_length, length)
            
            # Create padded arrays
            for (tab_id, line_id), var in self.chromatogram_vars.items():
                if var.get() and tab_id in self.app.tabs:
                    tab = self.app.tabs[tab_id]
                    
                    if line_id in tab.results_data:
                        data = tab.results_data[line_id]
                        
                        # Get column labels
                        if hasattr(tab, 'file_path') and tab.file_path:
                            label = f"{os.path.basename(tab.file_path)}_Tab{tab_id}"
                        else:
                            label = f"Tab{tab_id}"
                        
                        # Add distance column if not added yet
                        if 'Distance' not in data_dict:
                            # Pad to max length
                            if len(data['distances']) < max_length:
                                padded = np.pad(
                                    data['distances'], 
                                    (0, max_length - len(data['distances'])),
                                    'constant', 
                                    constant_values=np.nan
                                )
                                data_dict['Distance'] = padded
                            else:
                                data_dict['Distance'] = data['distances']
                        
                        # Add intensity data
                        # Pad to max length
                        if len(data['filtered']) < max_length:
                            padded = np.pad(
                                data['filtered'], 
                                (0, max_length - len(data['filtered'])),
                                'constant', 
                                constant_values=np.nan
                            )
                            data_dict[f'Intensity_{label}'] = padded
                        else:
                            data_dict[f'Intensity_{label}'] = data['filtered']
                        
                        # Add peak data if available
                        if hasattr(tab, 'peaks') and line_id in tab.peaks:
                            peak_array = np.zeros(max_length)
                            peak_array[:] = np.nan
                            
                            peak_indices = tab.peaks[line_id]
                            for idx in peak_indices:
                                if idx < max_length:
                                    peak_array[idx] = data['filtered'][idx]
                                    
                            data_dict[f'Peaks_{label}'] = peak_array
            
            # Create and save DataFrame
            if data_dict:
                df = pd.DataFrame(data_dict)
                df.to_csv(file_path, index=False)
                
                # Update status
                self.app.set_status(f"Comparison data saved to {os.path.basename(file_path)}")
            else:
                messagebox.showinfo("Info", "No data to save")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save data: {str(e)}")
            traceback.print_exc()
