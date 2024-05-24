class Credentials:
    """
    Stores the user's credentials.

    Parameters
    ----------
        sender_email: str
            This is the email to use to 
            send email notifications.

        sender_password: str
            This is the password of the sender email.

        receivers: list
            These are the recipients to receive the email.

        location: str
            The location at which the camera is situated.

        users: dict
            The users that are allowed to login to the application.
    """
    def __init__(
            self,
            sender_email: str,
            sender_password: str,
            receivers: list,
            location: str,
            users: dict
        ) -> None:
        
        self._sender_email = sender_email
        self._sender_password = sender_password
        self._receivers = receivers
        self._location = location
        self._users = users

    @property
    def sender_email(self) -> str:
        """
        This is the email to use to send
        the email notifications.
        This requires a gmail address.

        Returns
        -------
            self._sender_email: str
                The sender email currently set.
        """
        return self._sender_email
    
    @sender_email.setter
    def sender_email(self, email: str):
        """
        Sets the sender email to a new value. This requires
        a gmail address.

        Parameters
        ----------
            email: str
                The new email to set for the sender.
        """
        self._sender_email = email

    @property
    def sender_password(self) -> str:
        """
        This is the password of the 
        sender email.

        Returns
        -------
            self._sender_password: str
                The sender password currently set.
        """
        return self._sender_password
    
    @sender_password.setter
    def sender_password(self, password: str):
        """
        Sets the sender password to a new value.

        Parameters
        ----------
            password: str
                The new password to set for the sender.
        """
        self._sender_password = password

    @property
    def receivers(self) -> list:
        """
        These are the recipients to receive
        the email notifications.

        Returns
        -------
            self._receivers: list
                The recipients currently set.
        """
        return self._receivers
    
    @receivers.setter
    def receivers(self, emails: list):
        """
        Sets the recipients to a new value.

        Parameters
        ----------
            emails: list
                The new emails to set for the recipients.
        """
        self._receivers = emails

    @property
    def location(self):
        """
        The location at which the 
        camera is situated.

        Returns
        -------
            location: str
                The location of the camera.
        """
        return self._location

    @location.setter
    def location(self, loc: str):
        """
        Sets the location to a new value.

        Parameters
        ----------
            loc: str
                The new location value to set.
        """
        self._location = loc

    @property
    def users(self) -> dict:
        """
        This dictionary contains the users
        and their login information.

        Returns
        -------
            users: dict
                This can be in the form of

                {
                    "username": "password"
                }
        """
        return self._users
    
    @users.setter
    def users(self, usrs: dict):
        """
        Sets users to a new value.

        Parameters
        ----------
            usrs: dict
                This contains the user information.

                This can be in the form of:

                {
                    "username": "password"
                }
        """
        self._users = usrs

    def append_user(self, username: str, password: str):
        """
        Adds a new users to the dictionary.
        """
        self._users[username] = password