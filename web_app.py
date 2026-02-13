"""
Simple web interface for Personal AI Employee System.
For Railway deployment and demo purposes.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import uvicorn
from datetime import datetime
import os

app = FastAPI(title="AI Employee System", version="0.1.0")

# Simulated data for demo (in cloud, no local vault)
demo_stats = {
    "tasks_pending": 0,
    "awaiting_approval": 0,
    "completed": 6,
    "system_status": "Running",
    "mode": "DEMO"
}

demo_logs = []

def classify_task(content: str) -> dict:
    """Simulate HITL classification."""
    content_lower = content.lower()

    # Check for payment amounts
    import re
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


@app.get("/", response_class=HTMLResponse)
async def home():
    """Dashboard homepage."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🤖 AI Employee System</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                color: #fff;
                min-height: 100vh;
                padding: 20px;
            }
            .container { max-width: 900px; margin: 0 auto; }
            h1 { text-align: center; margin-bottom: 10px; font-size: 2.5em; }
            .subtitle { text-align: center; color: #8892b0; margin-bottom: 30px; }
            .badge {
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 0.8em;
                margin: 5px;
            }
            .badge-green { background: #10b981; }
            .badge-yellow { background: #f59e0b; }
            .badge-blue { background: #3b82f6; }
            .card {
                background: rgba(255,255,255,0.05);
                border-radius: 15px;
                padding: 25px;
                margin-bottom: 20px;
                border: 1px solid rgba(255,255,255,0.1);
            }
            .card h2 { margin-bottom: 15px; color: #64ffda; }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
            }
            .stat-box {
                background: rgba(255,255,255,0.05);
                padding: 20px;
                border-radius: 10px;
                text-align: center;
            }
            .stat-number { font-size: 2em; font-weight: bold; color: #64ffda; }
            .stat-label { color: #8892b0; font-size: 0.9em; }
            textarea {
                width: 100%;
                padding: 15px;
                border-radius: 10px;
                border: 1px solid rgba(255,255,255,0.2);
                background: rgba(0,0,0,0.3);
                color: #fff;
                font-size: 1em;
                resize: vertical;
                min-height: 100px;
            }
            button {
                background: linear-gradient(135deg, #64ffda 0%, #10b981 100%);
                color: #1a1a2e;
                border: none;
                padding: 12px 30px;
                border-radius: 25px;
                font-size: 1em;
                font-weight: bold;
                cursor: pointer;
                margin-top: 15px;
                transition: transform 0.2s;
            }
            button:hover { transform: scale(1.05); }
            .result {
                margin-top: 20px;
                padding: 20px;
                border-radius: 10px;
                display: none;
            }
            .result.high { background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; }
            .result.low { background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; }
            .workflow {
                display: flex;
                justify-content: space-between;
                flex-wrap: wrap;
                gap: 10px;
                margin-top: 15px;
            }
            .workflow-step {
                flex: 1;
                min-width: 100px;
                text-align: center;
                padding: 15px;
                background: rgba(255,255,255,0.05);
                border-radius: 10px;
            }
            .workflow-step .icon { font-size: 2em; margin-bottom: 10px; }
            .arrow { color: #64ffda; font-size: 1.5em; align-self: center; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }
            th { color: #64ffda; }
            .risk-high { color: #ef4444; }
            .risk-low { color: #10b981; }
            .form-input {
                width: 100%;
                padding: 12px 15px;
                border-radius: 10px;
                border: 1px solid rgba(255,255,255,0.2);
                background: rgba(0,0,0,0.3);
                color: #fff;
                font-size: 1em;
                margin-bottom: 10px;
            }
            .action-form { animation: fadeIn 0.3s ease; }
            @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
            footer { text-align: center; margin-top: 40px; color: #8892b0; }
            footer a { color: #64ffda; text-decoration: none; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 AI Employee System</h1>
            <p class="subtitle">Your life and business on autopilot</p>

            <div style="text-align: center; margin-bottom: 30px;">
                <span class="badge badge-green">✅ Gold Tier</span>
                <span class="badge badge-blue">🔒 HITL Enabled</span>
                <span class="badge badge-yellow">🧪 Demo Mode</span>
            </div>

            <div class="card">
                <h2>📊 System Stats</h2>
                <div class="stats-grid">
                    <div class="stat-box">
                        <div class="stat-number">56+</div>
                        <div class="stat-label">Tasks Completed</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">9</div>
                        <div class="stat-label">Action Handlers</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">3</div>
                        <div class="stat-label">Active Watchers</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">$50</div>
                        <div class="stat-label">Approval Threshold</div>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>🔄 Workflow</h2>
                <div class="workflow">
                    <div class="workflow-step">
                        <div class="icon">📥</div>
                        <div>Inbox</div>
                    </div>
                    <div class="arrow">→</div>
                    <div class="workflow-step">
                        <div class="icon">🤖</div>
                        <div>AI Analyzes</div>
                    </div>
                    <div class="arrow">→</div>
                    <div class="workflow-step">
                        <div class="icon">⚖️</div>
                        <div>HITL Check</div>
                    </div>
                    <div class="arrow">→</div>
                    <div class="workflow-step">
                        <div class="icon">✅</div>
                        <div>Done</div>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>📨 Quick Actions</h2>
                <p style="color: #8892b0; margin-bottom: 15px;">Submit tasks directly to the AI Employee system:</p>
                <div style="display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap;">
                    <button onclick="showAction('email')" style="margin-top:0">📧 Send Email</button>
                    <button onclick="showAction('whatsapp')" style="margin-top:0">💬 WhatsApp</button>
                    <button onclick="showAction('linkedin')" style="margin-top:0">💼 LinkedIn Post</button>
                </div>

                <div id="action-email" class="action-form" style="display:none;">
                    <h3 style="margin-bottom:10px;">📧 Send Email</h3>
                    <input type="text" id="email-to" placeholder="To: recipient@example.com" class="form-input">
                    <input type="text" id="email-subject" placeholder="Subject" class="form-input">
                    <textarea id="email-body" placeholder="Email body..." style="min-height:80px;"></textarea>
                    <button onclick="submitAction('email')">📤 Send Email</button>
                </div>

                <div id="action-whatsapp" class="action-form" style="display:none;">
                    <h3 style="margin-bottom:10px;">💬 WhatsApp Message</h3>
                    <input type="text" id="wa-to" placeholder="To: +923001234567" class="form-input">
                    <textarea id="wa-body" placeholder="Message..." style="min-height:80px;"></textarea>
                    <button onclick="submitAction('whatsapp')">📤 Send WhatsApp</button>
                </div>

                <div id="action-linkedin" class="action-form" style="display:none;">
                    <h3 style="margin-bottom:10px;">💼 LinkedIn Post</h3>
                    <textarea id="li-body" placeholder="Write your LinkedIn post..." style="min-height:80px;"></textarea>
                    <input type="text" id="li-hashtags" placeholder="Hashtags: #AI #Automation" class="form-input">
                    <button onclick="submitAction('linkedin')">📝 Create Draft</button>
                </div>

                <div id="action-result" class="result" style="display:none;"></div>
            </div>

            <div class="card">
                <h2>🧪 Try HITL Classification</h2>
                <p style="color: #8892b0; margin-bottom: 15px;">Enter a task to see how the system classifies it:</p>
                <textarea id="taskInput" placeholder="Example: Pay $150 to vendor ABC for monthly subscription"></textarea>
                <button onclick="classifyTask()">🔍 Classify Task</button>
                <div id="result" class="result"></div>
            </div>

            <div class="card">
                <h2>⚖️ HITL Decision Rules</h2>
                <table>
                    <tr>
                        <th>Content</th>
                        <th>Risk</th>
                        <th>Action</th>
                    </tr>
                    <tr>
                        <td>Read/analyze files</td>
                        <td class="risk-low">🟢 Low</td>
                        <td>Auto-approve</td>
                    </tr>
                    <tr>
                        <td>Payment < $50</td>
                        <td class="risk-low">🟢 Low</td>
                        <td>Auto-approve</td>
                    </tr>
                    <tr>
                        <td>Payment > $50</td>
                        <td class="risk-high">🔴 High</td>
                        <td>Manual approval</td>
                    </tr>
                    <tr>
                        <td>Delete files</td>
                        <td class="risk-high">🔴 High</td>
                        <td>Manual approval</td>
                    </tr>
                    <tr>
                        <td>Sensitive data</td>
                        <td class="risk-high">🔴 High</td>
                        <td>Manual approval</td>
                    </tr>
                </table>
            </div>

            <div class="card">
                <h2>🔐 Core Principles</h2>
                <ul style="list-style: none; line-height: 2;">
                    <li>🏠 <strong>Local-First</strong> - All data stays on YOUR machine</li>
                    <li>👤 <strong>Human-in-the-Loop</strong> - Sensitive actions need YOUR approval</li>
                    <li>🔒 <strong>Security-First</strong> - Credentials never committed</li>
                    <li>🤖 <strong>Autonomous Where Safe</strong> - AI handles routine tasks</li>
                </ul>
            </div>

            <footer>
                <p>Built for Personal AI Employee Hackathon 2026</p>
                <p>
                    <a href="https://github.com/Shaistatosif/-ai-employee" target="_blank">GitHub</a> |
                    Author: Shaista Tosif
                </p>
            </footer>
        </div>

        <script>
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
                resultDiv.innerHTML = `
                    <h3>${data.requires_approval ? '🔴 Manual Approval Required' : '🟢 Auto-Approved'}</h3>
                    <p><strong>Risk Level:</strong> ${data.risk_level}</p>
                    <p><strong>Reason:</strong> ${data.reason}</p>
                    <p><strong>Action:</strong> ${data.requires_approval ? 'Task goes to Pending_Approval folder' : 'Task auto-processed to Done'}</p>
                `;
            }

            function showAction(type) {
                document.querySelectorAll('.action-form').forEach(f => f.style.display = 'none');
                document.getElementById('action-' + type).style.display = 'block';
                document.getElementById('action-result').style.display = 'none';
            }

            async function submitAction(type) {
                let payload = { type: type };
                const resultDiv = document.getElementById('action-result');

                if (type === 'email') {
                    payload.to = document.getElementById('email-to').value;
                    payload.subject = document.getElementById('email-subject').value;
                    payload.body = document.getElementById('email-body').value;
                    if (!payload.to || !payload.subject || !payload.body) {
                        alert('Please fill all email fields!'); return;
                    }
                } else if (type === 'whatsapp') {
                    payload.to = document.getElementById('wa-to').value;
                    payload.body = document.getElementById('wa-body').value;
                    if (!payload.to || !payload.body) {
                        alert('Please fill all WhatsApp fields!'); return;
                    }
                } else if (type === 'linkedin') {
                    payload.body = document.getElementById('li-body').value;
                    payload.hashtags = document.getElementById('li-hashtags').value;
                    if (!payload.body) {
                        alert('Please write the LinkedIn post!'); return;
                    }
                }

                const response = await fetch('/api/submit-task', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const data = await response.json();
                resultDiv.style.display = 'block';
                resultDiv.className = 'result ' + (data.status === 'submitted' ? 'low' : 'high');
                resultDiv.innerHTML = '<h3>' + (data.status === 'submitted' ? '✅ Task Submitted!' : '❌ Error') + '</h3>'
                    + '<p>' + data.message + '</p>'
                    + (data.file ? '<p><strong>File:</strong> ' + data.file + '</p>' : '');
            }
        </script>
    </body>
    </html>
    """
    return html


@app.post("/api/classify")
async def classify(data: dict):
    """API endpoint for task classification."""
    content = data.get("content", "")
    result = classify_task(content)

    # Log for demo
    demo_logs.append({
        "time": datetime.now().isoformat(),
        "content": content[:50] + "..." if len(content) > 50 else content,
        "result": result
    })

    return result


@app.post("/api/submit-task")
async def submit_task(data: dict):
    """Submit a task to the Inbox for processing."""
    task_type = data.get("type", "")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    vault_path = Path(os.environ.get("VAULT_PATH", "./obsidian_vault"))
    inbox = vault_path / "Inbox"
    inbox.mkdir(parents=True, exist_ok=True)

    if task_type == "email":
        content = f"type: email_send\nto: {data.get('to', '')}\nsubject: {data.get('subject', '')}\n\n{data.get('body', '')}"
        filename = f"{timestamp}_send_email.txt"
    elif task_type == "whatsapp":
        content = f"type: whatsapp_message\nto: {data.get('to', '')}\n\n{data.get('body', '')}"
        filename = f"{timestamp}_whatsapp_message.txt"
    elif task_type == "linkedin":
        hashtags = data.get("hashtags", "")
        content = f"type: linkedin_post\nhashtags: {hashtags}\n\n{data.get('body', '')}"
        filename = f"{timestamp}_linkedin_post.txt"
    else:
        raise HTTPException(status_code=400, detail="Unknown task type")

    file_path = inbox / filename
    file_path.write_text(content, encoding="utf-8")

    # Classify for immediate feedback
    result = classify_task(content)

    demo_logs.append({
        "time": datetime.now().isoformat(),
        "content": f"[{task_type.upper()}] {filename}",
        "result": result
    })

    return {
        "status": "submitted",
        "message": f"Task dropped in Inbox. Risk: {result['risk_level']}. {'Needs approval.' if result['requires_approval'] else 'Will auto-process.'}",
        "file": filename
    }


@app.get("/api/stats")
async def get_stats():
    """Get system stats."""
    return demo_stats


@app.get("/api/logs")
async def get_logs():
    """Get recent classification logs."""
    return {"logs": demo_logs[-10:]}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
