"""Performance & Scalability Optimization — static analysis heuristics."""

import re


class PerformanceOptimizer:
    """Analyze code and suggest performance improvements."""

    def analyze_performance(self, code: str) -> dict:
        return {
            "time_complexity": self.analyze_time_complexity(code),
            "space_complexity": self.analyze_space_complexity(code),
            "memory_usage": self.analyze_memory_usage(code),
            "bottlenecks": self.find_bottlenecks(code),
            "optimizations": self.suggest_optimizations(code),
        }

    def analyze_time_complexity(self, code: str) -> str:
        depth = self._max_nesting(code)
        if depth >= 2:
            return "O(n^2) or worse (nested loops detected)"
        if depth == 1:
            return "O(n) (linear loop)"
        return "O(1) (constant) — verify with profiling"

    def analyze_space_complexity(self, code: str) -> str:
        if re.search(r"\[.*\]\s*=\s*\[.*\]", code) or re.search(r"\bmemmove\b", code):
            return "O(n) auxiliary memory (full copies detected)"
        return "O(1) auxiliary memory (no large copies detected)"

    def analyze_memory_usage(self, code: str) -> list:
        issues = []
        if re.search(r"readlines\(\)", code):
            issues.append("readlines() loads whole file into memory — stream instead")
        if re.search(r"\.append\s*\([^)]*\)\s*$", code) and re.search(r"for\s", code):
            issues.append("Consider generator expressions instead of building lists")
        if re.search(r"import\s+\*\s*$", code):
            issues.append("Star imports bloat memory/namespace — import explicitly")
        return issues

    def find_bottlenecks(self, code: str) -> list:
        bottlenecks = []
        if re.search(r"math\.\w+\s*\(", code) and re.search(r"for\s", code):
            bottlenecks.append("Math calls inside loops — hoist invariant computations")
        if len(re.findall(r"for\s", code)) > 3:
            bottlenecks.append("Many loops — consider vectorization or batching")
        return bottlenecks

    def suggest_optimizations(self, code: str) -> list:
        suggestions = []
        if re.search(r"len\s*\([^)]*\)\s*", code) and re.search(r"range\s*\(", code):
            suggestions.append("Cache len() outside loop condition")
        if re.search(r"list\b", code) and re.search(r"\bfor\b", code) and re.search(r"\bin\b", code):
            suggestions.append("Use a set for O(1) membership tests")
        if re.search(r"math\.sqrt", code) and re.search(r"for\s", code):
            suggestions.append("Move math.sqrt() outside the loop")
        if re.search(r"pd\.concat|DataFrame\.append", code):
            suggestions.append("Pre-allocate or use list-of-dicts before concat")
        if not suggestions:
            suggestions.append("No obvious static optimizations — profile with a profiler")
        return suggestions

    def _max_nesting(self, code: str) -> int:
        depth = 0
        max_depth = 0
        in_indent = None
        for line in code.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            current = len(line) - len(line.lstrip())
            if in_indent is not None and current > in_indent:
                depth += 1
                max_depth = max(max_depth, depth)
            else:
                if re.match(r"(for|while|if|elif|else|def|with|try|except|finally)\b", stripped):
                    depth = 1
                else:
                    depth = 0
            if re.match(r"(for|while|if|elif|else|def|with|try|except|finally)\b", stripped):
                in_indent = current
            else:
                in_indent = None
        return max_depth
