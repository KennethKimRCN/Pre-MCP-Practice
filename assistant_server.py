from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
import json
import subprocess
import re
import win32com.client
import time
import win32gui
import win32con

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # ✅ Enable CORS so frontend (HTML) can talk to this backend

# LM Studio settings
openai.api_base = "http://localhost:1234/v1"
openai.api_key = "lm-studio"

# Supported apps
app_commands = {
    "calculator": {
        "open": "calc",
        "process": "Calculator.exe"
    },
    "notepad": {
        "open": "notepad",
        "process": "notepad.exe"
    },
    "paint": {
        "open": "mspaint",
        "process": "mspaint.exe"
    }
}

def ask_llm(prompt):
    response = openai.ChatCompletion.create(
        model="llama3",
        messages=[
            {"role": "system", "content": "Return ONLY JSON like {\"action\": \"open\", \"app\": \"notepad\"} or {\"action\": \"email\", \"subject\": \"...\", \"body\": \"...\"}. No explanation."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=300
    )
    return response.choices[0].message.content.strip()

def extract_json(text):
    match = re.search(r"\{.*?\}", text, re.DOTALL)
    return match.group(0) if match else None

def create_outlook_email(subject, body):
    outlook = win32com.client.Dispatch("Outlook.Application")
    mail = outlook.CreateItem(0)
    mail.Subject = subject
    mail.Body = body
    mail.Display()
    time.sleep(1)

    def enum_handler(hwnd, ctx):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if subject.lower() in title.lower():
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)

    win32gui.EnumWindows(enum_handler, None)

@app.route("/command", methods=["POST"])
def command():
    data = request.json
    user_input = data.get("prompt", "")
    print(f"📥 Input: {user_input}")

    raw = ask_llm(user_input)
    json_text = extract_json(raw)
    print(f"🧾 LLM: {json_text}")

    try:
        cmd = json.loads(json_text)
        action = cmd.get("action", "").lower()

        if action == "open":
            app_name = cmd.get("app", "").lower()
            if app_name in app_commands:
                os.system(app_commands[app_name]["open"])
                return jsonify({"status": "opened", "app": app_name})
            else:
                return jsonify({"error": f"Unknown app: {app_name}"}), 400

        elif action == "close":
            app_name = cmd.get("app", "").lower()
            if app_name in app_commands:
                subprocess.run(f'taskkill /f /im {app_commands[app_name]["process"]}', shell=True)
                return jsonify({"status": "closed", "app": app_name})
            else:
                return jsonify({"error": f"Unknown app: {app_name}"}), 400

        elif action == "email":
            subject = cmd.get("subject", "")
            body = cmd.get("body", "")
            create_outlook_email(subject, body)
            return jsonify({"status": "email_created", "subject": subject})

        else:
            return jsonify({"error": "Unknown action"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5005)
