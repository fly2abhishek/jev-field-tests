#!/usr/bin/env python3
"""Replay the saved 28 Gemini requests against a specified model (paid API calls)."""
import argparse
import concurrent.futures
import datetime
import json
from pathlib import Path
import re

from run_followup import HERE, credential, post


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--env', default='.env')
    parser.add_argument('--model', default='gemini-3.8-flash')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'gemini-[a-zA-Z0-9.-]+', args.model):
        raise SystemExit('Expected a Gemini model identifier.')
    original = json.loads((HERE / 'followup-results.json').read_text())
    jobs = [row for row in original['results']
            if row['provider'] == 'gemini' and row['variant'] == 'baseline']
    print(f'Planned: {len(jobs)} calls to {args.model}; identical saved request bodies.', flush=True)
    if not args.run:
        return
    if args.output.exists():
        raise SystemExit('Output exists; choose a new path.')
    key = credential(args.env, 'GEMINI_API_KEY')

    def run(row):
        result = post(
            f'https://generativelanguage.googleapis.com/v1beta/models/{args.model}:generateContent',
            row['request'], {'x-goog-api-key': key})
        return {'provider': 'gemini', 'requested_model': args.model,
                'case_id': row['case_id'], 'variant': 'baseline', 'repeat': 0,
                'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'request': row['request'], **result}

    metadata = {key: value for key, value in original.items() if key != 'results'}
    metadata.update({'date': datetime.date.today().isoformat(),
                     'planned_calls': len(jobs), 'workers': 4,
                     'source': 'followup-results.json Gemini request bodies', 'results': []})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        for result in pool.map(run, jobs):
            metadata['results'].append(result)
            args.output.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + '\n')
            print(json.dumps({key: result[key] for key in
                              ['case_id', 'status', 'elapsed_ms']}), flush=True)

    if any(row['status'] != 200 for row in metadata['results']):
        raise SystemExit('Some requests failed; inspect the saved status fields.')


if __name__ == '__main__':
    main()
