"""
QuickTok backend — extracts TikTok download links using yt-dlp and
streams the video file back through this server (so file size and
download progress show up natively in the browser).

Deploy this on a platform that can run a persistent Python process
(Render, Railway, Fly.io, a VPS, etc). It will NOT run on Cloudflare
Pages/Workers — those only run small JS, not real binaries like yt-dlp.
"""

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import yt_dlp
import requests

app = Flask(__name__)
CORS(app)  # allow the Cloudflare Pages frontend (different domain) to call this API


@app.route("/")
def health():
    return jsonify({"status": "ok", "service": "quicktok-backend"})


@app.route("/api/fetch", methods=["POST"])
def fetch():
    data = request.get_json(force=True, silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Missing TikTok video URL."}), 400

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        # Some TikTok links need a normal browser User-Agent to resolve.
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception:
        return jsonify({"error": "Could not process this link. Check it's a valid TikTok video URL."}), 502

    formats = []
    seen_labels = set()
    for f in info.get("formats", []) or []:
        ext = f.get("ext")
        if ext not in ("mp4", "m4a"):
            continue
        is_audio = ext == "m4a"
        label = f.get("format_note") or f.get("format_id") or ext
        display = "Audio (m4a)" if is_audio else f"{label} (mp4)"
        if display in seen_labels:
            continue
        seen_labels.add(display)
        formats.append(
            {
                "quality": display,
                "url": f.get("url"),
                "filesize": f.get("filesize") or f.get("filesize_approx"),
                "is_audio": is_audio,
            }
        )

    # Fallback: some extractions only expose a single top-level url.
    if not formats and info.get("url"):
        formats.append(
            {
                "quality": "Video (mp4)",
                "url": info["url"],
                "filesize": info.get("filesize"),
                "is_audio": False,
            }
        )

    if not formats:
        return jsonify({"error": "No downloadable video found for that link."}), 404

    return jsonify(
        {
            "title": info.get("title"),
            "author": info.get("uploader") or info.get("creator"),
            "duration": info.get("duration"),
            "thumbnail": info.get("thumbnail"),
            "formats": formats,
        }
    )


@app.route("/api/download-file")
def download_file():
    target = request.args.get("url")
    if not target:
        return "Missing url parameter.", 400

    # TikTok's CDN rejects requests that don't look like they came from a
    # real browser referred from tiktok.com — without these headers it
    # returns an error instead of the video bytes.
    fetch_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.tiktok.com/",
    }

    try:
        upstream = requests.get(target, stream=True, timeout=30, headers=fetch_headers)
        upstream.raise_for_status()
    except requests.exceptions.HTTPError:
        status = upstream.status_code if 'upstream' in locals() else 502
        return f"Could not fetch the video file (upstream returned {status}).", 502
    except Exception:
        return "Could not fetch the video file.", 502

    def generate():
        for chunk in upstream.iter_content(chunk_size=65536):
            if chunk:
                yield chunk

    headers = {"Content-Disposition": 'attachment; filename="quicktok-video.mp4"'}
    if "content-length" in upstream.headers:
        headers["Content-Length"] = upstream.headers["content-length"]

    return Response(
        generate(),
        headers=headers,
        content_type=upstream.headers.get("content-type", "video/mp4"),
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
