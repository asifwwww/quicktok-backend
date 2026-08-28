# QuickTok Backend — yt-dlp powered (deploy from your phone)

This replaces the third-party RapidAPI with your own service using
**yt-dlp**, an open-source, actively maintained video extractor. No API
key, no rate limits from a paid vendor, no "please retry" behavior.

## Files
- `app.py` — the Flask server (extracts links + streams the video file)
- `requirements.txt` — Python dependencies
- `Procfile` / `render.yaml` — tells the host how to run it

## Honest limitation
This needs a host that runs real Python code (not Cloudflare Pages —
Cloudflare only runs small JS, it can't run yt-dlp). We'll use
**Render.com**, which has a free tier. The free tier "sleeps" after 15
minutes of no traffic — the first request after sleeping takes ~30–40
seconds to wake up, then it's fast again. That's the honest trade-off
for free hosting; a paid Render plan (from ~$7/month) removes the sleep.

## Deploy — entirely from your phone, no computer/terminal needed

### Step 1 — Put the code on GitHub
1. Go to github.com in your phone browser (or the GitHub app) and sign up / log in.
2. Tap **+** → **New repository**. Name it `quicktok-backend`. Create it (Public or Private, either works).
3. Inside the empty repo, tap **Add file** → **Upload files**.
4. Upload `app.py`, `requirements.txt`, `Procfile`, `render.yaml` from this zip.
5. Scroll down, tap **Commit changes**.

### Step 2 — Deploy on Render
1. Go to render.com → sign up (you can sign up with your GitHub account — this also connects them automatically).
2. Tap **New +** → **Web Service**.
3. Pick your `quicktok-backend` repo.
4. Render should auto-detect `render.yaml`; if it asks manually:
   - Environment: **Python 3**
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app --timeout 60`
   - Plan: **Free**
5. Tap **Create Web Service**. Wait for the build to finish (a few minutes).
6. Once live, Render gives you a URL like:
   `https://quicktok-backend-xxxx.onrender.com`

### Step 3 — Point your frontend at it
Open your site's `index.html`, find this line near the top of the `<script>`:

```js
const BACKEND_URL = 'PASTE_YOUR_RENDER_URL_HERE';
```

Replace it with your real Render URL (no trailing slash), e.g.:

```js
const BACKEND_URL = 'https://quicktok-backend-xxxx.onrender.com';
```

Re-upload `index.html` to your Cloudflare Pages project the same way as before.

## Testing it worked
Visit `https://your-render-url.onrender.com/` in a browser — you should see
`{"status":"ok","service":"quicktok-backend"}`. If you see that, the backend is live.
