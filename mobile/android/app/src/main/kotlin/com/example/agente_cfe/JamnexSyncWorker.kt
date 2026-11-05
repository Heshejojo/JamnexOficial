package com.example.agente_cfe

import android.app.ActivityManager
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.app.usage.NetworkStatsManager
import android.os.BatteryManager
import android.os.Build
import android.os.Environment
import android.os.StatFs
import android.provider.Settings
import android.telephony.SubscriptionInfo
import android.telephony.SubscriptionManager
import android.telephony.TelephonyManager
import android.util.Log
import androidx.work.Worker
import androidx.work.WorkerParameters
import androidx.work.Constraints
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.workDataOf
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.Calendar
import kotlin.math.roundToInt

class JamnexSyncWorker(
	context: Context,
	parameters: WorkerParameters,
) : Worker(context, parameters) {
	override fun doWork(): Result {
		val baseUrl = inputData.getString("base_url")?.trimEnd('/')
		if (baseUrl.isNullOrBlank()) return Result.failure()

		Log.i("JamnexSyncWorker", "Sincronización en segundo plano iniciada")
		return try {
			sync(baseUrl)
			Log.i("JamnexSyncWorker", "Sincronización en segundo plano completada")
			if (inputData.getBoolean("network_watchdog", false)) {
				scheduleNextNetworkWatchdog(baseUrl)
			}
			Result.success()
		} catch (error: Exception) {
			Log.e("JamnexSyncWorker", "La sincronización en segundo plano falló", error)
			Result.retry()
		}
	}

	private fun scheduleNextNetworkWatchdog(baseUrl: String) {
		val request = OneTimeWorkRequestBuilder<JamnexSyncWorker>()
			.setConstraints(
				Constraints.Builder()
					.setRequiredNetworkType(NetworkType.CONNECTED)
					.build(),
			)
			.setInitialDelay(2, java.util.concurrent.TimeUnit.HOURS)
			.setInputData(
				workDataOf(
					"base_url" to baseUrl,
					"network_watchdog" to true,
				),
			)
			.build()
		WorkManager.getInstance(applicationContext).enqueueUniqueWork(
			"jamnex_network_watchdog",
			ExistingWorkPolicy.APPEND_OR_REPLACE,
			request,
		)
	}

	private fun sync(baseUrl: String) {
		val deviceUuid = Settings.Secure.getString(
			applicationContext.contentResolver,
			Settings.Secure.ANDROID_ID,
		)?.takeIf { it.isNotBlank() } ?: error("Android ID no disponible")

		val telephony = applicationContext.getSystemService(TelephonyManager::class.java)
		val memory = ActivityManager.MemoryInfo()
		(applicationContext.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager)
			.getMemoryInfo(memory)
		val storage = StatFs(Environment.getDataDirectory().path)
		val totalStorage = storage.totalBytes
		val availableStorage = storage.availableBytes
		val battery = applicationContext.registerReceiver(
			null,
			IntentFilter(Intent.ACTION_BATTERY_CHANGED),
		)
		val batteryLevel = battery?.let {
			val level = it.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
			val scale = it.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
			if (level < 0 || scale <= 0) null
			else (level * 100.0 / scale).roundToInt().coerceIn(0, 100)
		}
		val batteryStatus = when (
			battery?.getIntExtra(BatteryManager.EXTRA_STATUS, -1)
		) {
			BatteryManager.BATTERY_STATUS_CHARGING -> "CARGANDO"
			BatteryManager.BATTERY_STATUS_FULL -> "CARGADA"
			BatteryManager.BATTERY_STATUS_DISCHARGING,
			BatteryManager.BATTERY_STATUS_NOT_CHARGING -> "DESCARGANDO"
			else -> "DESCONOCIDO"
		}
		val batteryTemperature = battery
			?.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, Int.MIN_VALUE)
			?.takeIf { it != Int.MIN_VALUE }
			?.div(10.0)
		val now = System.currentTimeMillis()
		val connection = connectionState()
		val ramTotalMb = bytesToMb(memory.totalMem)
		val ramAvailableMb = bytesToMb(memory.availMem)
		val storageTotalMb = bytesToMb(totalStorage)
		val storageAvailableMb = bytesToMb(availableStorage)
		val devicePayload = json(
			"device_uuid" to deviceUuid,
			"fabricante" to Build.MANUFACTURER,
			"modelo" to Build.MODEL,
			"version_android" to Build.VERSION.RELEASE,
			"android_sdk" to Build.VERSION.SDK_INT,
			"serial" to deviceSerial(),
			"imei_1" to imei(telephony, 0),
			"imei_2" to imei(telephony, 1),
			"ram_total" to ramTotalMb,
			"almacenamiento_total" to storageTotalMb,
		)
		val storedToken = applicationContext
			.getSharedPreferences("FlutterSharedPreferences", Context.MODE_PRIVATE)
			.getString("flutter.device_token", null)
			?.takeIf { it.isNotBlank() }
		var token = storedToken ?: registerDevice(baseUrl, devicePayload)

		token = postDevice(
			baseUrl,
			"/device/status/",
			json(
				"device_uuid" to deviceUuid,
				"battery_percent" to batteryLevel,
				"battery_status" to batteryStatus,
				"connected" to connection.first,
				"ram_total" to ramTotalMb,
				"ram_usada" to (ramTotalMb - ramAvailableMb).coerceAtLeast(0),
				"ram_disponible" to ramAvailableMb,
				"almacenamiento_total" to storageTotalMb,
				"almacenamiento_usado" to (storageTotalMb - storageAvailableMb).coerceAtLeast(0),
				"almacenamiento_disponible" to storageAvailableMb,
				"battery_temperature" to batteryTemperature,
				"timestamp" to java.time.Instant.ofEpochMilli(now).toString(),
			),
			token,
			devicePayload,
		)
		token = postDevice(
			baseUrl,
			"/device/network/",
			json("tipo_conexion" to connection.second),
			token,
			devicePayload,
		)

		val subscriptionRead = activeSubscriptions()
		val subscriptions = subscriptionRead.orEmpty()
		subscriptions.forEach { subscription ->
			token = postDevice(
				baseUrl,
				"/device/sim/",
				json(
					"sim_uuid" to subscription.subscriptionId.toString(),
					"iccid" to runCatching { subscription.iccId }.getOrNull(),
					"slot" to subscription.simSlotIndex,
					"operador_nombre" to subscription.carrierName?.toString(),
					"pais" to subscription.countryIso,
					"mcc" to subscriptionMcc(subscription),
					"mnc" to subscriptionMnc(subscription),
					"numero_telefonico" to runCatching { subscription.number }.getOrNull(),
					"carrier_id" to if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) subscription.carrierId else null,
					"esim" to if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) subscription.isEmbedded else false,
					"tecnologia" to networkTechnology(telephony),
					"roaming" to runCatching { telephony.isNetworkRoaming }.getOrDefault(false),
				),
				token,
				devicePayload,
			)
		}
		if (subscriptionRead != null) {
			token = postDevice(
				baseUrl,
				"/device/sims/status/",
				json(
					"sim_count" to subscriptions.size,
					"sim_slots" to subscriptions.map { it.simSlotIndex },
				),
				token,
				devicePayload,
				badRequestFallback = json("sim_count" to subscriptions.size),
				allowNotFound = true,
			)
		}

		val dataSimSlot = defaultDataSimSlot(subscriptions)
		val monthDays = Calendar.getInstance().get(Calendar.DAY_OF_MONTH)
		val monthlyUsage = mobileUsageMb(monthDays)
		for (dayOffset in 0 until monthDays) {
			val dailyUsage = mobileUsageForDay(dayOffset)
			if (dailyUsage == null) continue
			token = postDevice(
				baseUrl,
				"/device/consumption/",
				json(
					"consumo_datos_movil" to dailyUsage,
					"periodo" to "diario",
					"sim_slot" to (dataSimSlot ?: -1),
					"fecha" to dayEndIso(dayOffset),
				),
				token,
				devicePayload,
			)
		}
		if (monthlyUsage != null) {
			token = postDevice(
				baseUrl,
				"/device/consumption/",
				json(
					"consumo_datos_movil" to monthlyUsage,
					"periodo" to "mensual",
					"sim_slot" to (dataSimSlot ?: -1),
				),
				token,
				devicePayload,
			)
		}
	}

	private fun postDevice(
		baseUrl: String,
		endpoint: String,
		payload: JSONObject,
		currentToken: String,
		devicePayload: JSONObject,
		allowNotFound: Boolean = false,
		badRequestFallback: JSONObject? = null,
	): String {
		var effectivePayload = payload
		var response = request(baseUrl, endpoint, effectivePayload, currentToken)
		if (response.first == HttpURLConnection.HTTP_BAD_REQUEST && badRequestFallback != null) {
			Log.w(
				"JamnexSyncWorker",
				"El backend rechazó el reporte extendido de SIM ($endpoint); se reintentará con el formato básico: ${response.second}",
			)
			effectivePayload = badRequestFallback
			response = request(baseUrl, endpoint, effectivePayload, currentToken)
		}
		if (response.first in 200..299) return currentToken
		if (allowNotFound && response.first == HttpURLConnection.HTTP_NOT_FOUND) {
			Log.w("JamnexSyncWorker", "El backend aún no admite $endpoint; se omite este reporte")
			return currentToken
		}
		if (
			response.first != HttpURLConnection.HTTP_UNAUTHORIZED &&
			response.first != HttpURLConnection.HTTP_FORBIDDEN
		) {
			error("Backend respondió HTTP ${response.first} en $endpoint: ${response.second}")
		}
		val refreshedToken = registerDevice(baseUrl, devicePayload)
		val retryResponse = request(baseUrl, endpoint, effectivePayload, refreshedToken)
		if (allowNotFound && retryResponse.first == HttpURLConnection.HTTP_NOT_FOUND) {
			Log.w("JamnexSyncWorker", "El backend aún no admite $endpoint; se omite este reporte")
			return refreshedToken
		}
		if (retryResponse.first !in 200..299) {
			error("Backend respondió HTTP ${retryResponse.first} en $endpoint: ${retryResponse.second}")
		}
		return refreshedToken
	}

	private fun registerDevice(baseUrl: String, payload: JSONObject): String {
		val response = request(baseUrl, "/device/register/", payload, null)
		if (response.first !in 200..299) {
			error("No se pudo registrar el dispositivo: HTTP ${response.first}")
		}
		val token = JSONObject(response.second).optString("token").takeIf { it.isNotBlank() }
			?: error("El backend no devolvió el token del dispositivo")
		applicationContext
			.getSharedPreferences("FlutterSharedPreferences", Context.MODE_PRIVATE)
			.edit()
			.putString("flutter.device_token", token)
			.apply()
		return token
	}

	private fun request(
		baseUrl: String,
		endpoint: String,
		payload: JSONObject,
		token: String?,
	): Pair<Int, String> {
		val connection = URL("$baseUrl$endpoint").openConnection() as HttpURLConnection
		try {
			connection.requestMethod = "POST"
			connection.connectTimeout = 20_000
			connection.readTimeout = 20_000
			connection.doOutput = true
			connection.setRequestProperty("Content-Type", "application/json")
			if (token != null) connection.setRequestProperty("Authorization", "Device $token")
			connection.outputStream.use { output ->
				output.write(payload.toString().toByteArray(Charsets.UTF_8))
			}
			val status = connection.responseCode
			val bodyStream = if (status in 200..299) connection.inputStream else connection.errorStream
			val body = bodyStream?.bufferedReader()?.use { it.readText() }.orEmpty()
			return status to body
		} finally {
			connection.disconnect()
		}
	}

	private fun connectionState(): Pair<Boolean, String> {
		val manager = applicationContext.getSystemService(ConnectivityManager::class.java)
		val capabilities = manager.getNetworkCapabilities(manager.activeNetwork)
			?: return false to "SIN_CONEXION"
		return when {
			capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) -> true to "WIFI"
			capabilities.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) -> true to "DATOS_MOVILES"
			else -> true to "SIN_CONEXION"
		}
	}

	private fun activeSubscriptions(): List<SubscriptionInfo>? = try {
		val manager = applicationContext.getSystemService(SubscriptionManager::class.java)
			?: return null
		manager.activeSubscriptionInfoList.orEmpty()
	} catch (_: SecurityException) {
		null
	}

	private fun defaultDataSimSlot(subscriptions: List<SubscriptionInfo>): Int? = try {
		val manager = applicationContext.getSystemService(SubscriptionManager::class.java)
		if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
			val defaultId = SubscriptionManager.getDefaultDataSubscriptionId()
			subscriptions.firstOrNull { it.subscriptionId == defaultId }?.simSlotIndex
		} else {
			subscriptions.singleOrNull()?.simSlotIndex
		}
	} catch (_: SecurityException) {
		null
	}

	private fun mobileUsageMb(days: Int): Double? {
		return try {
			val telephony = applicationContext.getSystemService(TelephonyManager::class.java)
			val subscriberId = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
				null
			} else {
				telephony.subscriberId ?: return null
			}
			val end = System.currentTimeMillis()
			val start = Calendar.getInstance().apply {
				timeInMillis = end
				set(Calendar.HOUR_OF_DAY, 0)
				set(Calendar.MINUTE, 0)
				set(Calendar.SECOND, 0)
				set(Calendar.MILLISECOND, 0)
				add(Calendar.DAY_OF_YEAR, -(days - 1))
			}
			val manager = applicationContext.getSystemService(NetworkStatsManager::class.java)
			val bucket = manager.querySummaryForDevice(
				ConnectivityManager.TYPE_MOBILE,
				subscriberId,
				start.timeInMillis,
				end,
			)
			(bucket.rxBytes + bucket.txBytes).toDouble() / (1024.0 * 1024.0)
		} catch (_: Exception) {
			null
		}
	}

	private fun mobileUsageForDay(dayOffset: Int): Double? {
		return try {
			val telephony = applicationContext.getSystemService(TelephonyManager::class.java)
			val subscriberId = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
				null
			} else {
				telephony.subscriberId ?: return null
			}
			val end = Calendar.getInstance().apply {
				add(Calendar.DAY_OF_YEAR, -dayOffset)
				set(Calendar.HOUR_OF_DAY, 23)
				set(Calendar.MINUTE, 59)
				set(Calendar.SECOND, 59)
				set(Calendar.MILLISECOND, 999)
			}
			val start = (end.clone() as Calendar).apply {
				set(Calendar.HOUR_OF_DAY, 0)
				set(Calendar.MINUTE, 0)
				set(Calendar.SECOND, 0)
				set(Calendar.MILLISECOND, 0)
			}
			val manager = applicationContext.getSystemService(NetworkStatsManager::class.java)
			val bucket = manager.querySummaryForDevice(
				ConnectivityManager.TYPE_MOBILE,
				subscriberId,
				start.timeInMillis,
				end.timeInMillis,
			)
			(bucket.rxBytes + bucket.txBytes).toDouble() / (1024.0 * 1024.0)
		} catch (_: Exception) {
			null
		}
	}

	private fun dayEndIso(dayOffset: Int): String =
		java.time.Instant.ofEpochMilli(
			Calendar.getInstance().apply {
				add(Calendar.DAY_OF_YEAR, -dayOffset)
				set(Calendar.HOUR_OF_DAY, 23)
				set(Calendar.MINUTE, 59)
				set(Calendar.SECOND, 59)
				set(Calendar.MILLISECOND, 999)
			}.timeInMillis,
		).toString()

	private fun deviceSerial(): String? {
		val frameworkSerial = runCatching {
			if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) Build.getSerial() else Build.SERIAL
		}.getOrNull()?.trim()?.takeUnless { it.isBlank() || it.equals("unknown", true) }
		if (frameworkSerial != null) return frameworkSerial

		return runCatching {
			Runtime.getRuntime().exec(arrayOf("getprop", "ro.serialno")).inputStream
				.bufferedReader()
				.use { it.readLine()?.trim() }
		}.getOrNull()?.takeUnless { it.isNullOrBlank() || it.equals("unknown", true) }
	}

	private fun imei(telephony: TelephonyManager, slot: Int): String? =
		if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
			runCatching { telephony.getImei(slot) }.getOrNull()
		} else {
			null
		}

	private fun subscriptionMcc(subscription: SubscriptionInfo): String? =
		if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
			subscription.mccString
		} else {
			subscription.mcc.takeIf { it > 0 }?.toString()?.padStart(3, '0')
		}

	private fun subscriptionMnc(subscription: SubscriptionInfo): String? =
		if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
			subscription.mncString
		} else {
			subscription.mnc.takeIf { it > 0 }?.toString()
		}

	private fun networkTechnology(telephony: TelephonyManager): String = when (
		telephony.dataNetworkType
	) {
		TelephonyManager.NETWORK_TYPE_GPRS,
		TelephonyManager.NETWORK_TYPE_EDGE,
		TelephonyManager.NETWORK_TYPE_CDMA,
		TelephonyManager.NETWORK_TYPE_1xRTT,
		TelephonyManager.NETWORK_TYPE_IDEN -> "2G"
		TelephonyManager.NETWORK_TYPE_UMTS,
		TelephonyManager.NETWORK_TYPE_EVDO_0,
		TelephonyManager.NETWORK_TYPE_EVDO_A,
		TelephonyManager.NETWORK_TYPE_EVDO_B,
		TelephonyManager.NETWORK_TYPE_HSDPA,
		TelephonyManager.NETWORK_TYPE_HSUPA,
		TelephonyManager.NETWORK_TYPE_HSPA,
		TelephonyManager.NETWORK_TYPE_HSPAP -> "3G"
		TelephonyManager.NETWORK_TYPE_LTE -> "4G"
		TelephonyManager.NETWORK_TYPE_NR -> "5G"
		else -> "Desconocida"
	}

	private fun bytesToMb(value: Long): Int =
		(value.toDouble() / (1024.0 * 1024.0)).toInt()

	private fun json(vararg fields: Pair<String, Any?>): JSONObject =
		JSONObject().apply {
			fields.forEach { (key, value) ->
				if (value != null) put(key, value)
			}
		}
}
