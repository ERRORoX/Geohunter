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

data class LsbInspection(
    val bitOnePercent: Double,
    val byteEntropy: Double,
    val extractedBytes: Int,
    val detectedSignatures: List<String>,
    val printableStrings: List<String>
)

data class ForensicResult(
    val elaBitmap: Bitmap?,
    val noiseBitmap: Bitmap,
    val lsbInspection: LsbInspection,
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
        while (max(bounds.outWidth, bounds.outHeight) / sample > MAX_SIDE) sample *= 2
        val options = BitmapFactory.Options().apply { inSampleSize = sample }
        val original = resolver.openInputStream(uri)?.use {
            BitmapFactory.decodeStream(it, null, options)
        } ?: throw IOException("Не удалось декодировать изображение")

        val jpeg = (mimeType == "image/jpeg" || mimeType == "image/jpg" ||
            uri.toString().substringBefore('?').lowercase().endsWith(".jpg") ||
            uri.toString().substringBefore('?').lowercase().endsWith(".jpeg"))

        val ela = if (jpeg) createEla(original) else null
        val noise = createNoiseMap(original)
        val lsb = inspectLsb(original)
        val result = ForensicResult(
            elaBitmap = ela?.first,
            noiseBitmap = noise.first,
            lsbInspection = lsb,
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

    /**
     * Reads the least significant bit of each RGB channel in row-major order.
     * This is a basic sequential LSB probe, not a universal steganography detector.
     */
    private fun inspectLsb(source: Bitmap): LsbInspection {
        val pixels = IntArray(source.width * source.height)
        source.getPixels(pixels, 0, source.width, 0, 0, source.width, source.height)

        val bitCount = pixels.size * 3
        val bytes = ByteArray((bitCount + 7) / 8)
        var ones = 0
        var bitIndex = 0

        for (pixel in pixels) {
            val redBit = (pixel shr 16) and 1
            val greenBit = (pixel shr 8) and 1
            val blueBit = pixel and 1
            if (redBit == 1) ones++
            bytes[bitIndex / 8] = (bytes[bitIndex / 8].toInt() or (redBit shl (7 - bitIndex % 8))).toByte()
            bitIndex++
            if (greenBit == 1) ones++
            bytes[bitIndex / 8] = (bytes[bitIndex / 8].toInt() or (greenBit shl (7 - bitIndex % 8))).toByte()
            bitIndex++
            if (blueBit == 1) ones++
            bytes[bitIndex / 8] = (bytes[bitIndex / 8].toInt() or (blueBit shl (7 - bitIndex % 8))).toByte()
            bitIndex++
        }

        val frequencies = IntArray(256)
        for (value in bytes) frequencies[value.toInt() and 255]++
        var entropy = 0.0
        if (bytes.isNotEmpty()) {
            for (frequency in frequencies) {
                if (frequency > 0) {
                    val probability = frequency.toDouble() / bytes.size
                    entropy -= probability * (kotlin.math.ln(probability) / kotlin.math.ln(2.0))
                }
            }
        }

        val signatures = mutableListOf<String>()
        val signaturesToCheck = listOf(
            byteArrayOf(0x50, 0x4B, 0x03, 0x04) to "ZIP",
            byteArrayOf(0x25, 0x50, 0x44, 0x46) to "PDF",
            byteArrayOf(0x89.toByte(), 0x50, 0x4E, 0x47) to "PNG",
            byteArrayOf(0x47, 0x49, 0x46, 0x38) to "GIF",
            byteArrayOf(0x1F, 0x8B.toByte(), 0x08) to "GZIP",
            byteArrayOf(0x52, 0x61, 0x72, 0x21) to "RAR",
            byteArrayOf(0x37, 0x7A, 0xBC.toByte(), 0xAF.toByte()) to "7-Zip"
        )
        for ((signature, name) in signaturesToCheck) {
            val limit = min(bytes.size - signature.size, 65536)
            for (offset in 0..limit) {
                var match = true
                for (i in signature.indices) {
                    if (bytes[offset + i] != signature[i]) {
                        match = false
                        break
                    }
                }
                if (match) {
                    signatures.add("$name: сигнатура найдена со смещением $offset байт")
                    break
                }
            }
        }

        val strings = mutableListOf<String>()
        val current = StringBuilder()
        for (value in bytes.take(262144)) {
            val ch = value.toInt() and 255
            if (ch in 32..126 || ch in 192..255) {
                current.append(ch.toChar())
            } else {
                if (current.length >= 6 && strings.size < 12) strings.add(current.toString())
                current.setLength(0)
            }
            if (strings.size >= 12) break
        }
        if (current.length >= 6 && strings.size < 12) strings.add(current.toString())

        return LsbInspection(
            bitOnePercent = if (bitCount == 0) 0.0 else ones * 100.0 / bitCount,
            byteEntropy = entropy,
            extractedBytes = bytes.size,
            detectedSignatures = signatures,
            printableStrings = strings
        )
    }

    private fun luminance(color: Int): Int =
        (((color shr 16) and 255) * 299 +
            ((color shr 8) and 255) * 587 +
            (color and 255) * 114) / 1000
}
