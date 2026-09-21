"""
app.py — Flask backend for the "Wire" application-layer dashboard.

Routes:
    GET  /                 -> renders the dual-panel dashboard page
    POST /api/browse       -> body {"url": "..."}                       -> DNS+HTTP sequence
    POST /api/mail         -> body {"to","subject","body"}              -> DNS+SMTP sequence
    POST /api/stream       -> body {"url","quality"}                    -> DNS+HTTP(manifest+segments) sequence

Run with:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000
"""

import os
from flask import Flask, render_template, request, jsonify

import protocols

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/browse", methods=["POST"])
def api_browse():
    data = request.get_json(force=True) or {}
    url = (data.get("url") or "www.example.com/index.html").strip()
    sequence = protocols.build_browsing_sequence(url)
    return jsonify({"sequence": sequence, "status": f"resolving and fetching {url} …"})


@app.route("/api/mail", methods=["POST"])
def api_mail():
    data = request.get_json(force=True) or {}
    to = (data.get("to") or "[email protected]").strip()
    subject = (data.get("subject") or "(no subject)").strip()
    body = (data.get("body") or "").strip()
    sequence = protocols.build_mail_sequence(to, subject, body)
    return jsonify({"sequence": sequence, "status": f"delivering mail to {to} …"})


@app.route("/api/stream", methods=["POST"])
def api_stream():
    data = request.get_json(force=True) or {}
    url = (data.get("url") or "video.example.com/stream").strip()
    quality = data.get("quality") or "720p"
    if quality not in protocols.QUALITY_BITRATE:
        quality = "720p"
    sequence = protocols.build_streaming_sequence(url, quality)
    return jsonify({"sequence": sequence, "status": f"buffering and requesting segments at {quality} …"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() in ("true", "1", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug)
