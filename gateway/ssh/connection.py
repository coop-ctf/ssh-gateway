import logging
import socket
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import paramiko

from gateway.ssh import pty

logger = logging.getLogger("gateway.ssh")


@dataclass
class ServerConnection:
    client: socket.socket
    channel: paramiko.Channel
    transport: paramiko.Transport
    server: Any
    backend: paramiko.Channel
    last_active: datetime
    pty_dimensions: pty.PtyDimensions

    def kill(self):
        logger.debug("Connection with %s is closing", id(self.client))

        if self.backend and not self.backend.closed:
            self.backend.close()
        if self.channel and not self.channel.closed:
            self.channel.close()
        if self.transport and self.transport.active:
            self.transport.close()

    def is_alive(self) -> bool:
        if self.backend and self.backend.closed:
            return False
        if self.channel and self.channel.closed:
            return False
        if self.transport and not self.transport.active:
            return False
        return True
