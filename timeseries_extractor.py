import json
import logging
import re

import requests

logger = logging.getLogger()

PROMETHEUS_API_QUERY_PREFIX = '/api/v1/query?query='
PROMETHEUS_TOTAL_TIMESERIES_COUNT_METRIC = 'prometheus_tsdb_head_series'
PROMETHEUS_LAST_OVER_TIME_QUERY_PREFIX = 'last_over_time('
PROMETHEUS_COUNT_FUNCTION_PREFIX = 'count('
CLOSING_PERENTHESIS = ')'
PROMETHEUS_INTERVAL_TIME_FUNCTION_SUFFIX = f'[])'
PROMETHEUS_METRIC_NAME_PREFIX = '{__name__=~"'
PROMETHEUS_METRIC_NAME_CLOSING_PERENTHESIS = '"}'
PROMETHEUS_ACTIVE_TIMESERIES_INTERVAL_REGEX = r'^\d+m$'
DEFAULT_USED_TIMESERIES_INTERVAL = '5m'


def _count_prometheus_total_timeseries(response):
    response_json = json.loads(response.content)
    timeseries_count = response_json.get('data').get('result')[0].get('value')[1]
    print('Total time series count: {}'.format(timeseries_count))


def get_prometheus_timeseries_count(config: dict, metrics):
    try:
        prometheus_config = config['prometheus']
        if prometheus_config.get('endpoint'):
            _get_total_timeseries_count(prometheus_config.get('endpoint'))
            _get_used_timeseries_count(prometheus_config.get('endpoint'),
                                       prometheus_config.get('used_timeseries_interval'), metrics)
        else:
            logger.info("No prometheus endpoint found, skipping timeseries count")
    except KeyError:
        logger.error('Invalid config for prometheus server, skipping time series count')


def _get_used_timeseries_count(endpoint, used_timeseries_interval, metrics):
    if used_timeseries_interval and not re.match(PROMETHEUS_ACTIVE_TIMESERIES_INTERVAL_REGEX, used_timeseries_interval):
        logger.info(
            f"Used timeseries interval was not entered or invalid, using default of {DEFAULT_USED_TIMESERIES_INTERVAL}")
        used_timeseries_interval = DEFAULT_USED_TIMESERIES_INTERVAL

    query_url = endpoint + PROMETHEUS_API_QUERY_PREFIX + PROMETHEUS_COUNT_FUNCTION_PREFIX + PROMETHEUS_LAST_OVER_TIME_QUERY_PREFIX + PROMETHEUS_METRIC_NAME_PREFIX
    metrics_regex = ''
    for i, metric in enumerate(metrics):
        metrics_regex += metric
        if i < len(metrics) - 1:
            metrics_regex += '|'
    query_url += metrics_regex + PROMETHEUS_METRIC_NAME_CLOSING_PERENTHESIS + f'[{used_timeseries_interval}])' + CLOSING_PERENTHESIS
    response = requests.get(query_url)
    if response.status_code == 200:
        response_json = json.loads(response.content)
        try:
            used_timeseries_count = response_json.get('data').get('result')[0].get('value')[1]
        except Exception:
            used_timeseries_count = 0
        print(f'Total used time series in the last {used_timeseries_interval}: {used_timeseries_count}')
    else:
        logger.error(
            "Recieved status code: {} from prometheus, cannot complete the used time series request".format(
                response.status_code))


def _get_total_timeseries_count(endpoint):
    try:
        response = requests.get(
            endpoint + PROMETHEUS_API_QUERY_PREFIX + PROMETHEUS_LAST_OVER_TIME_QUERY_PREFIX + PROMETHEUS_TOTAL_TIMESERIES_COUNT_METRIC + PROMETHEUS_INTERVAL_TIME_FUNCTION_SUFFIX)
        if (response.status_code != 200):
            logger.error(
                "Recieved status code: {} from prometheus, cannot complete the total time series request".format(
                    response.status_code))
            return
        _count_prometheus_total_timeseries(response)
    except requests.HTTPError:
        logger.error(
            "Cannot get a response from prometheus server, please check the config file")
