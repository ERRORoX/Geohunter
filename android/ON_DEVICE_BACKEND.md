# GeoHunter Android — on-device runtime plan

## Product requirement

The Android application must run all image-local analysis without a network connection. Network-dependent actions must be unavailable or clearly reported as unavailable while offline. The app must not silently upload a selected image to a remote service.

The original web interface is the visual reference. Its HTML, CSS, JavaScript, labels, layout, tool ordering, and result presentation must be reused unchanged wherever possible. Android-specific code is an adapter, not a redesign.

## Runtime architecture

- **UI:** original `static/photo/` HTML/CSS/ES modules hosted in Android WebView from packaged assets.
- **Local API:** an in-process Android HTTP API bound only to loopback (127.0.0.1). The original `fetch('/api/...')` calls remain same-origin relative to the local app server.
- **Analysis engine:** Android-native Kotlin implementations and bundled on-device ML models. The local API translates the original JSON request/response contracts to these engines.
- **Storage:** app-private persistent files and database. User-selected images are read through Android's Storage Access Framework; no broad storage permission.
- **Network adapter:** only online map tiles/styles, reverse-image search, web search, and optional external geocoding. These are isolated from local analysis and must fail gracefully offline.

The original Flask backend is not launched inside Android. Its dependencies include desktop-oriented native packages (notably OpenCV, Tesseract, libzbar, SciPy and ExifTool); installing the Python requirements unchanged into an APK is not a valid Android port. The Kotlin API adapter is the on-device backend.

## API compatibility inventory

| Original endpoint | Android implementation target | Network |
|---|---|---|
| `POST /api/exif` | EXIF reader + GPS extraction + local reverse-geocoder data when bundled | Local |
| `POST /api/exif/exiftool/json` | Extended EXIF tag extraction; document unsupported ExifTool-only tags explicitly | Local |
| `POST /api/exif/strip` | Metadata removal by decoding and re-encoding image | Local |
| `POST /api/forensics/ela` | Port original Pillow recompression/difference parameters and response schema | Local |
| `POST /api/forensics/noise` | Port original noise algorithm and response schema | Local |
| `POST /api/forensics/stego` | Port original RGB LSB, entropy, chi-square and preview logic | Local |
| `POST /api/forensics/faces` | On-device face detector; validate output and image-coordinate semantics against original | Local |
| `POST /api/forensics/shadow-solve` | Port solar-elevation/latitude search and GeoJSON output | Local |
| `GET /api/forensics/sun` | Port solar azimuth/elevation calculation | Local |
| `POST /api/ocr` | Bundled offline OCR models; Russian and English language coverage required | Local |
| `POST /api/qr-barcode` | Bundled barcode/QR decoder with original result fields | Local |
| `POST /api/reverse-search` | Build provider links; actual provider search requires internet and explicit user action | Network |
| `POST /api/search` | Build search queries and provider links; opening/searching providers requires internet | Network |
| `POST /api/export-report` | Generate Markdown report from local result payload | Local |
| `POST /api/export-json` | Generate JSON export from local result payload | Local |
| `GET /api/ui/host-os` | Return Android device/platform information | Local |

## Compatibility and validation rules

1. Preserve request field names, response keys, success/error semantics, and tool identifiers used by `static/photo/js/modules/tool-runners.js`.
2. Keep all analysis on-device. No network fallback is permitted for a local endpoint.
3. Treat online map rendering and online address lookup as optional enhancements. GPS coordinates must still be displayed when offline.
4. Do not label an implementation as equivalent until its output has been compared against the original backend using a fixed image test corpus.
5. Where a library cannot be ported exactly, document the algorithmic difference and do not silently present it as an exact port.
6. Test airplane mode: image selection, EXIF, ELA, noise, LSB/steganography, face detection, OCR, QR/barcode, shadow calculations, and exports must continue to work.
7. Keep changes isolated to `android-native`; do not modify `main`.

## Current implementation status at this planning checkpoint

The Android branch contains a Compose prototype with local EXIF, ELA/noise/LSB screening, ML Kit OCR/barcode/face detection, and a heuristic shadow mask. These are not yet API-compatible replacements for all original Flask endpoints, and the current Compose UI is not visually identical to the original web UI. This plan is the acceptance contract for the migration; it is not a claim that parity has already been achieved.
