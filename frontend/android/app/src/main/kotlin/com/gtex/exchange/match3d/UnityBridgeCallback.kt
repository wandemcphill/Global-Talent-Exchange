package com.gtex.exchange.match3d

import android.os.Handler
import android.os.Looper

internal object UnityBridgeCallback {
    private val mainHandler = Handler(Looper.getMainLooper())

    @JvmStatic
    fun onRuntimeEvent(json: String?) {
        if (json.isNullOrBlank()) {
            return
        }
        mainHandler.post {
            UnityMatch3dRuntime.onUnityRuntimeEventJson(json)
        }
    }
}
