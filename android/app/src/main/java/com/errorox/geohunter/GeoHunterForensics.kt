package com.errorox.geohunter

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.util.Base64
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.util.Locale
import kotlin.math.abs
import kotlin.math.ln
import kotlin.math.max
import kotlin.math.min

/** Android port of backend/tools/tool_photo_forensics.py, tool_photo_noise.py and tool_photo_stego.py. */
object GeoHunterForensics {
    private const val MAX_SIDE = 1600

    private fun decode(bytes: ByteArray): Bitmap {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeByteArray(bytes, 0, bytes.size, bounds)
        require(bounds.outWidth > 0 && bounds.outHeight > 0) { "Формат изображения не поддерживается." }
        var sample = 1
        while (max(bounds.outWidth, bounds.outHeight) / sample > MAX_SIDE) sample *= 2
        return BitmapFactory.decodeByteArray(bytes, 0, bytes.size, BitmapFactory.Options().apply {
            inSampleSize = sample
            inPreferredConfig = Bitmap.Config.ARGB_8888
        }) ?: throw IOException("Не удалось декодировать изображение.")
    }

    private fun pngData(bitmap: Bitmap): String {
        val out = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.PNG, 100, out)
        return "data:image/png;base64," + Base64.encodeToString(out.toByteArray(), Base64.NO_WRAP)
    }

    fun ela(bytes: ByteArray, quality: Int = 90, scale: Double = 20.0): JSONObject {
        require(quality in 1..100) { "Качество JPEG должно быть от 1 до 100." }
        require(scale in 0.1..100.0) { "Масштаб ELA должен быть от 0.1 до 100." }
        val source = decode(bytes).let { if (it.config != Bitmap.Config.ARGB_8888) it.copy(Bitmap.Config.ARGB_8888, false) else it }
        val compressedBytes = ByteArrayOutputStream().also {
            source.compress(Bitmap.CompressFormat.JPEG, quality, it)
        }.toByteArray()
        val compressed = BitmapFactory.decodeByteArray(compressedBytes, 0, compressedBytes.size)
            ?: throw IOException("Не удалось повторно сжать изображение.")
        val w = source.width
        val h = source.height
        val a = IntArray(w * h)
        val b = IntArray(w * h)
        source.getPixels(a, 0, w, 0, 0, w, h)
        compressed.getPixels(b, 0, w, 0, 0, w, h)
        val output = IntArray(a.size)
        for (i in a.indices) {
            val r = (abs(Color.red(a[i]) - Color.red(b[i])) * scale).toInt().coerceIn(0, 255)
            val g = (abs(Color.green(a[i]) - Color.green(b[i])) * scale).toInt().coerceIn(0, 255)
            val bl = (abs(Color.blue(a[i]) - Color.blue(b[i])) * scale).toInt().coerceIn(0, 255)
            output[i] = Color.rgb(r, g, bl)
        }
        val result = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        result.setPixels(output, 0, w, 0, 0, w, h)
        val data = pngData(result)
        source.recycle(); compressed.recycle(); result.recycle()
        return JSONObject()
            .put("success", true)
            .put("ela_image", data)
            .put("quality", quality)
            .put("scale", scale)
            .put("note", "Области с ярким цветом или сильным шумом могут указывать на вставки или ретушь.")
    }

    // scipy.ndimage.uniform_filter(size=5, default reflect mode), followed by
    // PIL ImageEnhance.Contrast(factor=3.0).
    fun noise(bytes: ByteArray): JSONObject {
        val source = decode(bytes)
        val w = source.width
        val h = source.height
        val pixels = IntArray(w * h)
        source.getPixels(pixels, 0, w, 0, 0, w, h)
        val lum = IntArray(pixels.size) { i ->
            val c = pixels[i]
            (Color.red(c) * 299 + Color.green(c) * 587 + Color.blue(c) * 114) / 1000
        }
        val padW = w + 4
        val padH = h + 4
        val stride = padW + 1
        val sum = DoubleArray((padW + 1) * (padH + 1))
        val sumSq = DoubleArray(sum.size)
        fun reflect(p: Int, n: Int): Int {
            if (n <= 1) return 0
            var v = p
            while (v < 0 || v >= n) v = if (v < 0) -v - 1 else 2 * n - v - 1
            return v
        }
        for (py in 0 until padH) {
            var row = 0.0
            var rowSq = 0.0
            val sy = reflect(py - 2, h)
            for (px in 0 until padW) {
                val sx = reflect(px - 2, w)
                val v = lum[sy * w + sx].toDouble()
                row += v; rowSq += v * v
                val idx = (py + 1) * stride + px + 1
                sum[idx] = sum[py * stride + px + 1] + row
                sumSq[idx] = sumSq[py * stride + px + 1] + rowSq
            }
        }
        val variance = IntArray(w * h)
        for (y in 0 until h) for (x in 0 until w) {
            val xA = x; val xB = x + 5; val yA = y; val yB = y + 5
            val iA = yA * stride + xA; val iB = yA * stride + xB
            val iC = yB * stride + xA; val iD = yB * stride + xB
            val s = sum[iD] - sum[iB] - sum[iC] + sum[iA]
            val q = sumSq[iD] - sumSq[iB] - sumSq[iC] + sumSq[iA]
            variance[y * w + x] = (q / 25.0 - (s / 25.0) * (s / 25.0)).coerceIn(0.0, 255.0).toInt()
        }
        val mean = variance.average()
        val outPixels = IntArray(variance.size) { i ->
            val v = ((variance[i] - mean) * 3.0 + mean).toInt().coerceIn(0, 255)
            total += v
            Color.rgb(v, v, v)
        }
        val result = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        result.setPixels(outPixels, 0, w, 0, 0, w, h)
        val data = pngData(result)
        source.recycle(); result.recycle()
        return JSONObject()
            .put("success", true)
            .put("noise_image", data)
            .put("note", "Однородные области на этой карте шума указывают на возможную ретушь или использование инструментов типа 'Кисть' и 'Штамп'.")
    }

    private fun chiSquare(channel: IntArray): Double {
        if (channel.size < 256) return 0.0
        val hist = IntArray(256)
        channel.forEach { hist[it and 255]++ }
        var score = 0.0
        for (k in 0 until 256 step 2) {
            val h0 = hist[k].toDouble()
            val h1 = hist[k + 1].toDouble()
            if (h0 + h1 < 16.0) continue
            val expected = (h0 + h1) / 2.0
            if (expected > 0) score += ((h0 - expected) * (h0 - expected) + (h1 - expected) * (h1 - expected)) / expected
        }
        return score / 128.0
    }

    private fun entropy(ones: Double): Double {
        val p0 = 1.0 - ones
        var value = 0.0
        for (p in doubleArrayOf(p0, ones)) if (p > 0.0 && p < 1.0) value -= p * (ln(p) / ln(2.0))
        return value
    }

    fun stego(bytes: ByteArray): JSONObject {
        val source = decode(bytes)
        val w = source.width
        val h = source.height
        val pixels = IntArray(w * h)
        source.getPixels(pixels, 0, w, 0, 0, w, h)
        val red = IntArray(pixels.size) { Color.red(pixels[it]) }
        val green = IntArray(pixels.size) { Color.green(pixels[it]) }
        val blue = IntArray(pixels.size) { Color.blue(pixels[it]) }
        val vis = IntArray(pixels.size) { i ->
            Color.rgb((red[i] and 1) * 255, (green[i] and 1) * 255, (blue[i] and 1) * 255)
        }
        val bitCount = pixels.size.toLong() * 3L
        val ones = (red.sumOf { it and 1 } + green.sumOf { it and 1 } + blue.sumOf { it and 1 }).toDouble()
        val ratio = if (bitCount == 0L) 0.0 else ones / bitCount
        val ent = entropy(ratio)
        val chi = (chiSquare(red) + chiSquare(green) + chiSquare(blue)) / 3.0
        val totalBits = bitCount.coerceAtMost(512L * 8L).toInt()
        val previewBits = ByteArray(totalBits)
        var p = 0
        for (channel in arrayOf(red, green, blue)) {
            for (v in channel) {
                if (p >= totalBits) break
                previewBits[p++] = (v and 1).toByte()
            }
            if (p >= totalBits) break
        }
        val raw = ByteArray(p / 8)
        for (i in raw.indices) {
            var value = 0
            for (bit in 0..7) value = (value shl 1) or previewBits[i * 8 + bit].toInt()
            raw[i] = value.toByte()
        }
        val decoded = raw.toString(Charsets.UTF_8)
        val cleaned = decoded.replace(Regex("[^\\x20-\\x7E\\u0400-\\u04FF\\n\\r\\t]"), ".").trim()
        val preview = cleaned.takeIf { it.length >= 4 }?.take(400)
        val suspicious = chi > 1.0 || ent > 0.99 || abs(ratio - 0.5) > 0.08
        val verdict = when {
            !preview.isNullOrEmpty() -> "Возможны скрытые данные (читаемый фрагмент в LSB)"
            suspicious -> "Подозрительная статистика LSB — стоит проверить вручную"
            else -> "Явных признаков LSB-встраивания не обнаружено"
        }
        val image = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        image.setPixels(vis, 0, w, 0, 0, w, h)
        val data = pngData(image)
        source.recycle(); image.recycle()
        return JSONObject()
            .put("success", true)
            .put("lsb_image", data)
            .put("lsb_entropy", String.format(Locale.US, "%.4f", ent).toDouble())
            .put("lsb_ones_ratio", String.format(Locale.US, "%.4f", ratio).toDouble())
            .put("chi_square_score", String.format(Locale.US, "%.3f", chi).toDouble())
            .put("verdict", verdict)
            .put("hidden_text_preview", preview ?: JSONObject.NULL)
            .put("note", "LSB-плоскость: белый = бит 1. Эвристики, не расшифровка стойкого стего.")
    }
}
