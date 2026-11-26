package com.errorox.geohunter

import android.content.ContentResolver
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import com.google.android.gms.tasks.Tasks
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.face.FaceDetection
import com.google.mlkit.vision.face.FaceDetectorOptions
import java.io.IOException
import kotlin.math.atan2
import kotlin.math.max
import kotlin.math.roundToInt

data class FaceFinding(
    val left: Int,
    val top: Int,
    val width: Int,
    val height: Int,
    val smilingProbability: Float?,
    val leftEyeOpenProbability: Float?,
    val rightEyeOpenProbability: Float?,
    val trackingId: Int?
)

data class SceneLightInspection(
    val shadowMask: Bitmap,
    val shadowAreaPercent: Float,
    val brightAreaPercent: Float,
    val contrastPercent: Float,
    val imagePlaneLightAngleDegrees: Int?
)

data class ImageSceneInspection(
    val faces: List<FaceFinding>,
    val imageWidth: Int,
    val imageHeight: Int,
    val light: SceneLightInspection
)

object ImageSceneAnalyzer {
    private const val MAX_SIDE = 1200
    private const val MAX_FACES = 30

    @Throws(IOException::class)
    fun analyze(resolver: ContentResolver, uri: Uri): ImageSceneInspection {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        resolver.openInputStream(uri)?.use {
            BitmapFactory.decodeStream(it, null, bounds)
        } ?: throw IOException("Не удалось открыть изображение")

        if (bounds.outWidth <= 0 || bounds.outHeight <= 0) {
            throw IOException("Формат изображения не поддерживается")
        }

        var sample = 1
        while (max(bounds.outWidth, bounds.outHeight) / sample > MAX_SIDE) sample *= 2
        val options = BitmapFactory.Options().apply { inSampleSize = sample }
        val bitmap = resolver.openInputStream(uri)?.use {
            BitmapFactory.decodeStream(it, null, options)
        } ?: throw IOException("Не удалось декодировать изображение")

        val detectorOptions = FaceDetectorOptions.Builder()
            .setPerformanceMode(FaceDetectorOptions.PERFORMANCE_MODE_ACCURATE)
            .setLandmarkMode(FaceDetectorOptions.LANDMARK_MODE_NONE)
            .setClassificationMode(FaceDetectorOptions.CLASSIFICATION_MODE_ALL)
            .setMinFaceSize(0.05f)
            .enableTracking()
            .build()
        val detector = FaceDetection.getClient(detectorOptions)

        try {
            val detected = Tasks.await(detector.process(InputImage.fromBitmap(bitmap, 0)))
            val faces = detected.take(MAX_FACES).map { face ->
                val box = face.boundingBox
                FaceFinding(
                    left = box.left.coerceAtLeast(0),
                    top = box.top.coerceAtLeast(0),
                    width = box.width(),
                    height = box.height(),
                    smilingProbability = face.smilingProbability,
                    leftEyeOpenProbability = face.leftEyeOpenProbability,
                    rightEyeOpenProbability = face.rightEyeOpenProbability,
                    trackingId = face.trackingId
                )
            }
            val light = analyzeLightAndShadows(bitmap)
            return ImageSceneInspection(faces, bitmap.width, bitmap.height, light)
        } finally {
            detector.close()
            bitmap.recycle()
        }
    }

    private fun analyzeLightAndShadows(bitmap: Bitmap): SceneLightInspection {
        val width = bitmap.width
        val height = bitmap.height
        val count = width * height
        val pixels = IntArray(count)
        bitmap.getPixels(pixels, 0, width, 0, 0, width, height)

        val luminance = IntArray(count)
        val histogram = IntArray(256)
        var total = 0L
        for (i in pixels.indices) {
            val color = pixels[i]
            val y = ((android.graphics.Color.red(color) * 299 +
                android.graphics.Color.green(color) * 587 +
                android.graphics.Color.blue(color) * 114) / 1000).coerceIn(0, 255)
            luminance[i] = y
            histogram[y]++
            total += y
        }

        val mean = total.toDouble() / count
        val lowThreshold = percentileThreshold(histogram, count, 0.25)
        val highThreshold = percentileThreshold(histogram, count, 0.75)
        val maskPixels = IntArray(count)

        var darkCount = 0
        var brightCount = 0
        var darkX = 0.0
        var darkY = 0.0
        var brightX = 0.0
        var brightY = 0.0

        for (i in luminance.indices) {
            val value = luminance[i]
            val x = i % width
            val y = i / width
            val isDark = value <= lowThreshold
            val isBright = value >= highThreshold

            if (isDark) {
                darkCount++
                darkX += x
                darkY += y
                maskPixels[i] = android.graphics.Color.WHITE
            } else {
                maskPixels[i] = android.graphics.Color.BLACK
            }
            if (isBright) {
                brightCount++
                brightX += x
                brightY += y
            }
        }

        val darkPercent = darkCount * 100f / count
        val brightPercent = brightCount * 100f / count
        val contrastPercent = (highThreshold - lowThreshold) * 100f / 255f

        val enoughRegions = darkCount > count * 0.015 && brightCount > count * 0.015
        val angle = if (enoughRegions) {
            val dx = brightX / brightCount - darkX / darkCount
            val dy = darkY / darkCount - brightY / brightCount
            ((Math.toDegrees(atan2(dy, dx)) + 360.0) % 360.0).roundToInt() % 360
        } else null

        val mask = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        mask.setPixels(maskPixels, 0, width, 0, 0, width, height)

        return SceneLightInspection(
            shadowMask = mask,
            shadowAreaPercent = darkPercent,
            brightAreaPercent = brightPercent,
            contrastPercent = contrastPercent,
            imagePlaneLightAngleDegrees = angle
        )
    }

    private fun percentileThreshold(histogram: IntArray, total: Int, percentile: Double): Int {
        val target = (total * percentile).roundToInt().coerceAtLeast(1)
        var cumulative = 0
        for (value in histogram.indices) {
            cumulative += histogram[value]
            if (cumulative >= target) return value
        }
        return 255
    }
}
