# Dashboard-metrics-extractor
Python scripts that extract metric names from Grafana dashboards, and time series from prometheus.

## How to use

### 1. Start the dashboard metrics extractor

You can start the dashboard metrics extractor either by running it as a python script or as an executable.

* To start the dashboard metrics extractor as an executable (Mac/Linux):

 Run the following command in the terminal:

```bash 
$ curl -L -O https://github.com/logzio/dashboard-metrics-extractor/releases/download/V0.0.2/extract \
       && sudo chmod 755 extract \
       && ./extract
```
* To start the dashboard metrics extractor as an executable (Windows):

 Download and run the executable (extract.exe) from the release page


To start the dashboard metrics extractor as a python script:

1. Clone the repository `git clone https://github.com/logzio/dashboard-metrics-extractor.git`
2. Run the following command in the repository folder:

``` bash
$ pip3 install -r requirements.txt \
&& python3 extract.py
```



### 2. Select the method to extract metrics

The dashboard metrics extractor can extract metrics either from the Grafana/Prometheus endpoints or from the Logz.io endpoint. To select the required method:

* Type **1** to select the Grafana/Prometheus endpoints and press Enter.
* Type **2** to select the Logz.io endpoint and press Enter.

### 3. Run the dashboard metrics extractor using the selected method

#### Extract metrics from the Grafana/Prometheus endpoint

If you select the Grafana/Prometheus endpoints, you need to specify these endpoints either via a config file or manually.

To specify the endpoints via a config file:

* Enter the path to the config file and press Enter.

To specify the endpoints manually:

1. Press Enter.
2. Type in the Prometheus endpoint address, for example `http://127.0.0.1:7000`, and press Enter.
3. Type in the Grafana endpoint address, for example `http://127.0.0.1:8000`, and press Enter.
4. Type in your Grafana API token and press Enter.


#### Extract metrics from the Logz.io endpoint

If you select the Logz.io endpoints, you need to specify the endpoint either via the `prom_dashboard.json` file or manually.

To specify the endpoint via `prom_dashboard.json`:

1. Make sure the `prom_dashboard.json` is located in the same folder as the dashboar metrics extractor exacutable.
2. Type **1** and press Enter.

To specify the endpoints manually:

1. Type **2** and press Enter.
2. Type in the region of your Logz.io metrics account, for example `us`, and press Enter.
3. Type in your Logz.io **API token** (not the data shipping token) and press Enter.

## Example data

### Example config:
    prometheus:
      endpoint: http://127.0.0.1:7000

    grafana:
      endpoint: http://127.0.0.1:8000
      token: <<GRAFANA_API_TOKEN>>

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
* The script can't extract metrics from panels with ES datasource
* Working only with editable dashboards
* Working only with valid dashboards (If grafana can't load it, the script won't extract the metrics)

