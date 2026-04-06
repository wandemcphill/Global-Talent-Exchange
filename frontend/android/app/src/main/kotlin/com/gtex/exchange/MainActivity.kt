package com.gtex.exchange

import com.gtex.exchange.match3d.NativeMatch3dPlatformViewFactory
import com.gtex.exchange.match3d.NativeMatch3dRuntime
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        flutterEngine.platformViewsController.registry.registerViewFactory(
            NativeMatch3dPlatformViewFactory.viewType,
            NativeMatch3dPlatformViewFactory(),
        )

        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            MATCH_3D_CHANNEL,
        ).setMethodCallHandler { call: MethodCall, result: MethodChannel.Result ->
            when (call.method) {
                "ping",
                "runtimeInfo" -> result.success(NativeMatch3dRuntime.runtimeInfoMap())

                "openSession" -> {
                    val payload = call.arguments as? Map<*, *>
                    if (payload == null) {
                        result.error(
                            "invalid_args",
                            "Expected a map payload for match_3d.openSession.",
                            null,
                        )
                        return@setMethodCallHandler
                    }
                    result.success(NativeMatch3dRuntime.openSession(payload.toStringKeyedMap()))
                }

                "closeSession" -> {
                    val payload = call.arguments as? Map<*, *>
                    val sessionId = payload?.toStringKeyedMap()?.get("sessionId")?.toString()
                    result.success(NativeMatch3dRuntime.closeSession(sessionId))
                }

                "getSessionState" -> result.success(NativeMatch3dRuntime.sessionStateMap())

                "handleEvent" -> {
                    val payload = call.arguments as? Map<*, *>
                    if (payload == null) {
                        result.error(
                            "invalid_args",
                            "Expected a map payload for match_3d.handleEvent.",
                            null,
                        )
                        return@setMethodCallHandler
                    }
                    result.success(NativeMatch3dRuntime.applyPayload(payload.toStringKeyedMap()))
                }

                else -> result.notImplemented()
            }
        }

        EventChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            MATCH_3D_EVENTS_CHANNEL,
        ).setStreamHandler(
            object : EventChannel.StreamHandler {
                override fun onListen(arguments: Any?, events: EventChannel.EventSink) {
                    NativeMatch3dRuntime.bindEventSink(events)
                }

                override fun onCancel(arguments: Any?) {
                    NativeMatch3dRuntime.bindEventSink(null)
                }
            },
        )
    }
}

private const val MATCH_3D_CHANNEL = "match_3d"
private const val MATCH_3D_EVENTS_CHANNEL = "match_3d/events"

private fun Map<*, *>.toStringKeyedMap(): Map<String, Any?> {
    val normalized = LinkedHashMap<String, Any?>()
    for ((key, value) in this) {
        if (key is String) {
            normalized[key] = normalizeChannelValue(value)
        }
    }
    return normalized
}

private fun normalizeChannelValue(value: Any?): Any? {
    return when (value) {
        is Map<*, *> -> value.toStringKeyedMap()
        is List<*> -> value.map(::normalizeChannelValue)
        else -> value
    }
}
