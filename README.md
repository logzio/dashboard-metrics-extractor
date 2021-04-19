# Dashboard-metrics-extractor
Python scripts that extract metric names from Grafana dashboards.
## How to use

* cd into this directory `cd dashboard-metrics-extractor`

### For prometheus dashboards
dependencies:
| Libarary name | Version | Install command |
|---|---|---|
|[pygments_promql](https://pypi.org/project/pygments-promql/)|0.0.5|`pip install pygments-promql` |
|Python|3.7| - |

* Add dashboards jsons (comma seperated) to `prom_dashboard.json` file
* Run script 👇
``` bash
python prom_metrics.py
```

