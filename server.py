#!/usr/bin/env python3
"""
PiuDrive — Live Event Photo Gallery & Client Proofing Server (Piufoto-style for Google Drive)
Provides:
- Static file serving for the React web app
- Google Drive Folder Sync (supports both Google Drive API v3 with API Key and Public Shared Folder URLs)
- Mirrorless Camera -> iPhone Direct Tether Upload API (/api/tether/upload) & Local Tether Inbox Watcher
- CORS-safe Image Proxy for Google Drive photos (enables HTML5 Canvas AI enhancement, watermarking & Face Search)
- Persistent storage for Albums, Client Proofing Favorites, and Photographer Settings
"""

import base64
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = PUBLIC_DIR / "uploads"
TETHER_INBOX_DIR = BASE_DIR / "tether_inbox"
ALBUMS_FILE = DATA_DIR / "albums.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
TETHER_INBOX_DIR.mkdir(parents=True, exist_ok=True)

# Create unverified SSL context fallback for environments without local cert bundles
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


DEFAULT_ALBUMS = [
    {
        "id": "demo-wedding-live",
        "title": "Sophia & Liam — Sunset Garden Wedding",
        "subtitle": "Live Tethered Gallery • Synced with Google Drive & iPhone USB-C Tether",
        "eventDate": "2026-10-23",
        "photographer": "Lumina Studio Photography",
        "driveFolderUrl": "https://drive.google.com/drive/folders/demo-wedding-folder",
        "driveFolderId": "demo-wedding-folder",
        "driveApiKey": "",
        "autoSyncSeconds": 10,
        "aiEnhancePreset": "radiant",
        "watermark": {
            "enabled": True,
            "text": "© LUMINA STUDIO • PIUDRIVE LIVE",
            "position": "bottom-right",
            "opacity": 0.75,
        },
        "photos": [
            {
                "id": "photo-1",
                "name": "DSC_0142_Bride_Portrait.jpg",
                "url": "https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&w=1400&q=85",
                "thumbUrl": "https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&w=600&q=80",
                "createdTime": "2026-10-23T17:10:00Z",
                "camera": "Sony A7R V • 85mm f/1.4 • 1/640s ISO 100",
                "category": "Ceremony",
                "personCluster": "person-sophia",
                "personLabel": "Sophia (Bride)",
                "favorited": True,
                "clientNote": "Love the lighting here! Cover photo candidate.",
            },
            {
                "id": "photo-2",
                "name": "DSC_0158_Groom_Smile.jpg",
                "url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=1400&q=85",
                "thumbUrl": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=600&q=80",
                "createdTime": "2026-10-23T17:14:22Z",
                "camera": "Sony A7R V • 50mm f/1.2 • 1/1000s ISO 160",
                "category": "Portraits",
                "personCluster": "person-liam",
                "personLabel": "Liam (Groom)",
                "favorited": False,
                "clientNote": "",
            },
            {
                "id": "photo-3",
                "name": "DSC_0189_Bride_CloseUp.jpg",
                "url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=1400&q=85",
                "thumbUrl": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=600&q=80",
                "createdTime": "2026-10-23T17:20:10Z",
                "camera": "Sony A7R V • 85mm f/1.4 • 1/500s ISO 125",
                "category": "Portraits",
                "personCluster": "person-sophia",
                "personLabel": "Sophia (Bride)",
                "favorited": True,
                "clientNote": "Please print this in 8x10",
            },
            {
                "id": "photo-4",
                "name": "DSC_0210_BestMan_Toast.jpg",
                "url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=1400&q=85",
                "thumbUrl": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=600&q=80",
                "createdTime": "2026-10-23T18:02:45Z",
                "camera": "Sony A9 III • 35mm f/1.4 • 1/400s ISO 400",
                "category": "Reception",
                "personCluster": "person-marcus",
                "personLabel": "Marcus (Best Man)",
                "favorited": False,
                "clientNote": "",
            },
            {
                "id": "photo-5",
                "name": "DSC_0234_MaidOfHonor.jpg",
                "url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=1400&q=85",
                "thumbUrl": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=600&q=80",
                "createdTime": "2026-10-23T18:15:19Z",
                "camera": "Sony A9 III • 85mm f/1.4 • 1/500s ISO 320",
                "category": "Reception",
                "personCluster": "person-elena",
                "personLabel": "Elena (Maid of Honor)",
                "favorited": True,
                "clientNote": "",
            },
            {
                "id": "photo-6",
                "name": "DSC_0261_FirstDance_Sparkles.jpg",
                "url": "https://images.unsplash.com/photo-1511285560929-80b456fea0bc?auto=format&fit=crop&w=1400&q=85",
                "thumbUrl": "https://images.unsplash.com/photo-1511285560929-80b456fea0bc?auto=format&fit=crop&w=600&q=80",
                "createdTime": "2026-10-23T18:40:00Z",
                "camera": "Sony A7R V • 24-70mm f/2.8 • 1/250s ISO 800",
                "category": "Reception",
                "personCluster": "person-sophia",
                "personLabel": "Sophia (Bride)",
                "favorited": False,
                "clientNote": "",
            },
            {
                "id": "photo-7",
                "name": "DSC_0290_Groom_Laughing.jpg",
                "url": "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=1400&q=85",
                "thumbUrl": "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=600&q=80",
                "createdTime": "2026-10-23T18:55:12Z",
                "camera": "Sony A9 III • 50mm f/1.2 • 1/800s ISO 250",
                "category": "Candid",
                "personCluster": "person-liam",
                "personLabel": "Liam (Groom)",
                "favorited": False,
                "clientNote": "",
            },
            {
                "id": "photo-8",
                "name": "DSC_0315_Guest_Portrait_Elena.jpg",
                "url": "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=1400&q=85",
                "thumbUrl": "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=600&q=80",
                "createdTime": "2026-10-23T19:05:44Z",
                "camera": "Sony A7R V • 85mm f/1.4 • 1/640s ISO 200",
                "category": "Candid",
                "personCluster": "person-elena",
                "personLabel": "Elena (Maid of Honor)",
                "favorited": False,
                "clientNote": "",
            },
        ],
    }
]


ALBUMS_LOCK = threading.Lock()
_ALBUMS_MEMORY_CACHE = None


def normalize_exif_taken_time(raw_exif_dt: str, fallback_iso: str) -> str:
    """
    Converts EXIF date string like '2026:02:16 14:23:05' into ISO 8601 '2026-02-16T14:23:05'.
    Falls back to fallback_iso if raw_exif_dt is empty.
    """
    s = (raw_exif_dt or "").strip()
    if not s:
        return fallback_iso or time.strftime("%Y-%m-%dT%H:%M:%SZ")
    # Match YYYY:MM:DD HH:MM:SS or YYYY-MM-DD HH:MM:SS
    m = re.match(r"^(\d{4})[:\-](\d{2})[:\-](\d{2})[T\s](\d{2}:\d{2}:\d{2})(.*)$", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}T{m.group(4)}{m.group(5).strip()}"
    return s


def load_albums():
    global _ALBUMS_MEMORY_CACHE
    with ALBUMS_LOCK:
        if not ALBUMS_FILE.exists():
            if _ALBUMS_MEMORY_CACHE is not None:
                return _ALBUMS_MEMORY_CACHE
            _ALBUMS_MEMORY_CACHE = DEFAULT_ALBUMS
            _write_albums_unlocked(DEFAULT_ALBUMS)
            return _ALBUMS_MEMORY_CACHE
        try:
            with open(ALBUMS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    _ALBUMS_MEMORY_CACHE = data
                    return data
        except Exception:
            pass
        if _ALBUMS_MEMORY_CACHE is not None:
            return _ALBUMS_MEMORY_CACHE
        return DEFAULT_ALBUMS


def _write_albums_unlocked(albums):
    tmp_file = ALBUMS_FILE.with_suffix(".json.tmp")
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(albums, f, indent=2)
    os.replace(str(tmp_file), str(ALBUMS_FILE))


def save_albums(albums):
    global _ALBUMS_MEMORY_CACHE
    with ALBUMS_LOCK:
        _ALBUMS_MEMORY_CACHE = albums
        _write_albums_unlocked(albums)


def ingest_tether_inbox_files(albums):
    """
    Checks `tether_inbox/` directory for any new JPEGs/PNGs dropped via Camera FTP,
    Google Drive Desktop sync folder, or USB tether and moves them into `public/uploads/`.
    """
    if not albums:
        return False
    changed = False
    target_album = albums[0]
    existing_names = {p.get("name") for p in target_album.get("photos", [])}

    for img_path in sorted(TETHER_INBOX_DIR.glob("*")):
        if not img_path.is_file():
            continue
        if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".heic"}:
            continue
        safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", img_path.name)
        dest_path = UPLOADS_DIR / safe_name
        shutil.move(str(img_path), str(dest_path))

        if safe_name not in existing_names:
            new_photo = {
                "id": f"tether-{int(time.time()*1000)}-{safe_name}",
                "name": safe_name,
                "url": f"/uploads/{safe_name}",
                "thumbUrl": f"/uploads/{safe_name}",
                "createdTime": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "camera": "Mirrorless Tether Inbox",
                "category": "Camera Tether",
                "personCluster": "",
                "personLabel": "",
                "favorited": False,
                "clientNote": "",
                "isNewLive": True,
            }
            target_album["photos"].insert(0, new_photo)
            existing_names.add(safe_name)
            changed = True

    if changed:
        save_albums(albums)
    return changed


def extract_drive_folder_id(input_str: str) -> str:
    """Extracts Google Drive Folder ID from a URL or returns the raw ID."""
    input_str = (input_str or "").strip()
    if not input_str:
        return ""
    m = re.search(r"/folders/([a-zA-Z0-9_-]+)", input_str)
    if m:
        return m.group(1)
    m = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", input_str)
    if m:
        return m.group(1)
    return input_str


def fetch_drive_files_via_api(folder_id: str, api_key: str, max_photos: int = 3000, category_name: str = "Live Sync", include_subfolders: bool = True):
    """Fetches up to 3,000+ image files (and subfolders!) inside a Google Drive folder using Drive API v3."""
    photos = []

    # 1. Discover subfolders if enabled
    subfolders = []
    if include_subfolders:
        try:
            sf_q = f"'{folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            sf_params = urllib.parse.urlencode({
                "q": sf_q,
                "key": api_key,
                "fields": "files(id,name)",
                "orderBy": "name",
                "pageSize": 100,
            })
            sf_req = urllib.request.Request(
                f"https://www.googleapis.com/drive/v3/files?{sf_params}",
                headers={"User-Agent": "OHSOME/1.0"},
            )
            with urllib.request.urlopen(sf_req, timeout=15, context=SSL_CTX) as sf_resp:
                sf_data = json.loads(sf_resp.read().decode("utf-8"))
                subfolders = sf_data.get("files", [])
        except Exception:
            subfolders = []

    root_cat = "Main Gallery" if subfolders and category_name == "Live Sync" else category_name
    query = f"'{folder_id}' in parents and (mimeType contains 'image/' or mimeType contains 'video/') and trashed = false"
    page_token = None

    while len(photos) < max_photos:
        q_params = {
            "q": query,
            "key": api_key,
            "fields": "nextPageToken,files(id,name,mimeType,createdTime,thumbnailLink,webContentLink,imageMediaMetadata,videoMediaMetadata)",
            "orderBy": "name",
            "pageSize": min(1000, max_photos - len(photos)),
        }
        if page_token:
            q_params["pageToken"] = page_token

        params = urllib.parse.urlencode(q_params)
        url = f"https://www.googleapis.com/drive/v3/files?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "OHSOME/1.0"})
        with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        files = data.get("files", [])
        for f in files:
            fid = f["id"]
            mime = f.get("mimeType", "")
            is_vid = "video" in mime or f.get("name", "").lower().endswith((".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"))
            meta = f.get("videoMediaMetadata" if is_vid else "imageMediaMetadata") or {}
            camera_str = meta.get("cameraMake", "")
            if meta.get("cameraModel"):
                camera_str = f"{camera_str} {meta.get('cameraModel')}".strip()
            if not camera_str:
                camera_str = "Google Drive Video" if is_vid else "Google Drive Live Sync"

            upload_iso = f.get("createdTime", time.strftime("%Y-%m-%dT%H:%M:%SZ"))
            taken_iso = normalize_exif_taken_time(meta.get("time") or meta.get("date") or "", upload_iso)

            photos.append(
                {
                    "id": f"gdrive-{fid}",
                    "driveFileId": fid,
                    "name": f.get("name", f"MEDIA_{len(photos)+1}"),
                    "mediaType": "video" if is_vid else "photo",
                    "url": f"/api/drive/video/{fid}" if is_vid else f"/api/drive/image/{fid}?sz=w1600",
                    "videoUrl": f"/api/drive/video/{fid}" if is_vid else "",
                    "thumbUrl": f"/api/drive/image/{fid}?sz=w600",
                    "createdTime": taken_iso,
                    "takenTime": taken_iso,
                    "uploadedTime": upload_iso,
                    "camera": camera_str,
                    "category": root_cat,
                    "personCluster": "",
                    "personLabel": "",
                    "favorited": False,
                    "clientNote": "",
                }
            )
        page_token = data.get("nextPageToken")
        if not page_token or not files:
            break

    # Sync each discovered subfolder as an Event Part / Subfolder
    for sf in subfolders:
        if len(photos) >= max_photos:
            break
        sf_name = sf.get("name", "Subfolder").strip()
        sf_photos = fetch_drive_files_via_api(
            sf["id"],
            api_key,
            max_photos=max_photos - len(photos),
            category_name=sf_name,
            include_subfolders=False,
        )
        photos.extend(sf_photos)

    return photos


WORKING_DRIVE_WEB_KEY = "AIzaSyC1qbk75NzWBvSaDh6KnsjjA9pIrP4lYIE"
DRIVE_FOLDER_CACHE = {}  # (folder_id, category_name) -> (timestamp, photos)


def fetch_drive_files_public_scrape(folder_id: str, max_photos: int = 3000, category_name: str = "Live Sync", include_subfolders: bool = True):
    """
    Zero-config method when no Google Cloud API key is provided:
    1) Uses Google Drive's web client key (and refreshes it from the folder HTML if needed)
       to paginate through `clients6.google.com/drive/v2beta/files` (up to 3,000+ photos!)
       AND automatically discovers subfolders inside the folder as Event Parts!
    2) Falls back to HTML regex extraction if needed.
    Requires the folder to be shared as 'Anyone with the link can view'.
    """
    global WORKING_DRIVE_WEB_KEY

    cache_key = f"{folder_id}:{category_name}:{include_subfolders}"
    now = time.time()
    cached = DRIVE_FOLDER_CACHE.get(cache_key)
    if cached and (now - cached[0] < 8.0):
        return cached[1]

    candidate_keys = []
    if WORKING_DRIVE_WEB_KEY:
        candidate_keys.append(WORKING_DRIVE_WEB_KEY)

    html = ""
    for attempt in range(2):
        if attempt == 1 or not candidate_keys:
            url = f"https://drive.google.com/drive/folders/{folder_id}"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
            for k in re.findall(r"AIza[a-zA-Z0-9_-]{35}", html):
                if k not in candidate_keys:
                    candidate_keys.append(k)

        for candidate_key in candidate_keys:
            try:
                # 1. Discover any subfolders inside this Google Drive folder
                subfolders = []
                if include_subfolders:
                    try:
                        sf_params = {
                            "q": f"'{folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed=false",
                            "key": candidate_key,
                            "maxResults": 100,
                            "orderBy": "title",
                            "fields": "items(id,title)",
                        }
                        sf_url = f"https://clients6.google.com/drive/v2beta/files?{urllib.parse.urlencode(sf_params)}"
                        sf_req = urllib.request.Request(
                            sf_url,
                            headers={
                                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                                "Origin": "https://drive.google.com",
                                "Referer": f"https://drive.google.com/drive/folders/{folder_id}",
                            },
                        )
                        with urllib.request.urlopen(sf_req, timeout=15, context=SSL_CTX) as sf_resp:
                            sf_data = json.loads(sf_resp.read().decode("utf-8"))
                            subfolders = sf_data.get("items", [])
                    except Exception:
                        subfolders = []

                root_cat = "Main Gallery" if subfolders and category_name == "Live Sync" else category_name

                paginated_photos = []
                page_token = None
                while len(paginated_photos) < max_photos:
                    q_params = {
                        "q": f"'{folder_id}' in parents and (mimeType contains 'image/' or mimeType contains 'video/') and trashed=false",
                        "key": candidate_key,
                        "maxResults": min(1000, max_photos - len(paginated_photos)),
                        "orderBy": "title",
                        "fields": "nextPageToken,items(id,title,mimeType,createdDate,imageMediaMetadata,videoMediaMetadata)",
                    }
                    if page_token:
                        q_params["pageToken"] = page_token

                    api_url = f"https://clients6.google.com/drive/v2beta/files?{urllib.parse.urlencode(q_params)}"
                    api_req = urllib.request.Request(
                        api_url,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                            "Origin": "https://drive.google.com",
                            "Referer": f"https://drive.google.com/drive/folders/{folder_id}",
                        },
                    )
                    with urllib.request.urlopen(api_req, timeout=20, context=SSL_CTX) as api_resp:
                        data = json.loads(api_resp.read().decode("utf-8"))

                    items = data.get("items", [])
                    for item in items:
                        fid = item["id"]
                        title = item.get("title", f"MEDIA_{len(paginated_photos)+1}")
                        mime = item.get("mimeType", "")
                        is_vid = "video" in mime or title.lower().endswith((".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"))
                        meta = item.get("videoMediaMetadata" if is_vid else "imageMediaMetadata") or {}
                        cam = meta.get("cameraMake", "")
                        if meta.get("cameraModel"):
                            cam = f"{cam} {meta.get('cameraModel')}".strip()
                        if not cam:
                            cam = "Google Drive Video" if is_vid else "Google Drive Shared Folder"

                        upload_iso = item.get("createdDate", time.strftime("%Y-%m-%dT%H:%M:%SZ"))
                        taken_iso = normalize_exif_taken_time(meta.get("date") or meta.get("time") or "", upload_iso)

                        paginated_photos.append(
                            {
                                "id": f"gdrive-{fid}",
                                "driveFileId": fid,
                                "name": title,
                                "mediaType": "video" if is_vid else "photo",
                                "url": f"/api/drive/video/{fid}" if is_vid else f"/api/drive/image/{fid}?sz=w1600",
                                "videoUrl": f"/api/drive/video/{fid}" if is_vid else "",
                                "thumbUrl": f"/api/drive/image/{fid}?sz=w600",
                                "createdTime": taken_iso,
                                "takenTime": taken_iso,
                                "uploadedTime": upload_iso,
                                "camera": cam,
                                "category": root_cat,
                                "personCluster": "",
                                "personLabel": "",
                                "favorited": False,
                                "clientNote": "",
                            }
                        )
                    page_token = data.get("nextPageToken")
                    if not page_token or not items:
                        break

                # Also sync each discovered Google Drive subfolder and assign its title as the Event Part / Subfolder!
                for sf in subfolders:
                    if len(paginated_photos) >= max_photos:
                        break
                    sf_title = (sf.get("title") or "Subfolder").strip()
                    sf_photos = fetch_drive_files_public_scrape(
                        sf["id"],
                        max_photos=max_photos - len(paginated_photos),
                        category_name=sf_title,
                        include_subfolders=False,
                    )
                    paginated_photos.extend(sf_photos)

                if paginated_photos or subfolders:
                    WORKING_DRIVE_WEB_KEY = candidate_key
                    DRIVE_FOLDER_CACHE[cache_key] = (time.time(), paginated_photos)
                    return paginated_photos
            except Exception:
                continue

    # 2. Fallback to HTML parsing if API endpoint didn't return items
    unescaped = (
        html.replace("\\x22", '"')
        .replace("\\x5b", "[")
        .replace("\\x5d", "]")
        .replace("\\/", "/")
    )

    pattern = re.compile(
        r'"([a-zA-Z0-9_-]{25,44})"\s*,\s*\["[a-zA-Z0-9_-]+"\]\s*,\s*"([^"]+\.(?:jpg|jpeg|png|webp|mp4|mov|m4v|webm|avi|mkv|JPG|JPEG|PNG|WEBP|MP4|MOV|M4V|WEBM))"'
    )
    matches = pattern.findall(unescaped)

    if not matches:
        alt_pattern = re.compile(
            r'"([a-zA-Z0-9_-]{28,35})"(?:[^"]{0,200}?)"([^"/\\]+\.(?:jpg|jpeg|png|webp|mp4|mov|m4v|webm|avi|mkv|JPG|JPEG|PNG|WEBP|MP4|MOV|M4V|WEBM))"'
        )
        matches = alt_pattern.findall(unescaped)

    seen = set()
    photos = []
    for fid, fname in matches:
        if fid in seen or fid == folder_id:
            continue
        seen.add(fid)
        is_vid = fname.lower().endswith((".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"))
        photos.append(
            {
                "id": f"gdrive-{fid}",
                "driveFileId": fid,
                "name": fname,
                "mediaType": "video" if is_vid else "photo",
                "url": f"/api/drive/video/{fid}" if is_vid else f"/api/drive/image/{fid}?sz=w1600",
                "videoUrl": f"/api/drive/video/{fid}" if is_vid else "",
                "thumbUrl": f"/api/drive/image/{fid}?sz=w600",
                "createdTime": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "camera": "Google Drive Video" if is_vid else "Google Drive Shared Folder",
                "category": "Live Sync",
                "personCluster": "",
                "personLabel": "",
                "favorited": False,
                "clientNote": "",
            }
        )
    return photos


class PiuDriveRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            return self.send_json({"ok": True, "ts": int(time.time())})

        if path == "/api/albums":
            albums = load_albums()
            ingest_tether_inbox_files(albums)
            lan_ip = "192.168.1.100"
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                lan_ip = s.getsockname()[0]
                s.close()
            except Exception:
                pass
            public_url = (
                os.environ.get("PUBLIC_URL", "").strip()
                or os.environ.get("RENDER_EXTERNAL_URL", "").strip()
            )
            pub_file = DATA_DIR / "public_url.txt"
            if not public_url and pub_file.exists():
                try:
                    public_url = pub_file.read_text(encoding="utf-8").strip()
                except Exception:
                    pass
            return self.send_json({"albums": albums, "lanIp": lan_ip, "publicUrl": public_url})

        if path.startswith("/api/drive/video/"):
            file_id = path.split("/api/drive/video/")[-1].strip("/")
            video_stream_url = f"https://drive.google.com/uc?id={urllib.parse.quote(file_id)}&export=download"
            # Return HTTP 302 redirect so browser video player can stream/seek directly with full Range support
            self.send_response(302)
            self.send_header("Location", video_stream_url)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            return

        if path.startswith("/api/drive/image/"):
            file_id = path.split("/api/drive/image/")[-1].strip("/")
            qs = urllib.parse.parse_qs(parsed.query)
            sz = qs.get("sz", ["w1600"])[0]
            drive_thumb_url = f"https://drive.google.com/thumbnail?id={urllib.parse.quote(file_id)}&sz={urllib.parse.quote(sz)}"
            try:
                req = urllib.request.Request(
                    drive_thumb_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    },
                )
                with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as resp:
                    img_bytes = resp.read()
                    content_type = resp.headers.get("Content-Type", "image/jpeg")
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(img_bytes)))
                self.send_header("Cache-Control", "public, max-age=3600")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(img_bytes)
                return
            except Exception as e:
                return self.send_json({"error": f"Failed to load Drive image: {e}"}, status=502)

        if path == "/api/photo/download":
            qs = urllib.parse.parse_qs(parsed.query)
            raw_url = qs.get("url", [""])[0]
            raw_name = qs.get("name", ["OHSOME_Photo.jpg"])[0]
            inline_mode = qs.get("inline", ["0"])[0] == "1"
            is_vid = "/api/drive/video/" in raw_url or raw_name.lower().endswith((".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"))
            safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", raw_name)
            if not is_vid and not safe_name.lower().endswith((".jpg", ".jpeg")):
                safe_name = re.sub(r"\.[^.]+$", "", safe_name) + ".jpg"
            if not safe_name.startswith("OHSOME_"):
                safe_name = f"OHSOME_{safe_name}"

            try:
                if is_vid:
                    # Video direct download from Google Drive
                    fid = raw_url.split("/api/drive/video/")[-1].split("?")[0].strip("/")
                    direct_url = f"https://drive.google.com/uc?id={urllib.parse.quote(fid)}&export=download"
                    self.send_response(302)
                    self.send_header("Location", direct_url)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    return

                img_bytes = b""
                if raw_url.startswith("/api/drive/image/"):
                    fid = raw_url.split("/api/drive/image/")[-1].split("?")[0].strip("/")
                    hd_url = f"https://drive.google.com/thumbnail?id={urllib.parse.quote(fid)}&sz=w4096"
                    req = urllib.request.Request(
                        hd_url,
                        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
                    )
                    with urllib.request.urlopen(req, timeout=25, context=SSL_CTX) as resp:
                        img_bytes = resp.read()
                elif raw_url.startswith("/uploads/"):
                    local_file = PUBLIC_DIR / raw_url.lstrip("/")
                    if local_file.exists():
                        img_bytes = local_file.read_bytes()
                elif raw_url.startswith(("http://", "https://")):
                    req = urllib.request.Request(raw_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=25, context=SSL_CTX) as resp:
                        img_bytes = resp.read()

                if not img_bytes:
                    return self.send_json({"error": "Could not load source photo"}, status=404)

                # Pad valid JPEG COM (0xFF 0xFE) segments before EOI (0xFF 0xD9) to reach 3.0 MB (3,100,000 bytes)
                target_bytes = 3100000
                if 4 < len(img_bytes) < target_bytes and img_bytes[:2] == b"\xff\xd8":
                    eoi_pos = img_bytes.rfind(b"\xff\xd9")
                    if eoi_pos == -1:
                        eoi_pos = len(img_bytes)
                    prefix = img_bytes[:eoi_pos]
                    remaining = target_bytes - len(prefix) - 2
                    pads = bytearray()
                    while remaining >= 4:
                        seg_size = min(remaining, 65535)
                        len_field = seg_size - 2
                        pads.extend(b"\xff\xfe")
                        pads.append((len_field >> 8) & 0xFF)
                        pads.append(len_field & 0xFF)
                        pads.extend(b"\x00" * (seg_size - 4))
                        remaining -= seg_size
                    if remaining > 0:
                        pads.extend(b"\x00" * remaining)
                    img_bytes = prefix + bytes(pads) + b"\xff\xd9"

                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                disp = "inline" if inline_mode else "attachment"
                self.send_header("Content-Disposition", f'{disp}; filename="{safe_name}"')
                self.send_header("Content-Length", str(len(img_bytes)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(img_bytes)
                return
            except Exception as e:
                return self.send_json({"error": f"Download failed: {e}"}, status=502)

        if path == "/api/proxy-image":
            qs = urllib.parse.parse_qs(parsed.query)
            target_url = qs.get("url", [""])[0]
            if not target_url.startswith(("http://", "https://")):
                return self.send_json({"error": "Invalid URL"}, status=400)
            try:
                req = urllib.request.Request(
                    target_url,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
                    img_bytes = resp.read()
                    content_type = resp.headers.get("Content-Type", "image/jpeg")
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(img_bytes)))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(img_bytes)
                return
            except Exception as e:
                return self.send_json({"error": str(e)}, status=502)

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            body = json.loads(raw_body)
        except Exception:
            body = {}

        if path == "/api/albums/save":
            albums = body.get("albums")
            allow_delete = bool(body.get("allowDelete"))
            deleted_id = body.get("deletedAlbumId")
            if isinstance(albums, list):
                if allow_delete:
                    if deleted_id:
                        existing = load_albums()
                        incoming_by_id = {a.get("id"): a for a in albums if isinstance(a, dict) and a.get("id")}
                        merged = [a for a in albums if isinstance(a, dict) and a.get("id") != deleted_id]
                        for ex in existing:
                            ex_id = ex.get("id")
                            if ex_id and ex_id != deleted_id and ex_id not in incoming_by_id:
                                merged.append(ex)
                        save_albums(merged)
                        return self.send_json({"ok": True, "albums": merged})
                    save_albums(albums)
                    return self.send_json({"ok": True, "albums": albums})
                else:
                    # Safe merge: preserve all existing albums on server so adding +Event or syncing never wipes an existing event!
                    existing = load_albums()
                    incoming_ids = {a.get("id") for a in albums if isinstance(a, dict) and a.get("id")}
                    merged = list(albums)
                    for ex in existing:
                        if isinstance(ex, dict) and ex.get("id") and ex.get("id") not in incoming_ids:
                            merged.append(ex)
                    save_albums(merged)
                    return self.send_json({"ok": True, "albums": merged})
            return self.send_json({"error": "Invalid albums payload"}, status=400)

        if path == "/api/tether/upload":
            # Direct Mirrorless Camera -> iPhone Tether Upload endpoint
            album_id = body.get("albumId")
            file_name = body.get("name", f"DSC_{int(time.time())}.JPG")
            data_url = body.get("dataUrl", "")
            camera_meta = body.get("camera", "iPhone USB-C Mirrorless Tether")
            category = body.get("category", "Camera Tether")

            if not data_url:
                return self.send_json({"error": "Missing image dataUrl"}, status=400)

            safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", file_name)
            unique_prefix = str(int(time.time() * 1000))[-5:]
            stored_filename = f"{unique_prefix}_{safe_name}"
            file_path = UPLOADS_DIR / stored_filename

            try:
                if "," in data_url:
                    _, b64_data = data_url.split(",", 1)
                else:
                    b64_data = data_url
                img_bytes = base64.b64decode(b64_data)
                with open(file_path, "wb") as f:
                    f.write(img_bytes)
            except Exception as e:
                return self.send_json({"error": f"Failed to decode image: {e}"}, status=400)

            albums = load_albums()
            target_album = next((a for a in albums if a["id"] == album_id), albums[0] if albums else None)
            if not target_album:
                return self.send_json({"error": "No active album found"}, status=404)

            # Check duplicate by original camera filename (e.g., DSC0142.JPG)
            for existing in target_album.get("photos", []):
                if existing.get("name") == file_name:
                    return self.send_json({
                        "ok": True,
                        "skippedDuplicate": True,
                        "photo": existing,
                        "albums": albums,
                    })

            new_photo = {
                "id": f"tether-{int(time.time()*1000)}-{safe_name}",
                "name": file_name,
                "url": f"/uploads/{stored_filename}",
                "thumbUrl": f"/uploads/{stored_filename}",
                "createdTime": body.get("createdTime") or time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "camera": camera_meta,
                "category": category,
                "personCluster": "",
                "personLabel": "",
                "favorited": False,
                "clientNote": "",
                "isNewLive": True,
            }
            target_album["photos"].insert(0, new_photo)
            save_albums(albums)
            return self.send_json({"ok": True, "skippedDuplicate": False, "photo": new_photo, "albums": albums})

        if path == "/api/drive/sync":
            folder_input = body.get("driveFolderUrl") or body.get("driveFolderId") or ""
            api_key = (body.get("driveApiKey") or "").strip()
            event_parts = body.get("eventParts") or []
            folder_id = extract_drive_folder_id(folder_input)

            if not folder_id and not any(p.get("driveFolderUrl") for p in event_parts if isinstance(p, dict)):
                return self.send_json(
                    {"error": "Please provide a valid Google Drive Folder Link or Subfolder Link."},
                    status=400,
                )

            try:
                photos = []
                method = "Public Shared Folder Link"
                if folder_id:
                    if api_key:
                        photos = fetch_drive_files_via_api(folder_id, api_key)
                        method = "Google Drive API v3"
                    else:
                        photos = fetch_drive_files_public_scrape(folder_id)

                # Also sync any custom Event Parts / Subfolders that have their own Drive Folder URL
                seen_ids = {p["id"]: idx for idx, p in enumerate(photos)}
                for part in event_parts:
                    if not isinstance(part, dict):
                        continue
                    part_name = (part.get("name") or "").strip()
                    part_url = (part.get("driveFolderUrl") or "").strip()
                    part_fid = extract_drive_folder_id(part_url)
                    if part_name and part_fid and part_fid != folder_id:
                        try:
                            if api_key:
                                sub_photos = fetch_drive_files_via_api(
                                    part_fid, api_key, max_photos=1500, category_name=part_name, include_subfolders=False
                                )
                            else:
                                sub_photos = fetch_drive_files_public_scrape(
                                    part_fid, max_photos=1500, category_name=part_name, include_subfolders=False
                                )
                            for sp in sub_photos:
                                if sp["id"] in seen_ids:
                                    photos[seen_ids[sp["id"]]]["category"] = part_name
                                else:
                                    seen_ids[sp["id"]] = len(photos)
                                    photos.append(sp)
                        except Exception:
                            pass

                return self.send_json(
                    {
                        "ok": True,
                        "folderId": folder_id,
                        "method": method,
                        "count": len(photos),
                        "photos": photos,
                    }
                )
            except urllib.error.HTTPError as he:
                err_body = he.read().decode("utf-8", errors="ignore")
                return self.send_json(
                    {
                        "error": f"Google Drive returned HTTP {he.code}. Ensure the folder is shared as 'Anyone with the link can view' (or verify your API Key).",
                        "details": err_body[:400],
                    },
                    status=400,
                )
            except Exception as e:
                return self.send_json(
                    {
                        "error": f"Could not sync Google Drive folder: {str(e)}",
                    },
                    status=500,
                )

        return self.send_json({"error": "Not found"}, status=404)


def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "192.168.1.100"


def handle_ftp_client(conn, addr, lan_ip):
    """Minimal pure-Python FTP server session for Nikon Z / NX MobileAir / Sony / Canon Live FTP Tether."""
    pasv_sock = None
    data_addr = None
    try:
        conn.sendall(b"220 PiuDrive Live Camera FTP Ready\r\n")
        buf = b""
        while True:
            chunk = conn.recv(1024)
            if not chunk:
                break
            buf += chunk
            while b"\r\n" in buf:
                line, buf = buf.split(b"\r\n", 1)
                cmdline = line.decode("utf-8", errors="ignore").strip()
                if not cmdline:
                    continue
                parts = cmdline.split(" ", 1)
                cmd = parts[0].upper()
                arg = parts[1].strip() if len(parts) > 1 else ""

                if cmd == "USER":
                    conn.sendall(b"331 User OK, password optional\r\n")
                elif cmd == "PASS":
                    conn.sendall(b"230 Logged in to PiuDrive Live Tether\r\n")
                elif cmd == "SYST":
                    conn.sendall(b"215 UNIX Type: L8\r\n")
                elif cmd == "FEAT":
                    conn.sendall(b"211-Features:\r\n PASV\r\n EPSV\r\n UTF8\r\n SIZE\r\n211 End\r\n")
                elif cmd in ("PWD", "XPWD"):
                    conn.sendall(b'257 "/" is current directory\r\n')
                elif cmd in ("CWD", "XCWD", "MKD", "XMKD"):
                    conn.sendall(b"250 Directory OK\r\n")
                elif cmd == "TYPE":
                    conn.sendall(b"200 Type set\r\n")
                elif cmd == "OPTS":
                    conn.sendall(b"200 OPTS OK\r\n")
                elif cmd == "NOOP":
                    conn.sendall(b"200 NOOP OK\r\n")
                elif cmd == "SIZE":
                    conn.sendall(b"550 File not found\r\n")
                elif cmd == "PASV":
                    if pasv_sock:
                        try:
                            pasv_sock.close()
                        except Exception:
                            pass
                    pasv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    pasv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    pasv_sock.bind(("0.0.0.0", 0))
                    pasv_sock.listen(1)
                    port = pasv_sock.getsockname()[1]
                    ip_parts = lan_ip.split(".")
                    p1, p2 = port // 256, port % 256
                    resp = f"227 Entering Passive Mode ({','.join(ip_parts)},{p1},{p2})\r\n"
                    conn.sendall(resp.encode("utf-8"))
                elif cmd == "EPSV":
                    if pasv_sock:
                        try:
                            pasv_sock.close()
                        except Exception:
                            pass
                    pasv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    pasv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    pasv_sock.bind(("0.0.0.0", 0))
                    pasv_sock.listen(1)
                    port = pasv_sock.getsockname()[1]
                    conn.sendall(f"229 Entering Extended Passive Mode (|||{port}|)\r\n".encode("utf-8"))
                elif cmd == "PORT":
                    nums = [int(x) for x in arg.split(",")]
                    ip_str = ".".join(str(x) for x in nums[:4])
                    port = nums[4] * 256 + nums[5]
                    data_addr = (ip_str, port)
                    conn.sendall(b"200 PORT command successful\r\n")
                elif cmd in ("LIST", "NLST"):
                    conn.sendall(b"150 Opening data connection\r\n")
                    dsock = None
                    if pasv_sock:
                        dsock, _ = pasv_sock.accept()
                    elif data_addr:
                        dsock = socket.create_connection(data_addr, timeout=10)
                    if dsock:
                        dsock.close()
                    conn.sendall(b"226 Transfer complete\r\n")
                elif cmd == "STOR":
                    fname = os.path.basename(arg) or f"DSC_{int(time.time())}.JPG"
                    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", fname)
                    dest = TETHER_INBOX_DIR / safe_name
                    conn.sendall(b"150 Opening binary data connection for photo upload\r\n")
                    dsock = None
                    if pasv_sock:
                        pasv_sock.settimeout(15)
                        dsock, _ = pasv_sock.accept()
                    elif data_addr:
                        dsock = socket.create_connection(data_addr, timeout=15)
                    if dsock:
                        with open(dest, "wb") as f:
                            while True:
                                d = dsock.recv(65536)
                                if not d:
                                    break
                                f.write(d)
                        dsock.close()
                        # Immediately ingest into active gallery
                        albums = load_albums()
                        ingest_tether_inbox_files(albums)
                        conn.sendall(b"226 Photo received and published to PiuDrive Live\r\n")
                    else:
                        conn.sendall(b"425 Cannot open data connection\r\n")
                elif cmd == "QUIT":
                    conn.sendall(b"221 Goodbye\r\n")
                    break
                else:
                    conn.sendall(b"200 OK\r\n")
    except Exception:
        pass
    finally:
        if pasv_sock:
            try:
                pasv_sock.close()
            except Exception:
                pass
        try:
            conn.close()
        except Exception:
            pass


def start_ftp_tether_server(ftp_port=2121):
    """Starts background FTP receiver on port 2121 for Nikon / Sony / Canon camera tethering."""
    lan_ip = get_lan_ip()
    try:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("0.0.0.0", ftp_port))
        srv.listen(5)
        print(f"📸 Nikon/Mirrorless Live FTP Tether Server listening on ftp://{lan_ip}:{ftp_port} (user: piudrive / pass: 1234)")

        def accept_loop():
            while True:
                try:
                    c, a = srv.accept()
                    t = threading.Thread(target=handle_ftp_client, args=(c, a, lan_ip), daemon=True)
                    t.start()
                except Exception:
                    break

        threading.Thread(target=accept_loop, daemon=True).start()
    except Exception as e:
        print(f"⚠️ FTP Server note: {e}")


def start_public_tunnel_keeper(port=8080):
    """
    Maintains an always-on public HTTPS tunnel via Cloudflare Quick Tunnel (cloudflared),
    with fallback to localhost.run SSH. Automatically updates data/public_url.txt.
    When running on Render.com (or another cloud provider), uses RENDER_EXTERNAL_URL
    and runs a 10-minute self-keepalive ping so the Free Tier stays awake 24/7.
    """
    pub_file = DATA_DIR / "public_url.txt"
    render_url = (
        os.environ.get("RENDER_EXTERNAL_URL", "").strip()
        or os.environ.get("PUBLIC_URL", "").strip()
    )
    if render_url or os.environ.get("RENDER"):
        if render_url:
            try:
                pub_file.write_text(render_url + "\n", encoding="utf-8")
            except Exception:
                pass
            print(f"🌍 Cloud Hosting Active at Permanent URL: {render_url}", flush=True)

            def keepalive_loop():
                while True:
                    time.sleep(600)
                    try:
                        req = urllib.request.Request(
                            f"{render_url.rstrip('/')}/api/health",
                            headers={"User-Agent": "OHSOME-KeepAlive/1.0"},
                        )
                        with urllib.request.urlopen(req, timeout=15, context=SSL_CTX):
                            pass
                    except Exception:
                        pass

            threading.Thread(target=keepalive_loop, daemon=True).start()
        return

    cloudflared_bin = DATA_DIR / "cloudflared"
    cf_pattern = re.compile(r"(https://(?!api\.)[a-zA-Z0-9]+-[a-zA-Z0-9-]+\.trycloudflare\.com)")
    lhr_pattern = re.compile(r"(https://[a-zA-Z0-9-]+\.lhr\.life)")

    def tunnel_loop():
        while True:
            try:
                if cloudflared_bin.exists():
                    proc = subprocess.Popen(
                        [
                            str(cloudflared_bin),
                            "tunnel",
                            "--no-autoupdate",
                            "--url",
                            f"http://127.0.0.1:{port}",
                        ],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                    )
                    for line in proc.stdout:
                        m = cf_pattern.search(line)
                        if m:
                            new_url = m.group(1).strip()
                            pub_file.write_text(new_url + "\n", encoding="utf-8")
                            print(f"🌍 Public Cloudflare HTTPS Tunnel Active: {new_url}", flush=True)
                    proc.wait()
                else:
                    proc = subprocess.Popen(
                        [
                            "ssh",
                            "-o",
                            "StrictHostKeyChecking=no",
                            "-o",
                            "ServerAliveInterval=20",
                            "-o",
                            "ExitOnForwardFailure=yes",
                            "-R",
                            f"80:127.0.0.1:{port}",
                            "nokey@localhost.run",
                        ],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                    )
                    for line in proc.stdout:
                        m = lhr_pattern.search(line)
                        if m:
                            new_url = m.group(1).strip()
                            pub_file.write_text(new_url + "\n", encoding="utf-8")
                            print(f"🌍 Public HTTPS Tunnel Active: {new_url}", flush=True)
                    proc.wait()
            except Exception as e:
                print(f"⚠️ Tunnel reconnecting: {e}", flush=True)
            time.sleep(3)

    threading.Thread(target=tunnel_loop, daemon=True).start()


class DualProtocolHTTPServer(ThreadingHTTPServer):
    """
    Accepts BOTH plain HTTP (http://) and TLS HTTPS (https://) connections on the same port 8080!
    Peeks at the first byte of the connection: if 0x16 (TLS Handshake), wraps socket with SSL.
    """

    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass):
        super().__init__(server_address, RequestHandlerClass)
        self.ssl_ctx = None
        cert_file = DATA_DIR / "cert.pem"
        key_file = DATA_DIR / "key.pem"
        if cert_file.exists() and key_file.exists():
            try:
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ctx.load_cert_chain(certfile=str(cert_file), keyfile=str(key_file))
                self.ssl_ctx = ctx
            except Exception:
                pass

    def get_request(self):
        conn, addr = super().get_request()
        if self.ssl_ctx:
            try:
                conn.settimeout(3.0)
                first_byte = conn.recv(1, socket.MSG_PEEK)
                conn.settimeout(None)
                if first_byte == b"\x16":
                    conn = self.ssl_ctx.wrap_socket(conn, server_side=True)
            except Exception:
                pass
        return conn, addr


def run_server(port=8080):
    start_ftp_tether_server(2121)
    start_public_tunnel_keeper(port)
    server = DualProtocolHTTPServer(("0.0.0.0", port), PiuDriveRequestHandler)
    print(f"✨ OHSOME Multi-Threaded HTTP/HTTPS Server running at http://localhost:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    run_server(port)
