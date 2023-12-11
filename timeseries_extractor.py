import json
import logging
import re

import requests

logger = logging.getLogger()

PROMETHEUS_BASE_QUERY_URL = '/api/v1/query'
PROMETHEUS_API_QUERY_PREFIX = '?query='
PROMETHEUS_TOTAL_TIMESERIES_COUNT_METRIC = 'prometheus_tsdb_head_series['
PROMETHEUS_LAST_OVER_TIME_QUERY_PREFIX = 'last_over_time('
PROMETHEUS_COUNT_FUNCTION_PREFIX = 'count('
CLOSING_PERENTHESIS = ')'
PROMETHEUS_INTERVAL_TIME_FUNCTION_SUFFIX = f'])'
PROMETHEUS_METRIC_NAME_PREFIX = '{__name__=~"'
PROMETHEUS_METRIC_NAME_CLOSING_PERENTHESIS = '"}'
PROMETHEUS_ACTIVE_TIMESERIES_INTERVAL_REGEX = r'^\d+m$'
DEFAULT_TIMESERIES_COUNT_INTERVAL = '5m'
MAX_QUERY_RETRIES = 4


def _count_prometheus_total_timeseries(response) -> int:
    timeseries_count = 0
    if response.status_code == 200:
        response_json = json.loads(response.content)
        try:
            timeseries_count = response_json.get('data').get('result')[0].get('value')[1]
        except Exception:
            logger.error(f"An error occurred while trying to parse response json for total timeseries count")
        return timeseries_count
    else:
        logger.error(f"Prometheus API returned error: {response.error_code} for total timeseries count query")
    return timeseries_count


def get_prometheus_timeseries_count(config: dict, metrics):
    used_timeseries_count = 0
    try:
        prometheus_config = config['prometheus']
        if prometheus_config.get('endpoint'):
            timeseries_interval = extract_timeseries_interval(prometheus_config)
            total_timeseries_count = _get_total_timeseries_count(prometheus_config.get('endpoint'), timeseries_interval)
            if metrics:
                used_timeseries_count, used_metrics_and_count = _get_used_timeseries_count(
                    prometheus_config.get('endpoint'),
                    timeseries_interval, metrics)
            else:
                logger.error(
                    "An error occurred when fetching distinct metrics from grafana dashboards, skipping count of used "
                    "timeseries count")
            if total_timeseries_count:
                logger.info(f'*** Total time series in the last {timeseries_interval}: {total_timeseries_count} ***')
                logger.info(f'*** Used time series in the last {timeseries_interval}: {used_timeseries_count} ***')
                if used_timeseries_count > 0:
                    logger.info(f"*** Detailed metrics and count:\n{json.dumps(used_metrics_and_count)} ***")
        else:
            logger.info("No prometheus endpoint found, skipping timeseries count")
    except KeyError:
        logger.error('Invalid config for prometheus server, skipping time series count')


def extract_timeseries_interval(prometheus_config):
    timeseries_interval = prometheus_config.get('timeseries_count_interval')
    if timeseries_interval and not re.match(PROMETHEUS_ACTIVE_TIMESERIES_INTERVAL_REGEX,
                                            timeseries_interval):
        logger.info(
            f"Timeseries count interval was not entered or invalid, using default of {DEFAULT_TIMESERIES_COUNT_INTERVAL}")
        timeseries_interval = DEFAULT_TIMESERIES_COUNT_INTERVAL
    return timeseries_interval


def _get_used_timeseries_count(endpoint, used_timeseries_interval, metrics) -> (int, dict):
    query_url = endpoint + PROMETHEUS_BASE_QUERY_URL
    used_timeseries_sum = 0
    query_retry_count = 1
    used_metrics_and_count = {}
    count_sum, failed_metrics = count_active_timeseries_for_metrics(metrics, query_url,
                                                                    used_timeseries_interval,
                                                                    used_metrics_and_count)
    used_timeseries_sum += count_sum
    while (len(failed_metrics) > 0 and query_retry_count <= MAX_QUERY_RETRIES):
        logger.warn(
            f"There was an issue querying prometheus for some of the metrics, retrying (attempt {query_retry_count})...")
        count_sum, failed_metrics = count_active_timeseries_for_metrics(failed_metrics,
                                                                        query_url,
                                                                        used_timeseries_interval,
                                                                        used_metrics_and_count)
        query_retry_count += 1
    if len(failed_metrics) > 0:
        logger.error(f"Some of the metric queries could not be completed due to errors: {failed_metrics}")
    return int(count_sum), used_metrics_and_count


def count_active_timeseries_for_metrics(metrics, query_url,
                                        used_timeseries_interval, used_metrics_and_count):
    metric_base_query = PROMETHEUS_COUNT_FUNCTION_PREFIX + PROMETHEUS_LAST_OVER_TIME_QUERY_PREFIX + PROMETHEUS_METRIC_NAME_PREFIX
    used_timeseries_sum = 0
    failed_metrics = []
    for i, metric in enumerate(metrics):
        metric_get_query = metric_base_query + metric + PROMETHEUS_METRIC_NAME_CLOSING_PERENTHESIS + f'[{used_timeseries_interval}' + PROMETHEUS_INTERVAL_TIME_FUNCTION_SUFFIX + CLOSING_PERENTHESIS
        logger.info(f"Prometheus used timeseries count query: {metric_get_query}")
        try:
            response = requests.get(query_url, params={"query": metric_get_query})
            if not response.text:
                logger.warn(f"Empty response for query {metric_get_query}")
                continue
            data = json.loads(response.text)
            result_length = len(data.get('data', {}).get('result', []))
            if not result_length:
                logger.warn(f"Empty result for query {metric_get_query}")
                continue
            value = float(data['data']['result'][0]['value'][1])
            logger.info(f"None empty result with value: {value}")
            used_timeseries_sum += value
            used_metrics_and_count[metric] = int(value)
        except Exception as e:
            failed_metrics.append(metric)
            logger.error(f"Failed querying metric: {metric}, with error: {e}")
    return used_timeseries_sum, failed_metrics


def _get_total_timeseries_count(endpoint, total_count_timeseries_interval) -> int:
    total_timeseries_count_url = endpoint + PROMETHEUS_BASE_QUERY_URL + PROMETHEUS_API_QUERY_PREFIX + PROMETHEUS_LAST_OVER_TIME_QUERY_PREFIX + PROMETHEUS_TOTAL_TIMESERIES_COUNT_METRIC + total_count_timeseries_interval + PROMETHEUS_INTERVAL_TIME_FUNCTION_SUFFIX
    logger.info(f"Prometheus total timeseries count query url: {total_timeseries_count_url}")
    try:
        response = requests.get(
            total_timeseries_count_url)
        if response.status_code != 200:
            logger.error(
                "Recieved status code: {} from prometheus, cannot complete the total time series request".format(
                    response.status_code))
            return
        return _count_prometheus_total_timeseries(response)
    except requests.HTTPError:
        logger.error(
            "Cannot get a response from prometheus server, please check the config file")
    except Exception as e:
        logger.error(
            f"An error occurred when trying to query prometheus server: {e}")
