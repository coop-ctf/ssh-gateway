import logging
import warnings

from cryptography.utils import CryptographyDeprecationWarning

from gateway.ssh.server import run_ssh_server

logging.basicConfig(format='%(asctime)s - [%(levelname)s] %(message)s')
logger = logging.getLogger("gateway")
logger.setLevel(logging.DEBUG)

if __name__ == '__main__':
    warnings.filterwarnings(
        action='ignore',
        category=CryptographyDeprecationWarning
    )
    run_ssh_server(ip_address="", port=2200, host_key_file="host.key", backend_key_file="backend.key")
