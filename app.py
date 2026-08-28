"""
QuickTok backend – extracts TikTok download links using yt-dlp and
streams the video file back through this server (so file size and
download progress show up natively in the browser).
"""

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import yt_dlp
import requests

app = Flask(__name__)
CORS(app)  # allow frontend to call this API


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
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception:
        return jsonify({"error": "Could not process this link. Check it's a valid TikTok URL."}), 400

    formats = []
    seen_labels = set()
    for f in info.get("formats", []) or []:
        ext = f.get("ext")
        if ext not in ("mp4", "m4a"):
            continue
        is_audio = ext == "m4a"
        vcodec = f.get("vcodec")
        if not is_audio and vcodec == "none":
            continue

        raw_url = f.get("url")
        if not raw_url:
            continue

        filesize = f.get("filesize") or f.get("filesize_approx") or 0
        format_note = f.get("format_note") or ""
        height = f.get("height")

        if is_audio:
            label = "Audio Only (MP3/M4A)"
        elif height:
            label = f"Video ({height}p)"
        elif format_note:
            label = f"Video ({format_note})"
        else:
            label = "Video (Standard)"

        if label in seen_labels:
            continue
        seen_labels.add(label)

        formats.append({
            "label": label,
            "quality": height or 0,
            "ext": ext,
            "filesize": filesize,
            "url": raw_url,
            "is_audio": is_audio,
        })

    formats.sort(key=lambda x: (x["is_audio"], x["quality"]), reverse=True)

    direct_url = info.get("url")
    if direct_url and not any(fmt["url"] == direct_url for fmt in formats):
        formats.insert(0, {
            "label": "Video (Best Quality)",
            "quality": 1080,
            "ext": "mp4",
            "filesize": 0,
            "url": direct_url,
            "is_audio": False,
        })

    return jsonify({
        "title": info.get("title") or "TikTok Video",
        "author": info.get("uploader") or info.get("uploader_id") or "Unknown Creator",
        "thumbnail": info.get("thumbnail") or "",
        "duration": info.get("duration") or 0,
        "formats": formats,
    })


@app.route("/api/download-file", methods=["GET"])
def download_file():
    target = request.args.get("url")
    if not target:
        return "Missing url parameter.", 400

    # TikTok CDN Bypass Headers
    fetch_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.tiktok.com/",
        "Accept": "*/*",
    }

    try:
        upstream = requests.get(target, stream=True, timeout=30, headers=fetch_headers)
        upstream.raise_for_status()
    except requests.exceptions.HTTPError:
        status = upstream.status_code if 'upstream' in locals() else 502
        return f"Could not fetch the video file (upstream returned {status}).", 502
    except Exception as e:
        return f"Could not fetch the video file: {str(e)}", 502

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
    app.run(host="0.0.0.0", port=5000, debug=True)
