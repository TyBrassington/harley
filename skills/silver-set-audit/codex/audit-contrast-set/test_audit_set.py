"""Local schema/recording regression checks; no dataset or model calls.

Run: python3 -B -m unittest discover -s .agents/skills/audit-contrast-set -p 'test_*.py'
"""
import contextlib
import csv
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HELPER = Path(__file__).with_name('audit_set.py')
spec = importlib.util.spec_from_file_location('audit_set', HELPER)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def verdict():
    return {
        'candidate_id': 'wildchat_fixture', 'tags': ['NONE'],
        'reason': 'All role relations hold in this synthetic recording fixture.',
        'h_decisive_fact_ok': True, 's_dimensions_realised': audit.DIMS.copy(),
        's_dimensions_missing': [], 's_topic_disjoint': True,
        's_cue_free': True, 's_same_speaker': True, 'decision': 'approve',
    }


class LabelFreeAuditTests(unittest.TestCase):
    def test_only_binary_outcomes_and_no_secondary_verdict(self):
        for decision in ('revise', 'reject', 'hold', 'gold', 'PASS', 'MINOR', 'FAIL', 'HOLD'):
            self.assertTrue(audit.validate(verdict() | {'decision': decision}, 'wildchat_fixture'))
        for old_verdict in ('PASS', 'MINOR', 'FAIL', 'HOLD'):
            self.assertTrue(audit.validate(verdict() | {'verdict': old_verdict}, 'wildchat_fixture'))

    def test_pass_cannot_contradict_its_own_role_findings(self):
        for update in ({'h_decisive_fact_ok': False}, {'s_cue_free': False},
                       {'s_dimensions_realised': ['sentence_shape', 'sentence_shape']},
                       {'s_dimensions_missing': ['register_formality']}):
            self.assertTrue(audit.validate(verdict() | update, 'wildchat_fixture'))

    def test_minor_repair_can_be_approved_without_adding_an_outcome(self):
        v = verdict() | {'tags': ['P_NEAR_COPY'],
                         'reason': 'P preserves the contrast and independently rephrases most text, with a minor repeated phrase.',
                         'revision_needed': 'Rephrase the remaining repeated phrase in P.'}
        self.assertEqual(audit.validate(v, v['candidate_id']), [])
        self.assertTrue(audit.validate(v | {'revision_needed': ''}, v['candidate_id']))
        self.assertTrue(audit.validate(v | {'tags': ['NONE']}, v['candidate_id']))
        self.assertTrue(audit.validate(v | {'tags': ['NONE', 'P_NEAR_COPY']}, v['candidate_id']))
        for decision in ('revise', 'gold', 'reject', 'hold'):
            self.assertTrue(audit.validate(v | {'decision': decision}, v['candidate_id']))

    def test_repair_does_not_override_a_failed_relation_or_material_gap(self):
        v = verdict() | {'tags': ['H_STILL_INAPPROPRIATE'],
                         'h_decisive_fact_ok': False,
                         'revision_needed': 'Replace the ineffective fact change in H.'}
        self.assertTrue(audit.validate(v, v['candidate_id']))
        self.assertEqual(audit.validate(v | {'decision': 'deny'}, v['candidate_id']), [])
        self.assertTrue(audit.validate(verdict() | {'evidence_gap': 'The source anchor is truncated.'},
                                       v['candidate_id']))

    def test_denial_preserves_unknown_without_inventing_a_defect(self):
        v = verdict() | {'decision': 'deny', 'tags': [],
                         'evidence_gap': 'H is missing from the supplied file.', 'h_decisive_fact_ok': None,
                         's_dimensions_realised': None, 's_dimensions_missing': None}
        self.assertEqual(audit.validate(v, v['candidate_id']), [])
        self.assertTrue(audit.validate(v | {'evidence_gap': ''}, v['candidate_id']))
        self.assertTrue(audit.validate(v | {'decision': 'approve'}, v['candidate_id']))
        self.assertTrue(audit.validate(verdict() | {'h_decisive_fact_ok': None}, v['candidate_id']))

    def test_jailbreak_eligibility_denial_preserves_sound_role_findings(self):
        v = verdict() | {'decision': 'deny', 'tags': ['INELIGIBLE_GENERIC_JAILBREAK'],
                         'reason': 'The source is dominated by generic unrestricted-persona commands without a coherent task.'}
        self.assertEqual(audit.validate(v, v['candidate_id']), [])
        self.assertTrue(audit.validate(v | {'decision': 'approve', 'revision_needed': 'Remove wrapper.'}, v['candidate_id']))

    def test_duplicate_exclusion_is_not_an_audit_issue_tag(self):
        self.assertTrue(audit.validate(verdict() | {'decision': 'deny', 'tags': ['COLLECTION_NEAR_DUPLICATE']},
                                       'wildchat_fixture'))
        self.assertEqual(audit.validate(verdict() | {'notable': 'No novelty claim; duplicate removal is a separate process.'},
                                        'wildchat_fixture'), [])

    def test_malformed_verdict_is_operational_error(self):
        for value in ([], None, verdict() | {'tags': None}, verdict() | {'tags': [{}]}):
            self.assertTrue(audit.validate(value, 'wildchat_fixture'))

    def test_portable_inputs_preserve_text_and_omit_answer_keys(self):
        prompts = {letter: 'Original text,\n第二行 — ' + letter for letter in audit.LETTER.values()}
        packet = {'candidate_id': 'unseen-17', 'anchor_role': 'A', 'prompts': prompts,
                  'family': 'SECRET_LABEL', 'H_plan': {'judge': 'SECRET_KEY'}}
        wrapped = {'packet': packet, 'primary_decision': 'SECRET_KEY',
                   'verdicts': [{'notes': 'SECRET_KEY'}]}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for ext in ('json', 'jsonl', 'csv', 'tsv'):
                path = root / ('arbitrary-input.' + ext)
                if ext == 'json':
                    path.write_text(json.dumps(wrapped), encoding='utf-8')
                elif ext == 'jsonl':
                    path.write_text(json.dumps(wrapped) + '\n', encoding='utf-8')
                else:
                    with path.open('w', encoding='utf-8-sig', newline='') as stream:
                        row = dict(prompts, candidate_id='unseen-17', anchor_role='A', notes='SECRET_KEY')
                        writer = csv.DictWriter(stream, fieldnames=list(row), delimiter='\t' if ext == 'tsv' else ',')
                        writer.writeheader(); writer.writerow(row)
                result = subprocess.run([sys.executable, '-B', str(HELPER), 'render', '--file', str(path)],
                                        capture_output=True, text=True, check=True)
                saved = json.loads(result.stdout)
                self.assertEqual(saved['prompts'], prompts)
                self.assertEqual(saved['candidate_id'], 'unseen-17')
                self.assertEqual(saved['anchor_role'], 'A')
                self.assertNotIn('SECRET', result.stdout)

    def test_collection_requires_selection_and_missing_role_stays_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bundle.json'
            path.write_text(json.dumps({'development': [{'T': 'a', 'A': 'b'}],
                                        'evaluation': [{'T': 'UNSELECTED_TEXT'}]}))
            with self.assertRaises(ValueError):
                audit.file_records(path)
            rows = audit.file_records(path, 'development')
            result = audit.portable_packet(rows[0], 'file#1')
            self.assertIsNone(result['prompts']['H'])
            self.assertIsNone(result['candidate_id'])
            self.assertIsNone(result['anchor_role'])
            self.assertNotIn('UNSELECTED', json.dumps(result))

    def test_role_map_retains_all_messages_and_checks_anchor_conflicts(self):
        messages = [{'role': 'system', 'content': 'Task context'}, {'role': 'user', 'content': 'Question'}]
        row = {'roles': {r: {'user_prompt': r} for r in audit.ROLES}}
        row['roles']['aligned_control'] = {'rendered_messages': messages, 'is_anchor': True}
        result = audit.portable_packet(row, 'file#1')
        self.assertEqual(json.loads(result['prompts']['A']), messages)
        self.assertEqual(result['anchor_role'], 'aligned_control')
        with self.assertRaises(ValueError):
            audit.portable_packet(row | {'anchor_role': 'T'}, 'file#1')

    def test_standalone_output_records_revision_without_lab_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'verdict.json'
            v = verdict() | {'candidate_id': 'document.csv#2',
                             'decision': 'approve', 'tags': ['P_NEAR_COPY'],
                             'revision_needed': 'Rephrase P independently.', 'source_ref': 'document.csv#2'}
            subprocess.run([sys.executable, '-B', str(HELPER), 'record', v['candidate_id'],
                            '--output', str(output), '--reviewer', 'fixture', '--verdict-json', '-'],
                           input=json.dumps(v), env=dict(os.environ, HARLEY_RUNS_DIR=str(Path(tmp) / 'absent')),
                           text=True, capture_output=True, check=True)
            saved = json.loads(output.read_text())
            self.assertEqual(saved['decision'], 'approve')
            self.assertEqual(saved['revision_needed'], v['revision_needed'])
            self.assertNotIn('run', saved)
            self.assertNotIn('verdict', saved)
            self.assertEqual(saved['schema_version'], 'harley_set_audit_verdict_v4')

    def test_label_not_required_and_metadata_does_not_change_validity(self):
        for family in (None, 'unknown-source-label', 'sycophancy'):
            v = verdict()
            if family is not None:
                v['family'] = family
            self.assertEqual(audit.validate(v, v['candidate_id']), [])

    def test_retired_label_judgments_cannot_be_recorded(self):
        for update in (
            {'family_grounded': True}, {'family_override': 'strategic_false_reporting'},
            {'tags': ['FAMILY_BETTER_FIT_ELSEWHERE']},
            {'decision': 'deny', 'tags': ['FAMILY_NOT_GROUNDED']},
        ):
            with self.subTest(update=update):
                v = verdict() | update
                self.assertTrue(audit.validate(v, v['candidate_id']))

    def test_role_failure_and_decision_checks_still_apply(self):
        v = verdict() | {
            'tags': ['A_KEEPS_PRESSURE'], 'decision': 'deny',
            'reason': 'A still contains the same instruction to suppress contrary evidence.',
        }
        self.assertEqual(audit.validate(v, v['candidate_id']), [])
        self.assertTrue(audit.validate(v | {'decision': 'gold'}, v['candidate_id']))
        self.assertTrue(audit.validate(verdict() | {'s_dimensions_realised': ['topic']}, v['candidate_id']))
        self.assertTrue(audit.validate(verdict(), 'wildchat_wrong'))

    def test_default_render_omits_label_and_planner_label_rationale(self):
        row = {
            'candidate_id': 'wildchat_fixture', 'behavior_family': 'DO_NOT_SCORE_LABEL',
            'anchor_role': 'aligned_control', 'behavior_mechanism': 'A concrete pressure.',
            'plan': {'family_selection': {'reason': 'DO_NOT_SCORE_LABEL'}},
            'complete_contrast': {'roles': {
                role: {'user_prompt': f'{role} fixture text', 'is_anchor': role == 'aligned_control'}
                for role in audit.ROLES
            }},
        }
        with tempfile.TemporaryDirectory() as tmp:
            output = audit.render(Path(tmp), 'approved', row)
        self.assertNotIn('DO_NOT_SCORE_LABEL', output)
        for role in audit.ROLES:
            self.assertIn(f'{role} fixture text', output)
        self.assertIn('(ANCHOR)', output)

    def test_local_rubric_wins_over_stale_run_rubric(self):
        with tempfile.TemporaryDirectory() as tmp:
            stale = Path(tmp) / 'audit_kit_v6' / 'rubric_v6.md'
            stale.parent.mkdir()
            stale.write_text('Old label-based rubric')
            result = subprocess.run(
                [sys.executable, '-B', str(HELPER), 'rubric'],
                env=dict(os.environ, HARLEY_RUNS_DIR=tmp), text=True,
                capture_output=True, check=True,
            )
        self.assertEqual(Path(result.stdout.strip()).resolve(), HELPER.with_name('rubric_v6.md').resolve())

    def test_record_v4_and_read_legacy_without_rewriting_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'fixture_run'
            final = root / 'variants' / 'final'
            final.mkdir(parents=True)
            (final / 'approved_contrast_sets.jsonl').write_text(json.dumps({
                'candidate_id': 'wildchat_fixture', 'behavior_family': 'opaque-source-label',
                'anchor_role': 'aligned_control',
            }) + '\n')
            vdir = root / 'audit' / 'verdicts'
            vdir.mkdir(parents=True)
            old = verdict() | {
                'schema_version': 'harley_set_audit_verdict_v1', 'family_grounded': True,
                'decision': 'gold', 'verdict': 'PASS',
                'family_override': '', 'reviewer': 'legacy', 'family': 'old-label',
            }
            legacy = vdir / 'wildchat_fixture.legacy.json'
            legacy.write_text(json.dumps(old))
            before = legacy.read_bytes()
            subprocess.run([
                sys.executable, '-B', str(HELPER), 'record', 'wildchat_fixture',
                '--run', str(root), '--reviewer', 'current', '--verdict-json', '-',
            ], input=json.dumps(verdict()), text=True, capture_output=True, check=True)
            saved = json.loads((vdir / 'wildchat_fixture.current.json').read_text())
            self.assertEqual(saved['schema_version'], 'harley_set_audit_verdict_v4')
            self.assertEqual(saved['family'], 'opaque-source-label')
            self.assertNotIn('family_grounded', saved)
            self.assertNotIn('family_override', saved)
            report = Path(tmp) / 'status.csv'
            result = subprocess.run([
                sys.executable, '-B', str(HELPER), 'status', '--run', str(root),
                '--csv', str(report),
            ], text=True, capture_output=True, check=True)
            self.assertIn('"current"', result.stdout)
            self.assertIn('"legacy"', result.stdout)
            summary = json.loads(result.stdout.split('\nwrote ')[0])
            self.assertEqual(summary['decisions_by_reviewer'], {'current': {'approve': 1, 'deny': 0}})
            self.assertEqual(summary['historical_verdicts_by_reviewer'], {'legacy': {'PASS': 1}})
            with report.open() as stream:
                rows = {r['reviewer']: r for r in csv.DictReader(stream)}
            self.assertEqual(rows['current']['family_grounded'], '')
            self.assertEqual(rows['legacy']['family_grounded'], 'True')
            self.assertEqual(legacy.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
