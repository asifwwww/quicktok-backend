from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

SOCIALKIT_API = "https://api.socialkit.dev/tiktok/download"

@app.route("/api/fetch", methods=["POST"])
def fetch_tiktok():
    data = request.get_json() or {}
    video_url = data.get("url")

    if not video_url:
        return jsonify({"error": "Please provide a valid TikTok URL."}), 400

    try:
        # Request data from SocialKit API
        response = requests.get(SOCIALKIT_API, params={"url": video_url}, timeout=15)
        res_data = response.json()

        if response.status_code != 200 or not res_data.get("success", False):
            return jsonify({"error": "Failed to fetch video using SocialKit API."}), 400

        video_info = res_data.get("data", {})

        return jsonify({
            "title": video_info.get("title", "TikTok Video"),
            "author": video_info.get("author", {}).get("nickname", "Unknown"),
            "thumbnail": video_info.get("cover", ""),
            "download_url": video_info.get("play", "")  # Watermark-less direct play link
        })

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
