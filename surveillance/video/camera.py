from __future__ import annotations
from typing import TYPE_CHECKING, Union
if TYPE_CHECKING:
    from surveillance.credentials import Credentials
    from picamera2.outputs import CircularOutput
    from picamera2.encoders import H264Encoder

from surveillance.video.utils import image2bytes, show_time
from PIL import Image, ImageChops, ImageFilter
from surveillance import logger, send_email
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput
from picamera2 import Picamera2
from datetime import datetime
import numpy as np
import threading
import time
import io
import os

class Camera:
    """
    Camera instance using the picamera2 library to capture image data 
    from a Raspberry Pi camera module. 

    Parameters
    ----------
        encoder: H264Encoder, ...
            The encoder to pass to the camera object
            to start recording.

        output: CircularOutput
            The output object to pass to the
            camera object to start recording.

        images_directory: str
            This is the path to save the images 
            when utilizing the snap functionality.

        credentials: Credentials
            This contains the user credentials.

        width: int
            This is the width to display the feed or the 
            width of the camera frames.

        height: int
            This is the height to display the feed or the
            height of the camera frames.

        silent: bool
            This parameter if set to True will stop detecting
            motions, notifying via email, and print logs on 
            the terminal.

        cooldown: int
            This is the time in seconds before sending another email if
            motion is detected.
    """
    def __init__(
            self, 
            encoder: Union[H264Encoder],
            output: Union[CircularOutput],
            images_directory: str,
            credentials: Credentials,
            width: int=800, 
            height: int=600,
            silent: bool=False,
            cooldown: int=300,
        ) -> None:

        self.camera = Picamera2()
        self.camera.configure(
            self.camera.create_video_configuration(
                main={
                    "size": (width, height)
                }))
        self.still_config = self.camera.create_still_configuration()

        self.encoder = MJPEGEncoder(10000000)
        self.streamOut = StreamingOutput()
        self.streamOut2 = FileOutput(self.streamOut)
        self.encoder.output = [self.streamOut2]

        self.camera.start_encoder(self.encoder)
        self.camera.start_recording(encoder, output)

        self.images_directory = images_directory
        self.credentials = credentials
        self.previous_image = None
        self.motion_detected = False  # Track if motion is currently detected.
        self.last_motion_detected_time = None  # Initialize to None.
        self.last_motion_time = None
        self.email_allowed = True
        self.silent = silent
        self.cooldown = cooldown

    def get_frame(self) -> bytes:
        """
        Retrieves a single frame from the camera.

        Returns
        -------
            frame_data: bytes
                The frame captured as bytes.
        """
        self.camera.start()
        with self.streamOut.condition:
            self.streamOut.condition.wait()
            frame_data = self.streamOut.frame
        image = Image.open(io.BytesIO(frame_data))  
        # Convert to grayscale and apply Gaussian blur.
        image_process = image.convert('L').filter(ImageFilter.GaussianBlur(radius=2))  
        if self.previous_image is not None and not self.silent:
            self.detect_motion(self.previous_image, image_process, image)
        self.previous_image = image_process
        return frame_data

    def detect_motion(self, previous_image: Image.Image, current_image: Image.Image, image: Image.Image):
        """
        Detects any motion at a set threshold. Notifies via email if motion
        is detected. A cooldown factor is in effect to avoid email spamming.

        Parameters
        ----------
            previous_image: Image.Image
                This is the previous frame.

            current_image: Image.Image
                This is the current frame.

            image: Image.Image
                This is the colored image to send by mail.
        """
        current_time = time.time()
        diff = ImageChops.difference(previous_image, current_image)
        # Adjust 40 to change sensitivity. Higher is less sensitve.
        diff = diff.point(lambda x: x > 40 and 255)    
        count = np.sum(np.array(diff) > 0)
        # Sensitivity threshold for motion.
        if count > 500:  
            if self.email_allowed:
                # Motion is detected and email is allowed.
                if (self.last_motion_time is None or 
                    (current_time - self.last_motion_time > self.cooldown)):
                    image_bytes = image2bytes(image)
                    send_email(
                        "[Surveillance] - Motion Detected Alert", 
                        f"Motion has been detected by your camera at {show_time()} in {self.credentials.location}.", 
                        self.credentials.sender_email, 
                        self.credentials.sender_password,
                        self.credentials.receivers, 
                        image_bytes,
                    )
                    logger(
                        f"Motion detected and email sent to {self.credentials.receivers}."
                    )
                    # Update the last motion time.
                    self.last_motion_time = current_time  
                    # Prevent further emails until condition resets.
                    self.email_allowed = False  
                else:
                    logger("Motion detected but ineligible for email due to cooldown.")
            else:
                logger("Motion detected but email was not sent due to recent activity.")
            self.last_motion_detected_time = current_time
        else:
            # No motion detected.
            if (self.last_motion_detected_time and 
                (current_time - self.last_motion_detected_time > self.cooldown) and 
                not self.email_allowed
            ):
                # Re-enable sending emails after self.cooldown seconds of no motion.
                self.email_allowed = True  
                logger(f"{self.cooldown} seconds of no motion passed, emails re-enabled.")
                # Reset to prevent message re-printing.
                self.last_motion_detected_time = current_time  

    def video_snap(self):
        """
        Takes a snapshot of the videostream and storing the 
        frame inside the images directory passed.
        """
        timestamp = datetime.now()
        if not self.silent:
            logger(f"Snap - [timestamp]: {timestamp}")
        self.still_config = self.camera.create_still_configuration()
        self.file_output = os.path.join(self.images_directory, f"snap_{timestamp}.jpg")
        self.job = self.camera.switch_mode_and_capture_file(
            self.still_config, self.file_output, wait=False)
        self.metadata = self.camera.wait(self.job)

class StreamingOutput(io.BufferedIOBase):
    """
    The object to direct video streaming. 
    """
    def __init__(self):
        self.frame = None
        self.condition = threading.Condition()

    def write(self, buf: bytes):
        """
        Write to the current frame. 

        Parameters
        ----------
            buf: bytes
                The current frame stored in a buffer.
        """
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

if __name__ == '__main__':
    camera = Camera()