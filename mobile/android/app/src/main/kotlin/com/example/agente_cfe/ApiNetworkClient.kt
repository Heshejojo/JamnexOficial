package com.example.agente_cfe

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.util.Log
import org.json.JSONObject
import java.io.Closeable
import java.io.IOException
import java.net.URL
import javax.net.ssl.HttpsURLConnection
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

class ApiNetworkClient(context: Context) {
	private val connectivityManager =
		context.getSystemService(ConnectivityManager::class.java)
			?: error("ConnectivityManager no disponible")

	fun openSession(): Session {
		val cellular = requestNetwork(
			NetworkCapabilities.TRANSPORT_CELLULAR,
			"celular",
		)
		val wifi = requestNetwork(
			NetworkCapabilities.TRANSPORT_WIFI,
			"Wi-Fi",
		)
		Log.i(
			TAG,
			"Redes API disponibles: celular=${cellular?.network != null}, Wi-Fi=${wifi?.network != null}",
		)
		return Session(cellular, wifi)
	}

	private fun requestNetwork(transport: Int, label: String): NetworkLease? {
		val request = NetworkRequest.Builder()
			.addTransportType(transport)
			.addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
			.build()
		val network = AtomicReference<Network?>()
		val available = CountDownLatch(1)
		val callback = object : ConnectivityManager.NetworkCallback() {
			override fun onAvailable(availableNetwork: Network) {
				Log.i(TAG, "Red $label disponible")
				val linkProperties = connectivityManager.getLinkProperties(availableNetwork)
				Log.i(
					TAG,
					"Propiedades red $label: linkAddresses=${linkProperties?.linkAddresses}, " +
						"dnsServers=${linkProperties?.dnsServers}, routes=${linkProperties?.routes}",
				)
				network.set(availableNetwork)
				available.countDown()
			}

			override fun onUnavailable() {
				Log.w(TAG, "Red $label no disponible")
				available.countDown()
			}

			override fun onLost(lostNetwork: Network) {
				Log.w(TAG, "Red $label perdida")
				network.compareAndSet(lostNetwork, null)
			}
		}

		try {
			connectivityManager.requestNetwork(request, callback, NETWORK_REQUEST_TIMEOUT_MS)
		} catch (error: RuntimeException) {
			Log.e(TAG, "No se pudo solicitar la red $label", error)
			return null
		}

		try {
			available.await(NETWORK_REQUEST_TIMEOUT_MS.toLong(), TimeUnit.MILLISECONDS)
		} catch (error: InterruptedException) {
			Thread.currentThread().interrupt()
			Log.w(TAG, "Se interrumpió la espera de la red $label", error)
		}

		if (network.get() == null) {
			runCatching { connectivityManager.unregisterNetworkCallback(callback) }
			return null
		}
		return NetworkLease(callback, network)
	}

	inner class Session internal constructor(
		private val cellular: NetworkLease?,
		private val wifi: NetworkLease?,
	) : Closeable {
		fun post(
			baseUrl: String,
			endpoint: String,
			payload: JSONObject,
			token: String?,
		): Pair<Int, String> {
			val baseUrls = if (baseUrl.trimEnd('/') == DEFAULT_API_BASE_URL) {
				listOf(baseUrl, INTERNAL_API_BASE_URL)
			} else {
				listOf(baseUrl)
			}
			val networks = listOfNotNull(
				cellular?.network?.get()?.let { "celular" to it },
				wifi?.network?.get()?.let { "Wi-Fi" to it },
			)
			if (networks.isEmpty()) {
				throw IOException("No hay una red celular ni Wi-Fi disponible para la API.")
			}

			var lastError: IOException? = null
			for ((label, network) in networks) {
				for (candidateBaseUrl in baseUrls) {
					try {
						Log.i(TAG, "Enviando $endpoint por $label a $candidateBaseUrl")
						return postOnNetwork(
							network,
							candidateBaseUrl,
							endpoint,
							payload,
							token,
						)
					} catch (error: IOException) {
						Log.w(
							TAG,
							"Falló $endpoint por $label en $candidateBaseUrl: ${error.message}",
							error,
						)
						lastError = error
					}
				}
			}
			throw lastError ?: IOException("No se pudo enviar la solicitud a la API.")
		}

		override fun close() {
			cellular?.close()
			wifi?.close()
		}
	}

	private fun postOnNetwork(
		network: Network,
		baseUrl: String,
		endpoint: String,
		payload: JSONObject,
		token: String?,
	): Pair<Int, String> {
		val url = URL("$baseUrl$endpoint")
		require(url.protocol.equals("https", ignoreCase = true)) {
			"Solo se permiten conexiones HTTPS a la API."
		}
		val connection = network.openConnection(url) as HttpsURLConnection
		try {
			connection.requestMethod = "POST"
			connection.connectTimeout = CONNECT_TIMEOUT_MS
			connection.readTimeout = READ_TIMEOUT_MS
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

	internal inner class NetworkLease(
		private val callback: ConnectivityManager.NetworkCallback,
		val network: AtomicReference<Network?>,
	) : Closeable {
		override fun close() {
			runCatching {
				connectivityManager.unregisterNetworkCallback(callback)
			}.onFailure { error ->
				Log.w(TAG, "No se pudo liberar una red solicitada", error)
			}
		}
	}

	private companion object {
		const val TAG = "JamnexApiNetwork"
		const val DEFAULT_API_BASE_URL = "https://jamnex-api.cfe.mx/api"
		const val INTERNAL_API_BASE_URL = "https://10.14.64.15/api"
		const val NETWORK_REQUEST_TIMEOUT_MS = 20_000
		const val CONNECT_TIMEOUT_MS = 8_000
		const val READ_TIMEOUT_MS = 20_000
	}
}
