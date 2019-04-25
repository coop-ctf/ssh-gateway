import socket
import sys
import threading
import traceback
from multiprocessing.dummy import Pool as ThreadPool
from time import sleep

import paramiko

from gateway.server import GatewayServer

pool = ThreadPool(4)


class ConnectionThread(threading.Thread):
    def __init__(self, transport: paramiko.Transport, server: GatewayServer):
        super().__init__()
        self.server = server
        self.transport = transport

    def run(self):
        chan: paramiko.Channel = self.transport.accept(20)
        print("Authenticated!")
        self.server.event.wait(10)
        if not self.server.event.is_set():
            print("*** Client never requested a shell, exiting")
            sys.exit(1)

        chan.send("Preparing resources...\r\n")
        sleep(5)
        try:
            backend = create_proxy_to_backend_and_forward(chan)
        except Exception:
            traceback.print_exc()
            chan.send("*********\r\n"
                      "  Could not create connection due to a backend error.\r\n"
                      "  Please tell the event organizers!\r\n"
                      "*********\r\n")
            chan.close()
            self.transport.close()
            return

        print("Listening from client")
        while not chan.closed and not backend.closed:
            recv = chan.recv(1024)
            if not backend.closed:
                backend.send(recv)
            else:
                break

        print("Connection closed")
        if not chan.closed:
            chan.close()
        if not backend.closed:
            backend.close()
        self.transport.close()


def create_proxy_to_backend_and_forward(chan: paramiko.Channel) -> paramiko.Channel:
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.WarningPolicy())
    client.connect(hostname="localhost", port=22, username="momo")
    backend: paramiko.Channel = client.invoke_shell()

    class ForwardThread(threading.Thread):
        def run(self):
            while not backend.closed:
                recv = backend.recv(1024)
                if not chan.closed:
                    chan.send(recv)
                else:
                    backend.close()
                    return
            chan.close()

    ForwardThread().start()
    return backend


def run():
    host_key = paramiko.RSAKey(filename="host.key")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", 2200))
    except Exception as e:
        print(f"*** Socket bind failed: {e}")
        traceback.print_exc()
        sys.exit(1)

    try:
        sock.listen(20)
        print("Listening for connections...")
    except Exception as e:
        print(f"*** Socket listen failed: {e}")
        traceback.print_exc()
        sys.exit(1)

    while True:
        client, addr = sock.accept()
        print("Received a connection")
        transport = paramiko.Transport(client)
        transport.add_server_key(host_key)
        server = GatewayServer()
        transport.start_server(server=server)
        ConnectionThread(transport, server).start()


if __name__ == '__main__':
    run()
