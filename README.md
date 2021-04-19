# Dashboard-metrics-extractor
Python scripts that extract metric names from Grafana dashboards.

Dependencies:

| Libarary name | Version | Install command |
|---|---|---|
|[pygments_promql](https://pypi.org/project/pygments-promql/)|0.0.5|`pip install pygments-promql` |
|Python|3.7| - |

## How to use

* Clone the repository `git clone https://github.com/logzio/dashboard-metrics-extractor.git`
* Run the script 
``` bash
python extract.py
```

You will have two options to load dashboards:
1. Manually add dashboards jsons (comma seperated) to `prom_dashboard.json` file
2. Provide the account region and api token (Not data shiping), if you use this option the script will perform api calls to get all of the grafana dashboards in the logzio account

### Example output
```text
Total number of metrics in K8s Cluster Summary : 24
------------
kube_deployment_status_replicas
kube_deployment_status_replicas_unavailable
kube_deployment_status_replicas_updated
kube_job_status_active
kube_job_status_failed
kube_job_status_succeeded
kube_node_spec_unschedulable
kube_node_status_allocatable_cpu_cores
kube_node_status_allocatable_memory_bytes
kube_node_status_allocatable_pods
kube_node_status_capacity_cpu_cores
kube_node_status_capacity_memory_bytes
kube_node_status_capacity_pods
kube_node_status_condition
kube_pod_container_resource_requests_cpu_cores
kube_pod_container_resource_requests_memory_bytes
kube_pod_container_status_restarts_total
kube_pod_container_status_running
kube_pod_container_status_terminated
kube_pod_container_status_waiting
kube_pod_status_phase
node_boot_time
node_filesystem_free
node_filesystem_size
As regex: 
kube_deployment_status_replicas|kube_deployment_status_replicas_unavailable|kube_deployment_status_replicas_updated|kube_job_status_active|kube_job_status_failed|kube_job_status_succeeded|kube_node_info|kube_node_spec_unschedulable|kube_node_status_allocatable_cpu_cores|kube_node_status_allocatable_memory_bytes|kube_node_status_allocatable_pods|kube_node_status_capacity_cpu_cores|kube_node_status_capacity_memory_bytes|kube_node_status_capacity_pods|kube_node_status_condition|kube_pod_container_resource_requests_cpu_cores|kube_pod_container_resource_requests_memory_bytes|kube_pod_container_status_restarts_total|kube_pod_container_status_running|kube_pod_container_status_terminated|kube_pod_container_status_waiting|kube_pod_info|kube_pod_status_phase|node_boot_time|node_filesystem_free|node_filesystem_size
------------
```

You can use the output Regex expression to filter metric names when you ship your data, for example in prometheus you can use `relabel_configs`
```yaml
relabel_configs:
  - source_labels: [__name__]
    action: keep
    regex: <<your-regex>>
```

## Limitations
* The script cant extract metrics from panels with ES datasource
* Working only with editble dashboards
* Working only with valid dashboards (If grafana cant load it, the script cant extract the metrics)
* As for now the total number of metrics is not 100% accurate, as in some cases the script detects labels as metric names

