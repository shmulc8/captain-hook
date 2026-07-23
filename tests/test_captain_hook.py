"""Unit tests for modular captain-hook Engine, Policies, and Adapters."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest

from captain_hook import Engine, HookPayload, PolicyResult
from captain_hook.policies import (
    BasePolicy,
    CommandSandboxPolicy,
    SecretScannerPolicy,
    SymlinkGuardPolicy,
)


class CustomTestPolicy(BasePolicy):
    name = "custom_test_policy"
    events_handled = ["PrePrompt"]

    def evaluate(self, event: str, payload: HookPayload) -> PolicyResult:
        if "forbidden" in payload.prompt:
            return PolicyResult(allowed=False, exit_code=2, message="Forbidden keyword detected")
        return PolicyResult(allowed=True, exit_code=0)


class TestModularPolicies(unittest.TestCase):
    def setUp(self):
        self.engine = Engine()

    def test_secret_scanner_policy(self):
        res = self.engine.dispatch("PrePrompt", json.dumps({"prompt": "my key is AKIA1234567890ABCDEF"}))
        self.assertFalse(res.allowed)
        self.assertEqual(res.exit_code, 2)
        self.assertIn("AWS Access Key", res.message)

    def test_command_sandbox_policy(self):
        res = self.engine.dispatch("PreCommand", json.dumps({"command": "rm -rf /"}))
        self.assertFalse(res.allowed)
        self.assertEqual(res.exit_code, 2)
        self.assertIn("Dangerous shell command", res.message)

    def test_symlink_guard_policy(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        target = os.path.join(d, "target.py")
        link = os.path.join(d, "link.py")
        with open(target, "w") as f:
            f.write("print(1)")
        os.symlink(target, link)

        res = self.engine.dispatch("PreWrite", json.dumps({"path": link}))
        self.assertFalse(res.allowed)
        self.assertEqual(res.exit_code, 2)
        self.assertIn("symlink", res.message)

    def test_custom_policy_registration(self):
        self.engine.register_policy(CustomTestPolicy())

        res1 = self.engine.dispatch("PrePrompt", json.dumps({"prompt": "this is fine"}))
        self.assertTrue(res1.allowed)

        res2 = self.engine.dispatch("PrePrompt", json.dumps({"prompt": "this is forbidden"}))
        self.assertFalse(res2.allowed)
        self.assertEqual(res2.exit_code, 2)
        self.assertIn("Forbidden keyword", res2.message)


class TestModularAdapters(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.engine = Engine()

    def test_init_all_adapters(self):
        self.engine.init_agent_configs("all", self.dir)
        self.assertTrue(os.path.exists(os.path.join(self.dir, ".cursor", "hooks.json")))
        self.assertTrue(os.path.exists(os.path.join(self.dir, ".windsurf", "hooks.json")))
        self.assertTrue(os.path.exists(os.path.join(self.dir, ".claude", "settings.json")))
        self.assertTrue(os.path.exists(os.path.join(self.dir, ".aider.conf.yml")))
        self.assertTrue(os.path.exists(os.path.join(self.dir, "hooks", "prevent.py")))


if __name__ == "__main__":
    unittest.main()
