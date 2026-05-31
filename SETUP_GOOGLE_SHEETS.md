# 📒 Persistent Journal via Google Sheets

By default the journal saves to a local CSV that **resets every time you redeploy**
on Streamlit Cloud. Connecting a Google Sheet makes it **permanent** — your trade
history survives redeploys and syncs to a sheet you can also open directly.

This is the fiddliest setup in the project (~15–20 min, one time). Follow exactly.
The app works fine without it — it just falls back to the CSV.

---

## Overview of what you're doing

1. Create a Google Cloud **service account** (a robot Google identity).
2. Download its **credentials JSON** (a key file).
3. Create a **Google Sheet** and share it with the robot's email.
4. Paste the credentials + sheet name into **Streamlit secrets**.

The app detects the secrets automatically and switches to Sheets. The Journal tab
shows a green "Storage: Google Sheets" banner when it's working.

---

## Step 1 — Create a Google Cloud project + service account

1. Go to https://console.cloud.google.com and sign in.
2. Top bar → project dropdown → **New Project**. Name it `trading-journal`, Create.
   Make sure that project is selected afterward.
3. Enable two APIs (search each in the top search bar, click **Enable**):
   - **Google Sheets API**
   - **Google Drive API**
4. Left menu → **APIs & Services → Credentials**.
5. **+ Create Credentials → Service account**.
   - Name: `journal-bot` → **Create and continue**.
   - Role: skip (click **Continue**), then **Done**.
6. You'll see the service account listed. Click it, go to the **Keys** tab.
7. **Add key → Create new key → JSON → Create.**
   A `.json` file downloads. **Keep it safe — it's a password.**

---

## Step 2 — Note the robot's email

Open the downloaded JSON. Find the line:
```json
"client_email": "journal-bot@trading-journal-xxxxx.iam.gserviceaccount.com"
```
Copy that email — you'll share the sheet with it next.

---

## Step 3 — Create and share the Google Sheet

1. Go to https://sheets.google.com → blank sheet.
2. Name it exactly: **`trading-journal`** (you'll put this name in secrets).
3. Click **Share**, paste the robot `client_email`, give it **Editor**, send.
   (No need to notify.)

That's it — you don't need to add headers; the app creates them automatically.

---

## Step 4 — Add secrets in Streamlit Cloud

1. Open your deployed app at https://share.streamlit.io → your app → **⋮ → Settings → Secrets**.
2. Paste the block below, then fill it from your JSON file. **Match it carefully** —
   TOML is whitespace-sensitive and the private key must keep its `\n` markers.

```toml
gsheet_name = "trading-journal"

[gcp_service_account]
type = "service_account"
project_id = "YOUR_PROJECT_ID"
private_key_id = "FROM_JSON"
private_key = "-----BEGIN PRIVATE KEY-----\nMIIE...long...key...\n-----END PRIVATE KEY-----\n"
client_email = "journal-bot@your-project.iam.gserviceaccount.com"
client_id = "FROM_JSON"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "FROM_JSON_client_x509_cert_url"
universe_domain = "googleapis.com"
```

**Filling `private_key` correctly is the #1 thing people get wrong:**
- Copy the entire value from the JSON, including the `BEGIN/END` lines.
- It must stay on ONE line in the TOML, with the literal `\n` sequences left as-is
  (don't convert them to real line breaks). Copying straight from the JSON value
  usually preserves them correctly — keep the surrounding quotes.

3. Click **Save**. The app reboots automatically.

> **Local testing instead?** Put the same block in
> `trading_dashboard/.streamlit/secrets.toml` on your machine. That file is
> git-ignored so it won't be uploaded — never commit credentials.

---

## Step 5 — Verify

Open the app → **Journal** tab. You should see:

> ✅ Storage: **Google Sheets** — Persists across redeploys

Log a trade from Recommendations, then open your Google Sheet — the row appears
there live. Record an outcome; the same row updates. Done.

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Banner still says "Local CSV" | Secrets not saved, or app hasn't rebooted. Re-save secrets; reboot from ⋮ menu. |
| Error mentions `private_key` / padding | The `\n` in the key got mangled. Re-paste, keeping `\n` literal and on one line. |
| `SpreadsheetNotFound` | Sheet name in secrets ≠ actual sheet name, OR you didn't share it with the robot email. |
| `PermissionError` / 403 | Robot wasn't given **Editor**, or Sheets/Drive API not enabled. |
| Works then suddenly CSV again | Transient Google API hiccup; the app auto-falls back so you never lose the session. Reload. |

**Security notes**
- The service-account JSON is a credential. Don't paste it into chats, commit it,
  or share it. If it leaks, delete the key in Cloud Console → Credentials.
- This robot can only touch sheets you explicitly share with it — nothing else in
  your Google account.
