FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create vault directories
RUN mkdir -p obsidian_vault/Inbox obsidian_vault/Needs_Action \
    obsidian_vault/Pending_Approval obsidian_vault/Approved \
    obsidian_vault/Done obsidian_vault/Logs obsidian_vault/Drafts \
    obsidian_vault/Plans

# Expose web port
EXPOSE 8000

# Default: run the web app (override with docker run command for main.py)
CMD ["python", "-m", "uvicorn", "web_app:app", "--host", "0.0.0.0", "--port", "8000"]
