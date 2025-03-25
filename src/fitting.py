"""
Peak fitting functions for chromatogram analysis.

This module provides functions for fitting peaks in chromatograms,
including the Mecozzi asymmetric exponential function.
"""

import numpy as np
from scipy.optimize import curve_fit
from .utils import calculate_area

def mecozzi_f(x, height, center, hwhm, asym=1.0):
    """
    Mecozzi function for peak fitting.
    
    This function implements the Mecozzi asymmetric exponential function,
    which is useful for fitting chromatographic peaks.
    
    Args:
        x (ndarray): x-values (typically distance)
        height (float): Peak height
        center (float): Peak center position
        hwhm (float): Half-width at half-maximum
        asym (float): Asymmetry parameter (1.0 for symmetric)
        
    Returns:
        ndarray: y-values of the fitted curve
    """
    try:
        term1 = (4/(asym**2) - 1)
        term2 = np.log(1 + 2*asym*(x-center)/(hwhm*(4-asym**2)))
        term3 = 2*asym*(x-center)/(hwhm*(4-asym**2))
        return height * np.exp(term1 * (term2 - term3))
    except (ZeroDivisionError, RuntimeWarning, FloatingPointError):
        return np.zeros_like(x)

def mecozzi_a(x, height, center, hwhm, asym=1.0):
    """
    Asymmetric Mecozzi function with cutoff.
    
    This is a modified version of the Mecozzi function that applies a cutoff
    to avoid instabilities in the negative tail of the function.
    
    Args:
        x (ndarray): x-values (typically distance)
        height (float): Peak height
        center (float): Peak center position
        hwhm (float): Half-width at half-maximum
        asym (float): Asymmetry parameter (1.0 for symmetric)
        
    Returns:
        ndarray: y-values of the fitted curve with cutoff applied
    """
    result = np.zeros_like(x, dtype=float)
    valid_indices = x >= (center - hwhm*(4-asym**2)/(2*asym))
    if np.any(valid_indices):
        result[valid_indices] = mecozzi_f(x[valid_indices], height, center, hwhm, asym)
    return result

def fit_mecozzi_to_peak(x_data, y_data, peak_idx):
    """
    Fit Mecozzi function to a peak in the data.
    
    Args:
        x_data (ndarray): x-values
        y_data (ndarray): y-values
        peak_idx (int): Index of the peak to fit
        
    Returns:
        dict: Fitting results containing parameters, fitted curve, and area
    """
    # Find a reasonable range around the peak
    window = 50  # points on each side
    start_idx = max(0, peak_idx - window)
    end_idx = min(len(x_data) - 1, peak_idx + window)
    
    x_segment = x_data[start_idx:end_idx]
    y_segment = y_data[start_idx:end_idx]
    
    # Initial parameter guesses
    height = y_data[peak_idx] - np.min(y_segment)
    center = x_data[peak_idx]
    hwhm = 20  # Half width at half maximum
    asym = 1.0  # Asymmetry parameter
    
    try:
        # Fit the Mecozzi function
        with np.errstate(all='ignore'):  # Suppress warnings
            popt, _ = curve_fit(mecozzi_a, x_segment, y_segment, 
                             p0=[height, center, hwhm, asym],
                             bounds=([0, x_segment[0], 0, 0.1], 
                                    [height*2, x_segment[-1], 100, 10]))
            
        # Generate fitted curve
        x_fit = np.linspace(x_segment[0], x_segment[-1], 500)
        y_fit = mecozzi_a(x_fit, *popt)
        
        # Calculate area under the fitted curve
        area = calculate_area(y_fit, x_fit)
        
        return {
            'peak_idx': peak_idx,
            'params': popt,
            'x_fit': x_fit,
            'y_fit': y_fit,
            'area': area
        }
    except Exception as e:
        raise ValueError(f"Failed to fit Mecozzi function: {str(e)}")
