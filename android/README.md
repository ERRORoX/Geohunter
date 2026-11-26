# GeoHunter Android

Native Android application for the GeoHunter project.

## Current milestone: 0.1.0

This first native milestone is an offline-first foundation:
- Kotlin + Jetpack Compose interface.
- Image selection through Android Storage Access Framework.
- Local EXIF metadata extraction.
- GPS latitude/longitude extraction from EXIF.
- Local image preview.
- No Flask server, laptop, account, or network permission required for this workflow.

The remaining GeoHunter analysis modules are listed in the UI as planned work. They are not represented as implemented yet.

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

The app does not request broad storage permissions. The user selects an image through the system document picker, and the app reads that selected URI. EXIF parsing is performed locally. GPS coordinates can be sensitive, so avoid sharing screenshots or exported reports containing them.

## Planned native ports

- ELA and image-noise analysis.
- LSB inspection.
- OCR and QR/barcode decoding.
- Shadow and sun-position analysis.
- Face detection.
- Offline map support and local case/report storage.

Advanced modules will be ported and validated individually against the existing GeoHunter implementation before being marked as available.
