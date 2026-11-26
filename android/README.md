# GeoHunter Android

Native Android application for the GeoHunter project.

## Current milestone: 0.1.0

This first native milestone is an offline-first foundation:
- Kotlin + Jetpack Compose interface.
- Image selection through Android Storage Access Framework.
- Local EXIF metadata extraction.
- GPS latitude/longitude extraction from EXIF.
- Downsampled local image preview for large files.
- JPEG ELA recompression-difference map (quality 90).
- Local high-frequency luminance-residual map.
- Sequential RGB LSB stream inspection, printable-string extraction, byte entropy, and common embedded-file signature checks.
- On-device OCR using the bundled ML Kit Latin text-recognition model.
- QR-code and common 1D/2D barcode decoding using the bundled ML Kit barcode model.
- On-device face detection with face rectangles and optional smile/eye-open probabilities.
- A luminance percentile mask for dark and bright image regions, with a rough light-vector estimate in image coordinates.
- Bounded analysis bitmap size to reduce memory pressure.
- No Flask server, laptop, account, or network permission required for these workflows.

ELA and noise maps are visual screening aids, not proof of manipulation. ELA is only generated for JPEG input; results depend on the image's compression history. The noise map highlights local brightness variation and is not a standalone authenticity classifier.

The LSB module reads the least significant bit from each RGB channel in row-major order and inspects the resulting byte stream for printable fragments and common file signatures. It does not detect every steganography method: shuffled pixel orders, alternate bit planes, encrypted/compressed payloads, alpha-channel payloads, and JPEG-domain methods may not be found. A match or high entropy is not proof of hidden content.\n\nOCR and QR/barcode recognition use bundled ML Kit models and run on the selected image locally. The bundled OCR model is for the Latin script; Cyrillic (including Russian) may not be recognized reliably. The app does not automatically open decoded links or execute decoded content. OCR is fallible and should be checked against the source image. The OCR/barcode analyzer limits the working image to 1600 pixels on its longest side and returns at most 12,000 text characters and 30 distinct codes. Face and luminance analysis use a separate image copy capped at 1200 pixels on its longest side. Face detection only locates faces in the image; it does not identify people. Smile and eye-open values are model estimates, not reliable biometric conclusions. The dark-region map is a simple brightness heuristic, not semantic shadow segmentation. Its light vector is measured in image coordinates and must not be treated as a geographic sun azimuth.

## Open in Android Studio

1. Open the `android/` directory as a project in Android Studio.
2. Use JDK 17 and Gradle 8.10.2.
3. Allow Gradle to sync and download Android dependencies.
4. Build and run the `app` configuration on an Android 8.0 (API 26) or newer device.

This initial repository scaffold does not include the Gradle wrapper JAR. If Android Studio asks for a local Gradle distribution, select Gradle 8.10.2. Alternatively, with Gradle 8.10.2 installed, run from this directory:

```bash
gradle wrapper --gradle-version 8.10.2
./gradlew assembleDebug
```

The APK is generated at `app/build/outputs/apk/debug/app-debug.apk`.

The project uses Android Gradle Plugin 8.8.2, Kotlin 2.0.21, and compile SDK 35.

## Privacy

The app does not request broad storage permissions. The user selects an image through the system document picker, and the app reads that selected URI. EXIF parsing, JPEG recompression, noise analysis, OCR, barcode decoding, face detection, and luminance analysis are performed locally. GPS coordinates can be sensitive, so avoid sharing screenshots or exported reports containing them.

## Planned native ports

- Geometry-aware shadow interpretation using scene geometry and camera orientation.
- Sun-position estimation only when reliable capture time, GPS, and camera-orientation metadata are available.
- Offline map support and local case/report storage.

Advanced modules will be ported and validated individually against the existing GeoHunter implementation before being marked as available.
