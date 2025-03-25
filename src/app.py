"""
Main application module for the Chromatogram Analyzer.

This module contains the main application class and entry point.
"""

import tkinter as tk
from tkinter import messagebox
import os
import traceback
import sys
import time
import json
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledFrame
from src.utils import set_tufte_style, create_icon_file
from src.themes import AVAILABLE_THEMES, DEFAULT_THEME, get_theme_style, apply_theme_to_matplotlib
from src.chromatogram_tab import ChromatogramTab
from src.image_tab import ImageTab
from src.comparison_tab import ComparisonTab

class TufteChromatogramApp(ttk.Window):
    """
    Main application class for the Chromatogram Analyzer.
    
    This class manages the application window, tabs, and global UI elements.
    """
    def __init__(self, theme=None):
        """Initialize the application
        
        Args:
            theme (str, optional): Theme name to use. Defaults to None, which will use saved theme or default.
        """
        # Load saved theme or use default
        self.theme = self._load_theme() if theme is None else theme
        
        # Initialize with the selected theme
        super().__init__(themename=self.theme)
        
        # Apply theme style to matplotlib
        theme_style = get_theme_style(self.theme)
        apply_theme_to_matplotlib(theme_style)
        
        # Set up Tufte style for plots (with theme-specific modifications)
        set_tufte_style()
        
        # Application settings
        self.title("Chromatogram Analyzer")
        self.geometry("1200x800")
        
        # Add application icon
        try:
            # Create the resources directory if it doesn't exist
            os.makedirs("resources", exist_ok=True)
            
            # Create an icon file if it doesn't exist
            icon_path = os.path.join("resources", "icon.ico")
            if not os.path.exists(icon_path):
                create_icon_file(icon_path)
            
            # Ensure the icon file exists before setting it
            if os.path.exists(icon_path):
                # Set the icon
                self.iconbitmap(icon_path)
            else:
                print("Warning: Icon file not found at", icon_path)
        except Exception as e:
            print(f"Error setting application icon: {e}")  # Log the error for debugging
        
        # Track tabs
        self.tab_counter = 0
        self.tabs = {}
        self.image_tab = None
        self.comparison_tab = None
        
        # Create main frame
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create toolbar at the top
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=5)
        
        # New tab button
        new_chromatogram_btn = ttk.Button(toolbar, text="New Chromatogram Tab", 
                                         bootstyle="success-outline",
                                         command=self.create_new_chromatogram_tab)
        new_chromatogram_btn.pack(side=tk.LEFT, padx=5, pady=3)
        
        # Comparison tab button
        comparison_btn = ttk.Button(toolbar, text="Comparison Tab", 
                                   bootstyle="info-outline",
                                   command=self.create_comparison_tab)
        comparison_btn.pack(side=tk.LEFT, padx=5, pady=3)
        
        # Theme selector
        theme_frame = ttk.Frame(toolbar)
        theme_frame.pack(side=tk.RIGHT, padx=5, pady=3)
        
        ttk.Label(theme_frame, text="Theme:").pack(side=tk.LEFT, padx=(5, 0))
        
        # Create theme dropdown
        self.theme_var = tk.StringVar(value=self.theme)
        theme_dropdown = ttk.Combobox(theme_frame, textvariable=self.theme_var, 
                                     values=list(AVAILABLE_THEMES.keys()),
                                     width=10, state="readonly")
        theme_dropdown.pack(side=tk.LEFT, padx=5)
        theme_dropdown.bind("<<ComboboxSelected>>", self._on_theme_change)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Enable tab closing
        self.notebook.enable_traversal()
        self.notebook.bind("<ButtonPress-3>", self.on_tab_right_click)
        
        # Status bar
        self.status_bar = ttk.Label(self, text="Ready", bootstyle="info", anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)
        
        # Create image tab (always present)
        self.create_image_tab()
    
    def create_image_tab(self):
        """
        Create the image tab for TLC analysis.
        """
        image_tab = ImageTab(self.notebook, self)
        self.notebook.add(image_tab, text="Image Analysis")
        
        # Store the image tab for reference
        self.image_tab = image_tab
        
        # Select the image tab
        self.notebook.select(image_tab)
    
    def create_new_chromatogram_tab(self, image=None, profile_points=None, line_color=None):
        """
        Create a new chromatogram analysis tab.
        
        Args:
            image (ndarray, optional): Image data
            profile_points (list, optional): List of points for profile extraction
            line_color (str, optional): Color for the profile line
            
        Returns:
            str: The ID of the new tab
        """
        self.tab_counter += 1
        tab_id = str(self.tab_counter)
        
        # Create tab
        tab = ChromatogramTab(self.notebook, self, tab_id)
        self.notebook.add(tab, text=f"Chromatogram {tab_id}")
        
        # Select the new tab
        self.notebook.select(tab)
        
        # Store in dictionary
        self.tabs[tab_id] = tab
        
        # If image and profile points are provided, set them
        if image is not None and profile_points is not None:
            tab.set_image_data(image.copy(), profile_points, line_color)
            
            # Extract profile and show the chromatogram
            tab.extract_and_analyze()
        
        return tab_id
    
    def create_comparison_tab(self):
        """
        Create or show the comparison tab.
        """
        if self.comparison_tab is None:
            # Create a new comparison tab
            comparison_tab = ComparisonTab(self.notebook, self)
            self.notebook.add(comparison_tab, text="Comparison")
            
            # Store for reference
            self.comparison_tab = comparison_tab
        
        # Select the comparison tab
        self.notebook.select(self.comparison_tab)
        
        # Update the comparison tab with current chromatograms
        self.comparison_tab.update_comparison_display(self.tabs)
    
    def on_tab_right_click(self, event):
        """
        Show context menu on tab right click.
        
        Args:
            event: The event object containing mouse coordinates
        """
        # Get tab index
        tab_idx = self.notebook.index(f"@{event.x},{event.y}")
        
        if tab_idx < 0:
            return
            
        # Create context menu
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Close", command=lambda: self.close_tab(tab_idx))
        
        # Show menu at mouse position
        menu.post(event.x_root, event.y_root)
    
    def close_tab(self, tab_idx):
        """
        Close the specified tab.
        
        Args:
            tab_idx (int): Index of the tab to close
        """
        # Find tab ID from the index
        tab = self.notebook.winfo_children()[tab_idx]
        
        # Don't close the image tab
        if tab == self.image_tab:
            messagebox.showinfo("Info", "Cannot close the Image Analysis tab")
            return
        
        # Check if it's the comparison tab
        if tab == self.comparison_tab:
            self.notebook.forget(tab_idx)
            self.comparison_tab = None
            return
        
        # Find the tab in our dictionary
        tab_id = None
        for tid, t in self.tabs.items():
            if t == tab:
                tab_id = tid
                break
                
        if tab_id:
            # Remove from notebook
            self.notebook.forget(tab_idx)
            
            # Remove from dictionary
            del self.tabs[tab_id]
    
    def set_tab_title(self, tab_id, title):
        """
        Set the title of a tab.
        
        Args:
            tab_id (str): ID of the tab
            title (str): New title for the tab
        """
        if tab_id in self.tabs:
            tab = self.tabs[tab_id]
            tab_idx = self.notebook.index(tab)
            
            if tab_idx >= 0:
                self.notebook.tab(tab_idx, text=title)
    
    def set_status(self, message):
        """
        Update the status bar.
        
        Args:
            message (str): Status message to display
        """
        self.status_bar.config(text=message)

    def _on_theme_change(self, event):
        """Handle theme change event
        
        Args:
            event: The event object
        """
        new_theme = self.theme_var.get()
        if new_theme != self.theme:
            # Ask user if they want to restart with a warning about data loss
            restart = messagebox.askyesno("Theme Changed", 
                                        f"Theme changed to {new_theme}. The application needs to restart for the change to take effect.\n\nWARNING: Any unsaved data will be lost. Do you want to restart now?")
            
            # Save the theme regardless of restart choice
            self.theme = new_theme
            self._save_theme(new_theme)
            
            if restart:
                # Destroy the current window
                self.destroy()
                
                # Restart the application
                self._restart_application()
    
    def _save_theme(self, theme_name):
        """Save theme preference to a config file
        
        Args:
            theme_name (str): Name of the theme to save
        """
        config = {"theme": theme_name}
        try:
            os.makedirs("resources", exist_ok=True)
            with open(os.path.join("resources", "config.json"), "w") as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Error saving theme: {e}")
    
    def _load_theme(self):
        """Load theme preference from config file
        
        Returns:
            str: Theme name
        """
        try:
            config_path = os.path.join("resources", "config.json")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)
                return config.get("theme", DEFAULT_THEME)
        except Exception as e:
            print(f"Error loading theme: {e}")
        return DEFAULT_THEME
        
    def _restart_application(self):
        """Restart the application with the new theme
        
        This method will restart the application by executing the launcher.py script
        """
        try:
            # Get the current working directory
            cwd = os.getcwd()
            
            # Construct the path to the python executable in the virtual environment
            venv_path = os.path.join(cwd, 'TLC')
            python_executable = os.path.join(venv_path, 'Scripts', 'python.exe')
            
            # Check if the python executable exists
            if not os.path.exists(python_executable):
                # Fall back to system python if venv python doesn't exist
                python_executable = sys.executable
            
            # Start a new process to run the launcher
            subprocess.Popen([python_executable, os.path.join(cwd, 'launcher.py')])
        except Exception as e:
            messagebox.showerror("Restart Error", f"Failed to restart the application: {e}\n\nPlease restart manually.")
        finally:
            # Exit the current instance
            sys.exit(0)

def run_application():
    """Run the application"""
    app = TufteChromatogramApp()
    app.mainloop()

if __name__ == "__main__":
    run_application()
