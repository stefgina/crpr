# crpr ✂️
A minimal img/video cropping tool with a retro terminal aesthetic. 

## Features
- Interactive crop selection with resize handles
- Square mode (hold Shift or toggle button)
- Operation logging
- Dark terminal-style UI

## Requirements
```bash
pip install opencv-python
pip install numpy
pip install tk  # or python3-tk on Linux
```

## Running the Tool
```bash
python crpr.py
```

## Usage
1. Click [SELECT VIDEO] to choose a video file
2. In the crop window:
   - Click and drag to create selection
   - Move selection by dragging inside it
   - Resize using corner/edge handles
   - Hold Shift or enable SQUARE MODE for perfect squares
   - Press 'c' to crop
   - Press 'r' to reset selection
   - Press 'ESC' to cancel
  
Hint: Before interacting with the UI, make sure the window is in focus (click on it)

## Output
- Cropped video saved as MP4
- Operation log file created alongside output with crop details

## Supported Formats
- Input: .mp4, .avi, .mov
- Output: .mp4
