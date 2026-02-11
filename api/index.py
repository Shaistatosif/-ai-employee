"""
Vercel serverless entry point for AI Employee System.
Simple HTTP handler (no FastAPI for Vercel compatibility).
"""

from http.server import BaseHTTPRequestHandler
import json
import re
from urllib.parse import parse_qs
from datetime import datetime


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


HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
    <title>AI Employee System</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }

        @keyframes glow {
            0%, 100% { box-shadow: 0 0 5px rgba(255, 204, 0, 0.5); }
            50% { box-shadow: 0 0 20px rgba(255, 204, 0, 0.8), 0 0 30px rgba(255, 204, 0, 0.4); }
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateX(-20px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }

        @keyframes gradientMove {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #000000;
            color: #fff;
            min-height: 100vh;
            padding: 20px;
            overflow-x: hidden;
        }

        .bg-gradient {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background:
                radial-gradient(circle at 20% 80%, rgba(255, 0, 0, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(255, 204, 0, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, rgba(255, 100, 0, 0.1) 0%, transparent 40%);
            pointer-events: none;
            z-index: 0;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
            position: relative;
            z-index: 1;
        }

        h1 {
            text-align: center;
            margin-bottom: 10px;
            font-size: 2.8em;
            background: linear-gradient(135deg, #fff 0%, #ffcc00 50%, #ff4444 100%);
            background-size: 200% 200%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: fadeInUp 0.8s ease-out, gradientMove 3s ease infinite;
        }

        .subtitle {
            text-align: center;
            color: #aaa;
            margin-bottom: 30px;
            animation: fadeInUp 0.8s ease-out 0.2s both;
        }

        .badge {
            display: inline-block;
            padding: 8px 18px;
            border-radius: 25px;
            font-size: 0.85em;
            margin: 5px;
            font-weight: 600;
            animation: fadeInUp 0.6s ease-out both;
            transition: all 0.3s ease;
        }

        .badge:hover {
            transform: translateY(-3px);
        }

        .badge-yellow {
            background: linear-gradient(135deg, #ffcc00 0%, #ff9900 100%);
            color: #000;
            animation-delay: 0.3s;
        }

        .badge-red {
            background: linear-gradient(135deg, #ff4444 0%, #cc0000 100%);
            color: #fff;
            animation-delay: 0.4s;
        }

        .badge-white {
            background: linear-gradient(135deg, #ffffff 0%, #dddddd 100%);
            color: #000;
            animation-delay: 0.5s;
        }

        .card {
            background: linear-gradient(145deg, rgba(30, 30, 30, 0.9) 0%, rgba(15, 15, 15, 0.95) 100%);
            border-radius: 20px;
            padding: 28px;
            margin-bottom: 25px;
            border: 1px solid rgba(255, 204, 0, 0.2);
            animation: fadeInUp 0.7s ease-out both;
            transition: all 0.4s ease;
            position: relative;
            overflow: hidden;
        }

        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 204, 0, 0.1), transparent);
            transition: left 0.5s ease;
        }

        .card:hover {
            border-color: rgba(255, 204, 0, 0.5);
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(255, 204, 0, 0.15);
        }

        .card:hover::before {
            left: 100%;
        }

        .card:nth-child(2) { animation-delay: 0.1s; }
        .card:nth-child(3) { animation-delay: 0.2s; }
        .card:nth-child(4) { animation-delay: 0.3s; }
        .card:nth-child(5) { animation-delay: 0.4s; }
        .card:nth-child(6) { animation-delay: 0.5s; }

        .card h2 {
            margin-bottom: 18px;
            color: #ffcc00;
            font-size: 1.4em;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .card h2::before {
            content: '';
            width: 4px;
            height: 24px;
            background: linear-gradient(180deg, #ffcc00 0%, #ff4444 100%);
            border-radius: 2px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 18px;
        }

        .stat-box {
            background: linear-gradient(145deg, rgba(50, 50, 50, 0.5) 0%, rgba(20, 20, 20, 0.8) 100%);
            padding: 22px;
            border-radius: 15px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
            animation: slideIn 0.5s ease-out both;
        }

        .stat-box:nth-child(1) { animation-delay: 0.2s; }
        .stat-box:nth-child(2) { animation-delay: 0.3s; }
        .stat-box:nth-child(3) { animation-delay: 0.4s; }
        .stat-box:nth-child(4) { animation-delay: 0.5s; }

        .stat-box:hover {
            background: linear-gradient(145deg, rgba(255, 204, 0, 0.2) 0%, rgba(255, 68, 68, 0.1) 100%);
            border-color: rgba(255, 204, 0, 0.4);
            transform: scale(1.05);
        }

        .stat-number {
            font-size: 2.2em;
            font-weight: bold;
            background: linear-gradient(135deg, #ffcc00 0%, #ff6600 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .stat-label {
            color: #999;
            font-size: 0.9em;
            margin-top: 5px;
        }

        textarea {
            width: 100%;
            padding: 18px;
            border-radius: 12px;
            border: 2px solid rgba(255, 204, 0, 0.3);
            background: rgba(0, 0, 0, 0.6);
            color: #fff;
            font-size: 1em;
            resize: vertical;
            min-height: 100px;
            transition: all 0.3s ease;
        }

        textarea:focus {
            outline: none;
            border-color: #ffcc00;
            box-shadow: 0 0 20px rgba(255, 204, 0, 0.3);
        }

        textarea::placeholder {
            color: #666;
        }

        button {
            background: linear-gradient(135deg, #ffcc00 0%, #ff9900 50%, #ff4444 100%);
            background-size: 200% 200%;
            color: #000;
            border: none;
            padding: 15px 35px;
            border-radius: 30px;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            margin-top: 18px;
            transition: all 0.3s ease;
            animation: glow 2s ease-in-out infinite;
        }

        button:hover {
            transform: scale(1.08);
            background-position: 100% 50%;
            box-shadow: 0 10px 30px rgba(255, 204, 0, 0.4);
        }

        button:active {
            transform: scale(0.98);
        }

        .result {
            margin-top: 22px;
            padding: 22px;
            border-radius: 15px;
            display: none;
            animation: fadeInUp 0.5s ease-out;
        }

        .result.high {
            background: linear-gradient(135deg, rgba(255, 68, 68, 0.2) 0%, rgba(200, 0, 0, 0.3) 100%);
            border: 2px solid #ff4444;
        }

        .result.low {
            background: linear-gradient(135deg, rgba(255, 204, 0, 0.2) 0%, rgba(200, 150, 0, 0.3) 100%);
            border: 2px solid #ffcc00;
        }

        .result h3 {
            margin-bottom: 12px;
            font-size: 1.2em;
        }

        .workflow {
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
            margin-top: 18px;
        }

        .workflow-step {
            flex: 1;
            min-width: 100px;
            text-align: center;
            padding: 18px 12px;
            background: linear-gradient(145deg, rgba(50, 50, 50, 0.5) 0%, rgba(20, 20, 20, 0.8) 100%);
            border-radius: 15px;
            border: 1px solid rgba(255, 204, 0, 0.2);
            transition: all 0.3s ease;
            animation: fadeInUp 0.6s ease-out both;
        }

        .workflow-step:nth-child(1) { animation-delay: 0.1s; }
        .workflow-step:nth-child(3) { animation-delay: 0.2s; }
        .workflow-step:nth-child(5) { animation-delay: 0.3s; }
        .workflow-step:nth-child(7) { animation-delay: 0.4s; }

        .workflow-step:hover {
            background: linear-gradient(145deg, rgba(255, 204, 0, 0.15) 0%, rgba(255, 68, 68, 0.1) 100%);
            border-color: #ffcc00;
            transform: translateY(-5px);
        }

        .workflow-step.clickable {
            cursor: pointer;
        }

        .workflow-step.active-step {
            border-color: #ffcc00;
            background: linear-gradient(145deg, rgba(255, 204, 0, 0.25) 0%, rgba(255, 68, 68, 0.15) 100%);
            animation: pulse 1s ease-in-out;
        }

        .workflow-step .icon {
            font-size: 1.6em;
            margin-bottom: 10px;
            color: #ffcc00;
        }

        .arrow {
            color: #ff4444;
            font-size: 1.8em;
            align-self: center;
            animation: pulse 1.5s ease-in-out infinite;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 18px;
        }

        th, td {
            padding: 14px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
        }

        tr:hover td {
            background: rgba(255, 204, 0, 0.1);
        }

        th {
            color: #ffcc00;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.9em;
            letter-spacing: 1px;
        }

        .risk-high { color: #ff4444; font-weight: 600; }
        .risk-low { color: #ffcc00; font-weight: 600; }

        footer {
            text-align: center;
            margin-top: 50px;
            padding: 30px;
            color: #666;
            animation: fadeInUp 0.8s ease-out 0.6s both;
        }

        footer a {
            color: #ffcc00;
            text-decoration: none;
            transition: all 0.3s ease;
            position: relative;
        }

        footer a::after {
            content: '';
            position: absolute;
            bottom: -2px;
            left: 0;
            width: 0;
            height: 2px;
            background: linear-gradient(90deg, #ffcc00, #ff4444);
            transition: width 0.3s ease;
        }

        footer a:hover {
            color: #fff;
        }

        footer a:hover::after {
            width: 100%;
        }

        .author-name {
            font-size: 1.3em;
            font-weight: bold;
            background: linear-gradient(135deg, #ffcc00 0%, #ff4444 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-top: 10px;
            display: inline-block;
        }

        ul {
            list-style: none;
            line-height: 2.2;
        }

        ul li {
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            transition: all 0.3s ease;
            animation: slideIn 0.5s ease-out both;
        }

        ul li:nth-child(1) { animation-delay: 0.1s; }
        ul li:nth-child(2) { animation-delay: 0.2s; }
        ul li:nth-child(3) { animation-delay: 0.3s; }
        ul li:nth-child(4) { animation-delay: 0.4s; }

        ul li:hover {
            padding-left: 15px;
            border-bottom-color: rgba(255, 204, 0, 0.3);
        }

        ul li strong {
            color: #ffcc00;
        }
    </style>
</head>
<body>
    <div class="bg-gradient"></div>
    <div class="container">
        <h1>AI Employee System</h1>
        <p class="subtitle">Your life and business on autopilot</p>

        <div style="text-align: center; margin-bottom: 35px;">
            <span class="badge badge-yellow">Silver Tier</span>
            <span class="badge badge-red">HITL Enabled</span>
            <span class="badge badge-white">Demo Mode</span>
        </div>

        <div class="card">
            <h2>System Stats</h2>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-number">48+</div>
                    <div class="stat-label">Tasks Completed</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">3</div>
                    <div class="stat-label">Action Handlers</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">2</div>
                    <div class="stat-label">Active Watchers</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">$50</div>
                    <div class="stat-label">Approval Threshold</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Workflow</h2>
            <div class="workflow">
                <div class="workflow-step clickable" onclick="simulateWorkflow('inbox')">
                    <div class="icon">&#128229; INBOX</div>
                    <div>Drop files</div>
                </div>
                <div class="arrow">&rarr;</div>
                <div class="workflow-step clickable" onclick="simulateWorkflow('ai')">
                    <div class="icon">&#129302; AI</div>
                    <div>Analyzes</div>
                </div>
                <div class="arrow">&rarr;</div>
                <div class="workflow-step clickable" onclick="simulateWorkflow('hitl')">
                    <div class="icon">&#128101; HITL</div>
                    <div>Check</div>
                </div>
                <div class="arrow">&rarr;</div>
                <div class="workflow-step clickable" onclick="simulateWorkflow('done')">
                    <div class="icon">&#9989; DONE</div>
                    <div>Complete</div>
                </div>
            </div>
            <div id="workflowDemo" style="margin-top:18px; display:none;" class="result low"></div>
        </div>

        <div class="card">
            <h2>Try HITL Classification</h2>
            <p style="color: #888; margin-bottom: 18px;">Enter a task to see how the system classifies it:</p>
            <textarea id="taskInput" placeholder="Example: Pay $150 to vendor ABC for monthly subscription"></textarea>
            <button onclick="classifyTask()">Classify Task</button>
            <div id="result" class="result"></div>
        </div>

        <div class="card">
            <h2>HITL Decision Rules</h2>
            <table>
                <tr><th>Content</th><th>Risk</th><th>Action</th></tr>
                <tr><td>Read/analyze files</td><td class="risk-low">Low</td><td>Auto-approve</td></tr>
                <tr><td>Payment &lt; $50</td><td class="risk-low">Low</td><td>Auto-approve</td></tr>
                <tr><td>Payment &gt; $50</td><td class="risk-high">High</td><td>Manual approval</td></tr>
                <tr><td>Delete files</td><td class="risk-high">High</td><td>Manual approval</td></tr>
                <tr><td>Sensitive data</td><td class="risk-high">High</td><td>Manual approval</td></tr>
            </table>
        </div>

        <div class="card">
            <h2>Core Principles</h2>
            <ul>
                <li><strong>Local-First</strong> - All data stays on YOUR machine</li>
                <li><strong>Human-in-the-Loop</strong> - Sensitive actions need YOUR approval</li>
                <li><strong>Security-First</strong> - Credentials never committed</li>
                <li><strong>Autonomous Where Safe</strong> - AI handles routine tasks</li>
            </ul>
        </div>

        <footer>
            <p>Built for Personal AI Employee Hackathon 2026</p>
            <p><a href="https://github.com/Shaistatosif/-ai-employee" target="_blank">GitHub</a></p>
            <p class="author-name">Shaista</p>
        </footer>
    </div>

    <script>
        function simulateWorkflow(step) {
            const demo = document.getElementById('workflowDemo');
            const steps = document.querySelectorAll('.workflow-step');
            steps.forEach(s => s.classList.remove('active-step'));
            event.currentTarget.classList.add('active-step');
            demo.style.display = 'block';

            const info = {
                inbox: {
                    title: '&#128229; INBOX - File Drop Zone',
                    desc: 'Drop any file into <code>obsidian_vault/Inbox/</code> folder. The Filesystem Watcher automatically detects new files within seconds. Gmail Watcher also monitors your email inbox every 60 seconds.',
                    example: 'Example: Drop <b>payment_request.txt</b> or receive an email with invoice'
                },
                ai: {
                    title: '&#129302; AI Analysis Engine',
                    desc: 'The system reads the file/email content, extracts key information (amounts, recipients, keywords), and creates a structured task in <code>Needs_Action/</code> with YAML frontmatter.',
                    example: 'Detects: payment amounts, email addresses, sensitive keywords, action types'
                },
                hitl: {
                    title: '&#128101; Human-in-the-Loop Check',
                    desc: 'HITL classifier evaluates risk level:<br>&#8226; <span style="color:#ffcc00">LOW risk</span> = Auto-approved (read files, organize notes)<br>&#8226; <span style="color:#ff4444">HIGH risk</span> = Needs YOUR approval (payments >$50, deletions, sensitive data)',
                    example: 'Safe tasks go to <b>Approved/</b>, risky tasks go to <b>Pending_Approval/</b>'
                },
                done: {
                    title: '&#9989; Task Complete',
                    desc: 'Approved tasks are executed (emails sent, files processed) and moved to <code>Done/</code> folder. Full audit log is maintained in <code>Logs/</code>.',
                    example: 'Everything is tracked: timestamps, actions taken, approval decisions'
                }
            };

            const data = info[step];
            demo.innerHTML = '<h3>' + data.title + '</h3><p style="margin:10px 0;color:#ccc;">' + data.desc + '</p><p style="color:#999;font-size:0.9em;">' + data.example + '</p>';
            demo.className = 'result low';
            demo.style.display = 'block';
        }

        async function classifyTask() {
            const input = document.getElementById('taskInput').value;
            const resultDiv = document.getElementById('result');

            if (!input.trim()) {
                alert('Please enter a task!');
                return;
            }

            const response = await fetch('/api/classify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: input })
            });

            const data = await response.json();

            resultDiv.style.display = 'block';
            resultDiv.className = 'result ' + (data.requires_approval ? 'high' : 'low');
            resultDiv.innerHTML = '<h3>' + (data.requires_approval ? 'Manual Approval Required' : 'Auto-Approved') + '</h3>' +
                '<p><strong>Risk Level:</strong> ' + data.risk_level + '</p>' +
                '<p><strong>Reason:</strong> ' + data.reason + '</p>' +
                '<p><strong>Action:</strong> ' + (data.requires_approval ? 'Task goes to Pending_Approval folder' : 'Task auto-processed to Done') + '</p>';
        }
    </script>
</body>
</html>"""


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode())

    def do_POST(self):
        if self.path == '/api/classify':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            result = classify_task(data.get('content', ''))

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
