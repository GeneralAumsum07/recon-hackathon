# Recon Hackathon — Reconstruction Report (CLI prototype)

## What it does
Given a short fragment of text (chat/forum slang or partial sentence), this tool:
- Produces an AI reconstruction (mocked or via Gemini).
- Searches the web for contextual sources (mocked or via a Search API).
- Renders a Markdown report with Original Fragment, Reconstructed Text, Explanations, and Sources.

## Quickstart (mock/demo mode)
1. Create a virtualenv and install:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
