import logging
import socket
import sys
import threading
import uuid
from datetime import datetime

import paramiko

from gateway.ssh import pty
from gateway.ssh.backend import get_pod_backend, is_username_known, is_challenge_known
from gateway.ssh.connection import ServerConnection
from gateway.ssh.ctf import CTF
from gateway.ssh.proxy import create_proxy_to_backend_and_forward

logger = logging.getLogger("gateway.ssh")

connections = {}


def run_ssh_server(ip_address: str, port: int, host_key_file: str, backend_key_file: str):
    host_key = paramiko.RSAKey(filename=host_key_file)
    backend_key = paramiko.RSAKey(filename=backend_key_file)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((ip_address, port))
    except Exception as e:
        logger.error("Socket bind failed: %s", e, exc_info=1)
        sys.exit(1)

    try:
        sock.listen(20)
        logger.info("Listening for connections on %s:%s", ip_address, port)
    except Exception as e:
        logger.error("Socket listen failed: %s", e, exc_info=1)
        sys.exit(1)

    while True:
        client, addr = sock.accept()
        client_id = str(uuid.uuid4())
        logger.debug("Received a connection from %s (id=%s)", addr, client_id)
        transport = paramiko.Transport(client)
        transport.add_server_key(host_key)

        connection = ServerConnection(
            client=client,
            transport=transport,
            last_active=datetime.utcnow(),
            addr=addr,
            id=client_id
        )

        try:
            connection.server = GatewayServer(connection)
            transport.start_server(server=connection.server)
            ConnectionThread(connection, backend_key).start()
        except Exception:
            logger.error("An error occurred while creating a connection to client %s", client_id, exc_info=1)


class GatewayServer(paramiko.ServerInterface):

    def __init__(self, connection: ServerConnection):
        self.client = connection.client
        self.wait_for_shell = threading.Event()
        self.connection = connection
        self.username = None

    def get_allowed_auths(self, username):
        return "password"

    def check_auth_password(self, username, password):
        if ":" in username:
            self.username, self.connection.challenge = username.split(":", 1)
            self.username = CTF.capitalize_team_name(self.username)
        else:
            self.username = username
        logger.debug("Checking password for %s (%s)", username, self.connection.id)
        if CTF.check_password(self.username, password):
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        logger.debug("Received channel request of type '%s' from channel %s (client: %s)", kind, chanid,
                     self.connection.id)
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel):
        self.wait_for_shell.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        logger.debug("Client %s is creating PTY with (t=%s,w=%s,h=%s,pw=%s,ph=%s)", self.connection.id,
                     term, width, height, pixelwidth, pixelheight)
        self.connection.pty_dimensions = pty.PtyDimensions(
            term=term,
            width=width, height=height,
            width_pixels=pixelwidth, height_pixels=pixelheight)
        return True

    def check_channel_window_change_request(self, channel, width, height, pixelwidth, pixelheight):
        self.connection.pty_dimensions.width = width
        self.connection.pty_dimensions.height = height
        self.connection.pty_dimensions.width_pixels = pixelwidth
        self.connection.pty_dimensions.height_pixels = pixelheight
        self.connection.resize_backend()
        return True


class ConnectionThread(threading.Thread):

    def __init__(self, connection: ServerConnection, backend_key: paramiko.PKey):
        super().__init__()
        self.backend_key = backend_key
        self.client = connection.client
        self.server: GatewayServer = connection.server
        self.transport = connection.transport
        self.connection = connection

    def run(self):
        self.connection.channel: paramiko.Channel = self.transport.accept(30)
        if not self.connection.channel:
            logger.debug("Client %s timed out, closing", self.connection.id)
            self.connection.kill()
            return
        self.server.wait_for_shell.wait(60)
        if not self.server.wait_for_shell.is_set():
            logger.debug("Client %s never requested a shell, closing", self.connection.id)
            self.connection.kill()
            return

        connections[self.connection.id] = self.connection

        if not is_username_known(self.connection.server.username):
            logger.info("Client %s used an invalid team code, therefore it is being killed.", self.connection.id)
            self.connection.channel.send("*********\r\n"
                                         f"  Unknown team code: {self.connection.server.username}. "
                                         f"Please use a valid code as a username, followed by : and the challenge name"
                                         f".\r\n"
                                         "  Example: ssh TeamCode:CATLWALK@ssh.coop-ctf.ca\r\n"
                                         "*********\r\n")
            self.connection.kill()
            return

        if not self.connection.challenge:
            logger.info("Client %s did not provide a challenge, therefore it is being killed.", self.connection.id)
            self.connection.channel.send("*********\r\n"
                                         "No challenge was provided.\r\n"
                                         "Please set a challenge by appending the username with ':CHALLENGE_NAME'.\r\n"
                                         f"  Example: ssh {self.connection.server.username}:CATWALK"
                                         f"@ssh.coop-ctf.ca\r\n"
                                         "*********\r\n")
            self.connection.kill()
            return

        if not is_challenge_known(self.connection.challenge):
            logger.info("Client %s provided an invalid challenge, therefore it is being killed.", self.connection.id)
            self.connection.channel.send("*********\r\n"
                                         f"Challenge not found: {self.connection.challenge}.\r\n"
                                         "Please set a valid challenge by appending the username "
                                         "with ':CHALLENGE_NAME'.\r\n"
                                         f"  Example: ssh {self.connection.server.username}:CATWALK"
                                         f"@ssh.coop-ctf.ca\r\n"
                                         "*********\r\n")
            self.connection.kill()
            return

        self.connection.channel.send(
            f"Preparing resources for {self.connection.server.username} "
            f"(challenge: {self.connection.challenge})...\r\n")

        backend_res = get_pod_backend(self.connection, self.backend_key)

        if not self.connection.is_alive():
            # TODO: Delete pod because it is no longer needed
            return

        if not backend_res:
            self.connection.channel.send("*********\r\n"
                                         "  Our apologies. Your challenge server never came up."
                                         "  This could be caused by increased load or a backend issue.\r\n"
                                         f"  Please notify the event organizers with this code: {self.connection.id}\r\n"
                                         "*********\r\n")
            self.connection.kill()
            return

        try:
            logger.debug("Creating proxy to %s:%s, with username %s (client: %s)",
                         backend_res.ssh_hostname, backend_res.ssh_port, backend_res.ssh_username, self.connection.id)
            self.connection.backend = create_proxy_to_backend_and_forward(backend_res, self.connection)
        except Exception:
            logger.error("Failed to create connection to backend (proxy) for client %s", self.connection.id, exc_info=1)
            self.connection.channel.send("*********\r\n"
                                         "  Could not create connection due to a backend error.\r\n"
                                         f"  Please notify the event organizers with this code: {self.connection.id}\r\n"
                                         "*********\r\n")
            self.connection.kill()
            return

        logger.debug("Listening from client %s to proxy", self.connection.id)
        while self.connection.is_alive():
            try:
                recv = self.connection.channel.recv(1024)
                self.connection.backend.send(recv)
                self.connection.last_active = datetime.utcnow()
            except Exception:
                break

        self.connection.kill()
