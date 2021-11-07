import json
import logging
import re
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers.promql import PromQLLexer
import requests

logger = logging.getLogger()

PROMQL_FUNCTIONS = ['sum', 'sumwithout', 'sumby', 'maxwithout', 'maxby', 'countwithout', 'countby']
PROMQL_GROUPING_STATEMENTS = ['by(', 'on(', ',', 'group_right(', 'group_left(', 'sum_rate(']
REGEX_FILTER = '[a-zA-Z_:][a-zA-Z0-9_:]*'


def _find_grouping(query_string):
    grouping_indices = []
    for statement in PROMQL_GROUPING_STATEMENTS:
        try:
            indices = [i for i in range(len(query_string)) if query_string.startswith(statement, i)]
            for idx in indices:
                grouping_indices.append(idx + len(statement))
        except ValueError:
            print(f'Error while group parsing, query string: {query_string}')

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
    if targets is not None:
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
    templating = dashboard['templating']['list']
    metrics = []
    for var in templating:
        if var['type'] == 'query':
            try:
                names = re.findall(REGEX_FILTER, str(var['query']))
                label_values_index = names.index('label_values')
                metrics.append(names[label_values_index + 1])
            except (IndexError, ValueError):
                dashboard_name = dashboard['title']
                print(
                    f'ERROR in dashboard {dashboard_name}, cannot parse: "{var["query"]}", dashboard might not be supported, skipping')
                break
    return metrics


def _to_regex(list):
    pattern = ''
    for i, metric in enumerate(list):
        pattern = f'{pattern}{metric}' if i == 0 else f'{pattern}|{metric}'
    print(f'As regex: \n{pattern}')


def _add_panels_metrics(dashboard, i, dataset):
    try:
        for row in dashboard['rows']:
            for panel in row['panels']:
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
    for i, uid in enumerate(uid_list):
        response = requests.get(f'{base_url}/api/dashboards/uid/{uid}', headers=headers)
        dashboard = response.json()
        try:
            del dashboard['meta']
            dashboards.append(dashboard['dashboard'])
        except KeyError:
            dash_title = dashboard['dashboard']['title']
            print(f'Error while removing meta from dashboard: {dash_title}')
    return dashboards


def _count_total_metrics(all_metrics, dataset) -> list:
    for s in dataset:
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


def logzio_metrics_extractor():
    choice = input("select:\n1. load data from `prom_dashboard.json`\n2. load data using api token\n")
    if int(choice) == 1:
        data = open('prom_dashboard.json')
        dashboards = json.load(data)
    elif int(choice) == 2:
        dashboards = _get_dashboards_logzio_api()
    else:
        raise ValueError('Input must be 1 or 2')

    dataset = []
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
            print('Error while parsing the dashboard panels')
    all_metrics = []
    _count_total_metrics(all_metrics, dataset)


def _get_dashboards_logzio_api():
    region = input("Enter logzio region:")
    api_token = input("Enter logzio api token:")

    supported_regions = ['us', 'eu', 'uk', 'nl', 'ca', 'au', 'wa']
    if region not in supported_regions:
        raise ValueError('region code is not supported: {}'.format(region))
    regex = '^[a-z 0-9]+-[a-z 0-9]+-[a-z 0-9]+-[a-z 0-9]+-[a-z 0-9]+$'
    match_obj = re.search(regex, api_token)
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
    uids = _extract_uid_from_response(all_dashboards)
    # init list
    return _init_dashboard_list(base_url, uids, LOGZIO_API_HEADERS)
