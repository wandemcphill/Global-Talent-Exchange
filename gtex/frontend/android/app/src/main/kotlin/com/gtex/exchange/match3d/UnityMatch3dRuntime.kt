package com.gtex.exchange.match3d

import android.app.Activity
import android.content.Context
import android.graphics.Color
import android.os.Handler
import android.os.Looper
import android.view.View
import android.view.ViewGroup
import android.widget.FrameLayout
import io.flutter.plugin.common.EventChannel
import java.io.File
import java.lang.ref.WeakReference
import org.json.JSONArray
import org.json.JSONObject

internal data class UnityMatchSessionState(
    val sessionId: String,
    val matchId: String,
    val status: String,
    val runtime: String = UNITY_MATCH_3D_RUNTIME,
    val platformViewAttached: Boolean = false,
    val ackCount: Int = 0,
    val entityCount: Int = 0,
    val playerCount: Int = 0,
    val lastFrameId: String? = null,
    val phase: String? = null,
    val clockMinute: Double? = null,
    val implicit: Boolean = false,
) {
    fun isOpen(): Boolean = status == "open" || status == "implicit"

    fun toMap(): Map<String, Any?> =
        mapOf(
            "sessionId" to sessionId,
            "matchId" to matchId,
            "status" to status,
            "runtime" to runtime,
            "platformViewAttached" to platformViewAttached,
            "ackCount" to ackCount,
            "entityCount" to entityCount,
            "playerCount" to playerCount,
            "lastFrameId" to lastFrameId,
            "phase" to phase,
            "clockMinute" to clockMinute,
            "implicit" to implicit,
        )

    companion object {
        val IDLE =
            UnityMatchSessionState(
                sessionId = "",
                matchId = "",
                status = "idle",
            )
    }
}

internal object UnityMatch3dRuntime {
    private val mainHandler = Handler(Looper.getMainLooper())

    @Volatile
    private var applicationContext: Context? = null

    @Volatile
    private var hostActivityRef: WeakReference<Activity>? = null

    @Volatile
    private var eventSink: EventChannel.EventSink? = null

    @Volatile
    private var sessionState: UnityMatchSessionState = UnityMatchSessionState.IDLE

    @Volatile
    private var unityReady: Boolean = false

    @Volatile
    private var closingSessionFromHost: Boolean = false

    @Volatile
    private var pendingOpenSessionJson: String? = null

    @Volatile
    private var pendingSceneSyncJson: String? = null

    @Volatile
    private var pendingAttachmentJson: String? = null

    @Volatile
    private var unityPlayer: Any? = null

    @Volatile
    private var unityPlayerView: View? = null

    @Volatile
    private var attachedContainerRef: WeakReference<FrameLayout>? = null

    @Volatile
    private var stagedBootstrapPath: String? = null

    fun attachHostActivity(activity: Activity) {
        applicationContext = activity.applicationContext
        hostActivityRef = WeakReference(activity)
    }

    fun onHostResumed() {
        val player = unityPlayer ?: return
        if (!sessionState.platformViewAttached) {
            return
        }
        UnityPlayerProxy.resume(player)
        UnityPlayerProxy.windowFocusChanged(player, true)
        dispatchPendingCommands()
    }

    fun onHostPaused() {
        val player = unityPlayer ?: return
        UnityPlayerProxy.windowFocusChanged(player, false)
        UnityPlayerProxy.pause(player)
    }

    fun onHostDestroyed(activity: Activity) {
        if (hostActivityRef?.get() !== activity) {
            return
        }
        hostActivityRef = null
        attachedContainerRef = null
        destroyUnityPlayer()
        unityReady = false
        sessionState = sessionState.copy(platformViewAttached = false)
    }

    fun bindEventSink(sink: EventChannel.EventSink?) {
        eventSink = sink
        if (sink != null) {
            emitEvent("RUNTIME_READY")
        }
    }

    fun runtimeInfoMap(): Map<String, Any?> {
        val available = UnityPlayerProxy.isAvailable()
        val activeSession = sessionState
        return mapOf(
            "available" to available,
            "platform" to if (available) "unity" else "android",
            "runtime" to UNITY_MATCH_3D_RUNTIME,
            "viewType" to UNITY_MATCH_3D_VIEW_TYPE,
            "supportsSessions" to available,
            "platformViewAttached" to activeSession.platformViewAttached,
            "sessionStatus" to activeSession.status,
            "sessionId" to activeSession.sessionId,
            "matchId" to activeSession.matchId,
            "ackCount" to activeSession.ackCount,
            "bootstrapPath" to stagedBootstrapPath,
        )
    }

    fun sessionStateMap(): Map<String, Any?> = sessionState.toMap()

    fun stageLiveBootstrap(request: Map<String, Any?>): Map<String, Any?> {
        val context = applicationContext ?: hostActivityRef?.get()?.applicationContext
        if (context == null) {
            return bootstrapFailure(
                request,
                "Android context was unavailable while staging the Unity bootstrap.",
            )
        }

        val matchId = request.stringValue("matchId")
        val baseUrl = request.stringValue("baseUrl")
        val accessToken = request.stringValue("liveAccessToken")
        val refreshToken = request.stringValue("liveRefreshToken")
        if (matchId.isBlank() || baseUrl.isBlank()) {
            return bootstrapFailure(
                request,
                "Unity live bootstrap requires both matchId and baseUrl.",
            )
        }
        if (accessToken.isBlank() && refreshToken.isBlank()) {
            return bootstrapFailure(
                request,
                "Unity live bootstrap requires a live access token or refresh token.",
            )
        }

        return runCatching {
            val bootstrapFile = resolveBootstrapFile(context)
            bootstrapFile.parentFile?.mkdirs()
            bootstrapFile.writeText(
                request.toJsonString(),
                Charsets.UTF_8,
            )
            stagedBootstrapPath = bootstrapFile.absolutePath
            applyBootstrapCommandLineOverride(stagedBootstrapPath)
            mapOf(
                "staged" to true,
                "bootstrapPath" to bootstrapFile.absolutePath,
                "matchId" to matchId,
                "message" to null,
            )
        }.getOrElse { error ->
            bootstrapFailure(
                request,
                "Unity live bootstrap could not be written on Android: ${error.message}",
            )
        }
    }

    fun openSession(request: Map<String, Any?>): Map<String, Any?> {
        if (!UnityPlayerProxy.isAvailable()) {
            return unavailableSessionState(request).toMap()
        }

        val matchId = request.stringValue("matchId", sessionState.matchId)
        val sessionId = request.stringValue("sessionId", fallbackSessionId(matchId))
        sessionState =
            UnityMatchSessionState(
                sessionId = sessionId,
                matchId = matchId,
                status = "open",
                platformViewAttached = sessionState.platformViewAttached,
                ackCount = 0,
                entityCount = 0,
                playerCount = request.intValue("expectedPlayerCount"),
                lastFrameId = request.nullableString("initialFrameId"),
                phase = request.nullableString("initialPhase"),
                clockMinute = request.nullableDouble("initialClockMinute"),
                implicit = false,
            )
        pendingOpenSessionJson = request.toJsonString()
        closingSessionFromHost = false

        ensureUnityPlayerView()
        emitEvent("SESSION_OPENED")
        if (sessionState.platformViewAttached) {
            dispatchPendingCommands()
        }
        return sessionState.toMap()
    }

    fun closeSession(sessionId: String?): Map<String, Any?> {
        val activeSession = sessionState
        val resolvedSessionId =
            sessionId?.takeIf { it.isNotBlank() } ?: activeSession.sessionId
        if (resolvedSessionId.isBlank()) {
            return activeSession.copy(status = "closed", platformViewAttached = false).toMap()
        }

        sessionState =
            activeSession.copy(
                sessionId = resolvedSessionId,
                status = "closed",
                platformViewAttached = false,
                implicit = false,
            )
        pendingSceneSyncJson = null
        pendingAttachmentJson = null
        closingSessionFromHost = true

        if (unityReady) {
            UnityPlayerProxy.sendMessage(
                UNITY_BRIDGE_GAME_OBJECT,
                "CloseSession",
                mapOf("sessionId" to resolvedSessionId).toJsonString(),
            )
        } else {
            emitEvent("SESSION_CLOSED")
        }

        return sessionState.toMap()
    }

    fun applyPayload(payload: Map<String, Any?>): Map<String, Any?> {
        if (!UnityPlayerProxy.isAvailable()) {
            return mapOf("ok" to false, "reason" to "unity_unavailable")
        }

        val activeSession = ensureSessionForPayload(payload)
        val entities = payload.listValue("entities")
        sessionState =
            activeSession.copy(
                matchId = payload.stringValue("matchId", activeSession.matchId),
                platformViewAttached = activeSession.platformViewAttached,
                entityCount = entities.size,
                playerCount =
                    entities.count { entity ->
                        (entity as? Map<*, *>)?.get("type")?.toString()
                            ?.equals("player", ignoreCase = true) == true
                    },
                lastFrameId = payload.nullableString("frameId") ?: activeSession.lastFrameId,
                phase = payload.nullableString("phase") ?: activeSession.phase,
                clockMinute = payload.nullableDouble("clockMinute") ?: activeSession.clockMinute,
            )
        pendingSceneSyncJson = payload.toJsonString()
        dispatchPendingCommands()
        return mapOf(
            "ok" to true,
            "queued" to true,
            "sessionId" to sessionState.sessionId,
            "matchId" to sessionState.matchId,
            "frameId" to sessionState.lastFrameId,
            "phase" to sessionState.phase,
            "playerCount" to sessionState.playerCount,
            "entityCount" to sessionState.entityCount,
            "ackCount" to sessionState.ackCount,
        )
    }

    fun attachPlatformView(container: FrameLayout) {
        attachedContainerRef = WeakReference(container)

        val player = ensureUnityPlayerView()
        val unityView = unityPlayerView
        if (player == null || unityView == null) {
            queuePlatformAttachment(false)
            emitEvent("PLATFORM_VIEW_DETACHED")
            return
        }

        reparentUnityView(unityView, container)
        UnityPlayerProxy.requestFocus(player)
        UnityPlayerProxy.resume(player)
        UnityPlayerProxy.windowFocusChanged(player, true)

        val attachmentChanged = !sessionState.platformViewAttached
        queuePlatformAttachment(true)
        if (unityReady) {
            dispatchPendingCommands()
        } else if (attachmentChanged) {
            emitEvent("PLATFORM_VIEW_ATTACHED")
        }
    }

    fun detachPlatformView(container: FrameLayout) {
        val attachedContainer = attachedContainerRef?.get()
        if (attachedContainer !== container) {
            return
        }

        attachedContainerRef = null
        unityPlayerView?.let { view ->
            (view.parent as? ViewGroup)?.removeView(view)
        }

        val player = unityPlayer
        if (player != null) {
            UnityPlayerProxy.windowFocusChanged(player, false)
            UnityPlayerProxy.pause(player)
        }

        val attachmentChanged = sessionState.platformViewAttached
        queuePlatformAttachment(false)
        if (unityReady) {
            dispatchPendingCommands()
        } else if (attachmentChanged) {
            emitEvent("PLATFORM_VIEW_DETACHED")
        }
    }

    fun onUnityRuntimeEventJson(json: String) {
        val payload = json.toMap() ?: return
        val type = payload.stringValue("type")
        if (type == "RUNTIME_READY") {
            unityReady = true
        }

        sessionState = payload.toSessionState(sessionState)
        if (type == "SESSION_CLOSED") {
            pendingSceneSyncJson = null
            if (closingSessionFromHost) {
                closingSessionFromHost = false
            }
        }

        emitEvent(payload)

        if (type == "RUNTIME_READY") {
            dispatchPendingCommands()
        }
    }

    fun destroyUnityPlayer() {
        unityPlayerView?.let { view ->
            (view.parent as? ViewGroup)?.removeView(view)
        }
        unityPlayerView = null
        unityPlayer?.let(UnityPlayerProxy::destroy)
        unityPlayer = null
    }

    fun dispatchPendingCommands() {
        if (!unityReady) {
            return
        }

        pendingOpenSessionJson?.let { json ->
            if (UnityPlayerProxy.sendMessage(UNITY_BRIDGE_GAME_OBJECT, "OpenSession", json)) {
                pendingOpenSessionJson = null
            }
        }

        pendingAttachmentJson?.let { json ->
            if (
                UnityPlayerProxy.sendMessage(
                    UNITY_BRIDGE_GAME_OBJECT,
                    "SetPlatformViewAttached",
                    json,
                )
            ) {
                pendingAttachmentJson = null
            }
        }

        pendingSceneSyncJson?.let { json ->
            if (
                UnityPlayerProxy.sendMessage(
                    UNITY_BRIDGE_GAME_OBJECT,
                    "HandleSceneSyncWithAck",
                    json,
                )
            ) {
                pendingSceneSyncJson = null
            }
        }
    }

    private fun ensureSessionForPayload(payload: Map<String, Any?>): UnityMatchSessionState {
        val activeSession = sessionState
        val matchId = payload.stringValue("matchId", activeSession.matchId)
        val sessionId = payload.stringValue("sessionId", fallbackSessionId(matchId))
        if (activeSession.isOpen() && activeSession.sessionId == sessionId) {
            return activeSession
        }

        val nextState =
            UnityMatchSessionState(
                sessionId = sessionId,
                matchId = matchId,
                status = if (activeSession.status == "open") "open" else "implicit",
                platformViewAttached = activeSession.platformViewAttached,
                ackCount = activeSession.ackCount,
                entityCount = activeSession.entityCount,
                playerCount = activeSession.playerCount,
                lastFrameId = activeSession.lastFrameId,
                phase = activeSession.phase,
                clockMinute = activeSession.clockMinute,
                implicit = activeSession.status != "open",
            )
        sessionState = nextState
        if (nextState.implicit) {
            emitEvent("SESSION_IMPLICIT")
        }
        return nextState
    }

    private fun unavailableSessionState(request: Map<String, Any?>): UnityMatchSessionState {
        return UnityMatchSessionState(
            sessionId = request.stringValue("sessionId"),
            matchId = request.stringValue("matchId"),
            status = "unavailable",
        )
    }

    private fun ensureUnityPlayerView(): Any? {
        unityPlayer?.let { existingPlayer ->
            if (unityPlayerView != null) {
                return existingPlayer
            }
        }

        val hostActivity = hostActivityRef?.get() ?: return null
        applyBootstrapCommandLineOverride(stagedBootstrapPath)
        val player = UnityPlayerProxy.create(hostActivity) ?: return null
        val view = UnityPlayerProxy.asView(player) ?: return null

        unityPlayer = player
        unityPlayerView = view
        view.setBackgroundColor(Color.BLACK)
        view.layoutParams =
            FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT,
            )
        return player
    }

    private fun reparentUnityView(
        view: View,
        container: FrameLayout,
    ) {
        val existingParent = view.parent as? ViewGroup
        if (existingParent === container) {
            return
        }

        existingParent?.removeView(view)
        container.removeAllViews()
        container.addView(view)
    }

    private fun queuePlatformAttachment(attached: Boolean) {
        sessionState = sessionState.copy(platformViewAttached = attached)
        pendingAttachmentJson = mapOf("attached" to attached).toJsonString()
    }

    private fun fallbackSessionId(matchId: String): String {
        return if (matchId.isBlank()) "" else "unity_match_3d:$matchId"
    }

    private fun bootstrapFailure(
        request: Map<String, Any?>,
        message: String,
    ): Map<String, Any?> {
        return mapOf(
            "staged" to false,
            "bootstrapPath" to (stagedBootstrapPath ?: ""),
            "matchId" to request.stringValue("matchId"),
            "message" to message,
        )
    }

    private fun resolveBootstrapFile(context: Context): File {
        val externalRoot = context.getExternalFilesDir(null)
        val primaryRoot = externalRoot ?: context.filesDir
        return File(File(primaryRoot, "tmp"), "gtex-live-bootstrap.json")
    }

    private fun applyBootstrapCommandLineOverride(bootstrapPath: String?) {
        val resolvedPath = bootstrapPath?.takeIf { it.isNotBlank() } ?: return
        val hostActivity = hostActivityRef?.get() ?: return
        val current = hostActivity.intent?.getStringExtra("unity").orEmpty()
        val flag = "--gtex-bootstrap-path=$resolvedPath"
        val normalized =
            current
                .split(' ')
                .filter { token -> token.isNotBlank() && !token.startsWith("--gtex-bootstrap-path=") }
                .toMutableList()
                .apply { add(flag) }
                .joinToString(separator = " ")
                .trim()
        hostActivity.intent?.putExtra("unity", normalized)
    }

    private fun emitEvent(type: String, extra: Map<String, Any?> = emptyMap()) {
        emitEvent(runtimeInfoMap() + sessionState.toMap() + extra + mapOf("type" to type))
    }

    private fun emitEvent(payload: Map<String, Any?>) {
        val sink = eventSink ?: return
        mainHandler.post {
            sink.success(payload)
        }
    }
}

private const val UNITY_MATCH_3D_RUNTIME = "unity_match_3d"
private const val UNITY_MATCH_3D_VIEW_TYPE = "match_3d/native_view"
private const val UNITY_BRIDGE_GAME_OBJECT = "GTEXUnityBridge"

private fun Map<String, Any?>.toSessionState(
    fallback: UnityMatchSessionState,
): UnityMatchSessionState {
    val status = stringValue("status", stringValue("sessionStatus", fallback.status))
    return UnityMatchSessionState(
        sessionId = stringValue("sessionId", fallback.sessionId),
        matchId = stringValue("matchId", fallback.matchId),
        status = status,
        runtime = stringValue("runtime", fallback.runtime),
        platformViewAttached = booleanValue("platformViewAttached", fallback.platformViewAttached),
        ackCount = intValue("ackCount", fallback.ackCount),
        entityCount = intValue("entityCount", fallback.entityCount),
        playerCount = intValue("playerCount", fallback.playerCount),
        lastFrameId = nullableString("lastFrameId") ?: nullableString("frameId") ?: fallback.lastFrameId,
        phase = nullableString("phase") ?: fallback.phase,
        clockMinute = nullableDouble("clockMinute") ?: fallback.clockMinute,
        implicit =
            booleanValue("implicit", booleanValue("implicitSession", status == "implicit")),
    )
}

private fun Map<String, Any?>.toJsonString(): String {
    return JSONObject().apply {
        for ((key, value) in this@toJsonString) {
            put(key, value.toJsonValue())
        }
    }.toString()
}

private fun Any?.toJsonValue(): Any? {
    return when (this) {
        null -> JSONObject.NULL
        is Map<*, *> ->
            JSONObject().apply {
                for ((nestedKey, nestedValue) in this@toJsonValue) {
                    if (nestedKey is String) {
                        put(nestedKey, nestedValue.toJsonValue())
                    }
                }
            }
        is Iterable<*> ->
            JSONArray().apply {
                for (item in this@toJsonValue) {
                    put(item.toJsonValue())
                }
            }
        is Array<*> ->
            JSONArray().apply {
                for (item in this@toJsonValue) {
                    put(item.toJsonValue())
                }
            }
        else -> this
    }
}

private fun String.toMap(): Map<String, Any?>? {
    return runCatching {
        JSONObject(this).toMap()
    }.getOrNull()
}

private fun JSONObject.toMap(): Map<String, Any?> {
    val normalized = LinkedHashMap<String, Any?>()
    val iterator = keys()
    while (iterator.hasNext()) {
        val key = iterator.next()
        normalized[key] = opt(key).fromJsonValue()
    }
    return normalized
}

private fun JSONArray.toList(): List<Any?> {
    val values = ArrayList<Any?>(length())
    for (index in 0 until length()) {
        values += opt(index).fromJsonValue()
    }
    return values
}

private fun Any?.fromJsonValue(): Any? {
    return when (this) {
        JSONObject.NULL -> null
        is JSONObject -> toMap()
        is JSONArray -> toList()
        else -> this
    }
}

private fun Map<String, Any?>.stringValue(key: String, fallback: String = ""): String {
    return this[key]?.toString()?.takeIf { it.isNotBlank() } ?: fallback
}

private fun Map<String, Any?>.nullableString(key: String): String? {
    return this[key]?.toString()?.takeIf { it.isNotBlank() }
}

private fun Map<String, Any?>.booleanValue(key: String, fallback: Boolean = false): Boolean {
    return when (val value = this[key]) {
        is Boolean -> value
        is Number -> value.toInt() != 0
        is String -> value.equals("true", ignoreCase = true)
        else -> fallback
    }
}

private fun Map<String, Any?>.intValue(key: String, fallback: Int = 0): Int {
    return when (val value = this[key]) {
        is Int -> value
        is Long -> value.toInt()
        is Float -> value.toInt()
        is Double -> value.toInt()
        is Number -> value.toInt()
        is String -> value.toIntOrNull() ?: fallback
        else -> fallback
    }
}

private fun Map<String, Any?>.nullableDouble(key: String): Double? {
    return when (val value = this[key]) {
        is Double -> value
        is Float -> value.toDouble()
        is Int -> value.toDouble()
        is Long -> value.toDouble()
        is Number -> value.toDouble()
        is String -> value.toDoubleOrNull()
        else -> null
    }
}

private fun Map<String, Any?>.listValue(key: String): List<Any?> {
    return (this[key] as? List<*>).orEmpty()
}
