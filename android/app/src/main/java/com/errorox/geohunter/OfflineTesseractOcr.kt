package com.errorox.geohunter

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import com.googlecode.tesseract.android.TessBaseAPI
import java.io.File
import java.io.IOException
import kotlin.math.max

data class OfflineOcrResult(
    val text: String,
    val language: String,
    val width: Int,
    val height: Int
)

object OfflineTesseractOcr {
    private const val MAX_SIDE = 2000
    private val lock = Any()

    @Throws(IOException::class)
    fun recognize(context: Context, uri: Uri, requestedLanguage: String): OfflineOcrResult =
        synchronized(lock) {
            val language = normalizeLanguage(requestedLanguage)
            val dataDir = File(context.filesDir, "geohunter-tesseract")
            val tessdataDir = File(dataDir, "tessdata")
            if (!tessdataDir.exists() && !tessdataDir.mkdirs()) {
                throw IOException("Не удалось создать каталог языковых моделей OCR.")
            }

            for (code in language.split("+")) {
                val target = File(tessdataDir, "$code.traineddata")
                if (!target.isFile || target.length() == 0L) {
                    try {
                        context.assets.open("tessdata/$code.traineddata").use { input ->
                            target.outputStream().use { output -> input.copyTo(output) }
                        }
                    } catch (e: Exception) {
                        throw IOException("Не найдена встроенная модель OCR: $code", e)
                    }
                }
            }

            val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            context.contentResolver.openInputStream(uri)?.use {
                BitmapFactory.decodeStream(it, null, bounds)
            } ?: throw IOException("Не удалось открыть изображение для OCR.")
            if (bounds.outWidth <= 0 || bounds.outHeight <= 0) {
                throw IOException("Формат изображения не поддерживается.")
            }

            var sample = 1
            while (max(bounds.outWidth, bounds.outHeight) / sample > MAX_SIDE) sample *= 2
            val options = BitmapFactory.Options().apply { inSampleSize = sample }
            val bitmap = context.contentResolver.openInputStream(uri)?.use {
                BitmapFactory.decodeStream(it, null, options)
            } ?: throw IOException("Не удалось декодировать изображение для OCR.")

            val tess = TessBaseAPI()
            try {
                if (!tess.init(dataDir.absolutePath, language)) {
                    throw IOException("Tesseract не смог загрузить языковые модели: $language")
                }
                tess.setImage(bitmap)
                val text = (tess.getUTF8Text() ?: "").replace("\r\n", "\n")
                    .lines().map { it.trim() }.filter { it.length >= 2 }.joinToString("\n")
                    .take(12000)
                OfflineOcrResult(text, language, bitmap.width, bitmap.height)
            } finally {
                tess.recycle()
                bitmap.recycle()
            }
        }

    private fun normalizeLanguage(value: String): String {
        val normalized = value.lowercase().replace(" ", "")
        return when (normalized) {
            "rus" -> "rus"
            "eng" -> "eng"
            "eng+rus", "rus+eng" -> "rus+eng"
            else -> "rus+eng"
        }
    }
}
