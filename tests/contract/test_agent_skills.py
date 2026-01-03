import os
import pytest
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent

CLAUDE_SKILLS = [
    ".claude/commands/container.md",
    ".claude/commands/connection.md",
    ".claude/commands/fixture.md",
    ".claude/commands/troubleshooting.md",
]

CURSOR_RULES = [
    ".cursor/rules/iris-container.mdc",
    ".cursor/rules/iris-connection.mdc",
    ".cursor/rules/iris-fixtures.mdc",
    ".cursor/rules/iris-troubleshooting.mdc",
]

@pytest.mark.unit
@pytest.mark.contract
class TestAgentSkills:
    
    @pytest.mark.parametrize("skill_path", CLAUDE_SKILLS)
    def test_claude_skill_structure(self, skill_path):
        path = REPO_ROOT / skill_path
        assert path.exists(), f"Skill file missing: {skill_path}"
        
        content = path.read_text()
        lines = content.splitlines()
        
        first_non_empty_line = next(l for l in lines if l.strip())
        assert first_non_empty_line.startswith("# description:"), f"Missing Claude description header in {skill_path}"
        
        assert "## Prerequisites" in content, f"Missing Prerequisites in {skill_path}"
        has_commands = "## CLI Commands" in content
        has_issues = "## Common Issues" in content
        assert has_commands or has_issues, f"Missing Commands/Content in {skill_path}"

    @pytest.mark.parametrize("rule_path", CURSOR_RULES)
    def test_cursor_rule_structure(self, rule_path):
        path = REPO_ROOT / rule_path
        assert path.exists(), f"Rule file missing: {rule_path}"
        
        content = path.read_text()
        assert content.startswith("---"), "Missing YAML frontmatter start"
        
        try:
            _, frontmatter, body = content.split("---", 2)
            data = yaml.safe_load(frontmatter)
            
            assert "description" in data, f"Missing description in frontmatter of {rule_path}"
            assert "globs" in data, f"Missing globs in frontmatter of {rule_path}"
            
        except ValueError:
            pytest.fail(f"Invalid frontmatter format in {rule_path}")
            
        has_skill_title = "# Skill:" in body
        has_troubleshooting_title = "# Troubleshooting" in body
        assert has_skill_title or has_troubleshooting_title, "Missing Title"
        assert "## Prerequisites" in body, "Missing Prerequisites"

    def test_copilot_instructions_exist(self):
        path = REPO_ROOT / ".github/copilot-instructions.md"
        assert path.exists()
        content = path.read_text()
        
        assert "## Agent Skills" in content
        assert "1. Container Management" in content
        assert "2. Database Connection" in content
