# JPAI Reality Studio — Phase 33

## Scope
Reality Studio establishes the governed media-intake and production-planning foundation for source extraction, scene reconstruction, image/frame enhancement, audio restoration and final delivery. It is integrated through `/api/v1/media-studio`.

## Output profiles
- Video defaults to 3840×2160 (4K UHD), with 24/25/30/50/60 fps and H.265/AAC MP4 delivery profile.
- Still images and reconstructed frame targets default to 3840×2160 PNG.
- Audio defaults to lossless 24-bit WAV at 48 kHz; 96 kHz is a supported target profile. Audio has sample rate/bit depth, not pixel resolution.

## Implemented in this phase
- Local media asset intake with extension/category validation, random storage identifiers, SHA-256 provenance hashes and a 20 MB upload ceiling (aligned with the current API gateway body limit; resumable large-file upload remains future work).
- Persistent SQLite media asset and job registries.
- Production job planning for extract, reconstruct, enhance, transcode, audio_restore and image_rebuild workflows.
- Explicit output specifications, source-ownership/authorization confirmation, speaker-voice authorization for voice cloning, mandatory provenance and human-review metadata.
- Engine capability reporting for FFmpeg/FFprobe and optional AI video/image/audio engine endpoints.
- Fail-closed reconstruction consent checks and strict output dimension/frame-rate validation.

## Capability boundary
This phase does **not** claim that AI video/image/audio generation is already available. FFmpeg can perform deterministic conversion, stream extraction and encoding; it cannot recreate missing scene detail, guarantee photorealism, or perform consent-aware voice synthesis by itself. Generative reconstruction is reported unavailable until a compatible provider is configured and integrated. Jobs remain `planned`; no fake completion status is emitted.

## Next implementation
Add pluggable, authenticated provider adapters; media probing and scene/shot segmentation; FFmpeg deterministic export workers; frame/image super-resolution; speech/music/effects separation; audio restoration; temporal consistency and lip-sync checks; render queue recovery; provenance manifests and review UI. Provider credentials must remain server-side.
