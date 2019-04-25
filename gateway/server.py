import logging
import threading

import paramiko

logger = logging.getLogger("gateway")


class GatewayServer(paramiko.ServerInterface):

    def __init__(self, client):
        self.client = client
        self.event = threading.Event()
        self.username = None

    def get_allowed_auths(self, username):
        return "none"

    def check_auth_none(self, username):
        logger.debug("Allowing client %s to connect without password for username: %s", id(self.client), username)
        self.username = username
        return paramiko.AUTH_SUCCESSFUL

    def check_channel_request(self, kind, chanid):
        logger.debug("Received channel request of type %s from channel %s (client: %s)", kind, chanid, id(self.client))
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(
            self, channel, term, width, height, pixelwidth, pixelheight, modes
    ):
        return True
