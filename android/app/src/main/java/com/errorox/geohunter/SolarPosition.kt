package com.errorox.geohunter

import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.TimeZone
import kotlin.math.*

/** Offline NOAA solar-position approximation; EXIF timestamps are interpreted as UTC, like Astral's naive datetime input. */
object SolarPosition {
    private fun parse(value: String): Double {
        val patterns = listOf("yyyy:MM:dd HH:mm:ss", "yyyy-MM-dd'T'HH:mm:ss", "yyyy-MM-dd HH:mm:ss", "yyyy:MM:dd HH:mm")
        for (pattern in patterns) {
            try {
                val format = SimpleDateFormat(pattern, Locale.US).apply {
                    isLenient = false
                    timeZone = TimeZone.getTimeZone("UTC")
                }
                val date = format.parse(value.trim()) ?: continue
                return date.time / 86400000.0 + 2440587.5
            } catch (_: Exception) { }
        }
        throw IllegalArgumentException("Неверный формат даты: ${value.take(30)}")
    }

    fun position(value: String, latitude: Double, longitude: Double): Pair<Double, Double> {
        require(latitude in -90.0..90.0 && longitude in -180.0..180.0) { "Некорректные GPS-координаты." }
        val jd = parse(value)
        val t = (jd - 2451545.0) / 36525.0
        val l0 = (280.46646 + t * (36000.76983 + t * 0.0003032)).mod(360.0)
        val m = Math.toRadians((357.52911 + t * (35999.05029 - 0.0001537 * t)).mod(360.0))
        val e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)
        val c = sin(m) * (1.914602 - t * (0.004817 + 0.000014 * t)) +
            sin(2 * m) * (0.019993 - 0.000101 * t) + sin(3 * m) * 0.000289
        val trueLong = l0 + c
        val omega = 125.04 - 1934.136 * t
        val lambda = Math.toRadians(trueLong - 0.00569 - 0.00478 * sin(Math.toRadians(omega)))
        val seconds = 21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))
        val obliq0 = 23.0 + (26.0 + seconds / 60.0) / 60.0
        val obliq = Math.toRadians(obliq0 + 0.00256 * cos(Math.toRadians(omega)))
        val decl = asin(sin(obliq) * sin(lambda))
        val y = tan(obliq / 2).pow(2)
        val eqTime = 4.0 * Math.toDegrees(
            y * sin(2 * Math.toRadians(l0)) - 2 * e * sin(m) +
                4 * e * y * sin(m) * cos(2 * Math.toRadians(l0)) -
                0.5 * y * y * sin(4 * Math.toRadians(l0)) -
                1.25 * e * e * sin(2 * m)
        )
        val utcMinutes = ((jd + 0.5) % 1.0) * 1440.0
        var trueSolarTime = (utcMinutes + eqTime + 4.0 * longitude) % 1440.0
        if (trueSolarTime < 0) trueSolarTime += 1440.0
        var hourAngle = trueSolarTime / 4.0 - 180.0
        if (hourAngle < -180.0) hourAngle += 360.0
        val ha = Math.toRadians(hourAngle)
        val lat = Math.toRadians(latitude)
        val zenith = acos((sin(lat) * sin(decl) + cos(lat) * cos(decl) * cos(ha)).coerceIn(-1.0, 1.0))
        val elevation = 90.0 - Math.toDegrees(zenith)
        val azimuth = (Math.toDegrees(atan2(sin(ha), cos(ha) * sin(lat) - tan(decl) * cos(lat))) + 180.0).mod(360.0)
        return Pair(azimuth, elevation)
    }

    fun result(dt: String, latitude: Double, longitude: Double): JSONObject = try {
        val (az, el) = position(dt, latitude, longitude)
        val normalized = dt.takeIf { it.length >= 19 } ?: dt
        JSONObject().put("success", true)
            .put("azimuth", String.format(Locale.US, "%.2f", az).toDouble())
            .put("elevation", String.format(Locale.US, "%.2f", el).toDouble())
            .put("dt", normalized)
    } catch (e: Exception) {
        JSONObject().put("success", false).put("error", e.message ?: "Не удалось рассчитать положение солнца.")
    }
}
