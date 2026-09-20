"""Offline checks for the portable runners and the published evidence."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'followup'))
import run_followup


class FollowupTests(unittest.TestCase):
    def test_documented_key_and_process_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            env = Path(directory) / '.env'
            env.write_text('TYPESAFE_API_KEY="fixture-file"\nJEV_API_KEY=fixture-alias\n')
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(run_followup.credential(env, 'JEV_API_KEY'), 'fixture-file')
            with patch.dict(os.environ, {'JEV_API_KEY': 'fixture-process'}, clear=True):
                self.assertEqual(run_followup.credential(env, 'TYPESAFE_API_KEY'), 'fixture-process')
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(SystemExit, 'Missing TYPESAFE_API_KEY'):
                    run_followup.credential(Path(directory) / 'absent', 'JEV_API_KEY')

    def test_dry_runs_need_no_keys_or_network(self):
        with tempfile.TemporaryDirectory() as directory:
            for filename in ['run_followup.py', 'run_exact_checks.py', 'run_gemini_baseline.py']:
                spec = importlib.util.spec_from_file_location('runner', ROOT / 'followup' / filename)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                output = Path(directory) / filename
                argv = [filename, '--output', str(output)]
                with patch.object(sys, 'argv', argv), patch.object(module, 'credential', side_effect=AssertionError('Read a key')), patch.object(module, 'post', side_effect=AssertionError('Used network')), contextlib.redirect_stdout(io.StringIO()):
                    module.main()
                self.assertFalse(output.exists())

    def test_mock_run_preserves_evidence_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'nested' / 'run.json'
            argv = ['run_followup.py', '--run', '--output', str(output)]
            fake = {'status': 200, 'response': {'model': 'jev-1.13.0'}, 'elapsed_ms': 1.0}
            with patch.object(sys, 'argv', argv), patch.object(run_followup, 'credential', return_value='fixture-secret'), patch.object(run_followup, 'post', return_value=fake) as post, contextlib.redirect_stdout(io.StringIO()):
                run_followup.main()
                self.assertEqual(post.call_count, 44)
                with self.assertRaisesRegex(SystemExit, 'already exists'):
                    run_followup.main()
            data = json.loads(output.read_text())
            self.assertEqual(len(data['results']), 44)
            self.assertEqual(data['cases_sha256'], hashlib.sha256((ROOT / 'followup/cases.json').read_bytes()).hexdigest())
            self.assertNotIn('fixture-secret', output.read_text())
            self.assertEqual(sum(row['variant'] == 'bundled' for row in data['results']), 4)

    def test_failed_run_is_saved_and_exits_unsuccessfully(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'failed.json'
            fake = {'status': 429, 'error': 'HTTPError', 'elapsed_ms': 1.0}
            with patch.object(sys, 'argv', ['runner', '--run', '--output', str(output)]), patch.object(run_followup, 'credential', return_value='fixture-secret'), patch.object(run_followup, 'post', return_value=fake), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(SystemExit, 'Some requests failed'):
                    run_followup.main()
            self.assertEqual(len(json.loads(output.read_text())['results']), 44)

    def test_saved_summary_runs_without_credentials(self):
        result = subprocess.run([sys.executable, str(ROOT / 'followup/summarize.py')], cwd=ROOT, env={}, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout)['followup_total'], 105)

    def test_opaque_response_fields_are_removed(self):
        value = {'responseId': 'opaque', 'nested': [{'thoughtSignature': 'opaque', 'text': 'answer'}]}
        self.assertEqual(run_followup.scrub_response_metadata(value), {'nested': [{'text': 'answer'}]})


if __name__ == '__main__':
    unittest.main()
