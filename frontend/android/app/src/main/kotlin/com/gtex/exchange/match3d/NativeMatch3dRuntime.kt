package com.gtex.exchange.match3d

import io.flutter.plugin.common.EventChannel
import java.util.concurrent.CopyOnWriteArraySet
import kotlin.math.sqrt

internal data class NativeVec3(
    val x: Float,
    val y: Float,
    val z: Float,
) {
    operator fun minus(other: NativeVec3): NativeVec3 =
        NativeVec3(x - other.x, y - other.y, z - other.z)

    operator fun plus(other: NativeVec3): NativeVec3 =
        NativeVec3(x + other.x, y + other.y, z + other.z)

    fun dot(other: NativeVec3): Float = (x * other.x) + (y * other.y) + (z * other.z)

    fun cross(other: NativeVec3): NativeVec3 =
        NativeVec3(
            x = (y * other.z) - (z * other.y),
            y = (z * other.x) - (x * other.z),
            z = (x * other.y) - (y * other.x),
        )

    fun magnitude(): Float = sqrt(dot(this))

    fun normalized(): NativeVec3 {
        val length = magnitude()
        if (length <= 0.0001f) {
            return ZERO
        }
        return NativeVec3(x / length, y / length, z / length)
    }

    companion object {
        val ZERO = NativeVec3(0f, 0f, 0f)

        fun fromMap(value: Any?): NativeVec3 {
            val payload = value as? Map<*, *> ?: return ZERO
            return NativeVec3(
                x = payload.floatValue("x"),
                y = payload.floatValue("y"),
                z = payload.floatValue("z"),
            )
        }
    }
}

internal data class NativeCameraState(
    val mode: String,
    val projectionPreset: String,
    val position: NativeVec3,
    val target: NativeVec3,
) {
    companion object {
        val DEFAULT = NativeCameraState(
            mode = "tactical",
            projectionPreset = "tactical_high",
            position = NativeVec3(x = -28f, y = 34f, z = 0f),
            target = NativeVec3.ZERO,
        )

        fun fromMap(value: Any?): NativeCameraState {
            val payload = value as? Map<*, *> ?: return DEFAULT
            return NativeCameraState(
                mode = payload.stringValue("mode", DEFAULT.mode),
                projectionPreset = payload.stringValue("projectionPreset", DEFAULT.projectionPreset),
                position = NativeVec3.fromMap(payload["position"]),
                target = NativeVec3.fromMap(payload["target"]),
            )
        }
    }
}

internal data class NativeNodePayload(
    val kind: String,
    val side: String?,
    val highlighted: Boolean,
    val hasPossession: Boolean,
    val speedRatio: Float,
    val staminaPct: Int,
    val state: String?,
    val trajectoryType: String?,
    val elevation: Float,
    val lengthMeters: Float?,
    val widthMeters: Float?,
) {
    companion object {
        val EMPTY = NativeNodePayload(
            kind = "",
            side = null,
            highlighted = false,
            hasPossession = false,
            speedRatio = 0f,
            staminaPct = 0,
            state = null,
            trajectoryType = null,
            elevation = 0f,
            lengthMeters = null,
            widthMeters = null,
        )

        fun fromMap(value: Any?): NativeNodePayload {
            val payload = value as? Map<*, *> ?: return EMPTY
            return NativeNodePayload(
                kind = payload.stringValue("kind"),
                side = payload.nullableString("side"),
                highlighted = payload.booleanValue("highlighted"),
                hasPossession = payload.booleanValue("hasPossession"),
                speedRatio = payload.floatValue("speedRatio"),
                staminaPct = payload.intValue("staminaPct"),
                state = payload.nullableString("state"),
                trajectoryType = payload.nullableString("trajectoryType"),
                elevation = payload.floatValue("elevation"),
                lengthMeters = payload.nullableFloat("lengthMeters"),
                widthMeters = payload.nullableFloat("widthMeters"),
            )
        }
    }
}

internal data class NativeSceneNode(
    val id: String,
    val type: String,
    val position: NativeVec3,
    val payload: NativeNodePayload,
) {
    companion object {
        fun fromMap(value: Any?): NativeSceneNode? {
            val payload = value as? Map<*, *> ?: return null
            val id = payload.stringValue("id")
            val type = payload.stringValue("type")
            if (id.isBlank() || type.isBlank()) {
                return null
            }
            return NativeSceneNode(
                id = id,
                type = type,
                position = NativeVec3.fromMap(payload["position"]),
                payload = NativeNodePayload.fromMap(payload["payload"]),
            )
        }
    }
}

internal data class NativeMatchFrame(
    val matchId: String,
    val frameId: String,
    val clockMinute: Float,
    val phase: String,
    val homeScore: Int,
    val awayScore: Int,
    val camera: NativeCameraState,
    val actionType: String,
    val entities: List<NativeSceneNode>,
    val pitchLengthMeters: Float,
    val pitchWidthMeters: Float,
) {
    val playerCount: Int
        get() = entities.count { it.type.equals("player", ignoreCase = true) }

    val entityCount: Int
        get() = entities.size

    val ballNode: NativeSceneNode?
        get() = entities.firstOrNull { it.type.equals("ball", ignoreCase = true) }

    companion object {
        val EMPTY = NativeMatchFrame(
            matchId = "",
            frameId = "",
            clockMinute = 0f,
            phase = "idle",
            homeScore = 0,
            awayScore = 0,
            camera = NativeCameraState.DEFAULT,
            actionType = "neutral",
            entities = emptyList(),
            pitchLengthMeters = 105f,
            pitchWidthMeters = 68f,
        )

        fun fromMap(value: Map<String, Any?>): NativeMatchFrame {
            val entities = (value["entities"] as? List<*>)
                .orEmpty()
                .mapNotNull(NativeSceneNode::fromMap)
            val pitchNode = entities.firstOrNull { it.type.equals("pitch", ignoreCase = true) }
            return NativeMatchFrame(
                matchId = value.stringValue("matchId"),
                frameId = value.stringValue("frameId"),
                clockMinute = value.floatValue("clockMinute"),
                phase = value.stringValue("phase", "in_play"),
                homeScore = value.intValue("homeScore"),
                awayScore = value.intValue("awayScore"),
                camera = NativeCameraState.fromMap(value["camera"]),
                actionType = (value["action"] as? Map<*, *>).stringValue("type", "neutral"),
                entities = entities,
                pitchLengthMeters = pitchNode?.payload?.lengthMeters ?: 105f,
                pitchWidthMeters = pitchNode?.payload?.widthMeters ?: 68f,
            )
        }
    }
}

internal data class NativeMatchSessionState(
    val sessionId: String,
    val matchId: String,
    val status: String,
    val runtime: String = NATIVE_MATCH_3D_RUNTIME,
    val platformViewAttached: Boolean = false,
    val ackCount: Int = 0,
    val entityCount: Int = 0,
    val playerCount: Int = 0,
    val lastFrameId: String? = null,
    val phase: String? = null,
    val clockMinute: Float? = null,
    val implicit: Boolean = false,
) {
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
        val IDLE = NativeMatchSessionState(
            sessionId = "",
            matchId = "",
            status = "idle",
        )
    }
}

internal object NativeMatch3dRuntime {
    interface Listener {
        fun onFrameUpdated(frame: NativeMatchFrame)
    }

    private val listeners = CopyOnWriteArraySet<Listener>()

    @Volatile
    private var latestFrame: NativeMatchFrame = NativeMatchFrame.EMPTY

    @Volatile
    private var eventSink: EventChannel.EventSink? = null

    @Volatile
    private var sessionState: NativeMatchSessionState = NativeMatchSessionState.IDLE

    @Volatile
    private var platformViewAttached: Boolean = false

    fun snapshot(): NativeMatchFrame = latestFrame

    fun runtimeInfoMap(): Map<String, Any?> {
        val activeSession = sessionState
        return mapOf(
            "available" to true,
            "platform" to "android",
            "runtime" to NATIVE_MATCH_3D_RUNTIME,
            "viewType" to NATIVE_MATCH_3D_VIEW_TYPE,
            "supportsSessions" to true,
            "platformViewAttached" to platformViewAttached,
            "sessionStatus" to activeSession.status,
            "sessionId" to activeSession.sessionId,
            "matchId" to activeSession.matchId,
            "ackCount" to activeSession.ackCount,
        )
    }

    fun sessionStateMap(): Map<String, Any?> = sessionState.toMap()

    fun addListener(listener: Listener) {
        listeners.add(listener)
        listener.onFrameUpdated(latestFrame)
    }

    fun removeListener(listener: Listener) {
        listeners.remove(listener)
    }

    fun bindEventSink(sink: EventChannel.EventSink?) {
        eventSink = sink
        sink?.success(runtimeEvent("RUNTIME_READY"))
    }

    fun setPlatformViewAttached(attached: Boolean) {
        platformViewAttached = attached
        sessionState = sessionState.copy(platformViewAttached = attached)
        emitEvent(if (attached) "PLATFORM_VIEW_ATTACHED" else "PLATFORM_VIEW_DETACHED")
    }

    fun openSession(request: Map<String, Any?>): Map<String, Any?> {
        val matchId = request.stringValue("matchId", latestFrame.matchId)
        val sessionId = request.stringValue("sessionId", fallbackSessionId(matchId))
        sessionState = NativeMatchSessionState(
            sessionId = sessionId,
            matchId = matchId,
            status = "open",
            platformViewAttached = platformViewAttached,
            ackCount = 0,
            entityCount = latestFrame.entityCount,
            playerCount = request.intValue("expectedPlayerCount"),
            lastFrameId = request.nullableString("initialFrameId"),
            phase = request.nullableString("initialPhase"),
            clockMinute = request.nullableFloat("initialClockMinute"),
            implicit = false,
        )
        if (latestFrame.matchId.isBlank() || latestFrame.matchId != matchId) {
            latestFrame = latestFrame.copy(
                matchId = matchId,
                frameId = request.stringValue("initialFrameId"),
                clockMinute = request.floatValue("initialClockMinute"),
                phase = request.stringValue("initialPhase", "idle"),
            )
        }
        emitEvent("SESSION_OPENED")
        return sessionState.toMap()
    }

    fun closeSession(sessionId: String?): Map<String, Any?> {
        val activeSession = sessionState
        val resolvedSessionId =
            sessionId?.takeIf { it.isNotBlank() } ?: activeSession.sessionId
        if (resolvedSessionId.isBlank()) {
            return activeSession.copy(
                status = "closed",
                platformViewAttached = platformViewAttached,
            ).toMap()
        }
        sessionState = activeSession.copy(
            sessionId = resolvedSessionId,
            status = "closed",
            platformViewAttached = platformViewAttached,
            entityCount = latestFrame.entityCount,
            playerCount = latestFrame.playerCount,
            lastFrameId = latestFrame.frameId.takeIf { it.isNotBlank() },
            phase = latestFrame.phase.takeIf { it.isNotBlank() },
            clockMinute = latestFrame.clockMinute,
        )
        emitEvent("SESSION_CLOSED")
        return sessionState.toMap()
    }

    fun applyPayload(payload: Map<String, Any?>): Map<String, Any?> {
        val currentSession = ensureSessionForPayload(payload)
        val nextFrame = NativeMatchFrame.fromMap(payload)
        latestFrame = nextFrame
        sessionState = currentSession.copy(
            matchId = nextFrame.matchId,
            status = currentSession.status,
            platformViewAttached = platformViewAttached,
            ackCount = currentSession.ackCount + 1,
            entityCount = nextFrame.entityCount,
            playerCount = nextFrame.playerCount,
            lastFrameId = nextFrame.frameId.takeIf { it.isNotBlank() },
            phase = nextFrame.phase.takeIf { it.isNotBlank() },
            clockMinute = nextFrame.clockMinute,
        )
        listeners.forEach { listener ->
            listener.onFrameUpdated(nextFrame)
        }
        emitEvent(
            "SCENE_SYNC_ACK",
            mapOf(
                "frameId" to nextFrame.frameId,
                "clockMinute" to nextFrame.clockMinute,
                "phase" to nextFrame.phase,
                "actionType" to nextFrame.actionType,
                "entityCount" to nextFrame.entityCount,
                "playerCount" to nextFrame.playerCount,
            ),
        )
        return mapOf(
            "ok" to true,
            "sessionId" to sessionState.sessionId,
            "matchId" to nextFrame.matchId,
            "frameId" to nextFrame.frameId,
            "phase" to nextFrame.phase,
            "playerCount" to nextFrame.playerCount,
            "entityCount" to nextFrame.entityCount,
            "ackCount" to sessionState.ackCount,
        )
    }

    private fun ensureSessionForPayload(payload: Map<String, Any?>): NativeMatchSessionState {
        val activeSession = sessionState
        val matchId = payload.stringValue("matchId", activeSession.matchId)
        val sessionId = payload.stringValue("sessionId", fallbackSessionId(matchId))
        if (activeSession.status == "open" && activeSession.sessionId == sessionId) {
            return activeSession
        }
        if (activeSession.status == "implicit" && activeSession.sessionId == sessionId) {
            return activeSession
        }
        val nextSession = NativeMatchSessionState(
            sessionId = sessionId,
            matchId = matchId,
            status = if (activeSession.status == "open") "open" else "implicit",
            platformViewAttached = platformViewAttached,
            ackCount = activeSession.ackCount,
            entityCount = activeSession.entityCount,
            playerCount = activeSession.playerCount,
            lastFrameId = activeSession.lastFrameId,
            phase = activeSession.phase,
            clockMinute = activeSession.clockMinute,
            implicit = activeSession.status != "open",
        )
        sessionState = nextSession
        if (nextSession.implicit) {
            emitEvent("SESSION_IMPLICIT")
        }
        return nextSession
    }

    private fun fallbackSessionId(matchId: String): String {
        return if (matchId.isBlank()) "" else "native_match_3d:$matchId"
    }

    private fun runtimeEvent(
        type: String,
        extra: Map<String, Any?> = emptyMap(),
    ): Map<String, Any?> {
        return runtimeInfoMap() + sessionState.toMap() + extra + mapOf("type" to type)
    }

    private fun emitEvent(type: String, extra: Map<String, Any?> = emptyMap()) {
        eventSink?.success(runtimeEvent(type, extra))
    }
}

private const val NATIVE_MATCH_3D_RUNTIME = "native_match_3d_canvas"
private const val NATIVE_MATCH_3D_VIEW_TYPE = "match_3d/native_view"

private fun Map<*, *>?.stringValue(key: String, fallback: String = ""): String {
    if (this == null) {
        return fallback
    }
    return this[key]?.toString()?.takeIf { it.isNotBlank() } ?: fallback
}

private fun Map<String, Any?>.stringValue(key: String, fallback: String = ""): String {
    return this[key]?.toString()?.takeIf { it.isNotBlank() } ?: fallback
}

private fun Map<*, *>?.nullableString(key: String): String? {
    if (this == null) {
        return null
    }
    return this[key]?.toString()?.takeIf { it.isNotBlank() }
}

private fun Map<*, *>?.booleanValue(key: String, fallback: Boolean = false): Boolean {
    if (this == null) {
        return fallback
    }
    return when (val value = this[key]) {
        is Boolean -> value
        is Number -> value.toInt() != 0
        is String -> value.equals("true", ignoreCase = true)
        else -> fallback
    }
}

private fun Map<*, *>?.intValue(key: String, fallback: Int = 0): Int {
    if (this == null) {
        return fallback
    }
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

private fun Map<*, *>?.floatValue(key: String, fallback: Float = 0f): Float {
    if (this == null) {
        return fallback
    }
    return when (val value = this[key]) {
        is Float -> value
        is Double -> value.toFloat()
        is Int -> value.toFloat()
        is Long -> value.toFloat()
        is Number -> value.toFloat()
        is String -> value.toFloatOrNull() ?: fallback
        else -> fallback
    }
}

private fun Map<String, Any?>.floatValue(key: String, fallback: Float = 0f): Float {
    return when (val value = this[key]) {
        is Float -> value
        is Double -> value.toFloat()
        is Int -> value.toFloat()
        is Long -> value.toFloat()
        is Number -> value.toFloat()
        is String -> value.toFloatOrNull() ?: fallback
        else -> fallback
    }
}

private fun Map<*, *>?.nullableFloat(key: String): Float? {
    if (this == null) {
        return null
    }
    return when (val value = this[key]) {
        is Float -> value
        is Double -> value.toFloat()
        is Int -> value.toFloat()
        is Long -> value.toFloat()
        is Number -> value.toFloat()
        is String -> value.toFloatOrNull()
        else -> null
    }
}
