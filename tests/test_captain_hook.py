"""Unit tests for captain-hook CLI and guards."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest

from src.captain_hook import (
    dispatch_event,
    guard_commands,
    guard_secrets,
    guard_symlinks,
    init_agent_configs,
)


class TestCaptainHookGuards(unittest.TestCase):
    def test_guard_secrets_detects_aws_key(self):
        text = 'aws_key = "AKIA1234567890ABCDEF"'
        res = guard_secrets(text)
        self.assertIsNotNone(res)
        self.assertIn("AWS Access Key", res)

    def test_guard_secrets_detects_github_pat(self):
        text = "ghp_" + "a" * 36
        res = guard_secrets(text)
        self.assertIsNotNone(res)
        self.assertIn("GitHub Personal Access Token", res)

    def test_guard_secrets_detects_anthropic_key(self):
        text = "sk-ant-" + "a" * 40
        res = guard_secrets(text)
        self.assertIsNotNone(res)
        self.assertIn("Anthropic API Key", res)

    def test_guard_commands_detects_rm_rf(self):
        res = guard_commands("rm -rf /")
        self.assertIsNotNone(res)
        self.assertIn("Dangerous shell command", res)

    def test_guard_commands_detects_force_push(self):
        res = guard_commands("git push origin main --force")
        self.assertIsNotNone(res)
        self.assertIn("Dangerous shell command", res)

    def test_guard_symlinks_blocks_symlink(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        target = os.path.join(d, "target.py")
        link = os.path.join(d, "link.py")
        with open(target, "w") as f:
            f.write("print(1)")
        os.symlink(target, link)
        self.assertIsNotNone(guard_symlinks(link))


class TestCaptainHookInit(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def test_init_all_agents(self):
        init_agent_configs("all", self.dir)
        self.assertTrue(os.path.exists(os.path.join(self.dir, ".cursor", "hooks.json")))
        self.assertTrue(os.path.exists(os.path.join(self.dir, ".windsurf", "hooks.json")))
        self.assertTrue(os.path.exists(os.path.join(self.dir, ".claude", "settings.json")))
        self.assertTrue(os.path.exists(os.path.join(self.dir, ".aider.conf.yml")))
        self.assertTrue(os.path.exists(os.path.join(self.dir, "hooks", "prevent.py")))

    def test_dispatch_pre_prompt_blocks_secret(self):
        payload = json.dumps({"prompt": "my token is ghp_" + "x" * 36})
        code = dispatch_event("PrePrompt", payload)
        self.assertEqual(code, 2)

    def test_dispatch_pre_prompt_allows_clean(self):
        payload = json.dumps({"prompt": "please fix the bug in main.py"})
        code = dispatch_event("PrePrompt", payload)
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
