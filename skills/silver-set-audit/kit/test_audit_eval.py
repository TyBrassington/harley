"""Offline evaluation regression tests, using synthetic prompts and judgments."""
import argparse
import importlib.util
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).with_name('audit_eval.py')
spec = importlib.util.spec_from_file_location('audit_eval', SCRIPT)
eval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eval)


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / 'source.json'
        self.run = self.root / 'run'
        self.labels = dict(a='approve', b='revise', c='reject', d='reject',
                           e='disputed', f='unsure', g='approve')
        rows = [dict(candidate_id=cid, primary_decision=label,
                     verdicts=[{'reviewer': 'SECRET_REVIEWER', 'notes': 'SECRET_NOTE'}],
                     packet={'family': 'SECRET_FAMILY', 'H_plan': 'SECRET_PLAN',
                             'anchor_role': 'A', 'language': 'English',
                             'prompts': {role: f'{cid}: {role} original\n第二行' for role in 'TAHSP'}})
                for cid, label in self.labels.items()]
        self.bundle.write_text(json.dumps({'dev': rows, 'blind': [{'candidate_id': 'BLIND_SENTINEL'}]}))

    def args(self, **kwargs):
        base = dict(bundle=self.bundle, split='dev', run=self.run, skill=eval.DEFAULT_SKILL,
                    model='synthetic-model', settings='test-only', sample_size=None,
                    seed=42, batch_size=3, exclude_id=[], disputed='credit')
        return argparse.Namespace(**(base | kwargs))

    def prepare(self, **kwargs):
        return eval.prepare(self.args(**kwargs))

    def rows(self):
        decisions = dict(a='approve', b='deny', c='approve', d='deny', e='deny', f='approve')
        return [dict(candidate_id=cid, decision=decision, reason='Synthetic construction judgment.')
                for cid, decision in decisions.items()] + [dict(candidate_id='g', operational_error='Synthetic refusal.')]

    def write_results(self, rows=None, filename='part.jsonl'):
        path = self.run / 'results' / filename
        path.write_text(''.join(json.dumps(row) + '\n' for row in (self.rows() if rows is None else rows)))
        return path

    def test_prepare_preserves_prompts_and_hides_keys(self):
        before = self.bundle.read_bytes()
        self.prepare()
        packets = [json.loads(line) for p in sorted((self.run/'reviewer/batches').glob('*.jsonl'))
                   for line in p.read_text().splitlines()]
        self.assertEqual(len(packets), 7)
        for packet in packets:
            self.assertEqual(set(packet), {'candidate_id', 'source_ref', 'anchor_role', 'language', 'prompts'})
            for role in 'TAHSP':
                self.assertEqual(packet['prompts'][role], f"{packet['candidate_id']}: {role} original\n第二行")
        contents = ''.join(p.read_text() for p in (self.run/'reviewer/batches').glob('*.jsonl'))
        self.assertNotIn('SECRET', contents)
        self.assertNotIn('BLIND_SENTINEL', contents)
        self.assertNotIn('primary_decision', contents)
        self.assertEqual(self.bundle.read_bytes(), before)
        with self.assertRaises(FileExistsError):
            self.prepare()

    def test_sampling_then_exclusion_without_replacement(self):
        drawn = random.Random(42).sample(sorted(self.labels), 4)
        not_drawn = next(cid for cid in self.labels if cid not in drawn)
        self.prepare(sample_size=4, exclude_id=[drawn[0], not_drawn])
        manifest = eval.read_json(self.run/'manifest.json')
        self.assertEqual(manifest['sampled_ids'], drawn)
        self.assertEqual(manifest['selected_ids'], drawn[1:])
        self.assertEqual(manifest['excluded_sample_ids'], [drawn[0]])
        self.assertEqual(manifest['exclusions_not_sampled'], [not_drawn])
        self.assertNotIn(drawn[0], [json.loads(line)['candidate_id']
                                    for p in (self.run/'reviewer/batches').glob('*.jsonl')
                                    for line in p.read_text().splitlines()])

    def test_bad_selection_rejected_before_creating_run(self):
        for changes in ({'sample_size': 0}, {'sample_size': 100}, {'batch_size': 0}, {'exclude_id': ['typo']}):
            with self.assertRaises(ValueError):
                self.prepare(**changes)
            self.assertFalse(self.run.exists())

    def test_parallel_results_complete_with_failures_and_missing_gates(self):
        self.prepare()
        self.write_results(self.rows()[:3], 'batch1.jsonl')
        summary = eval.validate(self.args())
        self.assertFalse(summary['ready_to_freeze'])
        with self.assertRaises(ValueError):
            eval.freeze(self.args())
        self.write_results(self.rows()[3:], 'batch2.jsonl')
        self.assertTrue(eval.validate(self.args())['ready_to_freeze'])
        frozen = eval.freeze(self.args())
        self.assertEqual((frozen['predictions'], frozen['operational_failures']), (6, 1))
        with self.assertRaises(FileExistsError):
            eval.freeze(self.args())

    def test_invalid_records_not_converted_to_denials(self):
        self.prepare()
        invalid = [
            [self.rows()[0], self.rows()[0]],
            [dict(candidate_id='alien', decision='deny', reason='unknown source')],
            [dict(candidate_id='a', decision='revise', reason='wrong outcome')],
            [dict(candidate_id='a', decision='approve', reason='')],
            [dict(candidate_id='a', decision='deny', operational_error='refused')],
            [dict(candidate_id='a', operational_error='')],
            [dict(candidate_id='a', decision='approve', reason='test', tags=['INELIGIBLE_GENERIC_JAILBREAK'])],
            [dict(candidate_id='a', decision='deny', reason='test', tags=['NONE'])],
            [dict(candidate_id='a', decision='deny', reason='test', tags=[{}])],
        ]
        for rows in invalid:
            with self.subTest(rows=rows):
                self.write_results(rows)
                with self.assertRaises(ValueError):
                    eval.validate(self.args())
        (self.run/'results/part.jsonl').write_text('{broken')
        with self.assertRaises(ValueError):
            eval.validate(self.args())
        self.assertFalse((self.run/'predictions_frozen.json').exists())

    def test_scoring_requires_freeze_before_opening_source(self):
        self.prepare()
        with patch.object(eval, 'input_rows', side_effect=AssertionError('source read before freeze')):
            with self.assertRaises(FileNotFoundError):
                eval.score(self.args())

    def test_score_mapping_kappa_coverage_and_no_overwrite(self):
        self.prepare(); self.write_results(); eval.freeze(self.args())
        output = eval.score(self.args())
        self.assertEqual(output['headline']['correct'], 3)
        self.assertEqual(output['headline']['denominator'], 5)
        self.assertEqual(output['headline']['disputed_credited'], 1)
        self.assertEqual(output['headline']['all_selected_scorable'], 6)
        self.assertEqual(output['headline']['unscored_due_to_failure'], 1)
        self.assertEqual(output['resolved']['cohens_kappa'], 0)
        report = eval.read_json(self.run/'comparison_report.json')
        self.assertEqual(report['confusion_matrix'], {'approve': {'approve': 1, 'deny': 1}, 'deny': {'approve': 1, 'deny': 1}})
        self.assertEqual(report['coverage']['operational_failures'], 1)
        self.assertEqual(len(report['disagreements']), 2)
        self.assertIn('SECRET_NOTE', json.dumps(report['disagreements']))
        before = (self.run/'comparison_report.json').read_bytes()
        with self.assertRaises(ValueError):
            eval.score(self.args())
        self.assertEqual((self.run/'comparison_report.json').read_bytes(), before)

    def test_disputed_exclude_policy(self):
        self.prepare(disputed='exclude'); self.write_results(); eval.freeze(self.args())
        result = eval.score(self.args())
        self.assertEqual(result['headline']['denominator'], 4)
        self.assertEqual(result['headline']['disputed_credited'], 0)

    def test_all_failures_have_no_agreement_or_disputed_credit(self):
        self.prepare()
        self.write_results([dict(candidate_id=cid, operational_error='Synthetic refusal.') for cid in self.labels])
        eval.freeze(self.args())
        result = eval.score(self.args())
        self.assertEqual(result['coverage']['predictions'], 0)
        self.assertEqual(result['headline']['disputed_credited'], 0)
        self.assertEqual(result['headline']['denominator'], 0)
        self.assertEqual(result['headline']['all_selected_scorable'], 6)
        self.assertEqual(result['headline']['unscored_due_to_failure'], 6)
        self.assertIsNone(result['headline']['agreement'])
        self.assertIsNone(result['resolved']['cohens_kappa'])

    def test_missing_human_label_cannot_be_guessed_or_silently_excluded(self):
        data = eval.read_json(self.bundle)
        del data['dev'][0]['primary_decision']
        self.bundle.write_text(json.dumps(data))
        self.prepare(); self.write_results(); eval.freeze(self.args())
        with self.assertRaisesRegex(ValueError, 'primary_decision'):
            eval.score(self.args())
        self.assertFalse((self.run/'comparison_report.json').exists())

    def test_integrity_checks(self):
        self.prepare(); self.write_results(); eval.freeze(self.args())
        paths = [self.run/'predictions_frozen.json', self.run/'manifest.json',
                 self.run/'reviewer/skill/rubric_v6.md', self.run/'reviewer/batches/batch_001.jsonl', self.bundle]
        for path in paths:
            before = path.read_bytes()
            path.chmod(0o644)
            path.write_bytes(before + b' ')
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    eval.score(self.args())
            path.write_bytes(before)
        self.assertFalse((self.run/'comparison_report.json').exists())

    def test_frozen_snapshot_not_later_result_edits_is_scored(self):
        self.prepare(); self.write_results(); eval.freeze(self.args())
        self.write_results([])
        self.assertEqual(eval.score(self.args())['coverage']['predictions'], 6)

    def test_known_matrix_and_undefined_kappa(self):
        result = eval.metrics({'approve': {'approve': 74, 'deny': 2}, 'deny': {'approve': 3, 'deny': 9}})
        self.assertAlmostEqual(result['cohens_kappa'], .75)
        self.assertEqual(result['correct'], 83)
        self.assertAlmostEqual(result['agreement'], 83/88)
        for matrix in ({'approve': {'approve': 0, 'deny': 0}, 'deny': {'approve': 0, 'deny': 0}},
                       {'approve': {'approve': 8, 'deny': 0}, 'deny': {'approve': 0, 'deny': 0}}):
            self.assertIsNone(eval.metrics(matrix)['cohens_kappa'])


if __name__ == '__main__':
    unittest.main()
