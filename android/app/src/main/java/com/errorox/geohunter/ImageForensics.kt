package com.errorox.geohunter

import android.content.ContentResolver
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import java.io.ByteArrayOutputStream
import java.io.IOException
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

data class ForensicResult(
    val elaBitmap: Bitmap?,
    val noiseBitmap: Bitmap,
    val elaMeanDifference: Double?,
    val noiseMeanResidual: Double,
    val sourceWidth: Int,
    val sourceHeight: Int,
    val sampledWidth: Int,
    val sampledHeight: Int,
    val isJpeg: Boolean
)

object ImageForensics {
    private const val MAX_SIDE = 1100
    private const val JPEG_QUALITY = 90
    private const val ELA_SCALE = 12.0

    @Throws(IOException::class)
    fun analyze(resolver: ContentResolver, uri: Uri, mimeType: String?): ForensicResult {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        resolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, bounds) }
            ?: throw IOException("Не удалось открыть изображение")

        if (bounds.outWidth <= 0 || bounds.outHeight <= 0) {
            throw IOException("Формат изображения не поддерживается")
        }

        var sample = 1
        while (max(bounds.outWidth, bounds.outHeight) / sample > MAX_SIDE * 2) sample *= 2
        val options = BitmapFactory.Options().apply { inSampleSize = sample }
        val original = resolver.openInputStream(uri)?.use {
            BitmapFactory.decodeStream(it, null, options)
        } ?: throw IOException("Не удалось декодировать изображение")

        val jpeg = (mimeType == "image/jpeg" || mimeType == "image/jpg" ||
            uri.toString().substringBefore('?').lowercase().endsWith(".jpg") ||
            uri.toString().substringBefore('?').lowercase().endsWith(".jpeg"))

        val ela = if (jpeg) createEla(original) else null
        val noise = createNoiseMap(original)
        val result = ForensicResult(
            elaBitmap = ela?.first,
            noiseBitmap = noise.first,
            elaMeanDifference = ela?.second,
            noiseMeanResidual = noise.second,
            sourceWidth = bounds.outWidth,
            sourceHeight = bounds.outHeight,
            sampledWidth = original.width,
            sampledHeight = original.height,
            isJpeg = jpeg
        )
        original.recycle()
        return result
    }

    private fun createEla(source: Bitmap): Pair<Bitmap, Double> {
        val bytes = ByteArrayOutputStream()
        source.compress(Bitmap.CompressFormat.JPEG, JPEG_QUALITY, bytes)
        val recompressed = BitmapFactory.decodeByteArray(bytes.toByteArray(), 0, bytes.size())
            ?: throw IOException("Не удалось выполнить JPEG-пересжатие")

        val output = Bitmap.createBitmap(source.width, source.height, Bitmap.Config.ARGB_8888)
        val src = IntArray(source.width * source.height)
        val cmp = IntArray(src.size)
        source.getPixels(src, 0, source.width, 0, 0, source.width, source.height)
        recompressed.getPixels(cmp, 0, source.width, 0, 0, source.width, source.height)
        val mapped = IntArray(src.size)
        var total = 0L

        for (i in src.indices) {
            val a = src[i]
            val b = cmp[i]
            val diff = (abs(((a shr 16) and 255) - ((b shr 16) and 255)) +
                abs(((a shr 8) and 255) - ((b shr 8) and 255)) +
                abs((a and 255) - (b and 255))) / 3
            total += diff
            val level = min(255, (diff * ELA_SCALE).toInt())
            mapped[i] = android.graphics.Color.rgb(level, (level * 0.55).toInt(), 0)
        }
        output.setPixels(mapped, 0, source.width, 0, 0, source.width, source.height)
        recompressed.recycle()
        return output to (total.toDouble() / src.size)
    }

    private fun createNoiseMap(source: Bitmap): Pair<Bitmap, Double> {
        val width = source.width
        val height = source.height
        val pixels = IntArray(width * height)
        source.getPixels(pixels, 0, width, 0, 0, width, height)
        val outputPixels = IntArray(pixels.size)
        var total = 0L
        var count = 0

        for (y in 1 until height - 1) {
            for (x in 1 until width - 1) {
                val i = y * width + x
                val center = luminance(pixels[i])
                val neighbors = (luminance(pixels[i - 1]) + luminance(pixels[i + 1]) +
                    luminance(pixels[i - width]) + luminance(pixels[i + width])) / 4
                val residual = abs(center - neighbors)
                total += residual
                count++
                val intensity = min(255, residual * 5)
                outputPixels[i] = android.graphics.Color.rgb(
                    (intensity * 0.10).toInt(),
                    (intensity * 0.65).toInt(),
                    intensity
                )
            }
        }
        val output = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        output.setPixels(outputPixels, 0, width, 0, 0, width, height)
        return output to if (count == 0) 0.0 else total.toDouble() / count
    }

    private fun luminance(color: Int): Int =
        (((color shr 16) and 255) * 299 +
            ((color shr 8) and 255) * 587 +
            (color and 255) * 114) / 1000
}
