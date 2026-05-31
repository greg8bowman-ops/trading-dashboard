# 📲 Deploy to Your Android Phone (Streamlit Community Cloud)

This gets your **live-data** trading dashboard running at a public URL you can
open — or install as an app icon — on your Android phone. Free. ~10 minutes.

You'll do three things: (1) put the code on GitHub, (2) connect it to Streamlit
Cloud, (3) add it to your phone's home screen.

---

## What you need

- A free **GitHub** account → https://github.com/signup
- A free **Streamlit Community Cloud** account → https://share.streamlit.io
  (sign in with your GitHub account — one click)

---

## Step 1 — Put the code on GitHub

**Easiest way (no command line, works from phone or laptop):**

1. Go to https://github.com/new and create a repository:
   - Name: `trading-dashboard`
   - Set it to **Public** (Streamlit's free tier needs public repos)
   - Tick **"Add a README"** then click **Create repository**
2. On the repo page, click **Add file → Upload files**.
3. Unzip `trading_dashboard.zip` on your computer, then drag in **the contents**
   of the `trading_dashboard` folder — so the repo root contains:
   ```
   app.py
   requirements.txt
   README.md
   .gitignore
   .streamlit/        (folder)
   modules/           (folder)
   data/              (folder, with .gitkeep inside)
   ```
   ⚠️ Important: `app.py` must sit at the **top level** of the repo, not inside
   another `trading_dashboard/` subfolder. If GitHub's uploader won't let you
   add folders, upload the files in each folder one batch at a time, typing the
   folder name as a path prefix (e.g. `modules/config.py`).
4. Click **Commit changes**.

> Prefer the command line? From the unzipped folder:
> ```bash
> git init && git add . && git commit -m "initial"
> git branch -M main
> git remote add origin https://github.com/YOUR_USERNAME/trading-dashboard.git
> git push -u origin main
> ```

---

## Step 2 — Deploy on Streamlit Cloud

1. Go to https://share.streamlit.io and sign in with GitHub.
2. Click **Create app → Deploy a public app from GitHub**.
3. Fill in:
   - **Repository:** `YOUR_USERNAME/trading-dashboard`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. Click **Deploy**.

It will install the packages from `requirements.txt` (takes 2–4 minutes the
first time) and then show your dashboard. You'll get a permanent URL like:

```
https://YOUR_USERNAME-trading-dashboard.streamlit.app
```

That URL works from any device, including your phone.

---

## Step 3 — Add it to your Android home screen (acts like an app)

1. Open the URL in **Chrome** on your phone.
2. Tap the **⋮** menu (top-right).
3. Tap **Add to Home screen** → **Add**.

You now have an icon that launches the dashboard full-screen, like a native app.

---

## Good to know

- **First load after idle:** Streamlit's free tier "sleeps" apps after inactivity.
  Opening a sleeping app shows a "waking up" screen for ~30 seconds, then it's
  live. Normal.
- **Live data:** On the cloud it fetches real daily prices via `yfinance`. If
  Yahoo briefly rate-limits a shared server, you may occasionally see the
  synthetic-data warning — just hit **🔄 Re-run scan** in the sidebar.
- **The journal resets on redeploy.** Streamlit Cloud storage is *ephemeral* —
  every time you push new code, `data/journal.csv` is wiped. For a phone-based
  journal that persists, see the note below.
- **Keep your repo private?** Not on the free tier — it needs a public repo.
  Don't put anything secret in it (there's nothing sensitive in this code).

---

## Optional: make the journal survive redeploys

The simplest durable option is to connect a free Google Sheet as the journal
store instead of the local CSV. If you want that, ask and I'll swap `journal.py`
to read/write a Google Sheet via `st.connection` — it's about a 30-line change
plus pasting one credentials secret into Streamlit's settings.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Main module does not exist" | `app.py` isn't at repo root — move it out of any subfolder. |
| Stuck on installing | Check `requirements.txt` is at repo root and spelled correctly. |
| Always shows synthetic data | Yahoo rate-limit on shared IP; tap Re-run, or try again later. |
| App won't wake | Refresh once; free-tier cold starts can take 30–60s. |
| Charts blank | Hard-refresh the page (pull down to refresh in Chrome). |
