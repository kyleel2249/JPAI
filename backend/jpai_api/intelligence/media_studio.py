"""Reality Studio: governed media assets, production jobs and delivery specifications.

AI reconstruction providers are deliberately capability-gated. This module records jobs
and validates deliverables; it never labels a transcode as photorealistic reconstruction.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}
MAX_UPLOAD_BYTES = int(os.getenv("JPAI_MEDIA_MAX_UPLOAD_BYTES", str(20 * 1024 * 1024)))


class MediaStudioError(ValueError):
    """Invalid or unsafe media-studio operation."""


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


class MediaStudioStore:
    def __init__(self, database_path=None, media_root=None):
        self.database_path = Path(database_path or os.getenv("JPAI_DATABASE_PATH", "data/jpai.sqlite3"))
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.media_root = Path(media_root or os.getenv("JPAI_MEDIA_ROOT", "data/media_studio")).expanduser()
        self.media_root.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS media_assets (
              id TEXT PRIMARY KEY, original_name TEXT NOT NULL, stored_name TEXT NOT NULL,
              media_type TEXT NOT NULL, extension TEXT NOT NULL, size_bytes INTEGER NOT NULL,
              sha256 TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS media_jobs (
              id TEXT PRIMARY KEY, title TEXT NOT NULL, mode TEXT NOT NULL,
              source_asset_id TEXT NOT NULL, status TEXT NOT NULL, request TEXT NOT NULL,
              output_spec TEXT NOT NULL, safety TEXT NOT NULL, created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL, FOREIGN KEY(source_asset_id) REFERENCES media_assets(id)
            );
            CREATE INDEX IF NOT EXISTS idx_media_jobs_updated ON media_jobs(updated_at DESC);
            """)

    def _connect(self):
        db = sqlite3.connect(self.database_path, timeout=20)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @staticmethod
    def _asset(row):
        return dict(row) if row else None

    @staticmethod
    def _job(row):
        if not row:
            return None
        item = dict(row)
        for key in ("request", "output_spec", "safety"):
            item[key] = json.loads(item[key])
        return item

    def add_asset(self, filename: str, content: bytes, media_type: str):
        if not filename or len(filename) > 255 or Path(filename).name != filename or "/" in filename or "\\\\" in filename:
            raise MediaStudioError("Invalid media filename.")
        if not content or len(content) > MAX_UPLOAD_BYTES:
            raise MediaStudioError("Media upload is empty or exceeds the configured size limit.")
        ext = Path(filename).suffix.lower()
        groups = {"video": VIDEO_EXTENSIONS, "audio": AUDIO_EXTENSIONS, "image": IMAGE_EXTENSIONS}
        if media_type not in groups or ext not in groups[media_type]:
            raise MediaStudioError("File extension does not match a supported media category.")
        asset_id = uuid.uuid4().hex
        stored_name = asset_id + ext
        target = self.media_root / stored_name
        target.write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        now = utcnow()
        with self._connect() as db:
            db.execute(
                """INSERT INTO media_assets VALUES(?,?,?,?,?,?,?,?)""",
                (asset_id, filename, stored_name, media_type, ext, len(content), digest, now),
            )
        return self.get_asset(asset_id)

    def get_asset(self, asset_id):
        with self._connect() as db:
            return self._asset(db.execute("SELECT * FROM media_assets WHERE id=?", (asset_id,)).fetchone())

    def list_assets(self, limit=50):
        with self._connect() as db:
            rows = db.execute("SELECT * FROM media_assets ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [self._asset(row) for row in rows]

    def create_job(self, title, mode, source_asset_id, request):
        if mode not in {"extract", "reconstruct", "enhance", "transcode", "audio_restore", "image_rebuild"}:
            raise MediaStudioError("Unsupported Reality Studio workflow.")
        asset = self.get_asset(source_asset_id)
        if not asset:
            raise MediaStudioError("Source media asset was not found.")
        if len(title.strip()) < 3:
            raise MediaStudioError("A descriptive job title is required.")
        output = self._output_spec(asset["media_type"], request)
        safety = {
            "consent_confirmed": bool(request.get("rights_confirmed")),
            "voice_identity_authorized": bool(request.get("voice_authorized")),
            "synthetic_media_disclosure": True,
            "provenance_required": True,
            "human_review_required": True,
        }
        if mode in {"reconstruct", "audio_restore", "image_rebuild"} and not safety["consent_confirmed"]:
            raise MediaStudioError("Confirm that you own or are authorized to process the source media.")
        if request.get("voice_cloning") and not safety["voice_identity_authorized"]:
            raise MediaStudioError("Voice cloning requires explicit authorization for the speaker's voice.")
        job_id = uuid.uuid4().hex
        now = utcnow()
        with self._connect() as db:
            db.execute(
                """INSERT INTO media_jobs VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (job_id, title.strip(), mode, source_asset_id, "planned",
                 json.dumps(request, ensure_ascii=False), json.dumps(output),
                 json.dumps(safety), now, now),
            )
        return self.get_job(job_id)

    @staticmethod
    def _output_spec(media_type, request):
        if media_type == "video":
            width, height = int(request.get("width", 3840)), int(request.get("height", 2160))
            if (width, height) not in {(3840, 2160), (1920, 1080), (1280, 720)}:
                raise MediaStudioError("Video output must be 3840x2160 (4K UHD), 1920x1080 or 1280x720.")
            fps = int(request.get("fps", 30))
            if fps not in {24, 25, 30, 50, 60}:
                raise MediaStudioError("Frame rate must be 24, 25, 30, 50 or 60 fps.")
            return {"media_type": "video", "width": width, "height": height, "resolution_label": "4K UHD" if width == 3840 else "HD", "fps": fps, "container": "mp4", "video_codec": "H.265", "audio_codec": "AAC", "quality": "high"}
        if media_type == "image":
            return {"media_type": "image", "width": 3840, "height": 2160, "resolution_label": "4K UHD", "format": "PNG", "color_profile": "sRGB"}
        sample_rate = int(request.get("sample_rate_hz", 48000))
        if sample_rate not in {48000, 96000}:
            raise MediaStudioError("Audio sample rate must be 48000 or 96000 Hz.")
        return {"media_type": "audio", "sample_rate_hz": sample_rate, "bit_depth": 24, "format": "WAV", "lossless": True}

    def get_job(self, job_id):
        with self._connect() as db:
            return self._job(db.execute("SELECT * FROM media_jobs WHERE id=?", (job_id,)).fetchone())

    def list_jobs(self, limit=50):
        with self._connect() as db:
            rows = db.execute("SELECT * FROM media_jobs ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
            return [self._job(row) for row in rows]


def engine_status():
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    return {
        "ffmpeg": {"available": bool(ffmpeg), "path": ffmpeg, "purpose": "deterministic media conversion, audio extraction and 4K encoding"},
        "ffprobe": {"available": bool(ffprobe), "path": ffprobe, "purpose": "media metadata and stream inspection"},
        "ai_video_reconstruction": {"available": bool(os.getenv("JPAI_VIDEO_ENGINE_URL")), "provider_configured": bool(os.getenv("JPAI_VIDEO_ENGINE_URL")), "purpose": "scene-aware generative video reconstruction"},
        "ai_image_reconstruction": {"available": bool(os.getenv("JPAI_IMAGE_ENGINE_URL")), "provider_configured": bool(os.getenv("JPAI_IMAGE_ENGINE_URL")), "purpose": "generative image/frame reconstruction and super-resolution"},
        "ai_audio_reconstruction": {"available": bool(os.getenv("JPAI_AUDIO_ENGINE_URL")), "provider_configured": bool(os.getenv("JPAI_AUDIO_ENGINE_URL")), "purpose": "speech restoration, separation and synthesis"},
        "status_note": "AI reconstruction requires a compatible, separately configured media engine. FFmpeg availability alone does not provide generative reconstruction.",
    }
