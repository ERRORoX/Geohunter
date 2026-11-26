package com.errorox.geohunter

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

private val GhBackground = Color(0xFF080C12)
private val GhSurface = Color(0xFF111923)
private val GhAccent = Color(0xFF00E5A0)
private val GhMuted = Color(0xFF8B9AA9)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(colorScheme = darkColorScheme(
                primary = GhAccent,
                background = GhBackground,
                surface = GhSurface,
                onPrimary = Color.Black,
                onBackground = Color(0xFFEAF0F6),
                onSurface = Color(0xFFEAF0F6)
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
            modifier = Modifier.fillMaxSize().padding(horizontal = 18.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            item {
                Spacer(Modifier.height(22.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier.size(42.dp).background(GhAccent, RoundedCornerShape(12.dp)),
                        contentAlignment = Alignment.Center
                    ) {
                        Text("GH", color = Color.Black, fontWeight = FontWeight.Black, fontSize = 17.sp)
                    }
                    Spacer(Modifier.width(12.dp))
                    Column {
                        Text("GEOHUNTER", fontWeight = FontWeight.Black, fontSize = 22.sp, letterSpacing = 2.sp)
                        Text("LOCAL IMAGE INTELLIGENCE", color = GhMuted, fontSize = 10.sp, letterSpacing = 1.5.sp)
                    }
                }
                Spacer(Modifier.height(22.dp))
                Text("ПАНЕЛЬ АНАЛИЗА", color = GhAccent, fontSize = 11.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.4.sp)
                Text("Исследование изображения", fontSize = 24.sp, fontWeight = FontWeight.Bold)
                Text("Обработка выбранного файла выполняется на устройстве.", color = GhMuted, fontSize = 13.sp)
                Spacer(Modifier.height(8.dp))
            }

            item {
                Card(colors = CardDefaults.cardColors(containerColor = GhSurface), shape = RoundedCornerShape(18.dp)) {
                    Column(Modifier.fillMaxWidth().padding(16.dp)) {
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
                            Text("Координаты извлечены из EXIF. Для просмотра на карте интернет не требуется только при наличии заранее загруженной офлайн-карты.", color = GhMuted, fontSize = 11.sp)
                        } else {
                            Text("В выбранном файле GPS-координаты не обнаружены.", color = GhMuted, fontSize = 11.sp)
                        }
                    }
                }
            }

            item {
                SectionCard(title = "ИНСТРУМЕНТЫ GEOHUNTER") {
                    ToolStatus("EXIF / GPS", "Доступно", true)
                    ToolStatus("ELA / Анализ шума", "Следующий этап разработки", false)
                    ToolStatus("LSB / Стеганография", "Следующий этап разработки", false)
                    ToolStatus("OCR / QR / Штрихкоды", "Следующий этап разработки", false)
                    ToolStatus("Тени / Положение солнца", "Следующий этап разработки", false)
                    ToolStatus("Детекция лиц", "Следующий этап разработки", false)
                }
            }

            item {
                Text("GeoHunter Android 0.1.0 · Локальная обработка EXIF/GPS", color = GhMuted, fontSize = 10.sp, modifier = Modifier.padding(vertical = 16.dp))
            }
        }
    }
}

@Composable
private fun ImagePreview(uri: Uri) {
    val context = LocalContext.current
    val bitmap: Bitmap? by produceState<Bitmap?>(initialValue = null, key1 = uri) {
        value = withContext(Dispatchers.IO) {
            context.contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it) }
        }
    }
    Card(colors = CardDefaults.cardColors(containerColor = GhSurface), shape = RoundedCornerShape(18.dp)) {
        Column(Modifier.fillMaxWidth().padding(12.dp)) {
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
private fun SectionCard(title: String, content: @Composable () -> Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = GhSurface), shape = RoundedCornerShape(18.dp)) {
        Column(Modifier.fillMaxWidth().padding(16.dp)) {
            Text(title, color = GhAccent, fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.2.sp)
            Spacer(Modifier.height(10.dp))
            content()
        }
    }
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 5.dp),
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
