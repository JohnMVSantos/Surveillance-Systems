from importlib.metadata import version as pkgver
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
import threading
import smtplib
import json

def version() -> str:
    """
    Return the current version of the project.

    Returns
    -------
        version: str
            This is the current version of the project.
    """
    try:
        return pkgver('surveillance-systems')
    except Exception:
        from subprocess import Popen, PIPE
        from re import sub
        pipe = Popen('git describe --tags --always', stdout=PIPE, shell=True)
        ver = str(pipe.communicate()[0].rstrip().decode("utf-8"))
        ver = str(sub(r'-g\w+', '', ver))
        return ver.replace('-', '.post')

def logger(message: str, code: str="INFO"):
    """
    Logs messages to the terminal.

    Parameters
    ----------
        message: str
            The message to log to the terminal.

        code: str
            The type of message to log. Available codes are
            "INFO", "SUCCESS", "WARNING", "ERROR".
    """
    print(f"\t - [{code.upper()}]: {message}")
    if code.upper() == "ERROR":
        exit(1)

def send_email(
        subject: str, 
        body: str, 
        sender: str, 
        password: str, 
        receivers: list,
        img: bytes=None
    ):
    """
    Sends an email message.

    Parameters
    ----------
        subject: str
            This is the email subject.

        body: str
            This is the body message of the email.

        sender: str
            This is the email to use to send.

        password: str
            This is the password of the email sender.

        receivers: str
            These are the email addresses to receive.

        img: bytes
            The image showing motion.
    """
    def email_thread():
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = ', '.join(receivers)

        # write the HTML part
        html = f"""\
        <html>
            <body>
                {body}\n
                <img src="cid:Mailtrapimage">
            </body>
        </html>
        """
        if img is not None:
            msg.attach(MIMEText(html, "html"))
            image = MIMEImage(img)
            # Specify the  ID according to the img src in the HTML part
            image.add_header('Content-ID', '<Mailtrapimage>')
            msg.attach(image)

        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(sender, password)
                server.send_message(msg)
            logger("Email sent successfully!", code="SUCCESS")
        except Exception as e:
            logger(f"Failed to send email: {e}", code="WARNING")
    thread = threading.Thread(target=email_thread)
    thread.start()

def read_configuration(config_file: str) -> dict:
    """
    Readers JSON configuration file.

    Parameters
    ----------
        config_file: str
            This is the path to the configuration file.

    Returns
    -------
        data: dict
            This contains the JSON contents.
    """
    with open(config_file) as fp:
        configuration = json.load(fp)
    return configuration