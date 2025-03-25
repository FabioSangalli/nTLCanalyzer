"""
Peak analysis functions for chromatogram processing.

This module provides functions for peak detection, filtering, and analysis
of chromatogram data.
"""

import numpy as np
from scipy import signal
from scipy import ndimage
from .utils import calculate_area

def apply_savitzky_golay(data, window_size, poly_order):
    """
    Apply Savitzky-Golay filter to smooth data.
    
    Args:
        data (ndarray): Input data
        window_size (int): Window size (must be odd)
        poly_order (int): Polynomial order
        
    Returns:
        ndarray: Filtered data
    """
    # Ensure window size is odd
    if window_size % 2 == 0:
        window_size += 1
        
    # Apply filter
    if len(data) > window_size:
        return signal.savgol_filter(data, window_size, poly_order)
    else:
        return data.copy()

def apply_gaussian_smooth(data, sigma):
    """
    Apply Gaussian smoothing filter.
    
    Args:
        data (ndarray): Input data
        sigma (float): Standard deviation for Gaussian kernel
        
    Returns:
        ndarray: Smoothed data
    """
    if sigma > 0:
        return ndimage.gaussian_filter1d(data, sigma)
    else:
        return data.copy()

def detect_peaks(data, height_threshold, distance, prominence=10, width=3):
    """
    Detect peaks in data with improved sensitivity.
    
    Args:
        data (ndarray): Input data
        height_threshold (float): Relative height threshold (0-1)
        distance (int): Minimum distance between peaks
        prominence (float): Minimum prominence of peaks (default: 10)
        width (int): Minimum width of peaks in samples (default: 3)
        
    Returns:
        ndarray: Indices of detected peaks
    """
    # Data validation
    if len(data) == 0:
        return np.array([])
    
    # Adaptive parameters based on data characteristics
    data_range = np.max(data) - np.min(data)
    if data_range == 0:  # Handle flat data
        return np.array([])
    
    # Convert relative height to absolute with improved scaling
    abs_height = height_threshold * data_range + np.min(data)
    
    # Adaptive prominence based on data range
    adaptive_prominence = prominence * (data_range / 100) if data_range > 0 else prominence
    
    # Find peaks with optimized parameters
    peak_indices, properties = signal.find_peaks(
        data, 
        height=abs_height, 
        distance=distance, 
        prominence=adaptive_prominence, 
        width=width
    )
    
    return peak_indices

def auto_integrate_peaks(distances, intensities, peak_indices, width_percent, sensitivity):
    """
    Automatically integrate peaks based on height threshold.
    
    Args:
        distances (ndarray): X-values
        intensities (ndarray): Y-values
        peak_indices (ndarray): Indices of peaks to integrate
        width_percent (float): Percentage of peak height to use as width threshold
        sensitivity (float): Sensitivity for finding baseline
        
    Returns:
        list: List of tuples (start_idx, end_idx) for each integration region
    """
    integrations = []
    
    for peak_idx in peak_indices:
        peak_height = intensities[peak_idx]
        
        # Find the threshold height for this peak
        threshold = peak_height * (1 - width_percent/100.0)
        
        # Find left bound (going left from peak)
        left_idx = peak_idx
        while left_idx > 0 and intensities[left_idx] > threshold:
            left_idx -= 1
            
        # Refine left bound using sensitivity
        while left_idx > 0 and abs(intensities[left_idx] - intensities[left_idx-1]) < sensitivity * peak_height:
            left_idx -= 1
            
        # Find right bound (going right from peak)
        right_idx = peak_idx
        while right_idx < len(intensities) - 1 and intensities[right_idx] > threshold:
            right_idx += 1
            
        # Refine right bound using sensitivity
        while right_idx < len(intensities) - 1 and abs(intensities[right_idx] - intensities[right_idx+1]) < sensitivity * peak_height:
            right_idx += 1
            
        # Add some padding
        left_idx = max(0, left_idx - 3)
        right_idx = min(len(intensities) - 1, right_idx + 3)
        
        # Add the integration
        integrations.append((left_idx, right_idx))
    
    return integrations

def calculate_integration_area(distances, intensities, start_idx, end_idx):
    """
    Calculate the area of an integration region.
    
    Args:
        distances (ndarray): X-values
        intensities (ndarray): Y-values
        start_idx (int): Start index
        end_idx (int): End index
        
    Returns:
        float: Area of the integration region
    """
    # Get the x and y ranges
    x_range = distances[start_idx:end_idx]
    y_range = intensities[start_idx:end_idx]
    
    # Calculate baseline (straight line between endpoints)
    baseline = np.linspace(intensities[start_idx], intensities[end_idx], len(x_range))
    
    # Calculate area above baseline
    area = calculate_area(y_range - baseline, x_range)
    
    return area
