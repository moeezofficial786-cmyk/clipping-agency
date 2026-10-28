# ✂️ ClipPulse — Clipping Agency Operations Hub

A zero-hosting, mobile-first agency management application designed to track campaigns, clippers, social account handles, and video views with live CPM calculation and approval controls.

---

## 🌟 Features

- **📱 Single-File Mobile Hub (`index.html`)**: Runs on any phone browser, tablet, or desktop with zero installation or server costs.
- **⚡ 24/7 Automated 30-Minute Extraction**: Automatically scans TikTok, YouTube Shorts, and Instagram Reels for new clips and updates views.
- **💰 Live CPM & Payout Engine**:
  $$\text{Clipper Earnings} = \left(\frac{\text{Approved Video Views}}{1000}\right) \times \text{Campaign CPM}$$
- **✅ Approval Gate**: Videos start in `Pending` review. Only videos you explicitly **Approve** count toward views and clipper payouts.
- **⚠️ Pre-Campaign Detection**: Clips posted before a campaign's start date are flagged with a badge to protect your agency from paying for old content.
- **🔄 Dual Mode (Zero Setup Required)**:
  - **Local Demo Mode**: Works immediately offline via browser `localStorage` with sample data.
  - **Cloud Sync Mode**: Connects to free Supabase for 24/7 background sync across all devices.

---

## 🚀 Quick Start (Running on Your Phone in 10 Seconds)

### Option 1: Instant Local View
1. Double-click `index.html` on your computer or send it to your phone via WhatsApp/AirDrop/Google Drive.
2. Tap to open it in Chrome or Safari.
3. You can immediately create campaigns, register clippers, and toggle video approvals!

### Option 2: 1-Click Free Hosting on GitHub Pages
1. Push this folder to a GitHub repository.
2. Go to **Settings > Pages > Branch: `main` > Save**.
3. GitHub gives you a free website link (e.g. `https://yourusername.github.io/clipping-agency`) that you can open on your phone anytime!

---

## ☁️ 3-Minute 24/7 Background Sync Setup (GitHub Actions + Supabase)

To have the cloud check your clippers' handles and refresh view counts every 30 minutes:

### 1. Free Cloud Database (Supabase)
1. Go to [supabase.com](https://supabase.com) and create a free project.
2. Open the **SQL Editor** on the left menu.
3. Paste the contents of [`schema.sql`](file:///c:/Users/HASHMI%20COMPUTERS/Desktop/My%20Projects/Automation%20Projects/Clipping%20Agency/schema.sql) and click **Run**.
4. Go to **Project Settings > API** and copy:
   - **Project URL**
   - **Project API Key (`anon` `public`)**

### 2. Connect Your Phone App
1. Open [`index.html`](file:///c:/Users/HASHMI%20COMPUTERS/Desktop/My%20Projects/Automation%20Projects/Clipping%20Agency/index.html) in your browser.
2. Go to the **Cloud/Sync** tab (or top gear icon).
3. Paste your **Supabase URL** and **Anon Key**, then tap **Save & Connect Cloud**.

### 3. Activate 24/7 Cloud Background Scraper
1. In your GitHub repository, go to **Settings > Secrets and variables > Actions**.
2. Add two repository secrets:
   - `SUPABASE_URL`: (Your Supabase project URL)
   - `SUPABASE_KEY`: (Your Supabase anon key)
3. Under the **Actions** tab on GitHub, enable workflows.
4. The scraper will now automatically run every 30 minutes in the cloud, extracting new clips and updating view counts!

---

## 📁 File Structure

| File | Purpose |
| :--- | :--- |
| [`index.html`](file:///c:/Users/HASHMI%20COMPUTERS/Desktop/My%20Projects/Automation%20Projects/Clipping%20Agency/index.html) | The mobile-first single-page web application. |
| [`tracker_cron.py`](file:///c:/Users/HASHMI%20COMPUTERS/Desktop/My%20Projects/Automation%20Projects/Clipping%20Agency/tracker_cron.py) | Python extraction engine for TikTok, YouTube Shorts, and Instagram Reels. |
| [`schema.sql`](file:///c:/Users/HASHMI%20COMPUTERS/Desktop/My%20Projects/Automation%20Projects/Clipping%20Agency/schema.sql) | 1-click database schema for Supabase. |
| [`.github/workflows/sync_views.yml`](file:///c:/Users/HASHMI%20COMPUTERS/Desktop/My%20Projects/Automation%20Projects/Clipping%20Agency/.github/workflows/sync_views.yml) | GitHub Actions configuration for automated 30-minute background runs. |
