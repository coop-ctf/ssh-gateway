import logging
import threading
import warnings

from cryptography.utils import CryptographyDeprecationWarning

from gateway.ssh.server import run_ssh_server
from gateway.web.server import run_web_server

logging.basicConfig(format='%(asctime)s - [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("gateway")
logger.setLevel(logging.DEBUG)


class SSHGatewayServer(threading.Thread):
    def run(self):
        run_ssh_server(ip_address="", port=2200, host_key_file="host.key", backend_key_file="backend.key")


class WebServer(threading.Thread):
    def run(self):
        run_web_server("127.0.0.1", 2201)


if __name__ == '__main__':
    warnings.filterwarnings(
        action='ignore',
        category=CryptographyDeprecationWarning
    )
    WebServer().start()
    SSHGatewayServer().start()
