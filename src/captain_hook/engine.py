"""Modular Policy Engine & Event Dispatcher."""

from __future__ import annotations

import json
import os
import sys
from typing import Dict, List, Type

from .adapters import BUILTIN_ADAPTERS, BaseAgentAdapter
from .models import HookPayload, PolicyResult
from .policies import BUILTIN_POLICIES, BasePolicy


def _extract_fields(payload: dict) -> HookPayload:
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}

    prompt = payload.get("prompt") or payload.get("user_prompt") or payload.get("raw") or ""
    path = (
        payload.get("path")
        or payload.get("filepath")
        or payload.get("file_path")
        or payload.get("file")
        or tool_input.get("file_path")
        or tool_input.get("path")
        or ""
    )
    command = (
        payload.get("command")
        or payload.get("command_string")
        or payload.get("cmd")
        or tool_input.get("command")
        or ""
    )
    tool = payload.get("tool") or payload.get("tool_name") or ""
    server = payload.get("server") or payload.get("mcp_server_name") or ""
    args = payload.get("args") or payload.get("arguments") or tool_input or {}
    raw = payload.get("raw") or ""

    return HookPayload(
        prompt=prompt,
        path=path,
        command=command,
        tool=tool,
        server=server,
        args=args,
        raw=raw,
    )


class Engine:
    """Modular Engine for captain-hook.
    
    Supports registering custom policies and custom agent adapters dynamically.
    """

    def __init__(self):
        self.policies: List[BasePolicy] = list(BUILTIN_POLICIES)
        self.adapters: Dict[str, BaseAgentAdapter] = {
            adapter.name: adapter for adapter in BUILTIN_ADAPTERS
        }

    def register_policy(self, policy: BasePolicy):
        """Add a custom security/quality policy module."""
        self.policies.append(policy)

    def register_adapter(self, adapter: BaseAgentAdapter):
        """Add a custom AI agent configuration adapter."""
        self.adapters[adapter.name] = adapter

    def dispatch(self, event_name: str, payload_data: dict | str) -> PolicyResult:
        if isinstance(payload_data, str):
            if payload_data.strip():
                try:
                    payload_dict = json.loads(payload_data)
                except json.JSONDecodeError:
                    payload_dict = {"raw": payload_data}
            else:
                payload_dict = {}
        else:
            payload_dict = payload_data

        payload = _extract_fields(payload_dict)

        for policy in self.policies:
            if not policy.events_handled or event_name in policy.events_handled:
                result = policy.evaluate(event_name, payload)
                if not result.allowed:
                    return result

        return PolicyResult(allowed=True, exit_code=0)

    def dispatch_from_stdin(self, event_name: str) -> int:
        stdin_data = sys.stdin.read() if not sys.stdin.isatty() else ""
        res = self.dispatch(event_name, stdin_data)
        if not res.allowed:
            sys.stderr.write(f"captain-hook: {res.message}\n")
            return res.exit_code
        return 0

    def init_agent_configs(self, target_agent: str, root_dir: str):
        print(f"captain-hook: Initializing agent hook configurations in {root_dir}")

        targets = list(self.adapters.keys()) if target_agent == "all" else [target_agent]

        for name in targets:
            adapter = self.adapters.get(name)
            if not adapter:
                print(f"  ⚠️ Warning: Agent adapter '{name}' not found.")
                continue

            target_path = os.path.join(root_dir, adapter.config_relpath)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            content = adapter.generate_config_content()

            if isinstance(content, dict):
                with open(target_path, "w", encoding="utf-8") as f:
                    json.dump(content, f, indent=2)
            else:
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(content)

            if target_path.endswith(".py"):
                os.chmod(target_path, 0o755)

            print(f"  ✓ Created {adapter.config_relpath} ({adapter.name.capitalize()})")

        print("\nInitialization complete! Captain Hook is ready to protect your project.")
