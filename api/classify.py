"""
API endpoint for task classification.
"""

from http.server import BaseHTTPRequestHandler
import json
import re


def classify_task(content: str) -> dict:
    """Simulate HITL classification."""
    content_lower = content.lower()

    # Check for payment amounts
    amounts = re.findall(r'\$\s*(\d+(?:\.\d{2})?)', content)
    max_amount = max([float(a) for a in amounts]) if amounts else 0

    if max_amount > 50:
        return {
            "risk_level": "HIGH",
            "requires_approval": True,
            "reason": f"Payment ${max_amount} exceeds $50 threshold"
        }

    if any(kw in content_lower for kw in ["delete", "remove"]):
        return {
            "risk_level": "HIGH",
            "requires_approval": True,
            "reason": "File deletion is irreversible"
        }

    if any(kw in content_lower for kw in ["password", "credit card", "ssn"]):
        return {
            "risk_level": "HIGH",
            "requires_approval": True,
            "reason": "Contains sensitive information"
        }

    return {
        "risk_level": "LOW",
        "requires_approval": False,
        "reason": "Safe task - auto-approved"
    }


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))

        result = classify_task(data.get('content', ''))

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
