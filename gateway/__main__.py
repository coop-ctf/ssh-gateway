import logging
import os
import threading
import warnings

from cryptography.utils import CryptographyDeprecationWarning

from gateway.ssh import kube
from gateway.ssh.ctf import CTF
from gateway.ssh.server import run_ssh_server
from gateway.web.server import run_web_server

logging.basicConfig(format='%(asctime)s - [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("gateway")
logger.setLevel(logging.DEBUG)


# def connect_to_kubernetes():
#     from kubernetes import config, client
#     config.load_incluster_config()
#     api = client.CoreV1Api()
#     container = client.V1Container(
#         name="child-container",
#         image="momothereal/ctf-linux-linux-cat",
#         image_pull_policy="Never"
#     )
#     spec = client.V1PodSpec(containers=[container])
#     metadata = client.V1ObjectMeta(name="child-pod")
#     pod = client.V1Pod(metadata=metadata, spec=spec)
#     pod = api.create_namespaced_pod(namespace="default", body=pod)
#     try:
#         while True:
#             sleep(0.5)
#             status = api.read_namespaced_pod_status(name=pod.metadata.name, namespace=pod.metadata.namespace).status
#             if str(status.pod_ip) != "None":
#                 logger.info("Pod available at IP %s", status.pod_ip)
#                 break
#     except Exception as e:
#         logger.error("Error", exc_info=e)
#         while True:
#             sleep(1)
# container = client.V1Container(
#     name="nginx",
#     image="nginx:1.7.9",
#     ports=[client.V1ContainerPort(container_port=80)])
# # Create and configure a spec section
# template = client.V1PodTemplateSpec(
#     metadata=client.V1ObjectMeta(labels={"app": "nginx"}),
#     spec=client.V1PodSpec(containers=[container]))
# # Create the specification of deployment
# spec = client.V1ReplicationControllerSpec(replicas=3, template=template)
# controller = client.V1ReplicationController(
#     spec=spec, metadata=client.V1ObjectMeta(name="test-rep-controller"))
# print(api.create_namespace(client.V1Namespace(metadata=client.V1ObjectMeta(name="ssh-challenges"))))
# response = api.create_namespaced_replication_controller(namespace="ssh-challenges", body=controller)
# print(response)
# sleep(5)
# print(api.list_namespaced_pod(namespace="ssh-challenges"))


class SSHGatewayServer(threading.Thread):
    def run(self):
        run_ssh_server(ip_address=os.getenv("SSH_HOST", ""),
                       port=2200, host_key_file="host.key", backend_key_file="backend.key")


class WebServer(threading.Thread):
    def run(self):
        run_web_server(os.getenv("WEB_HOST", "127.0.0.1"), 2201)


if __name__ == '__main__':
    warnings.filterwarnings(
        action='ignore',
        category=CryptographyDeprecationWarning
    )
    CTF.load_teams()
    kube.connect_to_kube()
    WebServer().start()
    SSHGatewayServer().start()
