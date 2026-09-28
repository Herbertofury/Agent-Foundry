import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DrivePersistencePolicyTests(unittest.TestCase):
    def test_skill_activation_covers_material_saved_output(self):
        text = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('mandatory Google Drive persistence', text)
        self.assertIn('creates, modifies, saves, packages, checkpoints, or delivers a material file', text)
        self.assertIn('references/DRIVE-PERSISTENCE.md', text)
        self.assertIn('Publish every material saved file/artifact/checkpoint to connected Drive and verify it', text)

    def test_drive_reference_is_linked_and_mandatory(self):
        skill = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
        ref = (ROOT / 'references' / 'DRIVE-PERSISTENCE.md').read_text(encoding='utf-8')
        self.assertIn('references/DRIVE-PERSISTENCE.md', skill)
        self.assertIn('Google Drive is a required durable remote', ref)
        self.assertIn('Do not upload after every micro-edit', ref)
        self.assertIn('GitHub/ProjectDump synchronization does not satisfy the Drive requirement by itself', ref)

    def test_generated_agents_contract_requires_drive(self):
        standalone = (ROOT / 'assets' / 'agents-md-hybrid' / 'AGENTS.md').read_text(encoding='utf-8')
        modular = (ROOT / 'assets' / 'agents-md-hybrid' / '.agents' / 'MEMORY-CONTINUITY.md').read_text(encoding='utf-8')
        self.assertIn('publish material artifacts/checkpoints to connected Google Drive', standalone)
        self.assertIn('connected Google Drive is a mandatory durable remote', modular)

    def test_library_is_not_drive_substitute(self):
        ref = (ROOT / 'references' / 'DRIVE-PERSISTENCE.md').read_text(encoding='utf-8')
        self.assertIn('Never silently downgrade to ChatGPT Library as the durable substitute', ref)


if __name__ == '__main__':
    unittest.main()
