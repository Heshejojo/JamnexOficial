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

/**
 * Observa el transporte predeterminado desde el inicio del proceso y programa
 * una sincronización cuando se conecta o cambia entre Wi-Fi y datos móviles.
 */
class JamnexApplication : FlutterApplication() {
	private var activeNetworkTransport: String? = null

	override fun onCreate() {
		super.onCreate()
		// registerDefaultNetworkCallback no existe en versiones Android anteriores a N.
		if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) return

		val connectivityManager =
			getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
		try {
			connectivityManager.registerDefaultNetworkCallback(
				object : ConnectivityManager.NetworkCallback() {
					override fun onAvailable(network: Network) {
						// No basta con que exista una red: debe ofrecer acceso a Internet.
						updateNetworkState(networkTransport(connectivityManager.getNetworkCapabilities(network)))
					}

					override fun onCapabilitiesChanged(
						network: Network,
						networkCapabilities: NetworkCapabilities,
					) {
						if (connectivityManager.activeNetwork == network) {
							updateNetworkState(networkTransport(networkCapabilities))
						}
					}

					override fun onLost(network: Network) {
						val activeNetwork = connectivityManager.activeNetwork
						updateNetworkState(
							activeNetwork?.let {
								networkTransport(connectivityManager.getNetworkCapabilities(it))
							},
						)
					}
				},
			)
			updateNetworkState(
				connectivityManager.activeNetwork?.let {
					networkTransport(connectivityManager.getNetworkCapabilities(it))
				},
			)
		} catch (error: RuntimeException) {
			Log.e("JamnexApplication", "No se pudo observar la conexión de red", error)
		}
	}

	private fun networkTransport(capabilities: NetworkCapabilities?): String? {
		// Se ignoran redes locales sin Internet y transportes distintos a Wi-Fi/celular.
		if (capabilities?.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) != true) {
			return null
		}
		return when {
			capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) -> "Wi-Fi"
			capabilities.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) -> "datos móviles"
			else -> null
		}
	}

	@Synchronized
	private fun updateNetworkState(transport: String?) {
		// Sincroniza una sola vez por cambio real de transporte para evitar duplicados.
		val networkChanged = transport != null && transport != activeNetworkTransport
		activeNetworkTransport = transport
		if (!networkChanged) return

		val preferences = getSharedPreferences("JamnexBackgroundSync", Context.MODE_PRIVATE)
		// La URL se guarda al programar el trabajo desde Flutter.
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
			// REPLACE cancela una tarea obsoleta si el usuario cambió de tipo de red.
			WorkManager.getInstance(applicationContext).enqueueUniqueWork(
				"jamnex_network_sync",
				ExistingWorkPolicy.REPLACE,
				request,
			)
			Log.i("JamnexApplication", "Sincronización programada al conectar Wi-Fi o datos móviles")
		} catch (error: IllegalStateException) {
			Log.e("JamnexApplication", "No se pudo programar la sincronización de red", error)
		}
	}
}
