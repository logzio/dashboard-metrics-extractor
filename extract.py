import sys

import settings_reader
import metrics_dashboard_extractor
import timeseries_extractor

SCRIPT_VERSION = "0.1.1"

if __name__ == '__main__':
    print(f"*** Running script version {SCRIPT_VERSION} ***")
    menu_choice = settings_reader.read_menu_input()
    if menu_choice == 1:
        config = settings_reader.get_config()
        distinct_metrics = metrics_dashboard_extractor.get_total_metrics_count(config)
        timeseries_extractor.get_prometheus_timeseries_count(config, distinct_metrics)
    elif menu_choice == 2:
        metrics_dashboard_extractor.logzio_metrics_extractor()
