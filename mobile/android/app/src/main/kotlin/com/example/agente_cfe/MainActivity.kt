package com.example.agente_cfe

import android.Manifest
import android.app.usage.NetworkStatsManager
import android.app.ActivityManager
import android.net.ConnectivityManager
import android.content.pm.PackageManager
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.provider.Settings
import android.app.AppOpsManager
import android.os.Build
import android.os.BatteryManager
import android.os.Environment
import android.os.Process
import android.os.StatFs
import android.telephony.TelephonyManager
import android.content.pm.ApplicationInfo
import android.telephony.SubscriptionManager
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.work.Constraints
import androidx.work.ExistingWorkPolicy
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.workDataOf
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.embedding.android.FlutterActivity
import io.flutter.plugin.common.MethodChannel
import java.util.concurrent.TimeUnit
import kotlin.math.roundToInt

class MainActivity : FlutterActivity() {
	private val channelName = "agente_cfe/sim"
	private val permissionRequestCode = 901
	private var usageAccessPromptShown = false

	private fun hasUsageAccess(): Boolean {
		if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) return true
		val appOps = getSystemService(Context.APP_OPS_SERVICE) as AppOpsManager
		return appOps.checkOpNoThrow(
			AppOpsManager.OPSTR_GET_USAGE_STATS,
			Process.myUid(),
			packageName,
		) == AppOpsManager.MODE_ALLOWED
	}

	private fun requestUsageAccessIfNeeded() {
		if (hasUsageAccess() || usageAccessPromptShown) return
		usageAccessPromptShown = true
		startActivity(Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS))
	}

	private fun requiredRuntimePermissions(): Array<String> {
		val permissions = mutableListOf<String>()

		if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
			permissions.add(Manifest.permission.ACCESS_COARSE_LOCATION)
			permissions.add(Manifest.permission.ACCESS_FINE_LOCATION)
		}

		permissions.add(Manifest.permission.READ_PHONE_STATE)

		return permissions.filter {
			ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
		}.distinct().toTypedArray()
	}

	private fun requestRequiredPermissionsIfNeeded() {
		if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) return
		val missingPermissions = requiredRuntimePermissions()
		if (missingPermissions.isNotEmpty()) {
			ActivityCompat.requestPermissions(this, missingPermissions, permissionRequestCode)
		}
	}

	private fun fallbackPhoneNumber(): String? {
		return runCatching { getSystemService(Context.TELEPHONY_SERVICE).let { it as TelephonyManager }.line1Number }
			.getOrNull()
	}

	private fun subscriptionMcc(subscription: android.telephony.SubscriptionInfo): String? {
		return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
			subscription.mccString
		} else {
			subscription.mcc.takeIf { it > 0 }?.toString()?.padStart(3, '0')
		}
	}

	private fun subscriptionMnc(subscription: android.telephony.SubscriptionInfo): String? {
		return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
			subscription.mncString
		} else {
			subscription.mnc.takeIf { it > 0 }?.toString()
		}
	}

	private fun validIccid(value: String?): String? {
		return value
			?.trim()
			?.takeIf { it.length in 18..22 && it.all(Char::isDigit) }
	}

	private fun subscriptionIccid(
		subscription: android.telephony.SubscriptionInfo,
		telephonyManager: TelephonyManager,
	): String? {
		val direct = runCatching { subscription.iccId }.getOrNull()
		val bySubscription = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
			runCatching {
				telephonyManager
					.createForSubscriptionId(subscription.subscriptionId)
					.simSerialNumber
			}.getOrNull()
		} else {
			null
		}
		val defaultSubscription = runCatching { telephonyManager.simSerialNumber }.getOrNull()
		return validIccid(direct)
			?: validIccid(bySubscription)
			?: validIccid(defaultSubscription)
	}

	private fun getDeviceSerial(): String? {
		val frameworkSerial = runCatching {
			when {
				Build.VERSION.SDK_INT >= Build.VERSION_CODES.O -> Build.getSerial()
				else -> Build.SERIAL
			}
		}.getOrNull()?.trim()?.takeUnless { it.isBlank() || it.equals("unknown", true) }
		if (frameworkSerial != null) return frameworkSerial

		return runCatching {
			Runtime.getRuntime().exec(arrayOf("getprop", "ro.serialno")).inputStream
				.bufferedReader()
				.use { it.readLine()?.trim() }
		}.getOrNull()?.takeUnless { it.isNullOrBlank() || it.equals("unknown", true) }
	}

	override fun onCreate(savedInstanceState: android.os.Bundle?) {
		super.onCreate(savedInstanceState)
		if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
			requestRequiredPermissionsIfNeeded()
		}
		requestUsageAccessIfNeeded()
	}

	override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
		super.configureFlutterEngine(flutterEngine)
		MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName).setMethodCallHandler { call, result ->
			if (call.method == "scheduleBackgroundSync") {
				val baseUrl = call.argument<String>("baseUrl")
				if (baseUrl.isNullOrBlank()) {
					result.error("invalid_base_url", "La URL de la API está vacía.", null)
					return@setMethodCallHandler
				}
				applicationContext
					.getSharedPreferences("JamnexBackgroundSync", Context.MODE_PRIVATE)
					.edit()
					.putString("base_url", baseUrl.trimEnd('/'))
					.apply()
				val request = PeriodicWorkRequestBuilder<JamnexSyncWorker>(
					2,
					TimeUnit.HOURS,
				)
					.setConstraints(
						Constraints.Builder()
							.setRequiredNetworkType(NetworkType.CONNECTED)
							.build(),
					)
					.setInputData(workDataOf("base_url" to baseUrl))
					.build()
				WorkManager.getInstance(applicationContext).enqueueUniquePeriodicWork(
					"jamnex_background_sync",
					ExistingPeriodicWorkPolicy.UPDATE,
					request,
				)
				val reconnectRequest = OneTimeWorkRequestBuilder<JamnexSyncWorker>()
					.setConstraints(
						Constraints.Builder()
							.setRequiredNetworkType(NetworkType.CONNECTED)
							.build(),
					)
					.setInitialDelay(1, TimeUnit.MINUTES)
					.setInputData(workDataOf("base_url" to baseUrl))
					.build()
				WorkManager.getInstance(applicationContext).enqueueUniqueWork(
					"jamnex_reconnect_sync",
					ExistingWorkPolicy.KEEP,
					reconnectRequest,
				)
				val watchdogRequest = OneTimeWorkRequestBuilder<JamnexSyncWorker>()
					.setConstraints(
						Constraints.Builder()
							.setRequiredNetworkType(NetworkType.CONNECTED)
							.build(),
					)
					.setInitialDelay(2, TimeUnit.HOURS)
					.setInputData(
						workDataOf(
							"base_url" to baseUrl,
							"network_watchdog" to true,
						),
					)
					.build()
				WorkManager.getInstance(applicationContext).enqueueUniqueWork(
					"jamnex_network_watchdog",
					ExistingWorkPolicy.KEEP,
					watchdogRequest,
				)
				result.success(null)
				return@setMethodCallHandler
			}

			if (call.method == "getTelemetry") {
				requestRequiredPermissionsIfNeeded()
				requestUsageAccessIfNeeded()
				Thread {
					try {
						result.success(collectTelemetry())
					} catch (_: Exception) {
						result.success(emptyMap<String, Any?>())
					}
				}.start()
				return@setMethodCallHandler
			}

			if (call.method != "getSimInfo") {
				result.notImplemented()
				return@setMethodCallHandler
			}

			val missingPermissions = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
				requiredRuntimePermissions()
			} else {
				emptyArray()
			}
			if (missingPermissions.isNotEmpty()) {
				ActivityCompat.requestPermissions(this, missingPermissions, permissionRequestCode)
				result.success(mapOf(
					"readable" to false,
					"sims" to emptyList<Map<String, Any?>>(),
				))
				return@setMethodCallHandler
			}

			try {
				val subscriptionManager =
					getSystemService(Context.TELEPHONY_SUBSCRIPTION_SERVICE) as? SubscriptionManager
				var subscriptions = subscriptionManager?.activeSubscriptionInfoList.orEmpty()
				if (subscriptions.isEmpty() && Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP_MR1) {
					val telephonyManager =
						getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager
					subscriptions = (0 until telephonyManager.phoneCount).mapNotNull { slot ->
						runCatching {
							subscriptionManager?.getActiveSubscriptionInfoForSimSlotIndex(slot)
						}.getOrNull()
					}.distinctBy { it.subscriptionId }
				}
				if (subscriptions.isEmpty()) {
					result.success(
						mapOf(
							"readable" to true,
							"sims" to emptyList<Map<String, Any?>>(),
						),
					)
					return@setMethodCallHandler
				}
				val telephonyManager =
					getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager
				result.success(mapOf("readable" to true, "sims" to subscriptions.map { subscription ->
					mapOf(
						"subscription_id" to subscription.subscriptionId,
						"slot" to subscription.simSlotIndex,
						"operador" to subscription.carrierName?.toString(),
						"pais" to subscription.countryIso,
						"mcc" to subscriptionMcc(subscription),
						"mnc" to subscriptionMnc(subscription),
						"iccid" to subscriptionIccid(subscription, telephonyManager),
						"numero" to (runCatching { subscription.number }.getOrNull() ?: fallbackPhoneNumber()),
						"carrier_id" to if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) subscription.carrierId else null,
						"esim" to if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) subscription.isEmbedded else false,
						"activa" to true,
					)
				}))
			} catch (_: SecurityException) {
				result.success(mapOf(
					"readable" to false,
					"sims" to emptyList<Map<String, Any?>>(),
				))
			}
		}
	}

	override fun onRequestPermissionsResult(
		requestCode: Int,
		permissions: Array<out String>,
		grantResults: IntArray,
	) {
		super.onRequestPermissionsResult(requestCode, permissions, grantResults)
		if (requestCode == permissionRequestCode) {
			requestUsageAccessIfNeeded()
		}
	}

	private fun collectTelemetry(): Map<String, Any?> {
		val activityManager = getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
		val telephonyManager = getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager
		val memory = ActivityManager.MemoryInfo()
		activityManager.getMemoryInfo(memory)
		val storage = StatFs(Environment.getDataDirectory().path)
		val totalStorageBytes = storage.totalBytes.toDouble()
		val availableStorageBytes = storage.availableBytes.toDouble()
		val battery = registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
		val batteryPercent = battery?.let {
			val level = it.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
			val scale = it.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
			if (level < 0 || scale <= 0) null
			else (level * 100.0 / scale).roundToInt().coerceIn(0, 100)
		}
		val temperature = battery?.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, Int.MIN_VALUE)
			?.takeUnless { it == Int.MIN_VALUE }?.div(10.0)

		return mapOf(
			"device_uuid" to Settings.Secure.getString(
				contentResolver,
				Settings.Secure.ANDROID_ID,
			)?.takeIf { it.isNotBlank() },
			"ram_total_mb" to bytesToMb(memory.totalMem),
			"ram_used_mb" to bytesToMb((memory.totalMem - memory.availMem)),
			"ram_available_mb" to bytesToMb(memory.availMem),
			"storage_total_mb" to bytesToMb(totalStorageBytes),
			"storage_used_mb" to bytesToMb((totalStorageBytes - availableStorageBytes).toLong()),
			"storage_available_mb" to bytesToMb(availableStorageBytes.toLong()),
			"battery_temperature_c" to temperature,
			"battery_percent" to batteryPercent,
			"serial" to getDeviceSerial(),
			"imei_1" to if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) runCatching { telephonyManager.getImei(0) }.getOrNull() else null,
			"imei_2" to if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) runCatching { telephonyManager.getImei(1) }.getOrNull() else null,
			"mobile_data_day_mb" to queryMobileDataUsage(1),
			"mobile_data_sim_slot" to defaultDataSimSlot(),
			"mobile_data_limit_mb" to 2048.0,
			"applications" to visibleApplications(),
			"network_technology" to networkTechnology(telephonyManager),
			"carrier_name" to telephonyManager.networkOperatorName,
			"carrier_id" to if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) telephonyManager.simCarrierId else null,
			"roaming" to runCatching { telephonyManager.isNetworkRoaming }.getOrDefault(false),
		)
	}

	private fun defaultDataSimSlot(): Int? = try {
		val manager = getSystemService(SubscriptionManager::class.java)
		val subscriptions = manager?.activeSubscriptionInfoList.orEmpty()
		if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
			val defaultId = SubscriptionManager.getDefaultDataSubscriptionId()
			subscriptions.firstOrNull { it.subscriptionId == defaultId }?.simSlotIndex
		} else {
			subscriptions.singleOrNull()?.simSlotIndex
		}
	} catch (_: SecurityException) {
		null
	}

	private fun bytesToMb(value: Long): Double {
		return value.toDouble() / (1024.0 * 1024.0)
	}

	private fun bytesToMb(value: Double): Double {
		return value / (1024.0 * 1024.0)
	}

	private fun queryMobileDataUsage(days: Int): Double? {
		return try {
			if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) return null
			val manager = getSystemService(Context.NETWORK_STATS_SERVICE) as NetworkStatsManager
			val end = System.currentTimeMillis()
			val startCalendar = java.util.Calendar.getInstance().apply {
				timeInMillis = end
				set(java.util.Calendar.HOUR_OF_DAY, 0)
				set(java.util.Calendar.MINUTE, 0)
				set(java.util.Calendar.SECOND, 0)
				set(java.util.Calendar.MILLISECOND, 0)
				add(java.util.Calendar.DAY_OF_YEAR, -(days - 1))
			}
			val subscriberId = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
				null
			} else {
				(getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager).subscriberId
			}
			val bucket = manager.querySummaryForDevice(
				ConnectivityManager.TYPE_MOBILE,
				subscriberId,
				startCalendar.timeInMillis,
				end,
			)
			(bucket.rxBytes + bucket.txBytes).toDouble() / (1024.0 * 1024.0)
		} catch (_: Exception) {
			null
		}
	}

	private fun networkTechnology(telephonyManager: TelephonyManager): String? {
		return runCatching {
			when (telephonyManager.dataNetworkType) {
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
		}.getOrNull()
	}

	private fun visibleApplications(): List<Map<String, Any?>> {
		return packageManager.getInstalledApplications(PackageManager.GET_META_DATA).map { app ->
			val packageInfo = runCatching { packageManager.getPackageInfo(app.packageName, 0) }.getOrNull()
			mapOf(
				"package_name" to app.packageName,
				"name" to app.loadLabel(packageManager).toString(),
				"version" to packageInfo?.versionName,
				"system" to ((app.flags and ApplicationInfo.FLAG_SYSTEM) != 0),
			)
		}
	}
}
