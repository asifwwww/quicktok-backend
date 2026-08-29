"""
QuickTok backend — fetches TikTok download links via tikwm.com, a free,
widely-used public API that already handles TikTok's CDN signing/IP
protections on its own infrastructure. This avoids the 403 errors we hit
trying to fetch TikTok's CDN directly (from a cloud server OR a client
browser) — tikwm's own domain serves the files, so no TikTok CDN request
happens on our side at all.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

TIKWM_API = "https://www.tikwm.com/api/"
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


@app.route("/")
def health():
    return jsonify({"status": "ok", "service": "quicktok-backend"})


@app.route("/api/fetch", methods=["POST"])
def fetch():
    data = request.get_json(force=True, silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Missing TikTok video URL."}), 400

    try:
        resp = requests.get(
            TIKWM_API, params={"url": url, "hd": 1}, headers=REQUEST_HEADERS, timeout=25
        )
        payload = resp.json()
    except Exception as exc:
        return jsonify({"error": f"Could not reach the download service ({type(exc).__name__}). Try again in a moment."}), 502

    if payload.get("code") != 0 or not payload.get("data"):
        return jsonify({"error": "No downloadable video found for that link."}), 404

    d = payload["data"]
    formats = []

    if d.get("play"):
        formats.append({"quality": "Video — No Watermark", "url": d["play"], "filesize": d.get("size")})
    if d.get("hdplay") and d.get("hdplay") != d.get("play"):
        formats.append({"quality": "Video — No Watermark (HD)", "url": d["hdplay"], "filesize": d.get("hd_size")})
    if d.get("wmplay"):
        formats.append({"quality": "Video — With Watermark", "url": d["wmplay"], "filesize": d.get("wm_size")})
    if d.get("music"):
        formats.append({"quality": "Audio (mp3)", "url": d["music"], "filesize": None})

    if not formats:
        return jsonify({"error": "No downloadable video found for that link."}), 404

    author = (d.get("author") or {}).get("nickname")

    return jsonify(
        {
            "title": d.get("title"),
            "author": author,
            "duration": d.get("duration"),
            "thumbnail": d.get("cover") or d.get("origin_cover"),
            "formats": formats,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
