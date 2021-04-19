import json
import re
import yaml

import requests
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments_promql import PromQLLexer


def _find_grouping(query_string):
    grouping_indices = []
    grouping_statements = ['by(', 'on(', ',', 'group_right(', 'group_left(', 'sum_rate(']
    for statement in grouping_statements:
        try:
            indices = [i for i in range(len(query_string)) if query_string.startswith(statement, i)]
            for idx in indices:
                grouping_indices.append(idx + len(statement))
        except ValueError:
            pass

    return grouping_indices


def _find_rules(expr):
    rules = []
    names = re.findall('[a-zA-Z_:][a-zA-Z0-9_:]*', expr)
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
        if ex[0]:
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


def _add_metrics(panel, i):
    for target in panel['targets']:
        metrics, rules = _find_metrics_names(target['expr'].replace(' ', ''))
        dataset[i]['metrics'].extend(rules)
        for metric in metrics:
            name_in_rules = False
            for rule in rules:
                if metric in rule:
                    name_in_rules = True
            if metric == 'le' or metric == 'p8s_logzio_name' or name_in_rules:
                pass
            else:
                dataset[i]['metrics'].append(metric)


def _to_regex(list):
    pattern = ''
    for i, metric in enumerate(list):
        pattern = f'{pattern}{metric}' if i == 0 else f'{pattern}|{metric}'
    print(f'As regex: \n--------------\n{pattern}')


def _init_dashboard_list(uid_list, base_url, r_headers):
    dashboards_list = []
    for uid in uid_list:
        request_url = f'{base_url}dashboards/uid/{uid}'
        response = requests.get(request_url, headers=r_headers)
        dashboard = response.json()
        try:
            del dashboard['meta']
            dashboards_list.append(dashboard['dashboard'])
        except KeyError:
            pass
    return dashboards_list


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
    base_url = 'https://api.logz.io/v1/grafana/api/' if region == 'us' else f'https://api-{region}.logz.io/v1/grafana/api/'
    all_dashboards = requests.get(f'{base_url}search', headers=LOGZIO_API_HEADERS).json()
    uids = []
    for item in all_dashboards:
        try:
            if item['type'] == 'dash-db':
                uids.append(item['uid'])
        except TypeError as e:
            raise TypeError(all_dashboards['message'])
    # init list
    return _init_dashboard_list(uids, base_url, LOGZIO_API_HEADERS)


def _get_varibles(templating):
    metrics = []
    for var in templating:
        if var['type'] == 'query':
            try:
                names = re.findall('[a-zA-Z_:][a-zA-Z0-9_:]*', var['query'])
                if names[0] == 'label_values':
                    metrics.append(names[1])
            except IndexError as e:
                print(f'Error while parsing "{var["query"]}", error:{e}')##
    return metrics


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
    var_metrics = _get_varibles(dashboard['templating']['list'])
    dataset.append({
        'name': dashboard['title'],
        'metrics': var_metrics
    })
    try:
        for panel in dashboard['panels']:
            if panel['type'] == 'row':
                for row_panel in panel['panels']:
                    _add_metrics(row_panel, i)
            elif panel['type'] == 'text':
                pass
            else:
                _add_metrics(panel, i)
    except KeyError:
        pass
all_metrics = []
for s in dataset:
    s['metrics'] = list(dict.fromkeys(s['metrics']))
    print('------------')
    print('Total number of metrics in {} : {}'.format(s['name'], len(s['metrics'])))
    print('------------')
    for metric in s['metrics']:
        print(metric)
    all_metrics.extend(s['metrics'])

all_metrics = list(set(all_metrics))
print('------------')
print(f'Total number of distinct metrics: {len(all_metrics)}')
print('------------')
for metric in all_metrics:
    print(metric)
_to_regex(all_metrics)
with open(f'prometheus_metrics_output.yaml', 'w') as yml_output:
    dataset.append({'name': 'all metrics',
                    'metrics': all_metrics})
    yaml.dump(dataset, yml_output, default_flow_style=False)
    yml_output.truncate()
    yml_output.close()
