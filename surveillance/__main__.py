
from surveillance.video.utils import show_time, convert_h264_to_mp4
from surveillance import read_configuration, version, logger
from surveillance.credentials import Credentials
from surveillance.video.camera import Camera
from picamera2.outputs import CircularOutput
from picamera2.encoders import H264Encoder
from flask_restful import Resource, Api
from flask import (
    Flask, 
    Response,
    render_template, 
    redirect, 
    jsonify, 
    request, 
    session, 
    url_for
)
from gpiozero import AngularServo
from datetime import datetime
from time import sleep
import subprocess
import threading
import argparse
import os

def main():
    """
    Define the command line arguments and start the server.
    """
    parser = argparse.ArgumentParser(
        description=("Standalone Surveillance Software"),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('-v', '--version',
                        help="Print the software version in the terminal.",
                        action='version',
                        version=version(),
                    )
    parser.add_argument('-r', '--resolution',
                        help="Set the resolution of the camera frames (height, width).",
                        type=tuple,
                        default=(600, 800),
                    )
    parser.add_argument('-c', '--configuration',
                        help="The path to the JSON configuration file.",
                        type=str,
                        required=True
                    )
    parser.add_argument('--cooldown',
                        help="Set the email cooldown time in seconds to avoid spams.",
                        type=int,
                        default=600
                    )
    args = parser.parse_args()

    configuration = read_configuration(args.configuration)
    silent = False # TODO: Control with a button.
    # Define the app.
    app = Flask(__name__, template_folder='template', static_url_path='/static')
    app.secret_key = configuration["secret_key"] 
    api = Api(app)

    encoder = H264Encoder()
    output = CircularOutput()

    # Global or session variable to hold the current recording file name.
    current_video_file = None

    # Global Thread Lock
    email_lock = threading.Lock()

    # Camera Handler
    images_directory = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "static/pictures")
    videos_directory = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "static/video")
    sound_directory = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "static/sound")

    credentials = Credentials(
        sender_email=configuration["sender_email"],
        sender_password=configuration["sender_password"],
        receivers=configuration["receivers"],
        location=configuration["location"],
        users=configuration["users"],
    )

    height, width = args.resolution
    camera = Camera(
        encoder=encoder,
        output=output,
        images_directory=images_directory,
        credentials=credentials,
        width=width,
        height=height,
        cooldown=args.cooldown,
    )

    servo = AngularServo(17, min_angle=0, max_angle=180)

    class VideoFeed(Resource):
        """
        This is the login redirector.
        """
        def get(self):
            if 'username' not in session:
                return redirect(url_for('login'))  # Ensure this follows your app's login logic
            return Response(genFrames(), mimetype='multipart/x-mixed-replace; boundary=frame')
                
    def genFrames():
        """
        Continuous generation of frames in a stream to display 
        in the endpoint.
        """
        while True:
            frame = camera.get_frame()
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n'
            )

    # @App Routes

    @app.route('/startRec.html')
    def startRec() -> str:
        """
        Start Recording Pane.

        Returns
        -------
            rendered_template: str
                The template for start recording session.
        """
        if not silent:
            logger("Starting video record progress...")
        basename = show_time()
        # Save the full path to a global variable.
        current_video_file = f"vid_{basename}.h264"  
        output.fileoutput = os.path.join(videos_directory, current_video_file)
        output.start()
        return render_template('startRec.html')

    @app.route('/stopRec.html')
    def stopRec() -> str:
        """
        Stop Recording Pane.

        Returns
        -------
            rendered_template: str
                The template for stopping recording.
        """
        if not silent:
            logger("Stopping video recording...")
        output.stop()
        if current_video_file:
            source_path = os.path.join(videos_directory, current_video_file)
            output_path = source_path.replace('.h264', '.mp4')
            convert_h264_to_mp4(source_path, output_path, silent)
            return render_template(
                'stopRec.html', 
                message=f"Conversion successful for {output_path}")
        else:
            return render_template(
                'stopRec.html', 
                message="No video was recorded or file path is missing.")

    @app.route('/')
    def index() -> str:
        """
        Video streaming home page.

        Returns
        -------
            rendered_template: str
                The template for the homepage.
        """
        return render_template('index.html')

    @app.route('/home', methods = ['GET', 'POST'])
    def home_func() -> str:
        """
        Video streaming home page.

        Returns
        -------
            The template for the homepage.
        """
        return render_template("index.html")
    
    @app.route("/test", methods=["POST"])
    def test():
        # Get slider values for servo movement.
        slider = request.form["slider"]
        servo.angle = int(slider)
        # Give servo some time to move.
        sleep(1)
        return redirect(url_for('index'))

    @app.route('/info.html')
    def info() -> str:
        """
        Info Pane

        Returns
        -------
            rendered_template: str
                Provides a template to display camera information.
        """
        if 'username' not in session:
            # Redirect to login if not authenticated.
            return redirect(url_for('login'))  
        return render_template('info.html')

    @app.route('/srecord.html')
    def srecord() -> str:
        """
        Sound Record Pane.

        Returns
        --------
            rendered_template: str
                The template to show when recording sounds.
        """
        timestamp = datetime.now()
        if not silent:
            logger(f"Starting sound recording session {timestamp}...")
        subprocess.Popen(
            f'arecord -D dmic_sv -d 30 -f S32_LE {sound_directory}/cam_$(date "+%b-%d-%y-%I").wav -c 2', 
            shell=True
        )
        return render_template('srecord.html')

    @app.route('/snap.html')
    def snap():
        """
        Snap Pane.

        Returns
        -------
            rendered_template: str
                This provides a template for 
                snapping a picture.
        """
        if not silent:
            logger("Taking a photo.")
        camera.video_snap()
        #return render_template('snap.html')
        return render_template("index.html")

    @app.route('/api/files')
    def api_files():
        """
        Fetches the files for images and videos captured.

        Returns
        -------
            Response
                This displays the files stored.
        """
        try:
            images = [img for img in os.listdir(images_directory) if img.endswith(('.jpg', '.jpeg', '.png'))]
            videos = [file for file in os.listdir(videos_directory) if file.endswith('.mp4')]
            if not silent:
                logger(f"Images found: {images}") 
                logger(f"Videos found: {videos}") 
            return jsonify({'images': images, 'videos': videos})
        except Exception as e:
            if not silent:
                logger(f"Error in api_files: {str(e)}", code="ERROR") 
            return jsonify({'error': str(e)})

    @app.route('/delete-file/<filename>', methods=['DELETE'])
    def delete_file(filename):
        """
        Deletes the file by providing the filename.

        Returns
        -------
            message: str
                This could be an error, or a blank string if successful.

            code: int
                This is the code of complete: 204 for successful, 500 for an error.
        """
        # Determine if it's a video or picture based on the extension or another method
        if filename.endswith('.mp4') or filename.endswith('.mkv'):
            file_path = os.path.join(videos_directory, filename)
        else:
            file_path = os.path.join(images_directory, filename)
        try:
            os.remove(file_path)
            return '', 204  # Successful deletion
        except Exception as e:
            return str(e), 500  # Internal server error

    @app.route('/files') 
    def files() -> str:
        """
        Fetches the files stored so far.

        Returns
        -------
            rendered_template: str
                Display all the files stored so far.
        """
        try:
            images = os.listdir(images_directory)
            videos = [file for file in os.listdir(videos_directory) if file.endswith(('.mp4', '.h264'))]  # Assuming video formats
            # Filtering out system files like .DS_Store which might be present in directories
            images = [img for img in images if img.endswith(('.jpg', '.jpeg', '.png'))]
            return render_template('files.html', images=images, videos=videos)
        except Exception as e:
            return str(e)  # For debugging purposes, show the exception in the browser
    
    api.add_resource(VideoFeed, '/cam')

    @app.route('/login', methods=['GET', 'POST'])
    def login() -> str:
        """
        Login Page.

        Returns
        -------
            rendered_template: str
                This is the rendered template of the login page.
        """
        if 'username' in session:
            return redirect(url_for('index'))
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            if username in configuration["users"] and configuration["users"][username] == password:
                session['username'] = username
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error="Invalid username or password")
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        """
        Logout redirection.

        Returns
        -------
            Response
                Logout response.
        """
        session.pop('username', None)
        return redirect(url_for('index'))  # Redirect to index which will force login due to session check

    @app.before_request
    def require_login():
        """
        Request login credentials.

        Returns
        --------
            Response
                This is the request for login information.
        """
        allowed_routes = ['login', 'static']  # Make sure the streaming endpoints are either correctly authenticated or exempted here.
        if request.endpoint not in allowed_routes and 'username' not in session:
            return redirect(url_for('login'))

    app.run(debug=False, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()