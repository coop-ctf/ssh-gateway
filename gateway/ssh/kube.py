import logging
from datetime import datetime
from time import sleep
from typing import Optional

from kubernetes import client, config
from kubernetes.config import ConfigException

logger = logging.getLogger("gateway.kube")


class KubeClient:
    INSTANCE = None

    def __init__(self, api: client.CoreV1Api):
        self.api = api

    @staticmethod
    def get():
        return KubeClient.INSTANCE

    def create_pod(self, name: str, image: str) -> Optional[client.V1Pod]:
        try:
            container = client.V1Container(
                name=f"{name}-c",
                image=image,
                image_pull_policy="Never"
            )
            spec = client.V1PodSpec(containers=[container])
            metadata = client.V1ObjectMeta(name=f"{name}-p")
            pod = client.V1Pod(metadata=metadata, spec=spec)
            return self.api.create_namespaced_pod(namespace="default", body=pod)
        except Exception as e:
            logger.error(f"Error while creating pod {name}", exc_info=e)
            return None

    def wait_until_pod_has_ip(self, pod: client.V1Pod, timeout_s: float) -> Optional[str]:
        max_time = datetime.now().timestamp() + timeout_s
        try:
            while True:
                if max_time < datetime.now().timestamp():
                    return None
                sleep(0.5)
                status = self.api.read_namespaced_pod_status(
                    name=pod.metadata.name, namespace=pod.metadata.namespace).status
                if str(status.pod_ip) != "None":
                    return status.pod_ip
        except Exception as e:
            logger.error(f"Error while waiting for pod {pod.metadata.name}", exc_info=e)
            return None


def connect_to_kube() -> Optional[KubeClient]:
    try:
        config.load_incluster_config()
    except ConfigException as e:
        logger.warning("Cannot connect to Kubernetes cluster", exc_info=e)
        return None

    api = client.CoreV1Api()
    KubeClient.INSTANCE = KubeClient(api)
    return KubeClient.INSTANCE