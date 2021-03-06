import logging
import socket
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Tuple

import paramiko

from gateway.ssh import pty

logger = logging.getLogger("gateway.ssh")


@dataclass
class ServerConnection:
    client: socket.socket = None
    channel: paramiko.Channel = None
    transport: paramiko.Transport = None
    server: Any = None
    backend: paramiko.Channel = None
    last_active: datetime = None
    pty_dimensions: pty.PtyDimensions = None
    addr: Tuple[str, int] = None
    challenge: str = None
    id: str = None

    def kill(self):
        logger.debug("Connection with %s is closing", self.id)

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

    def resize_backend(self):
        if self.is_alive() and self.backend:
            self.backend.resize_pty(
                width=self.pty_dimensions.width,
                height=self.pty_dimensions.height,
                width_pixels=self.pty_dimensions.width_pixels,
                height_pixels=self.pty_dimensions.height_pixels,
            )
