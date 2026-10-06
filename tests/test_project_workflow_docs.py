"""Documentation contract checks; not a claim of agent behavioral performance."""
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
class ProjectWorkflowDocumentationTests(unittest.TestCase):
    def test_canonical_todo_contract_preserves_primary_task_and_authority(self):
        body=(ROOT/'PRODUCT_INVARIANTS.md').read_text().split('## 19. Project to-do awareness without task drift')[1]
        for clause in ('primary objective', 'authorized', 'acceptance checks pass', 'not new permission', 'does not halt independent work'):
            self.assertIn(clause, body)
    def test_agent_router_points_to_canonical_contract(self):
        body=(ROOT/'AGENTS.md').read_text()
        self.assertIn('PRODUCT_INVARIANTS.md` section 19', body)
        self.assertIn('without duplicating active work', body)
    def test_chat_catalog_and_agent_boundary_stay_explicit(self):
        self.assertIn('not a roster of autonomous agents', (ROOT/'README.md').read_text())
        self.assertIn('not independent agents', (ROOT/'wiki/Skills-Catalog.md').read_text())
        self.assertIn('No prompt can grant permissions', (ROOT/'docs/CHAT-AND-AGENT-BOUNDARIES.md').read_text())
if __name__=='__main__': unittest.main()
