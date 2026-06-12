import os
import json
import requests
from flask import Flask, request, jsonify, Response, stream_with_context
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

app = Flask(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"


def get_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None, jsonify({
            "error": "ANTHROPIC_API_KEY is not configured.",
            "hint": "Add your Anthropic API key in Vercel → Project Settings → Environment Variables → ANTHROPIC_API_KEY"
        }), 500
    return key, None, None


def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


@app.after_request
def after_request(response):
    return add_cors_headers(response)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def home():
    """Beautiful HTML status page — shows API key status and verify button."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    # Only consider key configured if it's not empty AND not a placeholder
    key_configured = bool(api_key) and not "your-actual-key" in api_key.lower() and len(api_key) > 20
    
    # Debug logging
    print(f"[DEBUG] ANTHROPIC_API_KEY is set: {bool(api_key)}")
    print(f"[DEBUG] Key is valid: {key_configured}")
    print(f"[DEBUG] Key length: {len(api_key) if api_key else 0}")

    if key_configured:
        status_color = "#22c55e"
        status_icon = "✅"
        status_text = "API Key Detected"
        status_sub = "Click the button below to verify it works end-to-end."
        button_html = """
        <button onclick="testKey()" id="btn">
            🧪 Verify API Key Now
        </button>
        """
    else:
        status_color = "#ef4444"
        status_icon = "❌"
        status_text = "API Key Not Set"
        status_sub = "Follow the steps below to add your Anthropic API key."
        button_html = ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Claude API Proxy</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #0f0f0f;
    color: #e5e5e5;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
  }}
  .card {{
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 16px;
    padding: 40px;
    max-width: 640px;
    width: 100%;
  }}
  .logo {{ font-size: 32px; margin-bottom: 8px; }}
  h1 {{ font-size: 22px; font-weight: 700; color: #fff; margin-bottom: 4px; }}
  .subtitle {{ color: #888; font-size: 14px; margin-bottom: 32px; }}
  .status-box {{
    background: #111;
    border: 1px solid {status_color}44;
    border-radius: 12px;
    padding: 20px 24px;
    display: flex;
    align-items: flex-start;
    gap: 14px;
    margin-bottom: 28px;
  }}
  .status-icon {{ font-size: 28px; line-height: 1; }}
  .status-text h2 {{ font-size: 16px; font-weight: 600; color: {status_color}; }}
  .status-text p {{ font-size: 13px; color: #888; margin-top: 4px; }}
  button {{
    background: #7c3aed;
    color: #fff;
    border: none;
    border-radius: 10px;
    padding: 13px 24px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    width: 100%;
    margin-bottom: 28px;
    transition: background 0.2s;
  }}
  button:hover {{ background: #6d28d9; }}
  button:disabled {{ background: #444; cursor: not-allowed; }}
  .result {{
    border-radius: 10px;
    padding: 16px 20px;
    font-size: 14px;
    margin-bottom: 28px;
    display: none;
    line-height: 1.6;
  }}
  .result.success {{
    background: #052e16;
    border: 1px solid #166534;
    color: #86efac;
    display: block;
  }}
  .result.error {{
    background: #1c0606;
    border: 1px solid #7f1d1d;
    color: #fca5a5;
    display: block;
  }}
  .result .reply-label {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    opacity: 0.6;
    margin-bottom: 6px;
  }}
  .result .reply-text {{
    font-size: 15px;
    font-weight: 500;
  }}
  h3 {{ font-size: 13px; font-weight: 600; color: #aaa; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }}
  .steps {{ list-style: none; }}
  .steps li {{
    display: flex;
    gap: 12px;
    margin-bottom: 14px;
    font-size: 14px;
    color: #ccc;
    align-items: flex-start;
  }}
  .step-num {{
    background: #2a2a2a;
    color: #aaa;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 700;
    flex-shrink: 0;
    margin-top: 1px;
  }}
  code {{
    background: #2a2a2a;
    padding: 2px 7px;
    border-radius: 5px;
    font-family: monospace;
    font-size: 13px;
    color: #c084fc;
  }}
  .divider {{ border: none; border-top: 1px solid #2a2a2a; margin: 28px 0; }}
  .endpoints {{ display: flex; flex-direction: column; gap: 8px; }}
  .endpoint {{
    display: flex;
    gap: 10px;
    align-items: center;
    font-size: 13px;
    color: #aaa;
  }}
  .method {{
    background: #1e3a5f;
    color: #60a5fa;
    padding: 2px 8px;
    border-radius: 5px;
    font-size: 11px;
    font-weight: 700;
    font-family: monospace;
    flex-shrink: 0;
  }}
  .method.post {{ background: #1a3326; color: #4ade80; }}
</style>
</head>
<body>
<div class="card">
  <h1>Claude API Proxy</h1>
  <p class="subtitle">Secure server-side proxy — API key never exposed to the browser</p>

  <div class="status-box">
    <div class="status-icon">{status_icon}</div>
    <div class="status-text">
      <h2>{status_text}</h2>
      <p>{status_sub}</p>
    </div>
  </div>

  {button_html}

  <div id="result" class="result"></div>

  <h3>How to add your API key</h3>
  <ul class="steps">
    <li>
      <span class="step-num">1</span>
      <span>Go to your <strong>Vercel Dashboard</strong> → select this project</span>
    </li>
    <li>
      <span class="step-num">2</span>
      <span>Click <strong>Settings</strong> → <strong>Environment Variables</strong></span>
    </li>
    <li>
      <span class="step-num">3</span>
      <span>Add a new variable: Name = <code>ANTHROPIC_API_KEY</code>, Value = your key starting with <code>sk-ant-...</code></span>
    </li>
    <li>
      <span class="step-num">4</span>
      <span>Go to <strong>Deployments</strong> → click the three dots → <strong>Redeploy</strong></span>
    </li>
  </ul>

  <hr class="divider"/>

  <h3>Available Endpoints</h3>
  <div class="endpoints">
    <div class="endpoint"><span class="method">GET</span> /api/health — health check</div>
    <div class="endpoint"><span class="method post">POST</span> /api/chat — send a message to Claude</div>
    <div class="endpoint"><span class="method post">POST</span> /api/chat/stream — streaming response (SSE)</div>
    <div class="endpoint"><span class="method">GET</span> /api/verify — verify API key programmatically</div>
  </div>
</div>

<script>
async function testKey() {{
  const btn = document.getElementById('btn');
  const result = document.getElementById('result');
  btn.disabled = true;
  btn.textContent = 'Testing connection to Claude...';
  result.className = 'result';
  result.style.display = 'none';

  try {{
    const resp = await fetch('/api/verify');
    const data = await resp.json();

    if (data.success) {{
      result.className = 'result success';
      result.innerHTML = `
        <div class="reply-label">Claude responded successfully</div>
        <div class="reply-text">${{data.reply}}</div>
      `;
      btn.textContent = 'API Key is Working!';
      btn.style.background = '#166534';
    }} else {{
      result.className = 'result error';
      result.innerHTML = `
        <div class="reply-label">Verification Failed</div>
        <div class="reply-text">${{data.error}}</div>
      `;
      btn.disabled = false;
      btn.textContent = 'Verify API Key Now';
    }}
  }} catch (e) {{
    result.className = 'result error';
    result.innerHTML = `<div class="reply-label">Network Error</div><div class="reply-text">${{e.message}}</div>`;
    btn.disabled = false;
    btn.textContent = 'Verify API Key Now';
  }}
}}
</script>
</body>
</html>"""
    return html


@app.route("/api/verify", methods=["GET"])
def verify():
    """
    Sends a real test message to Claude and returns the result.
    Used by the homepage verify button.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return jsonify({
            "success": False,
            "error": "ANTHROPIC_API_KEY is not set. Add it in Vercel → Settings → Environment Variables."
        }), 500

    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 64,
        "messages": [
            {
                "role": "user",
                "content": "Reply with exactly this sentence and nothing else: API key verified — Claude is connected and ready."
            }
        ]
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_API_VERSION,
        "content-type": "application/json",
    }

    try:
        resp = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=30)
        data = resp.json()

        if resp.status_code == 200:
            reply = data["content"][0]["text"].strip()
            return jsonify({"success": True, "reply": reply})
        else:
            error_msg = data.get("error", {}).get("message", "Unknown error from Anthropic.")
            return jsonify({"success": False, "error": error_msg}), resp.status_code

    except requests.exceptions.Timeout:
        return jsonify({"success": False, "error": "Request timed out."}), 504
    except requests.exceptions.RequestException as exc:
        return jsonify({"success": False, "error": str(exc)}), 502


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "api_key_configured": bool(os.environ.get("ANTHROPIC_API_KEY"))
    })


@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    api_key, err_response, err_code = get_api_key()
    if err_response:
        return err_response, err_code

    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Request body must be valid JSON."}), 400
    if "messages" not in body:
        return jsonify({"error": "'messages' field is required."}), 400

    payload = {
        "model":      body.get("model", "claude-sonnet-4-6"),
        "max_tokens": body.get("max_tokens", 1024),
        "messages":   body["messages"],
    }
    if "system" in body:
        payload["system"] = body["system"]

    headers = {
        "x-api-key":         api_key,
        "anthropic-version": ANTHROPIC_API_VERSION,
        "content-type":      "application/json",
    }

    try:
        resp = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=60)
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.Timeout:
        return jsonify({"error": "Request timed out."}), 504
    except requests.exceptions.RequestException as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/api/chat/stream", methods=["POST", "OPTIONS"])
def chat_stream():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    api_key, err_response, err_code = get_api_key()
    if err_response:
        return err_response, err_code

    body = request.get_json(silent=True)
    if not body or "messages" not in body:
        return jsonify({"error": "'messages' field is required."}), 400

    payload = {
        "model":      body.get("model", "claude-sonnet-4-6"),
        "max_tokens": body.get("max_tokens", 1024),
        "messages":   body["messages"],
        "stream":     True,
    }
    if "system" in body:
        payload["system"] = body["system"]

    headers = {
        "x-api-key":         api_key,
        "anthropic-version": ANTHROPIC_API_VERSION,
        "content-type":      "application/json",
    }

    def generate():
        try:
            with requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, stream=True, timeout=120) as r:
                for chunk in r.iter_content(chunk_size=None):
                    if chunk:
                        yield chunk
        except requests.exceptions.RequestException as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n".encode()

    return Response(
        stream_with_context(generate()),
        content_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)