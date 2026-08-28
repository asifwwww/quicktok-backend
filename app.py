@app.route("/api/download-file", methods=["GET"])
def download_file():
    target = request.args.get("url")
    if not target:
        return "Missing url parameter.", 400

    # Extended TikTok CDN headers to bypass 403 Forbidden
    fetch_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.tiktok.com/",
        "Accept": "video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Dest": "video",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "cross-site",
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
