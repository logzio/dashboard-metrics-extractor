# Dashboard-metrics-extractor
Python scripts that extract metric names from Grafana dashboards, and time series from prometheus.
The script will extract the metric names from all  grafana dashboards and provide a regex that can be used to with prometheus filter or telegraf fieldpass. 
When extracting metrics from grafana endpoint, the script will also count the total time series in the provided prometheus database (within interval)
and count the used timeseries of the extracted dashboard metrics (within interval).

## How to use

### 1. Start the dashboard metrics extractor

You can start the dashboard metrics extractor either by running it as a python script or as an executable.

* To start the dashboard metrics extractor as an executable (Mac/Linux):

 Run the following command in the terminal:

```bash 
$ curl -L -O https://github.com/logzio/dashboard-metrics-extractor/releases/download/V0.1.2/extract \
       && sudo chmod 755 extract \
       && ./extract
```
* To start the dashboard metrics extractor as an executable (Windows):

 Download and run the executable (extract.exe) from the release page


* To start the dashboard metrics extractor as a python script:

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
2. Type in the Grafana endpoint address, for example `http://127.0.0.1:8000`, and press Enter.
3. Type in your Grafana API token and press Enter.
4. Type in the Prometheus endpoint address, for example `http://127.0.0.1:7000`, and press Enter.
5. Type in the Prometheus timeseries count interval (only minutes timeframe is supported), for example `10m` or press Enter to use the default (5m).



#### Extract metrics from the Logz.io endpoint

If you select the Logz.io endpoints, you need to specify the dashboards input either via the `dashboards` folder or by the Logzio API token.

To specify the input via `dashboards` folder:

1. Make sure the `dashboards` folder is located in the same folder as the dashboard metrics extractor executable.
2. Place each dashboard file in the `dashboards` - the output will be presented with the dashboard name.
3. Type **1** and press Enter.

To specify the input via an API token:

1. Type **2** and press Enter.
2. Type in the region of your Logz.io metrics account, for example `us`, and press Enter.
3. Type in your Logz.io **API token** (not the data shipping token) and press Enter.

## Example data

### Example config:
    prometheus:
      endpoint: http://127.0.0.1:7000
      timeseries_count_interval: 5m    // optional. Only minute timeframe is supported. defaults to 5m.

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
Telegraf filter by input:
kube fieldpass regex: ["deployment_status_replicas","deployment_status_replicas_unavailable","deployment_status_replicas_updated","job_status_active","job_status_failed,"job_status_succeeded","node_spec_unschedulable","node_status_allocatable_cpu_cores","node_status_allocatable_memory_bytes","node_status_allocatable_pods","node_status_capacity_cpu_cores","node_status_capacity_memory_bytes","node_status_capacity_pods","node_status_condition","pod_container_resource_requests_cpu_cores","pod_container_resource_requests_memory_bytes","pod_container_status_restarts_total","pod_container_status_running","pod_container_status_terminated","pod_container_status_waiting","pod_status_phase"]
node fieldpass regex: ["boot_time","filesystem_free","filesystem_size"]
```

You can use the output Regex expression to filter metric names when you ship your data:
1. In prometheus you can use `relabel_configs`
```yaml
relabel_configs:
  - source_labels: [__name__]
    action: keep
    regex: <<your-regex>>
```

2. In telegraf you can use fieldpass:
```yaml
[[inputs.__name__]]:
  fieldpass = <<fieldpass-regex>>
```

## Limitations
* The script can't extract metrics from panels with ES datasource
* Working only with editable dashboards
* Working only with valid dashboards (If grafana can't load it, the script won't extract the metrics)
* Telegraf regex output might not be valid in the cases of custom metrics and dashboards that are not using telegraf metric namings.


## Changelog
* 0.1.2
  - Changed prometheus used timeseries query: 
    Each metric will be queried separately to avoid long response times and processing errors.
  - Added a retry mechanism for failed queries - up to 4 retries.
  - Improved logging and error handling.

