package com.errorox.geohunter

import android.content.ContentResolver
import android.net.Uri
import androidx.exifinterface.media.ExifInterface
import java.io.IOException
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

data class ImageMetadata(
    val fileName: String,
    val mimeType: String,
    val fileSize: Long,
    val width: Int?,
    val height: Int?,
    val cameraMake: String?,
    val cameraModel: String?,
    val dateTime: String?,
    val software: String?,
    val iso: String?,
    val exposureTime: String?,
    val aperture: String?,
    val focalLength: String?,
    val orientation: String?,
    val latitude: Double?,
    val longitude: Double?,
    val gpsAltitude: String?
)

object ImageMetadataReader {
    @Throws(IOException::class)
    fun read(contentResolver: ContentResolver, uri: Uri): ImageMetadata {
        val name = queryDisplayName(contentResolver, uri) ?: "image"
        val mime = contentResolver.getType(uri) ?: "image/unknown"
        val size = querySize(contentResolver, uri)

        val exif = contentResolver.openInputStream(uri)?.use { input ->
            ExifInterface(input)
        } ?: throw IOException("Не удалось открыть изображение")

        val latLong = FloatArray(2)
        val hasGps = exif.getLatLong(latLong)

        return ImageMetadata(
            fileName = name,
            mimeType = mime,
            fileSize = size,
            width = exif.getAttributeInt(ExifInterface.TAG_IMAGE_WIDTH, -1).takeIf { it > 0 },
            height = exif.getAttributeInt(ExifInterface.TAG_IMAGE_LENGTH, -1).takeIf { it > 0 },
            cameraMake = exif.getAttribute(ExifInterface.TAG_MAKE),
            cameraModel = exif.getAttribute(ExifInterface.TAG_MODEL),
            dateTime = exif.getAttribute(ExifInterface.TAG_DATETIME_ORIGINAL)
                ?: exif.getAttribute(ExifInterface.TAG_DATETIME),
            software = exif.getAttribute(ExifInterface.TAG_SOFTWARE),
            iso = exif.getAttribute(ExifInterface.TAG_PHOTOGRAPHIC_SENSITIVITY)
                ?: exif.getAttribute(ExifInterface.TAG_ISO_SPEED_RATINGS),
            exposureTime = exif.getAttribute(ExifInterface.TAG_EXPOSURE_TIME),
            aperture = exif.getAttribute(ExifInterface.TAG_F_NUMBER),
            focalLength = exif.getAttribute(ExifInterface.TAG_FOCAL_LENGTH),
            orientation = exif.getAttribute(ExifInterface.TAG_ORIENTATION),
            latitude = if (hasGps) latLong[0].toDouble() else null,
            longitude = if (hasGps) latLong[1].toDouble() else null,
            gpsAltitude = exif.getAttribute(ExifInterface.TAG_GPS_ALTITUDE)
        )
    }

    private fun queryDisplayName(resolver: ContentResolver, uri: Uri): String? {
        val cursor = resolver.query(uri, arrayOf(android.provider.OpenableColumns.DISPLAY_NAME), null, null, null)
        return cursor?.use {
            if (it.moveToFirst()) it.getString(0) else null
        }
    }

    private fun querySize(resolver: ContentResolver, uri: Uri): Long {
        val cursor = resolver.query(uri, arrayOf(android.provider.OpenableColumns.SIZE), null, null, null)
        return cursor?.use {
            if (it.moveToFirst()) it.getLong(0) else 0L
        } ?: 0L
    }

    fun formatBytes(bytes: Long): String = when {
        bytes >= 1024L * 1024L -> String.format(Locale.US, "%.2f MB", bytes / (1024.0 * 1024.0))
        bytes >= 1024L -> String.format(Locale.US, "%.1f KB", bytes / 1024.0)
        else -> "$bytes B"
    }

    fun formatCoordinate(value: Double?): String =
        value?.let { String.format(Locale.US, "%.6f", it) } ?: "Нет данных"
}
