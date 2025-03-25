"""
Utility functions and constants for the Chromatogram Analyzer.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy import integrate
import matplotlib.figure as mfigure
from matplotlib import rcParams
import os
import uuid

# Define color palettes for Tufte-inspired style (both light and dark)
COLORS = {
    # Light theme colors
    'light': {
        'primary': '#4D4D4D',  # Dark gray
        'secondary': ['#8C564B', '#1F77B4', '#2CA02C', '#9467BD', '#E377C2'],  # Muted colors
        'accent': '#D62728',  # Red for peaks
        'fit': '#E69F00',  # Orange for fits (more muted)
        'background': '#FFFFFF',  # Pure white
        'text': '#262626',  # Darker text for better contrast
        'axis': '#4D4D4D',  # Dark gray for axis
        'grid': '#E6E6E6',  # Light gray for grid lines
        'highlight': '#56B4E9',  # Light blue for highlights
        'selection': '#F0E442',  # Yellow for selections
        'annotation': '#F0E442',  # Yellow for annotations
    },
    
    # Dark theme colors
    'dark': {
        'primary': '#E0E0E0',  # Light gray
        'secondary': ['#FF9E9E', '#9ECAE1', '#A1D99B', '#C5B0D5', '#F7B6D2'],  # Brighter versions
        'accent': '#FF5252',  # Brighter red for peaks
        'fit': '#FFB74D',  # Brighter orange for fits
        'background': '#2B3E50',  # Dark blue background
        'text': '#FFFFFF',  # White text
        'axis': '#E0E0E0',  # Light gray for axis
        'grid': '#4D5D6C',  # Darker grid lines
        'highlight': '#29B6F6',  # Brighter blue for highlights
        'selection': '#FFEE58',  # Brighter yellow for selections
        'annotation': '#FFEE58',  # Brighter yellow for annotations
    }
}

# Set up Tufte-inspired matplotlib style
def set_tufte_style():
    """
    Set up a Tufte-inspired style for matplotlib plots.
    
    This style is minimalist and focuses on the data rather than chartjunk.
    It uses muted colors, removes unnecessary grid lines and boxes,
    and emphasizes the data.
    
    Note: The base colors are now managed by the theme system in themes.py,
    but this function still applies the Tufte-specific styling elements.
    """
    # Font settings
    rcParams['font.family'] = 'serif'
    rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif', 'Serif']
    rcParams['font.size'] = 9
    rcParams['axes.labelsize'] = 10
    rcParams['axes.titlesize'] = 11
    
    # Remove chart junk
    rcParams['axes.spines.top'] = False
    rcParams['axes.spines.right'] = False
    
    # Optional light grid for better readability
    rcParams['axes.grid'] = True
    rcParams['grid.alpha'] = 0.3
    rcParams['grid.linewidth'] = 0.5
    
    # Figure settings
    rcParams['figure.figsize'] = (6, 3.5)  # Slightly taller for better data-ink ratio
    rcParams['figure.dpi'] = 100
    
    # Line settings
    rcParams['lines.linewidth'] = 1.5
    rcParams['lines.markersize'] = 5
    
    # Tick settings
    rcParams['xtick.major.width'] = 0.5
    rcParams['ytick.major.width'] = 0.5
    rcParams['xtick.direction'] = 'out'
    rcParams['ytick.direction'] = 'out'
    
    # Legend settings
    rcParams['legend.frameon'] = False
    rcParams['legend.fontsize'] = 8

def calculate_area(y_values, x_values):
    """
    Calculate area using trapezoid integration.
    
    Args:
        y_values (ndarray): Y values (intensity)
        x_values (ndarray): X values (distance)
        
    Returns:
        float: Integrated area
    """
    return integrate.trapezoid(y_values, x_values)

def generate_unique_id():
    """
    Generate a unique ID for tracking objects.
    
    Returns:
        str: A unique ID string
    """
    return str(uuid.uuid4())

def get_color_for_line(index, theme_style='light'):
    """
    Get a color for a line based on its index and theme style.
    
    Args:
        index (int): Line index
        theme_style (str): 'light' or 'dark'
        
    Returns:
        str: Color code
    """
    if index == 0:
        return COLORS[theme_style]['primary']
    else:
        return COLORS[theme_style]['secondary'][(index - 1) % len(COLORS[theme_style]['secondary'])]

def create_icon_file(path):
    """
    Create a simple icon file for the application.
    
    Args:
        path (str): Path to save icon
    """
    try:
        # Create a small matplotlib figure for the icon
        fig = plt.figure(figsize=(1, 1), dpi=32)
        ax = fig.add_subplot(111)
        
        # Create a sample chromatogram
        x = np.linspace(0, 10, 100)
        y = np.zeros_like(x)
        
        # Add some peaks
        for center, height, width in [(2, 5, 0.5), (4, 8, 0.4), (7, 6, 0.6)]:
            y += height * np.exp(-((x - center) / width) ** 2)
        
        # Plot chromatogram
        ax.plot(x, y, 'k-', linewidth=2)
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')
        
        # Make the background transparent
        fig.patch.set_alpha(0)
        ax.patch.set_alpha(0)
        
        # Save as PNG
        temp_png = os.path.join(os.path.dirname(path), "temp_icon.png")
        fig.savefig(temp_png, transparent=True, bbox_inches='tight', pad_inches=0)
        plt.close(fig)
        
        # Convert to ICO using PIL if available
        try:
            from PIL import Image
            img = Image.open(temp_png)
            img.save(path)
            os.remove(temp_png)
        except ImportError:
            # If PIL is not available, just rename the png
            os.rename(temp_png, path)
    except Exception:
        # Ignore any errors in icon creation
        pass
