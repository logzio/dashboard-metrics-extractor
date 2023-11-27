import logging
import yaml

logger = logging.getLogger()


def read_menu_input() -> int:
    menu_choice = input(
        "Please enter 1 for extracting data from grafana and prometheus endpoints, or 2 for extracting metrics from "
        "logz.io: ")
    return int(menu_choice)


def get_config() -> dict:
    config_path = input('Please enter config file path, or enter to insert input manually: ')
    if config_path is not None:
        try:
            with open(f'{config_path}', 'r') as config:
                config = yaml.safe_load(config)
                return config
        except FileNotFoundError:
            grafana_endpoint = input('No config file found, please enter grafana endpoint: ')
            grafana_api_token = input('Please enter grafana api token: ')
            prometheus_endpoint = input('Please enter prometheus endpoint: ')
            prometheus_used_timeseries_interval = input(
                'Please enter prometheus timeseries count interval in minutes (i.e 1m, 2m) or enter to use the default of 5m (recommended): ')
            return {'grafana': {'endpoint': grafana_endpoint, 'token': grafana_api_token},
                    'prometheus': {'endpoint': prometheus_endpoint,
                                   'timeseries_count_interval': prometheus_used_timeseries_interval}}
