"""Theme management for the Chromatogram Analyzer application.

This module provides theme definitions and utilities for managing the application's appearance.
"""

import ttkbootstrap as ttk

# Available themes in ttkbootstrap
AVAILABLE_THEMES = {
    # Light themes
    'litera': 'Light theme with clean, modern appearance',
    'cosmo': 'Clean, modern light theme',
    'flatly': 'Flat design light theme',
    'journal': 'Crisp, clean light theme',
    'lumen': 'Light theme with subtle gradients',
    'minty': 'Fresh, light mint-colored theme',
    'pulse': 'Light theme with vibrant colors',
    'sandstone': 'Light theme with a sandstone texture',
    'united': 'Light theme with orange accents',
    'yeti': 'Light theme with a bluish tint',
    
    # Dark themes
    'darkly': 'Dark theme with blue accents',
    'cyborg': 'High contrast dark theme',
    'vapor': 'Dark theme with neon accents',
    'solar': 'Dark theme with amber accents',
    'superhero': 'Dark blue theme',
}

# Default theme settings
DEFAULT_THEME = 'darkly'  # Default to dark theme

# Theme categories
LIGHT_THEMES = ['litera', 'cosmo', 'flatly', 'journal', 'lumen', 'minty', 'pulse', 'sandstone', 'united', 'yeti']
DARK_THEMES = ['darkly', 'cyborg', 'vapor', 'solar', 'superhero']

def get_theme_style(theme_name):
    """Get the appropriate style for a theme (light or dark).
    
    Args:
        theme_name (str): Name of the theme
        
    Returns:
        str: 'light' or 'dark'
    """
    if theme_name in DARK_THEMES:
        return 'dark'
    return 'light'

def apply_theme_to_matplotlib(theme_style):
    """Apply theme style to matplotlib plots.
    
    Args:
        theme_style (str): 'light' or 'dark'
    """
    from matplotlib import rcParams
    
    if theme_style == 'dark':
        # Dark theme settings for matplotlib
        rcParams['figure.facecolor'] = '#2B3E50'  # Dark blue background
        rcParams['axes.facecolor'] = '#2B3E50'
        rcParams['savefig.facecolor'] = '#2B3E50'
        rcParams['text.color'] = '#FFFFFF'  # White text
        rcParams['axes.labelcolor'] = '#FFFFFF'
        rcParams['axes.titlecolor'] = '#FFFFFF'
        rcParams['xtick.color'] = '#FFFFFF'
        rcParams['ytick.color'] = '#FFFFFF'
        rcParams['grid.color'] = '#4D5D6C'  # Darker grid lines
    else:
        # Light theme settings for matplotlib
        rcParams['figure.facecolor'] = '#FFFFFF'  # White background
        rcParams['axes.facecolor'] = '#FFFFFF'
        rcParams['savefig.facecolor'] = '#FFFFFF'
        rcParams['text.color'] = '#262626'  # Dark text
        rcParams['axes.labelcolor'] = '#4D4D4D'
        rcParams['axes.titlecolor'] = '#262626'
        rcParams['xtick.color'] = '#4D4D4D'
        rcParams['ytick.color'] = '#4D4D4D'
        rcParams['grid.color'] = '#E6E6E6'  # Light grid lines