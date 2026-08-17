"""Built-in browser tool — fetches and extracts web content."""


try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


class BuiltInBrowser:
    """Fetch web pages and extract readable text (no browser dependency)."""

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def fetch(self, url: str) -> dict:
        """Fetch a URL and return status, text, and headers."""
        if requests is None:
            return {"ok": False, "error": "requests library not installed"}
        try:
            resp = requests.get(url, timeout=self.timeout, headers={"User-Agent": "Dutchkem/4.0"})
            resp.raise_for_status()
            text = resp.text
            return {
                "ok": True,
                "url": resp.url,
                "status": resp.status_code,
                "content_type": resp.headers.get("Content-Type", ""),
                "text": text,
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def extract_text(self, url: str, max_chars: int = 20000) -> str:
        """Fetch a URL and strip tags for a plain-text read."""
        result = self.fetch(url)
        if not result.get("ok"):
            return f"[fetch error: {result.get('error')}]"
        return self._strip_tags(result["text"])[:max_chars]

    @staticmethod
    def _strip_tags(html: str) -> str:
        import re
        html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
        html = re.sub(r"<[^>]+>", " ", html)
        html = re.sub(r"\s+", " ", html)
        return html.strip()
