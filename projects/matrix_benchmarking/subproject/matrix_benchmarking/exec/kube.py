import kubernetes.client
import kubernetes.config
import kubernetes.utils

kubernetes.config.load_kube_config()

corev1 = kubernetes.client.CoreV1Api()
appsv1 = kubernetes.client.AppsV1Api()
batchv1 = kubernetes.client.BatchV1Api()
custom = kubernetes.client.CustomObjectsApi()

k8s_client = kubernetes.client.ApiClient()
