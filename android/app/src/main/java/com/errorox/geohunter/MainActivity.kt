package com.errorox.geohunter

import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.location.Geocoder
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import org.maplibre.android.MapLibre
import org.maplibre.android.annotations.Marker
import org.maplibre.android.annotations.MarkerOptions
import org.maplibre.android.camera.CameraUpdateFactory
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.maps.MapLibreMap
import org.maplibre.android.maps.MapView
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.Locale
import kotlin.math.roundToInt

private val GhBackground = Color(0xFF060608) // GeoHunter --bg-page
private val GhSurface = Color(0xFF0A0A0E) // GeoHunter --bg-card
private val GhPanel = Color(0xFF0C0C10) // GeoHunter --bg-panel
private val GhAccent = Color(0xFF00FF88) // GeoHunter --accent
private val GhCyan = Color(0xFF00D4FF) // GeoHunter --cyan
private val GhMuted = Color(0xFF5C6B66) // GeoHunter --text-muted
private val GhText = Color(0xFFD8E4E0) // GeoHunter --text
private val GhBorder = Color(0xFF1A1A22) // GeoHunter --border

data class ForensicOutcome(val result: ForensicResult?, val error: String? = null)
data class TextCodeOutcome(val result: TextCodeInspection?, val error: String? = null)
data class SceneOutcome(val result: ImageSceneInspection?, val error: String? = null)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(colorScheme = darkColorScheme(
                primary = GhAccent,
                background = GhBackground,
                surface = GhPanel,
                onPrimary = Color.Black,
                onBackground = GhText,
                onSurface = GhText
            )) {
                GeoHunterApp()
            }
        }
    }
}

@Composable
private fun GeoHunterApp() {
    val context = LocalContext.current
    var selectedUri by remember { mutableStateOf<Uri?>(null) }
    var metadata by remember { mutableStateOf<ImageMetadata?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    val forensicOutcome by produceState<ForensicOutcome?>(initialValue = null, key1 = selectedUri) {
        value = selectedUri?.let { uri ->
            withContext(Dispatchers.IO) {
                try {
                    ForensicOutcome(ImageForensics.analyze(context.contentResolver, uri, context.contentResolver.getType(uri)))
                } catch (e: Exception) {
                    ForensicOutcome(null, e.localizedMessage ?: "Не удалось выполнить анализ")
                }
            }
        }
    }

    val textCodeOutcome by produceState<TextCodeOutcome?>(initialValue = null, key1 = selectedUri) {
        value = selectedUri?.let { uri ->
            withContext(Dispatchers.IO) {
                try {
                    TextCodeOutcome(ImageTextCodeAnalyzer.analyze(context.contentResolver, uri))
                } catch (e: Exception) {
                    TextCodeOutcome(null, e.localizedMessage ?: "Не удалось выполнить OCR и поиск кодов")
                }
            }
        }
    }

    val sceneOutcome by produceState<SceneOutcome?>(initialValue = null, key1 = selectedUri) {
        value = selectedUri?.let { uri ->
            withContext(Dispatchers.IO) {
                try {
                    SceneOutcome(ImageSceneAnalyzer.analyze(context.contentResolver, uri))
                } catch (e: Exception) {
                    SceneOutcome(null, e.localizedMessage ?: "Не удалось выполнить анализ сцены")
                }
            }
        }
    }

    val picker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri ->
        if (uri != null) {
            selectedUri = uri
            error = null
            metadata = null
            try {
                context.contentResolver.takePersistableUriPermission(
                    uri,
                    android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION
                )
            } catch (_: SecurityException) {
                // Некоторые поставщики файлов не поддерживают постоянное разрешение.
            }
            try {
                metadata = ImageMetadataReader.read(context.contentResolver, uri)
            } catch (e: Exception) {
                error = e.localizedMessage ?: "Не удалось прочитать метаданные"
            }
        }
    }

    Surface(modifier = Modifier.fillMaxSize(), color = GhBackground) {
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            item {
                Spacer(Modifier.height(10.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier.size(28.dp).background(Color(0x1F00FF88), RoundedCornerShape(8.dp)),
                        contentAlignment = Alignment.Center
                    ) {
                        Text("G", color = GhAccent, fontWeight = FontWeight.Bold, fontSize = 16.sp, fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace)
                    }
                    Spacer(Modifier.width(12.dp))
                    Column {
                        Row {
                            Text("Geo", color = GhAccent, fontWeight = FontWeight.Bold, fontSize = 13.sp, letterSpacing = 0.2.sp, fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace)
                            Text("Hunter", color = GhMuted, fontWeight = FontWeight.Bold, fontSize = 13.sp, letterSpacing = 0.2.sp, fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace)
                        }
                        Text("Поиск по фотографии · EXIF, обратный поиск, OCR, QR", color = GhMuted, fontSize = 8.sp, letterSpacing = 0.1.sp)
                    }
                }
                Spacer(Modifier.height(16.dp))
                Text("ПАНЕЛЬ АНАЛИЗА", color = GhAccent, fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.4.sp)
                Text("Исследование изображения", color = GhText, fontSize = 20.sp, fontWeight = FontWeight.SemiBold, fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace)
                Text("Обработка выбранного файла выполняется на устройстве.", color = GhMuted, fontSize = 13.sp)
                Spacer(Modifier.height(8.dp))
            }

            item {
                Card(colors = CardDefaults.cardColors(containerColor = GhSurface), shape = RoundedCornerShape(12.dp), border = BorderStroke(1.dp, GhBorder)) {
                    Column(Modifier.fillMaxWidth().padding(12.dp)) {
                        Text("ИСТОЧНИК ДАННЫХ", color = GhMuted, fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp)
                        Spacer(Modifier.height(12.dp))
                        Button(
                            onClick = { picker.launch(arrayOf("image/*")) },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(if (selectedUri == null) "Выбрать изображение" else "Выбрать другое изображение")
                        }
                        if (selectedUri == null) {
                            Text("Поддерживаются изображения, доступные в галерее и файловом хранилище.", color = GhMuted, fontSize = 12.sp)
                        }
                        error?.let {
                            Spacer(Modifier.height(8.dp))
                            Text(it, color = Color(0xFFFF7777), fontSize = 12.sp)
                        }
                    }
                }
            }

            selectedUri?.let { uri ->
                item { ImagePreview(uri) }
                item {
                    SectionCard(title = "ОБРАТНЫЙ ПОИСК ИЗОБРАЖЕНИЯ") {
                        Text(
                            "Передайте выбранное фото в приложение поиска изображений. Отправка произойдёт только после вашего выбора в системном меню Android.",
                            color = GhMuted,
                            fontSize = 11.sp
                        )
                        Spacer(Modifier.height(8.dp))
                        OutlinedButton(
                            onClick = { shareForReverseSearch(context, uri) },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Поделиться для обратного поиска")
                        }
                    }
                }
            }

            metadata?.let { data ->
                item {
                    SectionCard(title = "ОБЩИЕ СВЕДЕНИЯ") {
                        InfoRow("Файл", data.fileName)
                        InfoRow("Формат", data.mimeType)
                        InfoRow("Размер", ImageMetadataReader.formatBytes(data.fileSize))
                        InfoRow("Разрешение", if (data.width != null && data.height != null) "${data.width} × ${data.height}" else "Нет данных")
                    }
                }
                item {
                    SectionCard(title = "КАМЕРА И СЪЁМКА") {
                        InfoRow("Производитель", data.cameraMake ?: "Нет данных")
                        InfoRow("Модель", data.cameraModel ?: "Нет данных")
                        InfoRow("Дата съёмки", data.dateTime ?: "Нет данных")
                        InfoRow("ПО", data.software ?: "Нет данных")
                        InfoRow("ISO", data.iso ?: "Нет данных")
                        InfoRow("Выдержка", data.exposureTime ?: "Нет данных")
                        InfoRow("Диафрагма", data.aperture ?: "Нет данных")
                        InfoRow("Фокусное расстояние", data.focalLength ?: "Нет данных")
                    }
                }
                item {
                    SectionCard(title = "ГЕОЛОКАЦИЯ GPS") {
                        InfoRow("Широта", ImageMetadataReader.formatCoordinate(data.latitude))
                        InfoRow("Долгота", ImageMetadataReader.formatCoordinate(data.longitude))
                        InfoRow("Высота GPS", data.gpsAltitude ?: "Нет данных")
                        if (data.latitude != null && data.longitude != null) {
                            Text("Координаты извлечены непосредственно из EXIF. Карта загружает картографические данные через интернет.", color = GhMuted, fontSize = 11.sp)
                            Spacer(Modifier.height(10.dp))
                            ExifLocationMap(latitude = data.latitude, longitude = data.longitude)
                            Spacer(Modifier.height(10.dp))
                            ExifReverseGeocoding(latitude = data.latitude, longitude = data.longitude)
                        } else {
                            Text("В выбранном файле GPS-координаты не обнаружены. Поэтому поставить достоверную точку съёмки на карте нельзя.", color = GhMuted, fontSize = 11.sp)
                        }
                    }
                }
            }

            if (selectedUri != null) {
                item {
                    val outcome = forensicOutcome
                    SectionCard(title = "ЦИФРОВАЯ КРИМИНАЛИСТИКА") {
                        when {
                            outcome == null -> Text("Выполняется локальный анализ изображения…", color = GhMuted, fontSize = 12.sp)
                            outcome.error != null -> Text(outcome.error, color = Color(0xFFFF7777), fontSize = 12.sp)
                            outcome.result != null -> {
                                val result = outcome.result
                                Text("Размер исходника: ${result.sourceWidth} × ${result.sourceHeight}", color = GhMuted, fontSize = 11.sp)
                                Text("Размер анализа: ${result.sampledWidth} × ${result.sampledHeight} px", color = GhMuted, fontSize = 11.sp)
                                Spacer(Modifier.height(12.dp))
                                if (result.isJpeg && result.elaBitmap != null) {
                                    Text("ELA · JPEG ERROR LEVEL ANALYSIS", color = GhAccent, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                    ForensicImage(result.elaBitmap, "Карта различий после JPEG-пересжатия")
                                    InfoRow("Средняя разница RGB", String.format(java.util.Locale.US, "%.2f / 255", result.elaMeanDifference ?: 0.0))
                                    Text("Яркие участки показывают различия после повторного JPEG-сохранения. Это ориентир для проверки, а не доказательство редактирования.", color = GhMuted, fontSize = 11.sp)
                                } else {
                                    Text("ELA доступен только для JPEG. Для этого файла построена карта высокочастотных отклонений.", color = GhMuted, fontSize = 11.sp)
                                }
                                Spacer(Modifier.height(14.dp))
                                Text("NOISE · КАРТА ВЫСОКОЧАСТОТНЫХ ОТКЛОНЕНИЙ", color = GhAccent, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                ForensicImage(result.noiseBitmap, "Карта локальных различий яркости")
                                InfoRow("Среднее отклонение", String.format(java.util.Locale.US, "%.2f / 255", result.noiseMeanResidual))
                                Text("Карта показывает локальные перепады яркости и детали сцены. Она не определяет подделку автоматически.", color = GhMuted, fontSize = 11.sp)
                                Spacer(Modifier.height(18.dp))
                                Text("LSB · ПОИСК СКРЫТЫХ ДАННЫХ", color = GhAccent, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                InfoRow("Доля битов = 1", String.format(java.util.Locale.US, "%.2f%%", result.lsbInspection.bitOnePercent))
                                InfoRow("Энтропия байтов", String.format(java.util.Locale.US, "%.2f / 8 бит", result.lsbInspection.byteEntropy))
                                InfoRow("Извлечено для проверки", "${result.lsbInspection.extractedBytes} байт")
                                if (result.lsbInspection.detectedSignatures.isNotEmpty()) {
                                    Text("Найденные сигнатуры:", color = GhAccent, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
                                    result.lsbInspection.detectedSignatures.forEach {
                                        Text("• $it", color = GhText, fontSize = 11.sp)
                                    }
                                } else {
                                    Text("Известные сигнатуры файлов в начале извлечённого потока не обнаружены.", color = GhMuted, fontSize = 11.sp)
                                }
                                if (result.lsbInspection.printableStrings.isNotEmpty()) {
                                    Spacer(Modifier.height(8.dp))
                                    Text("Печатные фрагменты:", color = GhAccent, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
                                    result.lsbInspection.printableStrings.forEach {
                                        Text(it.take(120), color = Color(0xFFEAF0F6), fontSize = 10.sp)
                                    }
                                } else {
                                    Text("Читаемые текстовые фрагменты не найдены.", color = GhMuted, fontSize = 11.sp)
                                }
                                Text("Проверяется последовательный LSB-поток каналов RGB. Другие алгоритмы, перестановки пикселей, шифрование и JPEG-стеганография могут остаться незамеченными. Статистика не является доказательством наличия скрытого сообщения.", color = GhMuted, fontSize = 11.sp)
                            }
                        }
                    }
                }
            }

            if (selectedUri != null) {
                item {
                    SectionCard(title = "OCR · QR · ШТРИХКОДЫ") {
                        val scan = textCodeOutcome
                        when {
                            scan == null -> Text("Выполняется локальное распознавание текста и кодов…", color = GhMuted, fontSize = 12.sp)
                            scan.error != null -> Text(scan.error, color = Color(0xFFFF7777), fontSize = 12.sp)
                            scan.result != null -> {
                                val result = scan.result
                                InfoRow("Размер анализа", "${result.sampledWidth} × ${result.sampledHeight} px")
                                Text("РАСПОЗНАННЫЙ ТЕКСТ", color = GhAccent, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                if (result.recognizedText.isBlank()) {
                                    Text("Текст на изображении не обнаружен.", color = GhMuted, fontSize = 12.sp)
                                } else {
                                    Text(result.recognizedText, color = Color(0xFFEAF0F6), fontSize = 12.sp)
                                }
                                Spacer(Modifier.height(12.dp))
                                Text("НАЙДЕННЫЕ КОДЫ: ${result.codes.size}", color = GhAccent, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                if (result.codes.isEmpty()) {
                                    Text("QR-коды и поддерживаемые штрихкоды не обнаружены.", color = GhMuted, fontSize = 12.sp)
                                } else {
                                    result.codes.forEachIndexed { index, code ->
                                        Text("${index + 1}. ${code.format}", color = GhAccent, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
                                        Text(code.value, color = Color(0xFFEAF0F6), fontSize = 12.sp)
                                        Spacer(Modifier.height(6.dp))
                                    }
                                }
                                Text("Распознавание выполняется локально встроенной моделью ML Kit для латинского алфавита. Кириллица (русский текст) может распознаваться ненадёжно. Результат OCR может содержать ошибки; содержимое QR-кодов и штрихкодов отображается как данные, а не открывается автоматически.", color = GhMuted, fontSize = 11.sp)
                            }
                        }
                    }
                }
            }

            if (selectedUri != null) {
                item {
                    SectionCard(title = "ЛИЦА · ТЕНИ · ОСВЕЩЕНИЕ") {
                        val scene = sceneOutcome
                        when {
                            scene == null -> Text("Выполняется локальный анализ лиц и освещения…", color = GhMuted, fontSize = 12.sp)
                            scene.error != null -> Text(scene.error, color = Color(0xFFFF7777), fontSize = 12.sp)
                            scene.result != null -> {
                                val result = scene.result
                                InfoRow("Размер анализа", "${result.imageWidth} × ${result.imageHeight} px")
                                Text("ДЕТЕКЦИЯ ЛИЦ: ${result.faces.size}", color = GhAccent, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                if (result.faces.isEmpty()) {
                                    Text("Лица не обнаружены.", color = GhMuted, fontSize = 12.sp)
                                } else {
                                    result.faces.forEachIndexed { index, face ->
                                        Text("Лицо ${index + 1}", color = Color(0xFFEAF0F6), fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                                        InfoRow("Область (x, y)", "${face.left}, ${face.top}")
                                        InfoRow("Размер области", "${face.width} × ${face.height} px")
                                        face.smilingProbability?.let { InfoRow("Вероятность улыбки", "${(it * 100).roundToInt()}%") }
                                        face.leftEyeOpenProbability?.let { InfoRow("Левый глаз открыт", "${(it * 100).roundToInt()}%") }
                                        face.rightEyeOpenProbability?.let { InfoRow("Правый глаз открыт", "${(it * 100).roundToInt()}%") }
                                    }
                                }
                                Spacer(Modifier.height(16.dp))
                                Text("КАРТА ТЁМНЫХ ОБЛАСТЕЙ", color = GhAccent, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                ForensicImage(result.light.shadowMask, "Бинарная карта тёмных областей изображения")
                                InfoRow("Тёмные пиксели", String.format(java.util.Locale.US, "%.1f%%", result.light.shadowAreaPercent))
                                InfoRow("Светлые пиксели", String.format(java.util.Locale.US, "%.1f%%", result.light.brightAreaPercent))
                                InfoRow("Контраст диапазона", String.format(java.util.Locale.US, "%.1f%%", result.light.contrastPercent))
                                InfoRow("Вектор яркости на фото", result.light.imagePlaneLightAngleDegrees?.let { "$it° (от тёмной к светлой области)" } ?: "Недостаточно выраженных областей")
                                Text("Это эвристическая карта яркости, а не распознавание настоящих теней. Направление указано только в плоскости изображения. Азимут солнца по одному фото достоверно определить нельзя без ориентации камеры, геометрии сцены и подтверждённых EXIF-данных.", color = GhMuted, fontSize = 11.sp)
                            }
                        }
                    }
                }
            }

            if (selectedUri != null) {
                item {
                    SectionCard(title = "ВЕБ-ПОИСК ПО ДАННЫМ ФОТО") {
                        val searchTerms = listOfNotNull(
                            metadata?.cameraMake,
                            metadata?.cameraModel,
                            metadata?.dateTime,
                            metadata?.fileName
                        ).joinToString(" ").ifBlank { metadata?.fileName ?: "изображение" }
                        Text(
                            "Поиск использует только текстовые сведения о файле и EXIF. Само изображение в поисковик не передаётся.",
                            color = GhMuted,
                            fontSize = 11.sp
                        )
                        Spacer(Modifier.height(8.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            OutlinedButton(onClick = { openWebSearch(context, "google", searchTerms) }) {
                                Text("Google")
                            }
                            OutlinedButton(onClick = { openWebSearch(context, "yandex", searchTerms) }) {
                                Text("Яндекс")
                            }
                            OutlinedButton(onClick = { openWebSearch(context, "duckduckgo", searchTerms) }) {
                                Text("DuckDuckGo")
                            }
                        }
                    }
                }
            }

            item {
                SectionCard(title = "ИНСТРУМЕНТЫ GEOHUNTER") {
                    ToolStatus("EXIF / GPS", "Доступно", true)
                    ToolStatus("ELA / Анализ шума", if (selectedUri != null && forensicOutcome?.result != null) "Доступно" else "Ожидает фото", selectedUri != null && forensicOutcome?.result != null)
                    ToolStatus("LSB / Стеганография", if (selectedUri != null && forensicOutcome?.result != null) "Доступно" else "Ожидает фото", selectedUri != null && forensicOutcome?.result != null)
                    ToolStatus("OCR / QR / Штрихкоды", if (textCodeOutcome?.result != null) "Доступно" else if (textCodeOutcome?.error != null) "Ошибка анализа" else if (selectedUri != null) "Анализ…" else "Ожидает фото", textCodeOutcome?.result != null)
                    ToolStatus("Карта GPS-фотографии", if (metadata?.latitude != null && metadata?.longitude != null) "Координаты найдены" else "Ожидает GPS", metadata?.latitude != null && metadata?.longitude != null)
                    ToolStatus("Детекция лиц", if (sceneOutcome?.result != null) "Доступно" else if (selectedUri != null) "Анализ…" else "Ожидает фото", sceneOutcome?.result != null)
                    ToolStatus("Тени / Освещение", if (sceneOutcome?.result != null) "Доступно" else if (selectedUri != null) "Анализ…" else "Ожидает фото", sceneOutcome?.result != null)
                }
            }

            item {
                Text("GeoHunter Android 0.1.0 · Локальная обработка EXIF/GPS", color = GhMuted, fontSize = 10.sp, modifier = Modifier.padding(vertical = 16.dp))
            }
        }
    }
}


private const val GEOHUNTER_MAP_STYLE = "https://tiles.openfreemap.org/styles/liberty"

@Composable
private fun ExifLocationMap(latitude: Double, longitude: Double) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val latestLatitude by rememberUpdatedState(latitude)
    val latestLongitude by rememberUpdatedState(longitude)
    val mapView = remember(context) {
        MapLibre.getInstance(context)
        MapView(context).apply { onCreate(null) }
    }
    var map by remember { mutableStateOf<MapLibreMap?>(null) }
    var styleReady by remember { mutableStateOf(false) }
    var marker by remember { mutableStateOf<Marker?>(null) }

    DisposableEffect(mapView, lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_START -> mapView.onStart()
                Lifecycle.Event.ON_RESUME -> mapView.onResume()
                Lifecycle.Event.ON_PAUSE -> mapView.onPause()
                Lifecycle.Event.ON_STOP -> mapView.onStop()
                // onDestroy is called once from onDispose to avoid duplicate lifecycle teardown.
                else -> Unit
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        mapView.getMapAsync { readyMap ->
            map = readyMap
            readyMap.setStyle(GEOHUNTER_MAP_STYLE) {
                styleReady = true
            }
        }
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
            marker?.let { existing ->
                try { map?.removeMarker(existing) } catch (_: Exception) { }
            }
            marker = null
            map = null
            styleReady = false
            try { mapView.onDestroy() } catch (_: Exception) { }
        }
    }

    LaunchedEffect(map, styleReady, latitude, longitude) {
        val activeMap = map
        if (activeMap != null && styleReady &&
            latitude.isFinite() && longitude.isFinite() &&
            latitude in -90.0..90.0 && longitude in -180.0..180.0
        ) {
            marker?.let { activeMap.removeMarker(it) }
            marker = activeMap.addMarker(
                MarkerOptions()
                    .position(LatLng(latitude, longitude))
                    .title("Место съёмки по EXIF GPS")
                    .snippet(String.format(java.util.Locale.US, "%.6f, %.6f", latitude, longitude))
            )
            activeMap.animateCamera(
                CameraUpdateFactory.newLatLngZoom(LatLng(latitude, longitude), 15.0)
            )
        }
    }

    Column(Modifier.fillMaxWidth()) {
        AndroidView(factory = { mapView }, modifier = Modifier.fillMaxWidth().height(250.dp))
        Text(
            "MapLibre · OpenFreeMap · ${String.format(java.util.Locale.US, "%.6f", latestLatitude)}, ${String.format(java.util.Locale.US, "%.6f", latestLongitude)}",
            color = GhMuted,
            fontSize = 10.sp,
            modifier = Modifier.padding(top = 6.dp)
        )
        Text(
            "Точка отражает координаты, записанные в файле фотографии; это не подтверждение подлинности GPS.",
            color = GhMuted,
            fontSize = 10.sp
        )
    }
}

private fun shareForReverseSearch(context: android.content.Context, imageUri: Uri) {
    val shareIntent = Intent(Intent.ACTION_SEND).apply {
        type = context.contentResolver.getType(imageUri) ?: "image/*"
        putExtra(Intent.EXTRA_STREAM, imageUri)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    context.startActivity(Intent.createChooser(shareIntent, "Обратный поиск изображения"))
}

private fun openWebSearch(context: android.content.Context, engine: String, query: String) {
    val encoded = Uri.encode(query)
    val url = when (engine) {
        "yandex" -> "https://yandex.com/search/?text=$encoded"
        "duckduckgo" -> "https://duckduckgo.com/?q=$encoded"
        else -> "https://www.google.com/search?q=$encoded"
    }
    context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
}

@Composable
private fun ExifReverseGeocoding(latitude: Double, longitude: Double) {
    val context = LocalContext.current
    val address by produceState(
        initialValue = "Определение адреса…",
        key1 = latitude,
        key2 = longitude
    ) {
        value = withContext(Dispatchers.IO) {
            if (!Geocoder.isPresent()) {
                "Служба определения адресов недоступна на этом устройстве"
            } else {
                try {
                    @Suppress("DEPRECATION")
                    val matches = Geocoder(context, Locale.getDefault())
                        .getFromLocation(latitude, longitude, 1)
                    val place = matches?.firstOrNull()
                    if (place == null) {
                        "Адрес для этих координат не найден"
                    } else {
                        listOfNotNull(
                            place.thoroughfare,
                            place.subThoroughfare,
                            place.locality ?: place.subAdminArea,
                            place.adminArea,
                            place.countryName
                        ).distinct().joinToString(", ").ifBlank {
                            "Адресные сведения не предоставлены"
                        }
                    }
                } catch (_: Exception) {
                    "Не удалось определить адрес. Проверьте подключение к интернету."
                }
            }
        }
    }

    Column(Modifier.fillMaxWidth()) {
        Text("ПРИБЛИЗИТЕЛЬНЫЙ АДРЕС", color = GhAccent, fontSize = 10.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(4.dp))
        Text(address, color = Color(0xFFEAF0F6), fontSize = 12.sp)
        Text(
            "Адрес получен по координатам через системную службу геокодирования; точность зависит от картографических данных.",
            color = GhMuted,
            fontSize = 10.sp
        )
    }
}

@Composable
private fun ImagePreview(uri: Uri) {
    val context = LocalContext.current
    val bitmap: Bitmap? by produceState<Bitmap?>(initialValue = null, key1 = uri) {
        value = withContext(Dispatchers.IO) {
            val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            context.contentResolver.openInputStream(uri)?.use {
                BitmapFactory.decodeStream(it, null, bounds)
            }
            var sample = 1
            while (maxOf(bounds.outWidth, bounds.outHeight) / sample > 1600) sample *= 2
            val options = BitmapFactory.Options().apply { inSampleSize = sample }
            context.contentResolver.openInputStream(uri)?.use {
                BitmapFactory.decodeStream(it, null, options)
            }
        }
    }
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = GhSurface),
        shape = RoundedCornerShape(10.dp),
        border = BorderStroke(1.dp, GhBorder)
    ) {
        Column(Modifier.fillMaxWidth().padding(10.dp)) {
            Text("ПРЕДПРОСМОТР", color = GhMuted, fontSize = 10.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(10.dp))
            if (bitmap != null) {
                Image(
                    bitmap = bitmap!!.asImageBitmap(),
                    contentDescription = "Выбранное изображение",
                    modifier = Modifier.fillMaxWidth().height(220.dp),
                    contentScale = ContentScale.Fit
                )
            } else {
                Box(Modifier.fillMaxWidth().height(120.dp), contentAlignment = Alignment.Center) {
                    Text("Загрузка изображения…", color = GhMuted)
                }
            }
        }
    }
}

@Composable
private fun ForensicImage(bitmap: Bitmap, description: String) {
    Image(
        bitmap = bitmap.asImageBitmap(),
        contentDescription = description,
        modifier = Modifier.fillMaxWidth().height(210.dp),
        contentScale = ContentScale.Fit
    )
    Spacer(Modifier.height(6.dp))
}

@Composable
private fun SectionCard(title: String, content: @Composable () -> Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = GhSurface), shape = RoundedCornerShape(10.dp), border = BorderStroke(1.dp, GhBorder)) {
        Column(Modifier.fillMaxWidth().padding(12.dp)) {
            Text(title, color = GhAccent, fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.2.sp)
            Spacer(Modifier.height(10.dp))
            content()
        }
    }
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 3.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.Top
    ) {
        Text(label, color = GhMuted, fontSize = 12.sp, modifier = Modifier.weight(0.9f))
        Spacer(Modifier.width(10.dp))
        Text(value, color = Color(0xFFEAF0F6), fontSize = 12.sp, modifier = Modifier.weight(1.1f))
    }
}

@Composable
private fun ToolStatus(name: String, status: String, ready: Boolean) {
    Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(7.dp).background(if (ready) GhAccent else GhMuted, RoundedCornerShape(50)))
        Spacer(Modifier.width(10.dp))
        Text(name, fontSize = 12.sp, modifier = Modifier.weight(1f))
        Text(status, color = if (ready) GhAccent else GhMuted, fontSize = 10.sp)
    }
}
