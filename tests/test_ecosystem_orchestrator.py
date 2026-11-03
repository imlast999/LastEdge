"""
Unit Tests for LastEdge Root Ecosystem Orchestrator
tests/test_ecosystem_orchestrator.py
"""

import os
import re
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


class TestEcosystemOrchestrator(unittest.TestCase):
    """Verifica que el orquestador raíz del ecosistema se mantenga limpio y funcional."""

    def test_cli_syntax_and_structure(self):
        cli_path = ROOT_DIR / "cli.py"
        self.assertTrue(cli_path.exists(), "cli.py debe existir en la raíz")
        
        # Verify it compiles cleanly
        code = cli_path.read_text(encoding="utf-8")
        compiled = compile(code, str(cli_path), "exec")
        self.assertIsNotNone(compiled)

    def test_clone_repos_script(self):
        script_path = ROOT_DIR / "clone_repos.bat"
        self.assertTrue(script_path.exists(), "clone_repos.bat debe existir en la raíz")
        
        content = script_path.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("imlast999/lastedge-trading-engine.git", content)
        self.assertIn("imlast999/lastedge-strategy-lab.git", content)
        self.assertIn("imlast999/lastedge-app.git", content)

    def test_gitignore_protects_root_purity(self):
        """Verifica que el repositorio raíz no trackee los sub-repositorios."""
        gitignore_path = ROOT_DIR / ".gitignore"
        self.assertTrue(gitignore_path.exists(), ".gitignore debe existir en la raíz")
        
        content = gitignore_path.read_text(encoding="utf-8")
        self.assertIn("/LastEdge Trading Engine/", content)
        self.assertIn("/LastEdge Strategy Lab/", content)
        self.assertIn("/LastEdge App/", content)

    def test_tunnel_utilities_syntax(self):
        for util in ["ssh_tunnel.py", "dashboard_tunnel.py"]:
            util_path = ROOT_DIR / util
            if util_path.exists():
                code = util_path.read_text(encoding="utf-8")
                compiled = compile(code, str(util_path), "exec")
                self.assertIsNotNone(compiled)


if __name__ == "__main__":
    unittest.main()
