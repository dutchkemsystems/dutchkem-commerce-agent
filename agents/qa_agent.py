"""QA & Testing Agent — tests code, finds bugs, ensures quality."""

import re

from agents.base_agent import BaseAgent

SYSTEM_PROMPT = """You are the QA Agent, an expert in quality assurance.

You analyze and test code for:

1. Code Quality:
   - Cyclomatic complexity
   - Code duplication
   - Naming conventions
   - Code smells

2. Security Vulnerabilities:
   - OWASP Top 10
   - Injection flaws
   - XSS, CSRF, SQL Injection
   - Authentication issues

3. Performance Issues:
   - Bottlenecks
   - Memory leaks
   - N+1 queries
   - Slow algorithms

4. Architectural Consistency:
   - Design pattern adherence
   - Layered architecture
   - Dependency management

5. Test Coverage:
   - Unit tests
   - Integration tests
   - E2E tests
   - Performance tests

6. Technical Debt:
   - Identify technical debt
   - Estimate debt
   - Suggest refactoring

Provide detailed reports with issues found (priority levels), recommendations,
code fixes, test coverage analysis, and quality metrics."""


class QAAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(
            name="QA",
            description="quality assurance, testing, and bug detection",
            system_prompt=SYSTEM_PROMPT,
            **kwargs,
        )

    def analyze_code_static(self, code: str) -> dict:
        """Deterministic static analysis used to seed the LLM report."""
        checks = {
            "has_eval_or_exec": bool(re.search(r"\b(eval|exec)\s*\(", code)),
            "unsafe_sql_concat": bool(
                re.search(r'(?:execute|executemany|query|raw)\s*\([^)]*["\'`]\s*\+', code)
            ),
            "inner_html_or_document_write": bool(
                re.search(r"innerHTML\s*=|document\.write\s*\(", code)
            ),
            "plaintext_password": bool(
                re.search(r"password\s*=\s*[\"']", code)
                and not re.search(r"password\s*=\s*(hash|password_hash|make_password)", code)
            ),
            "todo_or_fixme": len(re.findall(r"\b(TODO|FIXME|HACK)\b", code)),
            "function_count": len(re.findall(r"\b(def|function)\s+\w+", code)),
            "has_tests": bool(re.search(r"\b(unittest|pytest|describe\(|it\(|test_)\b", code)),
            "line_count": code.count("\n") + 1,
        }
        risk = 0
        flags = []
        max_severity = 0
        if checks["has_eval_or_exec"]:
            risk += 3
            max_severity = max(max_severity, 3)
            flags.append("HIGH: eval()/exec() present — possible code injection")
        if checks["unsafe_sql_concat"]:
            risk += 3
            max_severity = max(max_severity, 3)
            flags.append("HIGH: possible SQL injection via string concatenation")
        if checks["inner_html_or_document_write"]:
            risk += 2
            max_severity = max(max_severity, 2)
            flags.append("MEDIUM: innerHTML/document.write — possible XSS")
        if checks["plaintext_password"]:
            risk += 3
            max_severity = max(max_severity, 3)
            flags.append("HIGH: password assigned directly — store hashes only")
        if checks["todo_or_fixme"] > 0:
            risk += 1
            max_severity = max(max_severity, 1)
            flags.append(f"LOW: {checks['todo_or_fixme']} TODO/FIXME markers")
        severity = "LOW" if max_severity == 0 else "MEDIUM" if max_severity == 2 else "HIGH"
        return {
            "severity": severity,
            "risk_score": min(risk, 10),
            "flags": flags,
            "metrics": checks,
        }
