"""CLI transport tests: mocked subprocesses only; no account/model calls."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import claude_audit_runner as runner
import test_audit_eval as fixtures

harness = fixtures.eval


AUTH = {'cli': '/fake/claude', 'version': '2.1.267 (Claude Code)',
        'subscription_login': True, 'auth_method': 'claude.ai', 'subscription_type': 'team'}


class RunnerTests(unittest.TestCase):
    setUp = fixtures.EvaluationTests.setUp
    args = fixtures.EvaluationTests.args
    prepare = fixtures.EvaluationTests.prepare

    def runner_args(self, **changes):
        return argparse.Namespace(**dict(run=self.run, workers=3, timeout=60,
                                         claude_bin=None, cli_model='claude-opus-5', effort='high') | changes)

    def fake_success(self, cmd, **kwargs):
        ids = json.loads(cmd[cmd.index('--json-schema') + 1])['properties']['records']['items']['anyOf'][0]['properties']['candidate_id']['enum']
        self.assertNotIn('SECRET_NOTE', kwargs['input'])
        self.assertNotIn('primary_decision', kwargs['input'])
        self.assertNotIn('BLIND_SENTINEL', kwargs['input'])
        self.assertEqual(cmd[cmd.index('--tools') + 1], '')
        self.assertIn('--safe-mode', cmd)
        self.assertNotIn('--bare', cmd)
        self.assertIn('--no-session-persistence', cmd)
        self.assertIn('--strict-mcp-config', cmd)
        self.assertEqual(kwargs['env']['CLAUDE_CODE_DISABLE_TERMINAL_TITLE'], '1')
        self.assertEqual(cmd[cmd.index('--disallowedTools') + 1], 'mcp__*')
        self.assertNotEqual(Path(kwargs['cwd']), self.run)
        body = {'records': [{'candidate_id': cid, 'decision': 'approve', 'reason': 'Synthetic audit.'} for cid in ids]}
        return subprocess.CompletedProcess(cmd, 0, json.dumps({'structured_output': body,
                         'modelUsage': {'claude-opus-5': {'inputTokens': 1}}, 'session_id': 'test'}), '')

    def test_child_environment_uses_login_without_altering_parent(self):
        values = {'ANTHROPIC_API_KEY': 'secret', 'ANTHROPIC_AUTH_TOKEN': 'secret2',
                  'ANTHROPIC_BASE_URL': 'https://example.invalid', 'ANTHROPIC_PROFILE': 'billing-profile',
                  'CLAUDE_CODE_USE_BEDROCK': '1', 'CLAUDE_CODE_OAUTH_TOKEN': 'secret3',
                  'CLAUDE_CODE_EFFORT_LEVEL': 'low'}
        with patch.dict(os.environ, values):
            env = runner.subscription_env()
            for key in values:
                self.assertNotIn(key, env)
                self.assertEqual(os.environ[key], values[key])
            self.assertEqual(env['CLAUDE_CODE_SAFE_MODE'], '1')

    def test_auth_preflight_returns_no_personal_identifiers(self):
        def fake(cmd, **kwargs):
            if '--version' in cmd:
                value = '2.1.267'
            elif '--help' in cmd:
                value = ' '.join(runner.REQUIRED_FLAGS)
            else:
                value = json.dumps({'loggedIn': True, 'authMethod': 'claude.ai', 'apiProvider': 'firstParty',
                                    'subscriptionType': 'team', 'email': 'PRIVATE', 'orgId': 'PRIVATE'})
            return subprocess.CompletedProcess(cmd, 0, value, '')
        with patch.object(runner, 'executable', return_value='/fake/claude'), patch.object(runner.subprocess, 'run', side_effect=fake):
            result = runner.check_cli(argparse.Namespace(claude_bin=None))
        self.assertTrue(result['subscription_login'])
        self.assertNotIn('PRIVATE', json.dumps(result))

    def test_missing_subscription_stops_before_any_model_call(self):
        self.prepare()
        with patch.object(runner, 'check_cli', return_value=AUTH | {'subscription_login': False}), patch.object(runner.subprocess, 'run') as call:
            with self.assertRaisesRegex(ValueError, 'login required'):
                runner.run_cli(self.runner_args(), harness)
            call.assert_not_called()
        self.assertFalse((self.run/'cli_run.json').exists())

    def test_parallel_run_freezes_scores_and_records_actual_model(self):
        self.prepare()
        with patch.object(runner, 'check_cli', return_value=AUTH), patch.object(runner.subprocess, 'run', side_effect=self.fake_success) as call:
            result = runner.run_cli(self.runner_args(), harness)
        self.assertEqual(call.call_count, 3)
        self.assertEqual(result['coverage']['predictions'], 7)
        report = harness.read_json(self.run/'comparison_report.json')
        self.assertEqual(report['observed_models'], ['claude-opus-5'])
        self.assertEqual(report['execution']['effort'], 'high')
        self.assertIn('cli_run.json', harness.read_json(self.run/'predictions_frozen.json')['execution_hashes'])
        with self.assertRaisesRegex(ValueError, 'already frozen'):
            runner.run_cli(self.runner_args(), harness)

    def test_refusal_timeout_or_bad_output_never_becomes_deny(self):
        self.prepare()
        def fake(cmd, **kwargs):
            ids = json.loads(cmd[cmd.index('--json-schema') + 1])['properties']['records']['items']['anyOf'][0]['properties']['candidate_id']['enum']
            if 'a' in ids:
                raise subprocess.TimeoutExpired(cmd, 60)
            if 'd' in ids:
                return subprocess.CompletedProcess(cmd, 1, '{"is_error":true}', '')
            return subprocess.CompletedProcess(cmd, 0, 'malformed', '')
        with patch.object(runner, 'check_cli', return_value=AUTH), patch.object(runner.subprocess, 'run', side_effect=fake):
            result = runner.run_cli(self.runner_args(), harness)
        self.assertEqual(result['coverage']['predictions'], 0)
        self.assertEqual(result['coverage']['operational_failures'], 7)
        self.assertEqual(result['headline']['disputed_credited'], 0)

    def test_wrong_model_is_an_operational_failure(self):
        self.prepare()
        def fake(cmd, **kwargs):
            result = self.fake_success(cmd, **kwargs)
            result.stdout = result.stdout.replace('claude-opus-5', 'claude-sonnet-5')
            return result
        with patch.object(runner, 'check_cli', return_value=AUTH), patch.object(runner.subprocess, 'run', side_effect=fake):
            result = runner.run_cli(self.runner_args(), harness)
        self.assertEqual(result['coverage']['operational_failures'], 7)

    def test_extra_background_model_is_not_silently_accepted(self):
        self.prepare()
        def fake(cmd, **kwargs):
            result = self.fake_success(cmd, **kwargs)
            payload = json.loads(result.stdout)
            payload['modelUsage']['claude-haiku-4-5'] = {'inputTokens': 1}
            result.stdout = json.dumps(payload)
            return result
        with patch.object(runner, 'check_cli', return_value=AUTH), patch.object(runner.subprocess, 'run', side_effect=fake):
            result = runner.run_cli(self.runner_args(), harness)
        self.assertEqual(result['coverage']['operational_failures'], 7)

    def test_changed_cli_logs_fail_integrity_check(self):
        self.prepare()
        with patch.object(runner, 'check_cli', return_value=AUTH), patch.object(runner.subprocess, 'run', side_effect=self.fake_success):
            runner.run_cli(self.runner_args(), harness)
        path = next((self.run/'cli_logs').glob('*/metadata.json'))
        path.write_text(path.read_text() + ' ')
        with self.assertRaisesRegex(ValueError, 'execution artifact changed'):
            harness.score(self.args())

    def test_interrupted_batch_not_automatically_replayed(self):
        self.prepare()
        (self.run/'cli_logs/batch_001').mkdir(parents=True)
        with patch.object(runner, 'check_cli', return_value=AUTH), patch.object(runner.subprocess, 'run') as call:
            with self.assertRaisesRegex(ValueError, 'interrupted batch'):
                runner.run_cli(self.runner_args(), harness)
            call.assert_not_called()

    def test_duplicate_or_missing_ids_fail_batch_decoding(self):
        for records in ([], [{'candidate_id': 'a', 'decision': 'approve', 'reason': 'one'}] * 2):
            with self.assertRaises(ValueError):
                runner.decode_response(json.dumps({'structured_output': {'records': records}}), ['a', 'b'])


if __name__ == '__main__':
    unittest.main()
