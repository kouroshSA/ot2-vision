"""Validate generated OT-2 protocols before execution."""

import ast
import subprocess
import tempfile
from pathlib import Path


class ProtocolValidator:
    """Validate generated OT-2 protocols."""

    @staticmethod
    def check_syntax(code: str) -> tuple[bool, str]:
        """Check Python syntax validity. Returns (is_valid, error_message)."""
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            return False, f"Syntax error at line {e.lineno}: {e.msg}"

    @staticmethod
    def check_required_elements(code: str) -> tuple[bool, list[str]]:
        """Check that required OT-2 protocol elements are present."""
        issues = []
        if "from opentrons" not in code:
            issues.append("Missing 'from opentrons import protocol_api'")
        if "def run(" not in code:
            issues.append("Missing 'def run(protocol)' function")
        if "'apiLevel'" not in code and '"apiLevel"' not in code:
            issues.append("Missing apiLevel in metadata/requirements")
        if "'robotType'" not in code and '"robotType"' not in code:
            issues.append("Missing robotType in requirements")
        return len(issues) == 0, issues

    @staticmethod
    def simulate(code: str, timeout: int = 60) -> tuple[bool, str]:
        """
        Run opentrons_simulate on the protocol.
        Requires opentrons package installed.
        Returns (success, output_text).
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            tmp_path = f.name

        try:
            result = subprocess.run(
                ["opentrons_simulate", tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            success = result.returncode == 0
            output = result.stdout + result.stderr
            return success, output
        except FileNotFoundError:
            return False, "opentrons_simulate not found. Install opentrons package."
        except subprocess.TimeoutExpired:
            return False, f"Simulation timed out after {timeout} seconds"
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @staticmethod
    def validate(code: str) -> tuple[bool, str]:
        """Run all validation checks. Returns (is_valid, summary_message)."""
        # Syntax check
        syntax_ok, syntax_err = ProtocolValidator.check_syntax(code)
        if not syntax_ok:
            return False, f"Syntax error: {syntax_err}"

        # Structure check
        struct_ok, struct_issues = ProtocolValidator.check_required_elements(code)
        if not struct_ok:
            return False, f"Missing elements: {', '.join(struct_issues)}"

        return True, "Protocol passes syntax and structure checks"
