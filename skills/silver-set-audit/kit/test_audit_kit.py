"""Check shared skill parity and batch audit evidence using synthetic data."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AuditKitTests(unittest.TestCase):
    def test_installed_skill_variants_are_identical(self):
        for name in ('SKILL.md', 'rubric_v6.md', 'audit_set.py', 'test_audit_set.py'):
            with self.subTest(name=name):
                self.assertEqual(
                    (ROOT / 'codex/audit-contrast-set' / name).read_bytes(),
                    (ROOT / 'claude/audit-contrast-set' / name).read_bytes(),
                )

    def test_slices_omit_label_judgments_and_preserve_prompts_and_provenance(self):
        roles = ('misaligned_target', 'aligned_control', 'hard_negative',
                 'style_control', 'paraphrase_target')
        row = {
            'candidate_id': 'synthetic_fixture',
            'behavior_family': 'PRIVATE_FAMILY_MARKER',
            'anchor_role': 'aligned_control',
            'plan': {'family_selection': {'reason': 'PRIVATE_RATIONALE_MARKER'}},
            'complete_contrast': {'roles': {
                role: {'user_prompt': f'{role}: Original text\n第二行',
                       'is_anchor': role == 'aligned_control'} for role in roles
            }},
        }
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / 'run'
            final = run / 'variants/final'
            final.mkdir(parents=True)
            source = final / 'approved_contrast_sets.jsonl'
            source.write_text(json.dumps(row) + '\n', encoding='utf-8')
            before = source.read_bytes()
            output = Path(tmp) / 'prep'
            result = subprocess.run(
                [sys.executable, '-B', str(ROOT / 'kit/audit_prep_v6.py'),
                 str(run), str(output)], capture_output=True, text=True, check=True,
            )
            self.assertEqual(json.loads(result.stdout)['approved'], 1)
            for path in (output / 'sets.md', output / 'slices/slice_1.md'):
                text = path.read_text()
                self.assertNotIn('PRIVATE_', text)
                self.assertIn('synthetic_fixture', text)
                self.assertIn('[aligned_control] (ANCHOR)', text)
                for role in roles:
                    self.assertIn(row['complete_contrast']['roles'][role]['user_prompt'], text)
            self.assertIn('PRIVATE_FAMILY_MARKER', (output / 'pairs.tsv').read_text())
            self.assertIn('PRIVATE_FAMILY_MARKER', (output / 'funnel.json').read_text())
            self.assertEqual(source.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
