"""Advanced Security & Compliance Framework — static scanners."""

import re


class VulnerabilityScanner:
    """Heuristic static vulnerability scanner."""

    OWASP_PATTERNS = {
        "injection": r"\b(eval|exec|system|popen|os\.system|shell_exec)\s*\(",
        "xss": r"innerHTML\s*=|document\.write\s*\(|\.html\s*\(",
        "sql_injection": r"(?:execute|executemany|query|raw)\s*\([^)]*[\"']\s*\+",
        "command_injection": r"(?:subprocess|os\.system)\.(?:call|run|popen)\s*\([^)]*\+",
    }

    def scan(self, code: str) -> dict:
        findings = []
        for vuln_type, pattern in self.OWASP_PATTERNS.items():
            matches = re.findall(pattern, code)
            if matches:
                findings.append(
                    {"type": vuln_type, "severity": "HIGH", "count": len(matches)}
                )
        return {"vulnerabilities": findings, "finding_count": len(findings)}


class ComplianceChecker:
    """Check code/spec text for compliance-related obligations."""

    FRAMEWORKS = ["GDPR", "HIPAA", "SOC2", "PCI-DSS", "NIST"]

    def scan(self, code: str) -> dict:
        issues = []
        lower = code.lower()
        if re.search(r"password\s*=\s*[\"']", code) and not re.search(
            r"(hash|bcrypt|argon|password_hash)", code
        ):
            issues.append("Storing raw passwords — GDPR/SOC2 concern")
        if "credit_card" in lower or "card_number" in lower:
            issues.append("Card data handling — PCI-DSS scope")
        if "health" in lower or "medical" in lower:
            issues.append("Health data handling — HIPAA scope")
        if "email" in lower and "log" in lower:
            issues.append("Logging PII (email) — minimize collection")
        status = {f: "review" for f in self.FRAMEWORKS}
        return {"issues": issues, "frameworks": status}


class SecureCodeAnalyzer:
    """Check for insecure coding patterns."""

    def scan(self, code: str) -> dict:
        issues = []
        if re.search(r"random\s*\.\s*choice|rand\s*\(|mt_rand\s*\(", code) and re.search(
            r"(password|token|secret|key)", code
        ):
            issues.append("Insecure randomness for secrets — use CSPRNG")
        if re.search(r"http://", code):
            issues.append("Cleartext http:// URLs — use TLS")
        if re.search(r"print\s*\(|console\.log\(", code) and re.search(
            r"(password|secret|api[_-]?key|token)", code.lower()
        ):
            issues.append("Potential secret leakage in logs")
        return {"issues": issues}


class SecurityFramework:
    """Aggregates all scanners and produces a security report."""

    def __init__(self):
        self.scanners = {
            "vulnerability": VulnerabilityScanner(),
            "compliance": ComplianceChecker(),
            "secure_code": SecureCodeAnalyzer(),
        }

    def scan_code(self, code: str) -> dict:
        results = {name: scanner.scan(code) for name, scanner in self.scanners.items()}
        return self.generate_report(results)

    def generate_report(self, results: dict) -> dict:
        findings = []
        for kind, result in results.items():
            for item in result.get("vulnerabilities", []) or result.get("issues", []):
                if isinstance(item, dict):
                    findings.append({**item, "source": kind})
                else:
                    findings.append({"type": kind, "severity": "LOW", "detail": item})
        high = sum(1 for f in findings if str(f.get("severity", "")).upper() == "HIGH")
        score = max(0, 100 - high * 25)
        return {
            "scan_results": results,
            "findings": findings,
            "high_severity_count": high,
            "security_score": score,
            "summary": f"Security score {score}/100 with {len(findings)} finding(s).",
        }
