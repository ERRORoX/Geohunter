package com.errorox.geohunter

import android.content.Context
import android.net.Uri
import android.webkit.JavascriptInterface
import android.webkit.WebView
import androidx.exifinterface.media.ExifInterface
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.Locale
import java.util.concurrent.Executors

/**
 * Local JSON API adapter for the original GeoHunter frontend.
 * CPU-heavy image processing runs off the WebView thread.
 */
class GeoHunterNativeApi(
    private val context: Context,
    private val webView: WebView
) {
    private val executor = Executors.newFixedThreadPool(2)

    @JavascriptInterface
    fun postJson(path: String, body: String, callbackId: String) {
        executor.execute {
            val result = runCatching { dispatch(path, JSONObject(body)) }
                .getOrElse { JSONObject().put("success", false).put("error", it.message ?: "Ошибка локального анализа") }
            val encoded = JSONObject.quote(result.toString())
            webView.post {
                webView.evaluateJavascript(
                    "window.__geoHunterNativeResolve && window.__geoHunterNativeResolve(" +
                        JSONObject.quote(callbackId) + ", $encoded)",
                    null
                )
            }
        }
    }

    private fun dispatch(path: String, body: JSONObject): JSONObject {
        return when (path) {
            "/api/ui/host-os" -> JSONObject()
                .put("system", "Android")
                .put("release", android.os.Build.VERSION.RELEASE)
                .put("version", android.os.Build.VERSION.SDK_INT)
                .put("machine", android.os.Build.SUPPORTED_ABIS.firstOrNull() ?: "unknown")
                .put("node", android.os.Build.MODEL)
            "/api/exif" -> exif(body)
            "/api/ocr" -> ocr(body)
            "/api/qr-barcode" -> qr(body)
            "/api/forensics/faces" -> faces(body)
            "/api/forensics/ela" -> withImageBytes(body) { GeoHunterForensics.ela(it, body.optInt("quality", 90), body.optDouble("scale", 20.0)) }
            "/api/forensics/noise" -> withImageBytes(body) { GeoHunterForensics.noise(it) }
            "/api/forensics/stego" -> withImageBytes(body) { GeoHunterForensics.stego(it) }
            "/api/reverse-search", "/api/search" -> JSONObject()
                .put("success", false)
                .put("error", "Эта функция требует интернет-соединения. Локальный анализ GeoHunter продолжает работать без сети.")
            else -> JSONObject()
                .put("success", false)
                .put("error", "Локальный API пока не реализован для маршрута: $path")
        }
    }


    private fun withImageBytes(body: JSONObject, action: (ByteArray) -> JSONObject): JSONObject {
        val encoded = body.optString("imageBase64", body.optString("image_base64", ""))
            .let { if (it.startsWith("data:")) it.substringAfter(",", "") else it }
        require(encoded.isNotBlank()) { "Загрузите файл изображения." }
        val bytes = android.util.Base64.decode(encoded, android.util.Base64.DEFAULT)
        require(bytes.isNotEmpty()) { "Файл изображения пуст." }
        require(bytes.size <= 40 * 1024 * 1024) { "Изображение превышает лимит 40 МБ." }
        return action(bytes)
    }

    private fun withImage(body: JSONObject, action: (Uri) -> JSONObject): JSONObject {
        val encoded = body.optString("imageBase64", body.optString("image_base64", ""))
            .substringAfter(",", body.optString("imageBase64", body.optString("image_base64", "")))
        require(encoded.isNotBlank()) { "Загрузите файл изображения." }
        val bytes = android.util.Base64.decode(encoded, android.util.Base64.DEFAULT)
        require(bytes.isNotEmpty()) { "Файл изображения пуст." }
        require(bytes.size <= 40 * 1024 * 1024) { "Изображение превышает лимит 40 МБ." }
        val file = File.createTempFile("geohunter-", ".img", context.cacheDir)
        return try {
            file.writeBytes(bytes)
            action(Uri.fromFile(file))
        } finally {
            file.delete()
        }
    }

    private fun exif(body: JSONObject): JSONObject = withImage(body) { uri ->
        val meta = ImageMetadataReader.read(context.contentResolver, uri)
        val camera = JSONObject()
        meta.cameraMake?.let { camera.put("Make", it) }
        meta.cameraModel?.let { camera.put("Model", it) }
        val dates = JSONObject()
        meta.dateTime?.let { dates.put("DateTimeOriginal", it) }
        val software = JSONObject()
        meta.software?.let { software.put("Software", it) }
        val shooting = JSONObject()
        meta.iso?.let { shooting.put("ISO", it) }
        meta.exposureTime?.let { shooting.put("ExposureTime", it) }
        meta.aperture?.let { shooting.put("FNumber", it) }
        meta.focalLength?.let { shooting.put("FocalLength", it) }
        val gps = JSONObject()
        if (meta.latitude != null && meta.longitude != null) {
            gps.put("latitude", meta.latitude)
                .put("longitude", meta.longitude)
                .put("googleMapsUrl", "https://www.google.com/maps?q=${meta.latitude},${meta.longitude}")
                .put("yandexMapsUrl", "https://yandex.ru/maps/?pt=${meta.longitude},${meta.latitude}&z=15&l=map")
                .put("openStreetMapUrl", "https://www.openstreetmap.org/?mlat=${meta.latitude}&mlon=${meta.longitude}")
                .put("note", "Координаты извлечены из EXIF; адрес требует интернета.")
        } else {
            gps.put("note", "GPS-координаты в EXIF не найдены.")
        }
        val hasMeta = camera.length() + dates.length() + software.length() + shooting.length() > 0 ||
            meta.latitude != null
        JSONObject()
            .put("success", true)
            .put("has_metadata", hasMeta)
            .put("gps", gps)
            .put("camera", camera)
            .put("dates", dates)
            .put("software", software)
            .put("shooting", shooting)
            .put("privacy", JSONArray())
            .put("sun", JSONObject().put("error", "Расчёт положения солнца будет подключён отдельно."))
            .put("hashes", JSONObject())
            .put("perceptual", JSONObject())
            .put("meta", JSONObject().put("filename", meta.fileName).put("mime_type", meta.mimeType))
            .put("file_stats", JSONObject()
                .put("filename", meta.fileName)
                .put("size", meta.fileSize)
                .put("width", meta.width ?: JSONObject.NULL)
                .put("height", meta.height ?: JSONObject.NULL))
            .put("exiftool", JSONObject().put("skipped", true))
    }

    private fun ocr(body: JSONObject): JSONObject = withImage(body) { uri ->
        val inspected = ImageTextCodeAnalyzer.analyze(context.contentResolver, uri)
        val text = inspected.recognizedText
        val emails = Regex("[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}", RegexOption.IGNORE_CASE)
            .findAll(text).map { it.value }.distinct().take(30).toList()
        val urls = Regex("\\bhttps?://[^\\s<>()\\\"']+\\b", RegexOption.IGNORE_CASE)
            .findAll(text).map { it.value }.distinct().take(30).toList()
        val phones = Regex("\\b(?:\\+?\\d[\\d\\s().-]{7,}\\d)\\b")
            .findAll(text).map { it.value }.distinct().take(30).toList()
        JSONObject()
            .put("success", true)
            .put("fullText", text)
            .put("emails", JSONArray(emails))
            .put("urls", JSONArray(urls))
            .put("phones", JSONArray(phones))
            .put("lang", body.optString("lang", "rus+eng"))
    }

    private fun qr(body: JSONObject): JSONObject = withImage(body) { uri ->
        val inspected = ImageTextCodeAnalyzer.analyze(context.contentResolver, uri)
        val items = JSONArray()
        val decoded = JSONArray()
        inspected.codes.forEach { code ->
            items.put(JSONObject().put("type", code.format).put("data", code.value))
            decoded.put(code.value)
        }
        JSONObject()
            .put("success", true)
            .put("decoded", decoded)
            .put("count", decoded.length())
            .put("items", items)
    }

    private fun faces(body: JSONObject): JSONObject = withImage(body) { uri ->
        val inspected = ImageSceneAnalyzer.analyze(context.contentResolver, uri)
        val list = JSONArray()
        inspected.faces.forEach { face ->
            list.put(JSONObject()
                .put("x", face.left)
                .put("y", face.top)
                .put("w", face.width)
                .put("h", face.height))
        }
        JSONObject()
            .put("success", true)
            .put("face_count", list.length())
            .put("faces", list)
            .put("image_width", inspected.imageWidth)
            .put("image_height", inspected.imageHeight)
            .put("verdict", if (list.length() > 0) "Найдено лиц: ${list.length()}" else "Лица не обнаружены")
            .put("note", "Обнаружение выполнено локальной моделью ML Kit на Android.")
    }
}
