#!/usr/bin/env python3
"""
=============================================================================
CLIPPING AGENCY - AUTOMATED 30-MINUTE EXTRACTOR & VIEW COUNTER
=============================================================================
This script runs in the background (via GitHub Actions cron or local scheduler).
It automatically:
1. Loads active campaigns and clipper handles from Supabase (or local store).
2. Scrapes TikTok, YouTube Shorts, and Instagram Reels for new posts and views.
3. Automatically marks pre-campaign videos so you don't pay for old clips.
4. Preserves approval states (approved / unsubmitted) while refreshing live views.
=============================================================================
"""

import os
import sys
import json
import time
import argparse
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ClippingTracker")

try:
    import requests
except ImportError:
    logger.error("Missing 'requests' library. Run: pip install requests")
    sys.exit(1)

# Optional Supabase client
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client, Client
        supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Connected to Supabase successfully.")
    except ImportError:
        logger.warning("Supabase SDK not installed. Using direct REST fallback.")


class SocialExtractor:
    """Extracts posts and live view counts from TikTok, YouTube, and Instagram."""

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    @classmethod
    def clean_handle(cls, handle: str) -> str:
        """Strip URL prefix, @, and slashes."""
        handle = handle.strip()
        if "tiktok.com/@" in handle:
            handle = handle.split("tiktok.com/@")[-1].split("/")[0].split("?")[0]
        elif "youtube.com/@" in handle:
            handle = handle.split("youtube.com/@")[-1].split("/")[0].split("?")[0]
        elif "instagram.com/" in handle:
            handle = handle.split("instagram.com/")[-1].split("/")[0].split("?")[0]
        return handle.lstrip("@").strip()

    @classmethod
    def extract_tiktok(cls, raw_handle: str) -> List[Dict[str, Any]]:
        """
        Extracts recent TikTok videos and live views.
        Uses public endpoint with graceful fallback to yt-dlp.
        """
        handle = cls.clean_handle(raw_handle)
        logger.info(f"Extracting TikTok posts for @{handle}...")
        results = []

        # 1. Primary Method: Public API endpoint (Fast & reliable)
        try:
            api_url = f"https://tikwm.com/api/user/posts?unique_id={handle}&count=15"
            resp = requests.get(api_url, headers=cls.HEADERS, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0 and "data" in data and "videos" in data["data"]:
                    for item in data["data"]["videos"]:
                        vid_id = str(item.get("video_id", ""))
                        video_url = f"https://www.tiktok.com/@{handle}/video/{vid_id}"
                        play_count = int(item.get("play_count", 0))
                        create_time = item.get("create_time", 0)
                        posted_at = datetime.fromtimestamp(create_time, tz=timezone.utc).isoformat() if create_time else datetime.now(timezone.utc).isoformat()

                        results.append({
                            "platform": "tiktok",
                            "handle": f"@{handle}",
                            "video_id_str": vid_id,
                            "video_url": video_url,
                            "title": item.get("title", ""),
                            "thumbnail_url": item.get("cover", ""),
                            "views": play_count,
                            "posted_at": posted_at
                        })
                    logger.info(f"TikTok @{handle}: Found {len(results)} videos.")
                    return results
        except Exception as e:
            logger.warning(f"TikTok public endpoint failed for @{handle}: {e}")

        # 2. Secondary Method: yt-dlp extraction
        results = cls._extract_with_ytdlp(f"https://www.tiktok.com/@{handle}", "tiktok", f"@{handle}")
        return results

    @classmethod
    def extract_youtube(cls, raw_handle: str) -> List[Dict[str, Any]]:
        """
        Extracts YouTube Shorts and videos with live views.
        Uses yt-dlp to inspect channel feed.
        """
        handle = cls.clean_handle(raw_handle)
        channel_url = f"https://www.youtube.com/@{handle}/shorts"
        logger.info(f"Extracting YouTube Shorts for @{handle}...")
        return cls._extract_with_ytdlp(channel_url, "youtube", f"@{handle}")

    @classmethod
    def extract_instagram(cls, raw_handle: str) -> List[Dict[str, Any]]:
        """
        Extracts Instagram Reels and live play counts.
        """
        handle = cls.clean_handle(raw_handle)
        reels_url = f"https://www.instagram.com/{handle}/reels/"
        logger.info(f"Extracting Instagram Reels for @{handle}...")
        return cls._extract_with_ytdlp(reels_url, "instagram", f"@{handle}")

    @classmethod
    def _extract_with_ytdlp(cls, target_url: str, platform: str, handle: str) -> List[Dict[str, Any]]:
        """Helper to invoke yt-dlp CLI for metadata extraction."""
        import subprocess
        results = []
        try:
            cmd = [
                sys.executable, "-m", "yt_dlp",
                "--dump-json",
                "--playlist-items", "1-12",
                "--no-download",
                "--quiet",
                "--ignore-errors",
                target_url
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
            if proc.returncode == 0 and proc.stdout:
                for line in proc.stdout.strip().split("\n"):
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        vid_id = str(entry.get("id", ""))
                        vid_url = entry.get("webpage_url") or entry.get("url") or target_url
                        view_count = int(entry.get("view_count") or entry.get("play_count") or 0)
                        upload_timestamp = entry.get("timestamp")
                        
                        if upload_timestamp:
                            posted_at = datetime.fromtimestamp(upload_timestamp, tz=timezone.utc).isoformat()
                        else:
                            posted_at = datetime.now(timezone.utc).isoformat()

                        results.append({
                            "platform": platform,
                            "handle": handle,
                            "video_id_str": vid_id,
                            "video_url": vid_url,
                            "title": entry.get("title", ""),
                            "thumbnail_url": entry.get("thumbnail", ""),
                            "views": view_count,
                            "posted_at": posted_at
                        })
                    except json.JSONDecodeError:
                        continue
                logger.info(f"{platform.capitalize()} {handle} via yt-dlp: Found {len(results)} videos.")
        except Exception as e:
            logger.warning(f"yt-dlp extraction failed for {target_url}: {e}")

        return results


def run_sync(dry_run: bool = False):
    """
    Core sync routine:
    1. Fetches campaigns and clippers from Supabase.
    2. Runs extractors.
    3. Upserts videos without overwriting user approval status.
    """
    logger.info("=== Starting 30-Minute Video Sync ===")
    
    # 1. Fetch campaigns and clippers
    campaigns = []
    clippers = []

    if supabase_client:
        try:
            res_camp = supabase_client.table("campaigns").select("*").eq("status", "active").execute()
            campaigns = res_camp.data or []
            res_clip = supabase_client.table("clippers").select("*").execute()
            clippers = res_clip.data or []
        except Exception as e:
            logger.error(f"Failed to query Supabase: {e}")
            return
    else:
        logger.info("No SUPABASE_URL configured. Running in local demonstration / dry-run mode.")
        campaigns = [{
            "id": "demo-camp-1",
            "name": "Summer Viral Campaign",
            "cpm": 1.50,
            "platform": "all",
            "tag_filter": None,
            "start_date": datetime.now(timezone.utc).isoformat(),
            "status": "active"
        }]
        clippers = [{
            "id": "demo-clip-1",
            "name": "Demo Clipper",
            "handles": [
                {"platform": "tiktok", "handle": "@khaby.lame"},
                {"platform": "youtube", "handle": "@MrBeast"}
            ],
            "assigned_campaign_ids": ["demo-camp-1"]
        }]

    if not campaigns:
        logger.info("No active campaigns found. Exiting sync.")
        return

    # Map campaigns by ID
    camp_map = {c["id"]: c for c in campaigns}
    
    total_handles = 0
    new_videos_count = 0
    views_updated_count = 0

    for clipper in clippers:
        c_id = clipper.get("id")
        handles_raw = clipper.get("handles") or []
        assigned_camps = clipper.get("assigned_campaign_ids") or []
        
        # Link to the first valid assigned campaign or first active campaign
        camp_id = assigned_camps[0] if assigned_camps and assigned_camps[0] in camp_map else campaigns[0]["id"]
        campaign = camp_map.get(camp_id, campaigns[0])
        camp_start_dt = datetime.fromisoformat(campaign.get("start_date", datetime.now(timezone.utc).isoformat()).replace("Z", "+00:00"))

        for h in handles_raw:
            platform = "tiktok"
            handle_str = ""

            if isinstance(h, dict):
                platform = h.get("platform", "tiktok").lower()
                handle_str = h.get("handle", "")
            elif isinstance(h, str):
                handle_str = h
                if "youtube" in handle_str.lower():
                    platform = "youtube"
                elif "instagram" in handle_str.lower():
                    platform = "instagram"
                else:
                    platform = "tiktok"

            if not handle_str:
                continue

            total_handles += 1
            extracted_videos = []

            if "tiktok" in platform:
                extracted_videos = SocialExtractor.extract_tiktok(handle_str)
            elif "youtube" in platform:
                extracted_videos = SocialExtractor.extract_youtube(handle_str)
            elif "instagram" in platform:
                extracted_videos = SocialExtractor.extract_instagram(handle_str)
            else:
                extracted_videos = SocialExtractor.extract_tiktok(handle_str)

            # Process extracted items
            for v in extracted_videos:
                # Check pre-campaign date
                try:
                    posted_dt = datetime.fromisoformat(v["posted_at"].replace("Z", "+00:00"))
                    is_pre_campaign = posted_dt < camp_start_dt
                except Exception:
                    is_pre_campaign = False

                # Tag filter check (if campaign requires specific tag)
                tag_req = campaign.get("tag_filter")
                if tag_req and tag_req.strip():
                    if tag_req.lower() not in (v.get("title") or "").lower():
                        logger.info(f"Skipping video {v['video_url']} (missing required tag: {tag_req})")
                        continue

                video_payload = {
                    "campaign_id": campaign["id"],
                    "clipper_id": c_id,
                    "platform": v["platform"],
                    "handle": v["handle"],
                    "video_url": v["video_url"],
                    "video_id_str": v["video_id_str"],
                    "title": v["title"][:255] if v["title"] else "Untitled Video",
                    "thumbnail_url": v["thumbnail_url"],
                    "views": v["views"],
                    "is_pre_campaign": is_pre_campaign,
                    "posted_at": v["posted_at"],
                    "last_scraped_at": datetime.now(timezone.utc).isoformat()
                }

                if dry_run or not supabase_client:
                    logger.info(f"[DRY-RUN] Processed: {v['handle']} - Views: {v['views']} (Pre-Campaign: {is_pre_campaign})")
                    views_updated_count += 1
                    continue

                # In Supabase: check if video already exists
                try:
                    existing = supabase_client.table("videos").select("id, status, views").eq("video_url", v["video_url"]).execute()
                    if existing.data and len(existing.data) > 0:
                        # Existing video: Update views ONLY. DO NOT overwrite status!
                        vid_db_id = existing.data[0]["id"]
                        supabase_client.table("videos").update({
                            "views": v["views"],
                            "thumbnail_url": v["thumbnail_url"] or existing.data[0].get("thumbnail_url"),
                            "last_scraped_at": datetime.now(timezone.utc).isoformat()
                        }).eq("id", vid_db_id).execute()
                        views_updated_count += 1
                    else:
                        # Brand new video: insert with default 'pending'
                        video_payload["status"] = "pending"
                        supabase_client.table("videos").insert(video_payload).execute()
                        new_videos_count += 1
                        logger.info(f"✨ New Video Found: {v['video_url']} ({v['views']} views)")
                except Exception as ex:
                    logger.error(f"Error upserting video {v['video_url']}: {ex}")

    # Log sync summary
    msg = f"Sync Completed: {total_handles} handles scanned, {new_videos_count} new videos, {views_updated_count} views refreshed."
    logger.info(msg)

    if supabase_client and not dry_run:
        try:
            supabase_client.table("sync_logs").insert({
                "status": "success",
                "handles_scanned": total_handles,
                "new_videos_found": new_videos_count,
                "views_updated": views_updated_count,
                "log_message": msg
            }).execute()
        except Exception as e:
            logger.warning(f"Could not record sync_log: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clipping Agency 30-Minute Video View Scraper")
    parser.add_argument("--dry-run", action="store_true", help="Run extractors in read-only / simulation mode")
    args = parser.parse_args()

    run_sync(dry_run=args.dry_run)
