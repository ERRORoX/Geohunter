package com.errorox.geohunter

import android.content.ContentResolver
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import com.google.android.gms.tasks.Tasks
import com.google.mlkit.vision.barcode.Barcode
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import java.io.IOException
import kotlin.math.max

data class DetectedCode(
    val format: String,
    val value: String
)

data class TextCodeInspection(
    val recognizedText: String,
    val codes: List<DetectedCode>,
    val sampledWidth: Int,
    val sampledHeight: Int
)

object ImageTextCodeAnalyzer {
    private const val MAX_SIDE = 1600
    private const val MAX_TEXT_CHARS = 12000
    private const val MAX_CODES = 30

    /**
     * Runs bundled ML Kit models locally. No image is uploaded and no model
     * download is needed at analysis time.
     */
    @Throws(IOException::class)
    fun analyze(resolver: ContentResolver, uri: Uri): TextCodeInspection {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        resolver.openInputStream(uri)?.use {
            BitmapFactory.decodeStream(it, null, bounds)
        } ?: throw IOException("Не удалось открыть изображение")

        if (bounds.outWidth <= 0 || bounds.outHeight <= 0) {
            throw IOException("Формат изображения не поддерживается")
        }

        var sample = 1
        while (max(bounds.outWidth, bounds.outHeight) / sample > MAX_SIDE) {
            sample *= 2
        }

        val options = BitmapFactory.Options().apply { inSampleSize = sample }
        val bitmap = resolver.openInputStream(uri)?.use {
            BitmapFactory.decodeStream(it, null, options)
        } ?: throw IOException("Не удалось декодировать изображение")

        val input = InputImage.fromBitmap(bitmap, 0)
        val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
        val scannerOptions = BarcodeScannerOptions.Builder()
            .setBarcodeFormats(Barcode.FORMAT_ALL_FORMATS)
            .build()
        val scanner = BarcodeScanning.getClient(scannerOptions)

        try {
            val text = Tasks.await(recognizer.process(input))
                .text
                .take(MAX_TEXT_CHARS)

            val codes = Tasks.await(scanner.process(input))
                .mapNotNull { barcode ->
                    val value = barcode.rawValue ?: barcode.displayValue
                    if (value.isNullOrBlank()) null
                    else DetectedCode(formatName(barcode.format), value.take(2000))
                }
                .distinctBy { it.format + "|" + it.value }
                .take(MAX_CODES)

            return TextCodeInspection(
                recognizedText = text,
                codes = codes,
                sampledWidth = bitmap.width,
                sampledHeight = bitmap.height
            )
        } finally {
            recognizer.close()
            scanner.close()
            bitmap.recycle()
        }
    }

    private fun formatName(format: Int): String = when (format) {
        Barcode.FORMAT_QR_CODE -> "QR Code"
        Barcode.FORMAT_AZTEC -> "Aztec"
        Barcode.FORMAT_CODABAR -> "Codabar"
        Barcode.FORMAT_CODE_39 -> "Code 39"
        Barcode.FORMAT_CODE_93 -> "Code 93"
        Barcode.FORMAT_CODE_128 -> "Code 128"
        Barcode.FORMAT_DATA_MATRIX -> "Data Matrix"
        Barcode.FORMAT_EAN_8 -> "EAN-8"
        Barcode.FORMAT_EAN_13 -> "EAN-13"
        Barcode.FORMAT_ITF -> "ITF"
        Barcode.FORMAT_PDF417 -> "PDF417"
        Barcode.FORMAT_UPC_A -> "UPC-A"
        Barcode.FORMAT_UPC_E -> "UPC-E"
        else -> "Другой формат"
    }
}
