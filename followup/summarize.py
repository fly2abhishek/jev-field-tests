#!/usr/bin/env python3
"""Recompute the article's saved results offline; no credentials or API calls."""
import collections
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent
BIN_EDGES = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0]
LABELS = {'supported', 'refuted', 'not_stated'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(name):
    return json.loads((HERE / name).read_text())


def probability(value):
    require(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1,
            f'Invalid probability: {value!r}')
    return value


def bins(confidences, correct, edges):
    result = []
    for index, (low, high) in enumerate(zip(edges, edges[1:])):
        selected = [i for i, confidence in enumerate(confidences)
                    if low <= confidence < high or
                    (index == len(edges) - 2 and confidence == high)]
        if selected:
            result.append({'lower_inclusive': low, 'upper': high,
                           'upper_inclusive': index == len(edges) - 2,
                           'n': len(selected),
                           'mean_confidence': statistics.mean(confidences[i] for i in selected),
                           'accuracy': statistics.mean(correct[i] for i in selected)})
    require(sum(row['n'] for row in result) == len(confidences), 'Bins lost observations')
    return {'bins': result, 'ece': sum(row['n'] * abs(row['mean_confidence'] - row['accuracy'])
                                     for row in result) / len(confidences)}


def binary_metrics(rows, provider):
    probabilities, confidence, correct = [], [], []
    for row in rows:
        require(type(row['y']) is bool, 'Expected a Boolean reference label')
        require(math.isfinite(row['ms']) and row['ms'] >= 0, 'Invalid original latency')
        if provider == 'jev':
            p = probability(row['p'])
            prediction, conf = p >= 0.5, max(p, 1 - p)
        else:
            require(type(row['ans']) is bool, 'Expected a Boolean prediction')
            prediction, conf = row['ans'], probability(row['c'])
            require(conf >= 0.5, 'Chosen-answer confidence must be >= 0.5')
            p = conf if prediction else 1 - conf
        probabilities.append(p)
        confidence.append(conf)
        correct.append(prediction == row['y'])
    threshold_rows = []
    for threshold in [0.7, 0.8, 0.9, 0.95, 0.99]:
        selected = [i for i, value in enumerate(confidence) if value >= threshold]
        threshold_rows.append({'threshold': threshold, 'retained': len(selected),
                               'coverage': len(selected) / len(rows),
                               'accuracy': statistics.mean(correct[i] for i in selected) if selected else None})
    token_fields = ['tok'] if provider == 'jev' else ['in', 'out']
    return {'n': len(rows), 'correct': sum(correct), 'accuracy': statistics.mean(correct),
            'six_bin_calibration': bins(confidence, correct, BIN_EDGES),
            'twenty_bin_ece': bins(confidence, correct, [0.5 + i / 40 for i in range(21)])['ece'],
            'brier': statistics.mean((p - row['y']) ** 2 for p, row in zip(probabilities, rows)),
            'median_ms': statistics.median(row['ms'] for row in rows),
            'tokens': {key: sum(row[key] for row in rows) for key in token_fields},
            'unique_confidence_rounded_8dp': len({round(value, 8) for value in confidence}),
            'confidence_095_099_100_count': sum(round(value, 8) in (0.95, 0.99, 1) for value in confidence),
            'thresholds': threshold_rows}


def original_results():
    jev, gemini = read('boolq-jev-original.json'), read('boolq-gemini-original.json')
    require(len(jev) == len(gemini) == 400, 'Expected 400 original paired observations')
    require(all(j['y'] == g['y'] for j, g in zip(jev, gemini)), 'Paired labels differ')
    news = read('agnews-jev-original.json')
    require(len(news) == 300, 'Expected 300 AG News observations')
    for row in news:
        probability(row['p'])
        probability(row['conf'])
        require(row['pred'] in {'world', 'sports', 'business', 'sci_tech'} and
                row['y'] in {'world', 'sports', 'business', 'sci_tech'}, 'Unknown news label')
    errors = collections.Counter(f"{r['y']} -> {r['pred']}" for r in news if r['pred'] != r['y'])
    return {'provenance': 'Original numeric exports omit response model IDs and dataset row IDs; paired order is inherited.',
            'boolq_jev': binary_metrics(jev, 'jev'),
            'boolq_gemini_version_unverified': binary_metrics(gemini, 'gemini'),
            'boolq_jev_cost_at_0042_per_million': sum(r['tok'] for r in jev) * 0.042 / 1_000_000,
            'agreement': sum((j['p'] >= 0.5) == g['ans'] for j, g in zip(jev, gemini)),
            'both_wrong': sum((j['p'] >= 0.5) != j['y'] and g['ans'] != g['y'] for j, g in zip(jev, gemini)),
            'ag_news': {'correct': sum(r['pred'] == r['y'] for r in news), 'n': len(news),
                        'selected_option_probability': bins([r['p'] for r in news], [r['pred'] == r['y'] for r in news], [0, 0.6, 0.8, 0.9, 0.97, 1]),
                        'api_confidence_statistic': bins([r['conf'] for r in news], [r['pred'] == r['y'] for r in news], [0, 0.6, 0.8, 0.9, 0.97, 1]),
                        'error_pairs': dict(errors)}}


def decode(row):
    require(row['status'] == 200, f"Unsuccessful request: {row.get('case_id', row.get('id'))}")
    require(math.isfinite(row['elapsed_ms']) and row['elapsed_ms'] >= 0, 'Invalid timing')
    response = row['response']
    if row['provider'] == 'jev':
        answers = response['answers']
        p, label = answers['supported']['noul'], answers['evidence']['choice']
        distribution = answers['evidence']['probabilities']
        probability(answers['evidence']['confidence'])
        model = response['model']
        usage = response['usage']
    else:
        parts = response['candidates'][0]['content']['parts']
        answer = json.loads(''.join(part.get('text', '') for part in parts if not part.get('thought')))
        p, label, distribution = answer['supported'], answer['evidence'], answer['probabilities']
        model, usage = response['modelVersion'], response['usageMetadata']
    probability(p)
    require(label in LABELS and set(distribution) == LABELS, 'Invalid evidence labels')
    for value in distribution.values():
        probability(value)
    # Three independently rounded two-decimal probabilities can differ from 1 by 0.015.
    require(abs(sum(distribution.values()) - 1) <= 0.015001, 'Distribution does not sum to one')
    require(model == row['requested_model'], 'Requested and returned model IDs differ')
    return {'p': p, 'label': label, 'distribution': distribution, 'model': model, 'usage': usage,
            'api_confidence': response['answers']['evidence']['confidence'] if row['provider'] == 'jev' else None}


def evidence_results(name, cases):
    document = read(name)
    require(document['cases_sha256'] == hashlib.sha256((HERE / 'cases.json').read_bytes()).hexdigest(), 'Cases hash differs')
    rows = document['results']
    require(len(rows) == document['planned_calls'], f'Incomplete run: {name}')
    seen = set()
    decoded = {}
    for row in rows:
        key = (row['provider'], row['case_id'], row['variant'], row['repeat'])
        require(key not in seen and row['case_id'] in cases, 'Duplicate or unknown case')
        seen.add(key)
        if row['provider'] == 'jev':
            state = row['request']['state']
        else:
            prompt = row['request']['contents'][0]['parts'][0]['text']
            state = json.loads(prompt.split('\n', 1)[1])['state']
        require(state == cases[row['case_id']]['state'], 'Request state differs from fixture')
        decoded[id(row)] = decode(row)
    output = {'file': name, 'requests': len(rows), 'models': {}}
    for model in sorted({answer['model'] for answer in decoded.values()}):
        all_rows = [r for r in rows if decoded[id(r)]['model'] == model]
        base = {r['case_id']: r for r in all_rows if r['variant'] == 'baseline'}
        require(set(base) == set(cases), 'Baseline must cover every case exactly once')
        groups = {}
        for prefix in ['support', 'refute', 'unknown', 'injection']:
            subset = [r for key, r in base.items() if key.startswith(prefix)]
            groups[prefix] = {'n': len(subset),
                              'binary_correct': sum((decoded[id(r)]['p'] >= 0.5) == (cases[r['case_id']]['label'] == 'supported') for r in subset),
                              'choice_correct': sum(decoded[id(r)]['label'] == cases[r['case_id']]['label'] for r in subset)}
        injected = []
        for key, row in base.items():
            if key.startswith('injection-'):
                clean = decoded[id(base[key.removeprefix('injection-')])]
                changed = decoded[id(row)]
                injected.append({'case': key, 'binary_before': clean['p'], 'binary_after': changed['p'],
                                 'binary_delta': changed['p'] - clean['p'], 'choice_before': clean['label'], 'choice_after': changed['label'],
                                 'choice_supported_delta': changed['distribution']['supported'] - clean['distribution']['supported']})
        variants = {}
        for variant in ['repeat', 'bundled']:
            subset = [r for r in all_rows if r['variant'] == variant]
            if subset:
                pairs = [(decoded[id(base[r['case_id']])], decoded[id(r)]) for r in subset]
                variants[variant] = {'n': len(subset), 'median_ms': statistics.median(r['elapsed_ms'] for r in subset),
                                     'matched_baseline_median_ms': statistics.median(base[key]['elapsed_ms'] for key in {r['case_id'] for r in subset}),
                                     'choice_flips': sum(a['label'] != b['label'] for a, b in pairs),
                                     'max_binary_probability_delta': max(abs(a['p'] - b['p']) for a, b in pairs),
                                     'max_choice_probability_delta': max(abs(a['distribution'][label] - b['distribution'][label]) for a, b in pairs for label in LABELS),
                                     'max_api_confidence_delta': max(abs(a['api_confidence'] - b['api_confidence']) for a, b in pairs)}
        tokens = collections.Counter()
        for row in all_rows:
            for key, value in decoded[id(row)]['usage'].items():
                if type(value) is int and ('token' in key.lower()):
                    require(value >= 0, 'Negative token usage')
                    tokens[key] += value
        output['models'][model] = {'all_requests': len(all_rows), 'baseline_n': len(base), 'groups': groups,
                                   'binary_correct': sum(r['binary_correct'] for r in groups.values()),
                                   'choice_correct': sum(r['choice_correct'] for r in groups.values()),
                                   'median_baseline_ms': statistics.median(r['elapsed_ms'] for r in base.values()),
                                   'label_disagreements': [{'case': key, 'expected': cases[key]['label'],
                                                            'binary_probability': decoded[id(row)]['p'],
                                                            'choice': decoded[id(row)]['label']}
                                                           for key, row in base.items()
                                                           if decoded[id(row)]['label'] != cases[key]['label'] or
                                                           (decoded[id(row)]['p'] >= 0.5) != (cases[key]['label'] == 'supported')],
                                   'all_request_tokens': dict(tokens), 'injection_pairs': injected, 'variants': variants}
    return output


def exact_results():
    rows = read('exact-results.json')
    require(len(rows) == 5 and len({row['id'] for row in rows}) == 5, 'Expected five exact checks')
    output = []
    for row in rows:
        require(row['status'] == 200, 'Exact check failed')
        require(row['response']['model'] == row['request']['model'], 'Exact-check model mismatch')
        answer = next(iter(row['response']['answers'].values()))
        p = probability(answer['noul'])
        entry = {'id': row['id'], 'model': row['response']['model'], 'expected': row['expected'], 'probability': p}
        if row['id'].startswith('invoice-'):
            state = row['request']['state']
            actual = sum(Decimal(str(item['amount'])) for item in state['line_items'])
            matches = actual == Decimal(str(state['invoice_total']))
            require(matches == row['expected'], 'Invoice reference label is incorrect')
            entry.update({'computed_total': str(actual), 'stated_total': state['invoice_total']})
        output.append(entry)
    return {'requests': len(rows), 'input_tokens': sum(row['response']['usage']['input_tokens'] for row in rows), 'checks': output}


def main():
    case_rows = read('cases.json')
    cases = {row['id']: row for row in case_rows}
    require(len(cases) == len(case_rows) == 28, 'Expected 28 unique evidence cases')
    require(all(row['label'] in LABELS for row in case_rows), 'Unknown reference label')
    followups = [evidence_results('followup-results.json', cases)]
    if (HERE / 'gemini-3.8-results.json').exists():
        followups.append(evidence_results('gemini-3.8-results.json', cases))
    exact = exact_results()
    counts = collections.Counter()
    for run in followups:
        counts.update({model: details['all_requests'] for model, details in run['models'].items()})
    counts['jev-1.13.0'] += exact['requests']
    print(json.dumps({'original': original_results(), 'evidence_runs': followups, 'exact_checks': exact,
                      'followup_request_counts': dict(counts), 'followup_total': sum(counts.values())}, indent=2))


if __name__ == '__main__':
    main()
