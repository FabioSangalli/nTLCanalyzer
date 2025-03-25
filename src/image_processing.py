"""
Image processing functions for chromatogram analysis.

This module provides functions for loading, processing, and extracting 
intensity profiles from chromatogram images.
"""

import numpy as np
import cv2
from PIL import ImageGrab, Image
import io

def load_image(file_path):
    """
    Load an image from file and convert to RGB.
    
    Args:
        file_path (str): Path to the image file
        
    Returns:
        tuple: (rgb_image, original_image) - RGB image and original image
        
    Raises:
        ValueError: If the image cannot be loaded
    """
    # Load image
    image = cv2.imread(file_path)
    if image is None:
        raise ValueError(f"Failed to read image: {file_path}")
    
    # Convert to RGB for display
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    return rgb_image, rgb_image.copy()

def load_image_from_clipboard():
    """
    Load an image from the system clipboard.
    
    Returns:
        tuple: (rgb_image, original_image) - RGB image and original image, or (None, None) if no image in clipboard
        
    Raises:
        ValueError: If the clipboard image cannot be processed
    """
    try:
        # Get image from clipboard
        clipboard_image = ImageGrab.grabclipboard()
        
        # Check if clipboard contains an image
        if clipboard_image is None or not isinstance(clipboard_image, Image.Image):
            return None, None
        
        # Convert PIL Image to numpy array (RGB format)
        rgb_image = np.array(clipboard_image.convert('RGB'))
        
        return rgb_image, rgb_image.copy()
        
    except Exception as e:
        raise ValueError(f"Failed to process clipboard image: {str(e)}")

def adjust_image(image, brightness=0, contrast=1):
    """
    Adjust brightness and contrast of an image.
    
    Args:
        image (ndarray): Input image
        brightness (float): Brightness adjustment (-1 to 1)
        contrast (float): Contrast adjustment (0.5 to 2)
        
    Returns:
        ndarray: Adjusted image
    """
    # Apply adjustments
    return cv2.convertScaleAbs(image, alpha=contrast, beta=brightness * 127)

def extract_profile(image, points, band_width):
    """
    Extract intensity profile along a line with specified band width.
    
    Args:
        image (ndarray): Input image
        points (ndarray): Array of (x, y) points defining the line
        band_width (int): Width of the band to sample perpendicular to the line
        
    Returns:
        tuple: (distances, intensities) - arrays of distance along the line and
               corresponding intensity values
    """
    # Convert points to numpy array if it's not already
    points_array = np.array(points)
    
    # Calculate path distances
    segments = np.diff(points_array, axis=0)
    segment_lengths = np.sqrt(np.sum(segments**2, axis=1))
    cumulative_dist = np.concatenate(([0], np.cumsum(segment_lengths)))
    total_dist = cumulative_dist[-1]
    
    # Create evenly spaced points along the path (optimize with fewer samples)
    num_samples = min(1000, max(500, int(total_dist / 2)))  # Adaptive sampling
    even_distances = np.linspace(0, total_dist, num_samples)
    
    # Interpolate coordinates in one step
    interp_points = np.column_stack((
        np.interp(even_distances, cumulative_dist, points_array[:, 0]),
        np.interp(even_distances, cumulative_dist, points_array[:, 1])
    ))
    
    # Sample intensities with band width
    intensities = sample_band(image, interp_points, band_width)
    
    return even_distances, intensities

def sample_band(image, points, band_width):
    """
    Sample a band of pixels perpendicular to a line.
    
    Args:
        image (ndarray): Input image
        points (ndarray): Array of (x, y) points defining the line
        band_width (int): Width of the band in pixels
        
    Returns:
        ndarray: Array of average intensity values along the line
    """
    intensities = []
    
    for i in range(len(points) - 1):
        p1 = points[i]
        p2 = points[i+1]
        
        # Vector from p1 to p2
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        
        # Perpendicular unit vector
        length = np.sqrt(dx*dx + dy*dy)
        if length > 0:
            nx = -dy / length
            ny = dx / length
            
            # Sample points perpendicular to the line
            x_center, y_center = p1[0], p1[1]
            
            # Sample band_width pixels
            values = []
            for offset in range(-band_width//2, band_width//2 + 1):
                # Calculate sample point
                x_sample = int(round(x_center + offset * nx))
                y_sample = int(round(y_center + offset * ny))
                
                # Check bounds
                if (0 <= x_sample < image.shape[1] and 
                    0 <= y_sample < image.shape[0]):
                    
                    # Get intensity (mean of RGB channels if color image)
                    if len(image.shape) == 3:
                        value = np.mean(image[y_sample, x_sample, :])
                    else:
                        value = image[y_sample, x_sample]
                    values.append(value)
            
            # Average the values
            if values:
                intensities.append(np.mean(values))
            else:
                intensities.append(0)
    
    # Ensure we have the right number of samples by interpolating
    if intensities:
        indices = np.linspace(0, len(intensities) - 1, len(points))
        intensities = np.interp(indices, np.arange(len(intensities)), intensities)
    
    return np.array(intensities)
