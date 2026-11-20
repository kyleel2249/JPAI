import pytest

from jpai_api.intelligence.media_studio import MediaStudioError, MediaStudioStore


def test_media_upload_is_hashed_and_filename_is_sanitized(tmp_path):
    store = MediaStudioStore(tmp_path / "db.sqlite3", tmp_path / "media")
    asset = store.add_asset("source.mp4", b"video-bytes", "video")
    assert asset["sha256"]
    assert asset["size_bytes"] == 11
    with pytest.raises(MediaStudioError, match="filename"):
        store.add_asset("../escape.mp4", b"x", "video")


def test_video_job_defaults_to_4k_uhd_and_preserves_provenance(tmp_path):
    store = MediaStudioStore(tmp_path / "db.sqlite3", tmp_path / "media")
    asset = store.add_asset("source.mp4", b"video", "video")
    job = store.create_job("Rebuild film sequence", "reconstruct", asset["id"], {
        "rights_confirmed": True, "fps": 24,
    })
    assert job["output_spec"]["width"] == 3840
    assert job["output_spec"]["height"] == 2160
    assert job["output_spec"]["resolution_label"] == "4K UHD"
    assert job["safety"]["provenance_required"] is True
    assert job["status"] == "planned"


def test_reconstruction_requires_rights_and_voice_authorization(tmp_path):
    store = MediaStudioStore(tmp_path / "db.sqlite3", tmp_path / "media")
    asset = store.add_asset("voice.wav", b"audio", "audio")
    with pytest.raises(MediaStudioError, match="authorized"):
        store.create_job("Restore interview", "audio_restore", asset["id"], {})
    with pytest.raises(MediaStudioError, match="Voice cloning"):
        store.create_job("Clone speaker", "audio_restore", asset["id"], {
            "rights_confirmed": True, "voice_cloning": True,
        })


def test_video_output_rejects_unsupported_dimensions(tmp_path):
    store = MediaStudioStore(tmp_path / "db.sqlite3", tmp_path / "media")
    asset = store.add_asset("source.mp4", b"video", "video")
    with pytest.raises(MediaStudioError, match="Video output"):
        store.create_job("Bad export", "transcode", asset["id"], {
            "width": 2560, "height": 1440,
        })


def test_audio_uses_lossless_sample_rate_profile(tmp_path):
    store = MediaStudioStore(tmp_path / "db.sqlite3", tmp_path / "media")
    asset = store.add_asset("source.wav", b"audio", "audio")
    job = store.create_job("Restore audio", "audio_restore", asset["id"], {"rights_confirmed": True})
    assert job["output_spec"]["format"] == "WAV"
    assert job["output_spec"]["lossless"] is True
    assert job["output_spec"]["sample_rate_hz"] == 48000
