# PiuDrive — Live Event Photo Gallery & AI Proofing for Google Drive

A full-featured, Piufoto-inspired live event photography delivery, AI enhancement, face search, and client proofing web application powered by **Google Drive**.

## ✨ Features Included

1. **Live Event Photo Gallery Synced with Google Drive**
   - Connect any Google Drive folder via its **Shared Folder URL** (`Anyone with the link can view`) — works out of the box with **zero API key required**, or optionally add a **Google Drive API v3 Key** for EXIF camera metadata & large folders.
   - Configurable **Live Auto-Sync** polling interval (e.g. every 15s) so as you shoot and upload to Google Drive (via Google Drive Desktop, phone upload, or camera FTP-to-Drive), new photos appear live in the gallery.
   - Includes a **⚡ Simulate Live Camera Shot** button and local file upload to test live event streaming immediately.

2. **QR Code & Shareable Client/Guest Link**
   - Generates a high-contrast, printable **Event QR Code Card** and copyable Guest Link (`?mode=guest&album=...`).
   - Switch between **Photographer Admin Mode** and **Guest / Client View** with one click.

3. **Client Proofing & Favorites**
   - Guests/clients can heart (`♥`) favorite photos and leave per-photo retouching or print notes.
   - Export selections via **One-Click Copy for Lightroom / Capture One** (comma-separated filename filter) or download a full **CSV Selection Report**.

4. **AI Face Search / Selfie Matching**
   - Guests can **Take a Live Webcam Selfie**, **Upload a Selfie Photo**, or click any recognized person's avatar chip to filter all photos they appear in with a similarity match score badge.

5. **AI Photo Enhancement & Custom Watermark Studio**
   - Real-time AI color & tone presets (`AI Radiant Pop`, `Soft Portrait Glow`, `Editorial Film`, `Fine Art Mono`, `Original`) with a **Hold-to-Compare Before/After** button in the lightbox.
   - Customizable Studio Watermark (text, opacity, corner/center/banner placement) that previews live and is **automatically baked into HD photo downloads** via HTML5 Canvas.

---

## 🚀 Quick Start

Run the server using Python 3 (no external `pip` or `npm` packages required):

```bash
cd /Users/weechengoon/.gemini/antigravity/scratch/piufoto-drive
python3 server.py
```

Then open **http://localhost:8080** in your browser.
