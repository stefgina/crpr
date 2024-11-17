import os
os.environ['OPENCV_VIDEOIO_MACTYPES_QUIET'] = '1'  # Suppress macOS warnings

import cv2
import tkinter as tk
from tkinter import filedialog, messagebox
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Optional, List
from enum import Enum, auto
import datetime

class DragMode(Enum):
    NONE = auto()
    CREATING = auto()
    MOVING = auto()
    RESIZING = auto()

@dataclass
class CropState:
    start_x: Optional[int] = None
    start_y: Optional[int] = None
    end_x: Optional[int] = None
    end_y: Optional[int] = None
    drag_mode: DragMode = DragMode.NONE
    move_start_x: Optional[int] = None
    move_start_y: Optional[int] = None
    frame: Optional[np.ndarray] = None
    original_frame: Optional[np.ndarray] = None
    frame_width: Optional[int] = None
    frame_height: Optional[int] = None
    resize_handle: Optional[str] = None

class VideoCropTool:

    HANDLE_SIZE = 6  
    HANDLE_SENSITIVITY = 10
    WINDOW_WIDTH = 400 
    WINDOW_HEIGHT = 300
    

    BG_COLOR = "#000000"        # Pure black background
    SECONDARY_BG = "#000000"    # Keep everything black
    TEXT_COLOR = "#33FF33"      # Terminal green
    ACCENT_COLOR = "#00FF00"    # Brighter green for highlights
    BUTTON_BG = "#000000"       # Black button
    BUTTON_HOVER_BG = "#003300" # Dark green hover
    BORDER_COLOR = "#33FF33"    # Terminal green border

    ASCII_LOGO = r"""                 
  _____ _____ ____   _____
 / ___// ___// __ \ / ___/
/ /__ / /   / /_/ // /    
\___//_/   / .___//_/     
          /_/             

        """

    def __init__(self):
        self.window = tk.Tk()
        self.window.title("crpr :: tool")
        self.window.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")
        self.window.configure(bg=self.BG_COLOR)
        self.window.resizable(False, False)
        
        # Initialize state
        self.crop_state = CropState()
        self.video_path = None
        
        # Create GUI
        self.create_gui()
        self.setup_button_hover_effects()

    def create_gui(self):
        # Main container
        main_frame = tk.Frame(self.window, bg=self.BG_COLOR)
        main_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # ASCII Logo
        logo_label = tk.Label(
            main_frame,
            text=self.ASCII_LOGO,
            font=("Courier", 12),
            bg=self.BG_COLOR,
            fg=self.ACCENT_COLOR,
            justify=tk.LEFT
        )
        logo_label.pack(pady=(0, 20))

        # Separator
        separator = tk.Label(
            main_frame,
            text="═" * 60,
            font=("IBM Plex Mono", 10),
            bg=self.BG_COLOR,
            fg=self.TEXT_COLOR
        )
        separator.pack(pady=5)

        # Select Video Button Frame
        select_frame = tk.Frame(
            main_frame,
            bg=self.BG_COLOR,
            bd=1,
            relief=tk.SOLID,
            highlightbackground=self.TEXT_COLOR,
            highlightthickness=1
        )
        select_frame.pack(pady=5)

        # Select Video Button
        self.select_btn = tk.Label(
            select_frame,
            text="[SELECT VIDEO]",
            bg=self.BG_COLOR,
            fg=self.TEXT_COLOR,
            font=("IBM Plex Mono", 11),
            padx=20,
            pady=8,
            cursor="hand2"
        )
        self.select_btn.pack()

        # Bind click events
        self.select_btn.bind("<Button-1>", lambda e: self.select_video())
        self.select_btn.bind("<Enter>", lambda e: self.select_btn.configure(fg=self.ACCENT_COLOR))
        self.select_btn.bind("<Leave>", lambda e: self.select_btn.configure(fg=self.TEXT_COLOR))

        # Square Mode Checkbox
        self.square_mode = tk.BooleanVar()
        self.square_btn = tk.Checkbutton(
            main_frame,
            text="[ ] SQUARE MODE",
            variable=self.square_mode,
            bg=self.BG_COLOR,
            fg=self.TEXT_COLOR,
            selectcolor=self.BG_COLOR,
            activebackground=self.BG_COLOR,
            activeforeground=self.ACCENT_COLOR,
            font=("IBM Plex Mono", 10),
            cursor="hand2"
        )
        self.square_btn.pack(pady=5)


    def setup_button_hover_effects(self):
        def on_enter(e):
            e.widget['background'] = self.BUTTON_HOVER_BG

        def on_leave(e):
            e.widget['background'] = self.BUTTON_BG

        self.select_btn.bind("<Enter>", on_enter)
        self.select_btn.bind("<Leave>", on_leave)

    def get_handle_at_position(self, x: int, y: int) -> Optional[str]:
        """Check if position is near a resize handle"""
        if not self.has_valid_selection():
            return None

        x1, x2 = sorted([self.crop_state.start_x, self.crop_state.end_x])
        y1, y2 = sorted([self.crop_state.start_y, self.crop_state.end_y])

        handles = {
            'top-left': (x1, y1),
            'top-right': (x2, y1),
            'bottom-left': (x1, y2),
            'bottom-right': (x2, y2),
            'top': ((x1 + x2) // 2, y1),
            'bottom': ((x1 + x2) // 2, y2),
            'left': (x1, (y1 + y2) // 2),
            'right': (x2, (y1 + y2) // 2)
        }

        for handle_name, (hx, hy) in handles.items():
            if abs(x - hx) <= self.HANDLE_SENSITIVITY and abs(y - hy) <= self.HANDLE_SENSITIVITY:
                return handle_name
        return None

    def point_in_selection(self, x: int, y: int) -> bool:
        if not self.has_valid_selection():
            return False
        x1, x2 = sorted([self.crop_state.start_x, self.crop_state.end_x])
        y1, y2 = sorted([self.crop_state.start_y, self.crop_state.end_y])
        
        if self.get_handle_at_position(x, y):
            return False
            
        return x1 < x < x2 and y1 < y < y2

    def make_square(self, start_x: int, start_y: int, current_x: int, current_y: int) -> Tuple[int, int]:
        dx = current_x - start_x
        dy = current_y - start_y
        abs_dx = abs(dx)
        abs_dy = abs(dy)
        max_delta = max(abs_dx, abs_dy)
        new_dx = max_delta if dx > 0 else -max_delta
        new_dy = max_delta if dy > 0 else -max_delta
        return start_x + new_dx, start_y + new_dy

    def handle_resize(self, x: int, y: int, flags):
        if not self.crop_state.resize_handle:
            return

        x = max(0, min(x, self.crop_state.frame_width))
        y = max(0, min(y, self.crop_state.frame_height))
        
        maintain_square = self.check_shift_key(flags)
        handle = self.crop_state.resize_handle

        if 'left' in handle:
            self.crop_state.start_x = x
        elif 'right' in handle:
            self.crop_state.end_x = x
        if 'top' in handle:
            self.crop_state.start_y = y
        elif 'bottom' in handle:
            self.crop_state.end_y = y

        if maintain_square and '-' in handle:
            x1, x2 = sorted([self.crop_state.start_x, self.crop_state.end_x])
            y1, y2 = sorted([self.crop_state.start_y, self.crop_state.end_y])
            width = x2 - x1
            height = y2 - y1
            max_size = max(width, height)

            if handle == 'top-left':
                self.crop_state.start_x = self.crop_state.end_x - max_size
                self.crop_state.start_y = self.crop_state.end_y - max_size
            elif handle == 'top-right':
                self.crop_state.end_x = self.crop_state.start_x + max_size
                self.crop_state.start_y = self.crop_state.end_y - max_size
            elif handle == 'bottom-left':
                self.crop_state.start_x = self.crop_state.end_x - max_size
                self.crop_state.end_y = self.crop_state.start_y + max_size
            elif handle == 'bottom-right':
                self.crop_state.end_x = self.crop_state.start_x + max_size
                self.crop_state.end_y = self.crop_state.start_y + max_size

    def move_selection(self, x: int, y: int):
        if self.crop_state.drag_mode != DragMode.MOVING:
            return

        dx = x - self.crop_state.move_start_x
        dy = y - self.crop_state.move_start_y
        x1, x2 = sorted([self.crop_state.start_x, self.crop_state.end_x])
        y1, y2 = sorted([self.crop_state.start_y, self.crop_state.end_y])
        width = x2 - x1
        height = y2 - y1
        
        new_x1 = x1 + dx
        new_y1 = y1 + dy

        if new_x1 < 0:
            new_x1 = 0
        if new_y1 < 0:
            new_y1 = 0
        if new_x1 + width > self.crop_state.frame_width:
            new_x1 = self.crop_state.frame_width - width
        if new_y1 + height > self.crop_state.frame_height:
            new_y1 = self.crop_state.frame_height - height

        self.crop_state.start_x = new_x1
        self.crop_state.start_y = new_y1
        self.crop_state.end_x = new_x1 + width
        self.crop_state.end_y = new_y1 + height
        self.crop_state.move_start_x = x
        self.crop_state.move_start_y = y

    def draw_handles(self, frame):
        """Draw minimal, dark handles on the frame"""
        if not self.has_valid_selection():
            return frame

        x1, x2 = sorted([self.crop_state.start_x, self.crop_state.end_x])
        y1, y2 = sorted([self.crop_state.start_y, self.crop_state.end_y])

        # Draw corner handles (small dark squares)
        corners = [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]
        for x, y in corners:
            cv2.rectangle(
                frame,
                (x - self.HANDLE_SIZE//2, y - self.HANDLE_SIZE//2),
                (x + self.HANDLE_SIZE//2, y + self.HANDLE_SIZE//2),
                (40, 40, 40),  # Dark gray
                -1  # Filled rectangle
            )

        # Draw edge handles (smaller dark squares)
        edges = [
            ((x1 + x2)//2, y1), ((x1 + x2)//2, y2),
            (x1, (y1 + y2)//2), (x2, (y1 + y2)//2)
        ]
        for x, y in edges:
            cv2.rectangle(
                frame,
                (x - self.HANDLE_SIZE//2, y - self.HANDLE_SIZE//2),
                (x + self.HANDLE_SIZE//2, y + self.HANDLE_SIZE//2),
                (60, 60, 60),  # Slightly lighter gray
                -1
            )

        return frame

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            handle = self.get_handle_at_position(x, y)
            if handle:
                self.crop_state.drag_mode = DragMode.RESIZING
                self.crop_state.resize_handle = handle
            elif self.has_valid_selection() and self.point_in_selection(x, y):
                self.crop_state.drag_mode = DragMode.MOVING
                self.crop_state.move_start_x = x
                self.crop_state.move_start_y = y
            else:
                self.crop_state.drag_mode = DragMode.CREATING
                self.crop_state.start_x = x
                self.crop_state.start_y = y
                self.crop_state.end_x = x
                self.crop_state.end_y = y

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.crop_state.drag_mode == DragMode.NONE:
                return

            self.crop_state.frame = self.crop_state.original_frame.copy()

            if self.crop_state.drag_mode == DragMode.CREATING:
                if self.check_shift_key(flags):
                    self.crop_state.end_x, self.crop_state.end_y = self.make_square(
                        self.crop_state.start_x,
                        self.crop_state.start_y,
                        x, y
                    )
                else:
                    self.crop_state.end_x = x
                    self.crop_state.end_y = y
            elif self.crop_state.drag_mode == DragMode.MOVING:
                self.move_selection(x, y)
            elif self.crop_state.drag_mode == DragMode.RESIZING:
                self.handle_resize(x, y, flags)

        elif event == cv2.EVENT_LBUTTONUP:
            self.crop_state.drag_mode = DragMode.NONE
            self.crop_state.resize_handle = None

    def check_shift_key(self, flags):
        """Check if shift is pressed either through CV2 flags or toggle button"""
        cv2_shift = bool(flags & cv2.EVENT_FLAG_SHIFTKEY)
        return cv2_shift or self.square_mode.get()

    def has_valid_selection(self):
        return all(v is not None for v in [
            self.crop_state.start_x,
            self.crop_state.start_y,
            self.crop_state.end_x,
            self.crop_state.end_y
        ])

    def show_frame_for_cropping(self):
        cap = cv2.VideoCapture(self.video_path)
        ret, frame = cap.read()
        
        if not ret:
            messagebox.showerror("error", "could not read video file")
            return
            
        self.crop_state.frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.crop_state.frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        cap.release()
        
        self.crop_state.frame = frame.copy()
        self.crop_state.original_frame = frame.copy()
        
        cv2.namedWindow("crpr", cv2.WINDOW_NORMAL)
        cv2.setMouseCallback("crpr", self.mouse_callback)
        
        while True:
            display_frame = self.crop_state.frame.copy()
            
            if self.has_valid_selection():
                x1, x2 = sorted([self.crop_state.start_x, self.crop_state.end_x])
                y1, y2 = sorted([self.crop_state.start_y, self.crop_state.end_y])
                
                # Draw thin white rectangle for selection
                cv2.rectangle(
                    display_frame,
                    (x1, y1),
                    (x2, y2),
                    (255, 255, 255),  # White
                    1  # Thin line
                )
                
                # Add handles
                display_frame = self.draw_handles(display_frame)
            
            cv2.imshow("Crop Video", display_frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('c'):
                if self.validate_selection():
                    self.process_video()
                    break
            elif key == ord('r'):
                self.reset_selection()
            elif key == 27:
                break
        
        cv2.destroyAllWindows()

    def select_video(self):
        self.video_path = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.avi *.mov")]
        )
        if not self.video_path:
            return
            
        filename = self.video_path.split("/")[-1]
        self.show_frame_for_cropping()

    def validate_selection(self):
        if not self.has_valid_selection():
            messagebox.showerror("error", "select a crop region first")
            return False
        if not self.check_minimum_size():
            messagebox.showerror("error", "selection too small. please select a larger region.")
            return False
        return True

    def check_minimum_size(self, min_size: int = 10):
        if not self.has_valid_selection():
            return False
        x1, x2 = sorted([self.crop_state.start_x, self.crop_state.end_x])
        y1, y2 = sorted([self.crop_state.start_y, self.crop_state.end_y])
        return (x2 - x1) >= min_size and (y2 - y1) >= min_size

    def log_operation(self, output_path, roi_info, status_msg):
        """Log operation details to a text file"""
        log_path = output_path.rsplit('.', 1)[0] + '_crop.txt'
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(log_path, 'w') as f:
            f.write(f"crpr:: operation log\n")
            f.write(f"timestamp:: {timestamp}\n")
            f.write(f"status:: {status_msg}\n\n")
            for key, value in roi_info.items():
                f.write(f"{key}: {value}\n")

    def reset_selection(self):
        self.crop_state.start_x = None
        self.crop_state.start_y = None
        self.crop_state.end_x = None
        self.crop_state.end_y = None
        self.crop_state.drag_mode = DragMode.NONE
        self.crop_state.resize_handle = None
        self.crop_state.frame = self.crop_state.original_frame.copy()
        self.roi_label.config(text="ROI: Not selected")

    def get_crop_roi(self):
        x1, x2 = sorted([self.crop_state.start_x, self.crop_state.end_x])
        y1, y2 = sorted([self.crop_state.start_y, self.crop_state.end_y])
        return (x1, y1, x2 - x1, y2 - y1)

    def process_video(self):
        output_path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 files", "*.mp4")]
        )
        if not output_path:
            return

        roi = self.get_crop_roi()
        x1, y1, w, h = roi
        
        # Prepare ROI info for logging
        roi_info = {
            f"roi crop: ({x1}, {y1}, {w}, {h})\n"
            "--------------------------\n"
            "position": f"({x1}, {y1})",
            "dimensions": f"{w} × {h} px",
            "aspect ratio": f"{w/h:.3f}" if h != 0 else "N/A"
        }
        
        try:
            crop_video(self.video_path, roi, output_path)
            status_msg = "cropped successfully"
            self.log_operation(output_path, roi_info, status_msg)
        except Exception as e:
            status_msg = f"Error processing video: {str(e)}"
            self.log_operation(output_path, roi_info, status_msg)
    def run(self):
        self.window.mainloop()

def crop_video(video_path: str, crop_roi: Tuple[int, int, int, int], output_path: str) -> None:
    """Crop a video according to the specified ROI."""
    cap = cv2.VideoCapture(video_path)
    
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    
    x, y, w, h = crop_roi
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        cropped_frame = frame[y:y+h, x:x+w]
        out.write(cropped_frame)
    
    cap.release()
    out.release()

if __name__ == "__main__":
    tool = VideoCropTool()
    tool.run()

