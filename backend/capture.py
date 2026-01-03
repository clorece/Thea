import mss
import mss.tools
import win32gui
import base64
from io import BytesIO
from PIL import Image

def get_active_window_title():
    try:
        w = win32gui.GetForegroundWindow()
        return win32gui.GetWindowText(w)
    except Exception as e:
        return f"Error getting window: {e}"

def capture_screen_base64(scale=0.75):
    """
    Captures the primary monitor, resizes it (for speed/LLM limits), 
    and returns a base64 string.
    """
    with mss.mss() as sct:
        # Capture primary monitor (monitor 1)
        monitor = sct.monitors[1]
        
        # Grab the data
        sct_img = sct.grab(monitor)
        
        # Convert to PIL Image
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        
        # Resize to reduce bandwidth/processing
        if scale != 1.0:
            new_size = (int(img.width * scale), int(img.height * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            
        # Convert to Base64
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=90)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        return img_str

if __name__ == "__main__":
    print(f"Active Window: {get_active_window_title()}")
    print(f"Snapshot size: {len(capture_screen_base64())} bytes")
