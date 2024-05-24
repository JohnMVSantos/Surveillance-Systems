from surveillance import logger
from datetime import datetime
from PIL import Image
import subprocess
import io

def convert_h264_to_mp4(source_file_path: str, output_file_path: str, silent: bool=False):
    """
    H264 to MP4 converter.

    Parameters
    ----------
        source_file_path: str
            This is the path to the H264 video file.

        output_file_path: str
            This is the path to save the MP4 formatted file.

        silent: bool
            Specify whether to print status messages on the terminal.
    """
    try:
        # Command to convert h264 to mp4
        command = ['ffmpeg', '-i', source_file_path, '-c', 'copy', output_file_path]
        subprocess.run(command, check=True)
        if not silent:
            logger(f"Conversion successful: {output_file_path}", code="SUCCESS")
    except subprocess.CalledProcessError as e:
        if not silent:
            logger(f"Error during conversion: {e}", code="WARNING")

def image2bytes(image: Image.Image) -> bytes:
    """
    Convert a Pillow Image object to bytes.

    Parameters
    ----------
        image: Image.Image
            A pillow Image object.

    Returns
    -------
        img_byte_arr: bytes
            The image as bytes.
    """
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    return img_byte_arr

def show_time() -> str:
    """
    Return current time formatted for file names.
    
    Returns
    -------
        The current datatime in year-month-day_hour-minute-second.
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")
