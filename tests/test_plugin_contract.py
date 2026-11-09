"""Standalone-plugin architecture contract tests."""

from __future__ import annotations

import ast
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "hermes_linear_agent"
HERMES_ROOTS = {"agent", "cron", "gateway", "hermes_cli", "hermes_constants", "tools", "toolsets", "utils"}


def _python_files():
    return sorted(PACKAGE.glob("*.py"))


def test_manifest_declares_external_platform_plugin():
    manifest = yaml.safe_load((ROOT / "plugin.yaml").read_text(encoding="utf-8"))
    assert manifest["name"] == "linear-agent"
    assert manifest["kind"] == "platform"
    assert manifest["version"] == "0.4.3"
    assert manifest["requires_env"] == []


def test_package_has_no_old_in_tree_namespace():
    for path in _python_files():
        assert "plugins.platforms.linear_agent" not in path.read_text(encoding="utf-8"), path


def test_package_does_not_import_private_hermes_apis():
    violations = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in HERMES_ROOTS:
                    private = [alias.name for alias in node.names if alias.name.startswith("_")]
                    if private:
                        violations.append((path.name, node.module, private))
    assert not violations


def test_tools_register_only_through_plugin_context():
    tools_source = (PACKAGE / "tools.py").read_text(encoding="utf-8")
    registry_source = (PACKAGE / "registry.py").read_text(encoding="utf-8")
    assert "from tools.registry import" not in tools_source
    assert "registry.register(" not in tools_source
    assert "from tools.registry import" not in registry_source
    assert "ctx.register_tool(" in tools_source


def test_pip_entry_point_targets_package_module():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'linear-agent = "hermes_linear_agent"' in pyproject
