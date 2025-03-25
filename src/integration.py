"""
Integration functions for chromatogram analysis.

This module provides functions for integrating peaks and areas
in chromatogram data.
"""

import numpy as np
from .utils import calculate_area

def find_integration_bounds(x_data, y_data, peak_idx, width_percent, sensitivity):
    """
    Find integration bounds for a peak.
    
    Args:
        x_data (ndarray): X-values
        y_data (ndarray): Y-values
        peak_idx (int): Index of the peak
        width_percent (float): Percentage of peak height to use as width threshold
        sensitivity (float): Sensitivity for finding baseline
        
    Returns:
        tuple: (start_idx, end_idx) for integration
    """
    peak_height = y_data[peak_idx]
    
    # Find the threshold height for this peak
    threshold = peak_height * (1 - width_percent/100.0)
    
    # Find left bound (going left from peak)
    left_idx = peak_idx
    while left_idx > 0 and y_data[left_idx] > threshold:
        left_idx -= 1
        
    # Refine left bound using sensitivity
    while left_idx > 0 and abs(y_data[left_idx] - y_data[left_idx-1]) < sensitivity * peak_height:
        left_idx -= 1
        
    # Find right bound (going right from peak)
    right_idx = peak_idx
    while right_idx < len(y_data) - 1 and y_data[right_idx] > threshold:
        right_idx += 1
        
    # Refine right bound using sensitivity
    while right_idx < len(y_data) - 1 and abs(y_data[right_idx] - y_data[right_idx+1]) < sensitivity * peak_height:
        right_idx += 1
        
    # Add some padding
    left_idx = max(0, left_idx - 3)
    right_idx = min(len(y_data) - 1, right_idx + 3)
    
    return (left_idx, right_idx)

def manual_integration(x_data, y_data, start_x, end_x):
    """
    Perform manual integration between two x-values.
    
    Args:
        x_data (ndarray): X-values
        y_data (ndarray): Y-values
        start_x (float): Start x-value
        end_x (float): End x-value
        
    Returns:
        tuple: (start_idx, end_idx, area) - indices and calculated area
    """
    # Find closest indices
    start_idx = np.argmin(np.abs(x_data - start_x))
    end_idx = np.argmin(np.abs(x_data - end_x))
    
    # Ensure start is before end
    if start_idx > end_idx:
        start_idx, end_idx = end_idx, start_idx
    
    # Calculate area
    x_range = x_data[start_idx:end_idx+1]
    y_range = y_data[start_idx:end_idx+1]
    
    # Calculate baseline (straight line between start and end points)
    baseline = np.linspace(y_data[start_idx], y_data[end_idx], len(x_range))
    
    # Calculate area above baseline
    area = calculate_area(y_range - baseline, x_range)
    
    return (start_idx, end_idx, area)

def integrate_fitted_peak(fit_data):
    """
    Calculate the area under a fitted peak.
    
    Args:
        fit_data (dict): Fit data dictionary with x_fit and y_fit
        
    Returns:
        float: Area under the fitted curve
    """
    return calculate_area(fit_data['y_fit'], fit_data['x_fit'])
