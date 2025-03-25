# Chromatogram Analyzer

A Python application for analyzing TLC (Thin Layer Chromatography) images and extracting quantitative data. The application features a customizable theme system with both light and dark themes.

## Features

- Load and process chromatogram images
- Draw multiple profile lines for analysis
- Extract intensity profiles from images
- Apply filters for signal processing
- Detect peaks in chromatograms
- Integrate peaks automatically or manually
- Fit peaks with Mecozzi asymmetric exponential function
- Save and load analysis data
- Customizable UI with light and dark themes

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/chromatogram-analyzer.git
   cd chromatogram-analyzer
   ```

2. Run the launcher script, which will check for and install required dependencies:
   ```
   python launcher.py
   ```

## Usage

1. Run the application using the launcher script:
   ```
   python launcher.py
   ```

2. Load an image using the "Open Image" button
3. Add profile lines by clicking "New Line" and then clicking points on the image
4. Extract profiles using "Extract & Analyze"
5. Use the tools in the Analysis tab to:
   - Apply filters to smooth the data
   - Detect peaks 
   - Integrate peaks
   - Fit peaks with Mecozzi function
6. Save your results using "Save Data"

## Requirements

- Python 3.6 or higher
- NumPy
- Matplotlib
- OpenCV-Python
- SciPy
- Pandas

## Project Structure

```
chromatogram-analyzer/
├── launcher.py              # Entry point script
├── src/                     # Source code directory
│   ├── __init__.py          # Package initialization
│   ├── app.py               # Main application class
│   ├── chromatogram_tab.py  # Tab implementation
│   ├── comparison_tab.py    # Comparison tab implementation
│   ├── image_tab.py         # Image tab implementation
│   ├── image_processing.py  # Image processing functions
│   ├── peak_analysis.py     # Peak detection functions
│   ├── integration.py       # Integration functionality
│   ├── fitting.py           # Curve fitting functions
│   ├── themes.py            # Theme management
│   └── utils.py             # Utility functions
├── resources/               # Resources directory
│   ├── icon.ico             # Application icon
│   └── config.json          # Configuration file (theme settings)
├── .gitignore               # Git ignore file
└── logs/                    # Log files directory
```

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
