import json
import logging
import os
import re
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers.promql import PromQLLexer
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

PROMQL_FUNCTIONS = ['sum', 'sumwithout', 'sumby', 'maxwithout', 'maxby', 'countwithout', 'countby']
PROMQL_GROUPING_STATEMENTS = ['by(', 'on(', ',', 'group_right(', 'group_left(', 'sum_rate(']
REGEX_FILTER = '[a-zA-Z_:][a-zA-Z0-9_:]*'
SUPPORTED_REGIONS = ['us', 'eu', 'uk', 'nl', 'ca', 'au', 'wa']
TOKEN_REGEX = '^[a-z 0-9]+-[a-z 0-9]+-[a-z 0-9]+-[a-z 0-9]+-[a-z 0-9]+$'


def _find_grouping(query_string):
    grouping_indices = []
    for statement in PROMQL_GROUPING_STATEMENTS:
        try:
            indices = [i for i in range(len(query_string)) if query_string.startswith(statement, i)]
            for idx in indices:
                grouping_indices.append(idx + len(statement))
        except ValueError:
            logger.error(f'Error while group parsing, query string: {query_string}')

    return grouping_indices


def _find_rules(expr):
    rules = []
    names = re.findall(REGEX_FILTER, expr)
    for name in names:
        if ':' in name:
            rules.append(name)
    return rules


def _find_metrics_names(expr):
    names = []
    rules = _find_rules(expr)
    grouping = []
    splited_query = highlight(expr, PromQLLexer(), HtmlFormatter()).split('"nv">')
    for ex in splited_query:
        ex = ex.split('<', 1)
        if ex[0] and ex[0] not in PROMQL_FUNCTIONS:
            names.append(ex[0])
    names = list(dict.fromkeys(names))
    grouping_indices = _find_grouping(expr)
    if grouping_indices:
        for name in names:
            indices = [i for i in range(len(expr)) if expr.startswith(name, i)]
            for idx in indices:
                for g_idx in grouping_indices:
                    if idx == g_idx:
                        grouping.append(name)
    return list(set(names) - set(grouping)), rules


def _add_metrics(panel, index, dataset):
    targets = panel.get('targets')
    if targets is not None and dataset[index].get('metrics') is not None:
        for target in targets:
            if target.get('expr') is not None:
                metrics, rules = _find_metrics_names(target['expr'].replace(' ', ''))
                dataset[index]['metrics'].extend(rules)
                for metric in metrics:
                    name_in_rules = False
                    for rule in rules:
                        if metric in rule:
                            name_in_rules = True
                    if metric == 'le' or name_in_rules:
                        pass
                    else:
                        dataset[index]['metrics'].append(metric)


def _extract_metrics(dashboard):
    dash_templating = dashboard.get('templating')
    if dash_templating is None:
        logger.error(f'No templating for dashboard: {dashboard}, skipping')
        return
    templating = dash_templating['list']
    metrics = []
    for var in templating:
        if var['type'] == 'query':
            try:
                names = re.findall(REGEX_FILTER, str(var['query']))
                label_values_index = names.index('label_values')
                metrics.append(names[label_values_index + 1])
            except (IndexError, ValueError):
                dashboard_name = dashboard['title']
                logger.error(
                    f'Cannot parse: "{var["query"]}" in {dashboard_name}, dashboard might not be '
                    f'supported, skipping')
                break
    return metrics


def check_metric_for_telegraf_input(metric, telegraf_mapping):
    input_end_index = 0
    try:
        input_end_index = metric.index('_')
    except ValueError:
        return

    if input_end_index > 0:
        input_name = metric[0:input_end_index]
        input_value = metric[input_end_index + 1:len(metric)]
        if input_name not in telegraf_mapping:
            telegraf_mapping[input_name] = set()
        telegraf_mapping[input_name].add(input_value)


def format_telegraf_fieldpass(field_list):
    fieldpass_pattern = '['
    telegraf_metric = ''
    for i, field in enumerate(field_list):
        fieldpass_pattern = f'{fieldpass_pattern}"{field}"' if i == 0 else f'{fieldpass_pattern},"{field}"'
    fieldpass_pattern += ']'
    return fieldpass_pattern


def print_telegraf_regex(telegraf_mapping):
    pattern = ''
    print('Telegraf filter by input:')
    for key, value in telegraf_mapping.items():
        pattern = format_telegraf_fieldpass(value)
        print(f'{key} fieldpass regex: {pattern}')


def _to_regex(list):
    pattern = ''
    telegraf_mapping = dict()
    for i, metric in enumerate(list):
        pattern = f'{pattern}{metric}' if i == 0 else f'{pattern}|{metric}'
        check_metric_for_telegraf_input(metric, telegraf_mapping)
    print(f'As Prometheus regex: \n{pattern}')
    print('------------')
    print_telegraf_regex(telegraf_mapping)


def _add_panels_metrics(dashboard, i, dataset):
    try:
        panels = dashboard.get('rows')
        if not panels:
            panels = dashboard['panels']
        for panel in panels:
            if panel['type'] == 'row':
                if panel.get('panels') is not None:
                    for row_panel in panel['panels']:
                        _add_metrics(row_panel, i, dataset)
            elif panel['type'] == 'text':
                pass
            else:
                _add_metrics(panel, i, dataset)
    except KeyError:
        dashboard_title = dashboard['title']
        logger.error(f'Could not parse dashboard panels, skipping panels for dashboard: {dashboard_title}')


def _extract_dashboards_metrics(base_url, headers, response):
    uid_list = _extract_uid_from_response(response)
    dataset = []
    all_metrics = []
    dashboards = _init_dashboard_list(base_url, uid_list, headers)
    for i, dashboard in enumerate(dashboards):
        metrics = _extract_metrics(dashboard)
        dataset.append({
            'name': dashboard['title'],
            'metrics': metrics
        })
        _add_panels_metrics(dashboard, i, dataset)
    return _count_total_metrics(all_metrics, dataset)


def _init_dashboard_list(base_url, uid_list, headers=None):
    dashboards = []
    logger.info('Initializing dashboards list from uids')
    for i, uid in enumerate(uid_list):
        response = requests.get(f'{base_url}/api/dashboards/uid/{uid}', headers=headers)
        if response.status_code != 200:
            response_message = response.text
            logger.error(f'Encountered in error while fetching dashboard with uid: {uid}, message: {response_message}')
        dashboard = response.json()
        try:
            del dashboard['meta']
            dashboards.append(dashboard['dashboard'])
        except KeyError:
            dash_title = dashboard['dashboard']['title']
            logger.error(f'Error while removing meta from dashboard: {dash_title}')
    return dashboards


def _count_total_metrics(all_metrics, dataset) -> list:
    for s in dataset:
        if s['metrics'] is None:
            continue
        s['metrics'] = sorted(list(dict.fromkeys(s['metrics'])))
        if len(s['metrics']) > 0:
            print('------------')
            print('Total number of metrics in {} : {}'.format(s['name'], len(s['metrics'])))
            print('------------')
            for metric in s['metrics']:
                print(metric)
            _to_regex(s['metrics'])
            all_metrics.extend(s['metrics'])
    all_metrics = sorted(list(set(all_metrics)))
    print('------------')
    print(f'Total number of distinct metrics: {len(all_metrics)}')
    print('------------')
    for metric in all_metrics:
        print(metric)
    _to_regex(all_metrics)
    return all_metrics


def _extract_uid_from_response(response):
    logger.info('Extracting dashboards uids')
    if response.status_code != 200:
        raise requests.ConnectionError(response.text)
    response_json = json.loads(response.content)
    uid_list = []
    for dashboard in response_json:
        if dashboard['type'] == 'dash-db':
            uid_list.append(dashboard.get('uid'))
    return uid_list


def get_total_metrics_count(config):
    try:
        grafana_config = config['grafana']
        if grafana_config.get('endpoint') is not None:
            try:
                base_url = grafana_config.get('endpoint')
                headers = {'Authorization': 'Bearer ' + grafana_config['token'],
                           'Content-Type': 'application/json', 'Accept': 'application/json'}
                response = requests.get(
                    base_url + '/api/search'
                    , headers=headers)
                if response.status_code != 200:
                    logger.error(
                        "Received status code: {} , cannot complete dashboards fetch".format(response.status_code))
                    return
                return _extract_dashboards_metrics(base_url, headers, response)
            except requests.HTTPError:
                logger.error(
                    "Cannot get a response from grafana api, please check the input")
        else:
            logger.error("Could not find Grafana endpoint in config file")
    except KeyError:
        logger.error('Invalid input for grafana api, skipping dashboard metrics count')


def get_dashboards_from_folder():
    dashboards = []
    filenames = os.listdir("dashboards")
    for filename in filenames:
        dashboard = json.load(open("dashboards/" + filename))
        dashboards.append(dashboard)
    return dashboards


def logzio_metrics_extractor():
    choice = input("select:\n1. load data from the dashboards folder\n2. load data using api token\n")
    if int(choice) == 1:
        dashboards = get_dashboards_from_folder()
    elif int(choice) == 2:
        dashboards = _get_dashboards_logzio_api()
    else:
        raise ValueError('Input must be 1 or 2')

    handle_dashboards(dashboards)


def handle_dashboards(dashboards):
    dataset = []
    if dashboards is not None:
        for i, dashboard in enumerate(dashboards):
            var_metrics = _extract_metrics(dashboard)
            dataset.append({
                'name': dashboard['title'],
                'metrics': var_metrics
            })
            try:
                for panel in dashboard['panels']:
                    if panel['type'] == 'row':
                        if panel.get('panels') is not None:
                            for row_panel in panel['panels']:
                                _add_metrics(row_panel, i, dataset)
                    elif panel['type'] == 'text':
                        pass
                    else:
                        _add_metrics(panel, i, dataset)
            except KeyError:
                dashboard_name = dashboard['title']
                logger.error(f'Error while parsing the dashboard panels for {dashboard_name}')
        all_metrics = []
        _count_total_metrics(all_metrics, dataset)


def _get_dashboards_logzio_api():
    region = input("Enter logzio region:")
    api_token = input("Enter logzio api token:")

    if region not in SUPPORTED_REGIONS:
        raise ValueError('region code is not supported: {}'.format(region))
    match_obj = re.search(TOKEN_REGEX, api_token)
    if match_obj is None or match_obj.group() is None:
        raise ValueError("API token is invalid: {}".format(api_token))
    LOGZIO_API_HEADERS = {
        'X-API-TOKEN': api_token,
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache',
        'User-Agent': None
    }
    base_url = 'https://api.logz.io/v1/grafana' if region == 'us' else f'https://api-{region}.logz.io/v1/grafana/'
    all_dashboards = requests.get(f'{base_url}/api/search', headers=LOGZIO_API_HEADERS)
    dashboard_list = None
    try:
        uids = _extract_uid_from_response(all_dashboards)
        dashboard_list = _init_dashboard_list(base_url, uids, LOGZIO_API_HEADERS)
    except requests.ConnectionError as e:
        logger.error(f"Encountered an error: {str(e)}")
    # init list
    return dashboard_list
