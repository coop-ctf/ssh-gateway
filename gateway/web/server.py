import datetime
import logging

import falcon
import waitress
from kubernetes.client import V1Pod, V1PodList

from gateway.ssh import server as ssh_server, kube

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
                client: kube.KubeClient = kube.KubeClient.get()
                pod: V1Pod = client.get_pod(team=conn.server.username, challenge=conn.challenge)
                connections.append({
                    "id": conn.id,
                    "last_active": datetime.datetime.utcnow().timestamp() - conn.last_active.timestamp(),
                    "username": conn.server.username,
                    "client_addr": f"{conn.addr[0]}:{conn.addr[1]}",
                    "challenge": conn.challenge,
                    "pod": {
                        "name": pod.metadata.name,
                        "namespace": pod.metadata.namespace,
                        "created": pod.metadata.creation_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    }
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


class PodListRoute:
    def on_get(self, req, resp):
        client: kube.KubeClient = kube.KubeClient.get()
        pod_list: V1PodList = client.api.list_namespaced_pod(namespace="ctf")
        pods = pod_list.items
        output = []
        for pod in pods:
            pod: V1Pod = pod
            output.append({
                "name": pod.metadata.name,
                "team": pod.metadata.labels.get("ctf_team"),
                "challenge": pod.metadata.labels.get("ctf_challenge"),
                "created": pod.metadata.creation_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            })
        resp.media = output


class PodRoute:
    def on_get(self, req, resp, team, challenge):
        client: kube.KubeClient = kube.KubeClient.get()
        pod: V1Pod = client.get_pod(team, challenge)
        if not pod:
            resp.status = falcon.HTTP_NOT_FOUND
            resp.media = {"success": False}
            return

        resp.media = {
            "name": pod.metadata.name,
            "team": pod.metadata.labels.get("ctf_team"),
            "challenge": pod.metadata.labels.get("ctf_challenge"),
            "created": pod.metadata.creation_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }

    def on_delete(self, req, resp, team, challenge):
        client: kube.KubeClient = kube.KubeClient.get()
        pod: V1Pod = client.get_pod(team=team, challenge=challenge)
        if not pod:
            resp.status = falcon.HTTP_NOT_FOUND
            resp.media = {"success": False}
            return
        try:
            client.api.delete_namespaced_pod(name=pod.metadata.name, namespace=pod.metadata.namespace,
                                             grace_period_seconds=0)
        except Exception as e:
            logger.warning("Failed to delete pod %s", pod.metadata.name, exc_info=e)
            resp.media = {"success": False}
            return

        resp.media = {"success": True}


def run_web_server(ip_address: str, port: int):
    api = falcon.API()
    api.add_route("/", IndexRoute())
    api.add_route("/ssh/connections", SSHConnectionListRoute())
    api.add_route("/ssh/connections/{conn_id}", SSHConnectionRoute())
    api.add_route("/ssh/pods", PodListRoute())
    api.add_route("/ssh/pods/{team}/{challenge}", PodRoute())

    logger.info("Listening for connections on %s:%s", ip_address, port)
    waitress.serve(api, host=ip_address, port=port, _quiet=True)
