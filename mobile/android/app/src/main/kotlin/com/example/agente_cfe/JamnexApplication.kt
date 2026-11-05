package com.example.agente_cfe

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.os.Build
import android.util.Log
import androidx.work.Constraints
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.workDataOf
import io.flutter.app.FlutterApplication

class JamnexApplication : FlutterApplication() {
	private var wifiAvailable = false

	override fun onCreate() {
		super.onCreate()
		if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) return

		val connectivityManager =
			getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
		try {
			connectivityManager.registerDefaultNetworkCallback(
				object : ConnectivityManager.NetworkCallback() {
					override fun onAvailable(network: Network) {
						updateWifiState(
							isUsableWifi(connectivityManager.getNetworkCapabilities(network)),
						)
					}

					override fun onCapabilitiesChanged(
						network: Network,
						networkCapabilities: NetworkCapabilities,
					) {
						if (connectivityManager.activeNetwork == network) {
							updateWifiState(isUsableWifi(networkCapabilities))
						}
					}

					override fun onLost(network: Network) {
						val activeNetwork = connectivityManager.activeNetwork
						updateWifiState(
							activeNetwork != null &&
								isUsableWifi(connectivityManager.getNetworkCapabilities(activeNetwork)),
						)
					}
				},
			)
			updateWifiState(
				isUsableWifi(
					connectivityManager.getNetworkCapabilities(connectivityManager.activeNetwork),
				),
			)
		} catch (error: RuntimeException) {
			Log.e("JamnexApplication", "No se pudo observar la conexión de red", error)
		}
	}

	private fun isUsableWifi(capabilities: NetworkCapabilities?): Boolean =
		capabilities?.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) == true &&
			capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) &&
			(Build.VERSION.SDK_INT < Build.VERSION_CODES.M ||
				capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED))

	@Synchronized
	private fun updateWifiState(isAvailable: Boolean) {
		val justConnectedToWifi = isAvailable && !wifiAvailable
		wifiAvailable = isAvailable
		if (!justConnectedToWifi) return

		val preferences = getSharedPreferences("JamnexBackgroundSync", Context.MODE_PRIVATE)
		val baseUrl = preferences.getString("base_url", null)?.trimEnd('/')
		if (baseUrl.isNullOrBlank()) return

		val request = OneTimeWorkRequestBuilder<JamnexSyncWorker>()
			.setConstraints(
				Constraints.Builder()
					.setRequiredNetworkType(androidx.work.NetworkType.CONNECTED)
					.build(),
			)
			.setInputData(workDataOf("base_url" to baseUrl))
			.build()
		try {
			WorkManager.getInstance(applicationContext).enqueueUniqueWork(
				"jamnex_wifi_sync",
				ExistingWorkPolicy.REPLACE,
				request,
			)
			Log.i("JamnexApplication", "Sincronización programada al conectar Wi-Fi")
		} catch (error: IllegalStateException) {
			Log.e("JamnexApplication", "No se pudo programar la sincronización de red", error)
		}
	}
}
