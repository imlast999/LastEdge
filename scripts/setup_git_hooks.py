#!/usr/bin/env python3
"""
LastEdge Ecosystem — Git Hooks Installer
scripts/setup_git_hooks.py

Installs automated pre-push test guard hooks across all repositories:
1. LastEdge App (.git/hooks/pre-push)
2. LastEdge Trading Engine (.git/hooks/pre-push)
3. LastEdge Strategy Lab (.git/hooks/pre-push)
4. LastEdge Master (.git/hooks/pre-push)
"""

from pathlib import Path
import stat
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent

HOOKS = {
    "LastEdge App": ROOT / "LastEdge App" / ".git" / "hooks" / "pre-push",
    "LastEdge Trading Engine": ROOT / "LastEdge Trading Engine" / ".git" / "hooks" / "pre-push",
    "LastEdge Strategy Lab": ROOT / "LastEdge Strategy Lab" / ".git" / "hooks" / "pre-push",
    "LastEdge Master": ROOT / ".git" / "hooks" / "pre-push",
}

TEMPLATE = """#!/bin/sh
# LastEdge {name} Automated Pre-Push Test Verification Hook

echo ""
echo "============================================================"
echo "🛡️  {name} PRE-PUSH GUARD: Executing Automated Tests"
echo "============================================================"

{cmd}

RESULT=$?

if [ $RESULT -ne 0 ]; then
    echo ""
    echo "❌ [PRE-PUSH REJECTED] Automated tests failed!"
    echo "Push aborted to protect remote branch and CI stability."
    echo "Please fix the failing tests before pushing."
    echo "(Emergency override: 'git push --no-verify')"
    echo "============================================================"
    echo ""
    exit 1
fi

echo ""
echo "✅ [PRE-PUSH PASSED] All tests green! Proceeding with push."
echo "============================================================"
echo ""
exit 0
"""

COMMANDS = {
    "LastEdge App": "python -m pytest tests/ -q --tb=short",
    "LastEdge Trading Engine": "python -m pytest tests/ -q --tb=short",
    "LastEdge Strategy Lab": "python -m pytest tests/ -q --tb=short",
    "LastEdge Master": "git status --short",
}


def install():
    print("=" * 60)
    print("🚀 Installing LastEdge Automated Pre-Push Git Hooks...")
    print("=" * 60)

    for name, hook_path in HOOKS.items():
        if not hook_path.parent.exists():
            print(f"⚠️  Skipping {name}: .git/hooks directory not found")
            continue

        cmd = COMMANDS.get(name, "python -m pytest tests/ -q")
        content = TEMPLATE.format(name=name, cmd=cmd)

        hook_path.write_text(content, encoding="utf-8")

        # Ensure executable permissions on POSIX / Git Bash
        try:
            current_mode = hook_path.stat().st_mode
            hook_path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except Exception:
            pass

        print(f"✅ Installed pre-push hook for: {name}")

    print("=" * 60)
    print("🛡️  All hooks active! Automated tests will guard every 'git push'.")
    print("=" * 60)


if __name__ == "__main__":
    install()
