import datetime
import logging

import falcon
import waitress

from gateway.ssh import server as ssh_server

logger = logging.getLogger("gateway.web")


class IndexRoute:
    def on_get(self, req, resp):
        # TODO: User interface
        resp.media = {}


class SSHConnectionListRoute:
    def on_get(self, req, resp):
        connections = []
        for conn in ssh_server.connections.values():
            conn: ssh_server.ServerConnection = conn
            if conn.is_alive():
                connections.append({
                    "id": conn.id,
                    "last_active": datetime.datetime.utcnow().timestamp() - conn.last_active.timestamp(),
                    "username": conn.server.username,
                    "client_addr": f"{conn.addr[0]}:{conn.addr[1]}",
                    "challenge": conn.challenge
                })

        resp.media = connections


class SSHConnectionRoute:
    def on_delete(self, req, resp, conn_id):
        connection: ssh_server.ServerConnection = ssh_server.connections.get(conn_id)
        if not connection:
            resp.status = falcon.HTTP_NOT_FOUND
            return

        if connection.is_alive():
            connection.kill()
            resp.status = falcon.HTTP_OK


def run_web_server(ip_address: str, port: int):
    api = falcon.API()
    api.add_route("/", IndexRoute())
    api.add_route("/ssh/connections", SSHConnectionListRoute())
    api.add_route("/ssh/connections/{conn_id:int}", SSHConnectionRoute())

    logger.info("Listening for connections on %s:%s", ip_address, port)
    waitress.serve(api, host=ip_address, port=port, _quiet=True)
