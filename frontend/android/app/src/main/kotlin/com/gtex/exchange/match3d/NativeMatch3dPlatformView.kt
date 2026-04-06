package com.gtex.exchange.match3d

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.Path
import android.graphics.PointF
import android.graphics.RadialGradient
import android.graphics.RectF
import android.graphics.Shader
import android.view.View
import io.flutter.plugin.platform.PlatformView
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin

internal class NativeMatch3dPlatformView(context: Context) : PlatformView {
    private val view = NativeMatch3dCanvasView(context)

    override fun getView(): View = view

    override fun dispose() {
        view.dispose()
    }
}

private class NativeMatch3dCanvasView(context: Context) :
    View(context),
    NativeMatch3dRuntime.Listener {
    private val backgroundPaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val pitchPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#194D31")
        style = Paint.Style.FILL
    }
    private val stripePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#215C3A")
        style = Paint.Style.FILL
    }
    private val linePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        alpha = 190
        style = Paint.Style.STROKE
        strokeWidth = 3f
    }
    private val shadowPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.BLACK
        alpha = 70
        style = Paint.Style.FILL
    }
    private val playerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
    }
    private val playerOutlinePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = 3f
        color = Color.argb(220, 255, 255, 255)
    }
    private val ballPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        style = Paint.Style.FILL
    }
    private val crowdPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(48, 255, 255, 255)
        style = Paint.Style.FILL
    }

    @Volatile
    private var frame: NativeMatchFrame = NativeMatch3dRuntime.snapshot()

    init {
        setWillNotDraw(false)
        NativeMatch3dRuntime.addListener(this)
    }

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        NativeMatch3dRuntime.setPlatformViewAttached(true)
    }

    override fun onDetachedFromWindow() {
        NativeMatch3dRuntime.setPlatformViewAttached(false)
        super.onDetachedFromWindow()
    }

    fun dispose() {
        NativeMatch3dRuntime.removeListener(this)
        NativeMatch3dRuntime.setPlatformViewAttached(false)
    }

    override fun onFrameUpdated(frame: NativeMatchFrame) {
        this.frame = frame
        postInvalidateOnAnimation()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        if (width <= 0 || height <= 0) {
            return
        }

        val resolvedFrame = frame
        drawBackground(canvas)
        drawCrowdGlow(canvas)

        val projector = NativeProjector(
            camera = resolvedFrame.camera,
            viewportWidth = width.toFloat(),
            viewportHeight = height.toFloat(),
        )

        drawPitch(canvas, projector, resolvedFrame)
        drawPlayers(canvas, projector, resolvedFrame)
        drawBall(canvas, projector, resolvedFrame)
    }

    private fun drawBackground(canvas: Canvas) {
        backgroundPaint.shader = LinearGradient(
            0f,
            0f,
            0f,
            height.toFloat(),
            intArrayOf(
                Color.parseColor("#09131B"),
                Color.parseColor("#102230"),
                Color.parseColor("#061018"),
            ),
            null,
            Shader.TileMode.CLAMP,
        )
        canvas.drawRect(0f, 0f, width.toFloat(), height.toFloat(), backgroundPaint)
    }

    private fun drawCrowdGlow(canvas: Canvas) {
        val radius = max(width, height).toFloat() * 0.85f
        crowdPaint.shader = RadialGradient(
            width * 0.5f,
            height * 0.18f,
            radius,
            intArrayOf(
                Color.argb(42, 255, 240, 212),
                Color.argb(18, 125, 235, 255),
                Color.TRANSPARENT,
            ),
            floatArrayOf(0f, 0.35f, 1f),
            Shader.TileMode.CLAMP,
        )
        canvas.drawCircle(width * 0.5f, height * 0.18f, radius, crowdPaint)
    }

    private fun drawPitch(
        canvas: Canvas,
        projector: NativeProjector,
        frame: NativeMatchFrame,
    ) {
        val halfLength = frame.pitchLengthMeters / 2f
        val halfWidth = frame.pitchWidthMeters / 2f
        val corners = listOf(
            NativeVec3(-halfLength, 0f, -halfWidth),
            NativeVec3(halfLength, 0f, -halfWidth),
            NativeVec3(halfLength, 0f, halfWidth),
            NativeVec3(-halfLength, 0f, halfWidth),
        ).mapNotNull(projector::project)

        if (corners.size < 4) {
            return
        }

        val pitchPath = Path().apply {
            moveTo(corners[0].x, corners[0].y)
            for (index in 1 until corners.size) {
                lineTo(corners[index].x, corners[index].y)
            }
            close()
        }
        canvas.drawPath(pitchPath, pitchPaint)

        val stripeStep = frame.pitchLengthMeters / 8f
        for (index in 0 until 8) {
            if (index % 2 == 0) {
                continue
            }
            val startX = -halfLength + (stripeStep * index)
            val stripeCorners = listOf(
                NativeVec3(startX, 0f, -halfWidth),
                NativeVec3(startX + stripeStep, 0f, -halfWidth),
                NativeVec3(startX + stripeStep, 0f, halfWidth),
                NativeVec3(startX, 0f, halfWidth),
            ).mapNotNull(projector::project)
            if (stripeCorners.size == 4) {
                val stripePath = Path().apply {
                    moveTo(stripeCorners[0].x, stripeCorners[0].y)
                    for (stripeIndex in 1 until stripeCorners.size) {
                        lineTo(stripeCorners[stripeIndex].x, stripeCorners[stripeIndex].y)
                    }
                    close()
                }
                canvas.drawPath(stripePath, stripePaint)
            }
        }

        drawFieldLine(
            canvas,
            projector,
            NativeVec3(0f, 0.03f, -halfWidth),
            NativeVec3(0f, 0.03f, halfWidth),
        )
        drawFieldCircle(
            canvas,
            projector,
            center = NativeVec3(0f, 0.03f, 0f),
            radius = 9.15f,
        )
        drawPenaltyBox(canvas, projector, x = -halfLength, direction = 1f)
        drawPenaltyBox(canvas, projector, x = halfLength, direction = -1f)
    }

    private fun drawPenaltyBox(
        canvas: Canvas,
        projector: NativeProjector,
        x: Float,
        direction: Float,
    ) {
        val depth = 16.5f * direction
        val boxHalfWidth = 20.15f
        drawFieldLine(
            canvas,
            projector,
            NativeVec3(x, 0.03f, -boxHalfWidth),
            NativeVec3(x + depth, 0.03f, -boxHalfWidth),
        )
        drawFieldLine(
            canvas,
            projector,
            NativeVec3(x + depth, 0.03f, -boxHalfWidth),
            NativeVec3(x + depth, 0.03f, boxHalfWidth),
        )
        drawFieldLine(
            canvas,
            projector,
            NativeVec3(x + depth, 0.03f, boxHalfWidth),
            NativeVec3(x, 0.03f, boxHalfWidth),
        )

        val sixDepth = 5.5f * direction
        val sixHalfWidth = 9.16f
        drawFieldLine(
            canvas,
            projector,
            NativeVec3(x, 0.03f, -sixHalfWidth),
            NativeVec3(x + sixDepth, 0.03f, -sixHalfWidth),
        )
        drawFieldLine(
            canvas,
            projector,
            NativeVec3(x + sixDepth, 0.03f, -sixHalfWidth),
            NativeVec3(x + sixDepth, 0.03f, sixHalfWidth),
        )
        drawFieldLine(
            canvas,
            projector,
            NativeVec3(x + sixDepth, 0.03f, sixHalfWidth),
            NativeVec3(x, 0.03f, sixHalfWidth),
        )
    }

    private fun drawFieldCircle(
        canvas: Canvas,
        projector: NativeProjector,
        center: NativeVec3,
        radius: Float,
    ) {
        val path = Path()
        var hasPoint = false
        for (step in 0..30) {
            val angle = ((step / 30f) * (PI * 2f)).toFloat()
            val point = NativeVec3(
                x = center.x + (cos(angle) * radius).toFloat(),
                y = center.y,
                z = center.z + (sin(angle) * radius).toFloat(),
            )
            val screenPoint = projector.project(point) ?: continue
            if (!hasPoint) {
                path.moveTo(screenPoint.x, screenPoint.y)
                hasPoint = true
            } else {
                path.lineTo(screenPoint.x, screenPoint.y)
            }
        }
        if (hasPoint) {
            path.close()
            canvas.drawPath(path, linePaint)
        }
    }

    private fun drawFieldLine(
        canvas: Canvas,
        projector: NativeProjector,
        start: NativeVec3,
        end: NativeVec3,
    ) {
        val screenStart = projector.project(start) ?: return
        val screenEnd = projector.project(end) ?: return
        canvas.drawLine(screenStart.x, screenStart.y, screenEnd.x, screenEnd.y, linePaint)
    }

    private fun drawPlayers(
        canvas: Canvas,
        projector: NativeProjector,
        frame: NativeMatchFrame,
    ) {
        val players = frame.entities
            .filter { it.type.equals("player", ignoreCase = true) }
            .sortedByDescending { projector.depth(it.position) }

        for (entity in players) {
            val foot = projector.project(entity.position) ?: continue
            val head = projector.project(entity.position + NativeVec3(0f, 1.78f, 0f)) ?: continue
            val projectedHeight = abs(foot.y - head.y).coerceAtLeast(18f)
            val bodyWidth = max(8f, projectedHeight * 0.34f)
            val shadowWidth = bodyWidth * 1.25f
            val shadowHeight = max(4f, bodyWidth * 0.35f)
            val shadowRect = RectF(
                foot.x - shadowWidth,
                foot.y - shadowHeight * 0.4f,
                foot.x + shadowWidth,
                foot.y + shadowHeight,
            )
            canvas.drawOval(shadowRect, shadowPaint)

            playerPaint.color = resolvePlayerColor(entity)
            val bodyRect = RectF(
                foot.x - bodyWidth,
                head.y,
                foot.x + bodyWidth,
                foot.y,
            )
            canvas.drawRoundRect(bodyRect, bodyWidth, bodyWidth, playerPaint)

            if (entity.payload.highlighted || entity.payload.hasPossession) {
                val outlineRect = RectF(bodyRect).apply {
                    inset(-4f, -4f)
                }
                playerOutlinePaint.color =
                    if (entity.payload.hasPossession) {
                        Color.argb(240, 255, 214, 102)
                    } else {
                        Color.argb(220, 255, 255, 255)
                    }
                canvas.drawRoundRect(outlineRect, bodyWidth, bodyWidth, playerOutlinePaint)
            }
        }
    }

    private fun drawBall(
        canvas: Canvas,
        projector: NativeProjector,
        frame: NativeMatchFrame,
    ) {
        val ball = frame.ballNode ?: return
        val position = projector.project(ball.position) ?: return
        val depth = projector.depth(ball.position)
        if (depth <= 0.1f) {
            return
        }
        val radius = min(16f, max(4f, projector.scaleForDepth(depth) * 0.48f))
        val shadowRect = RectF(
            position.x - radius * 1.2f,
            position.y + radius * 0.4f,
            position.x + radius * 1.2f,
            position.y + radius * 1.1f,
        )
        canvas.drawOval(shadowRect, shadowPaint)
        canvas.drawCircle(position.x, position.y, radius, ballPaint)
        playerOutlinePaint.color = Color.argb(120, 16, 24, 32)
        canvas.drawCircle(position.x, position.y, radius, playerOutlinePaint)
    }

    private fun resolvePlayerColor(entity: NativeSceneNode): Int {
        val side = entity.payload.side?.lowercase()
        return when {
            entity.payload.hasPossession -> Color.parseColor("#F6C945")
            side == "home" -> Color.parseColor("#2A6CF0")
            side == "away" -> Color.parseColor("#E24A3B")
            else -> Color.parseColor("#B8C5D6")
        }
    }
}

private data class NativeProjector(
    val camera: NativeCameraState,
    val viewportWidth: Float,
    val viewportHeight: Float,
) {
    private val worldUp = NativeVec3(0f, 1f, 0f)
    private val forward = (camera.target - camera.position).normalized()
    private val right = worldUp.cross(forward).normalized().let { candidate ->
        if (candidate.magnitude() <= 0.0001f) {
            NativeVec3(1f, 0f, 0f)
        } else {
            candidate
        }
    }
    private val up = forward.cross(right).normalized()
    private val focalLength = min(viewportWidth, viewportHeight) * 1.08f

    fun project(point: NativeVec3): PointF? {
        val relative = point - camera.position
        val cameraX = relative.dot(right)
        val cameraY = relative.dot(up)
        val cameraZ = relative.dot(forward)
        if (cameraZ <= 0.4f) {
            return null
        }
        val scale = focalLength / cameraZ
        val x = (viewportWidth * 0.5f) + (cameraX * scale)
        val y = (viewportHeight * 0.60f) - (cameraY * scale)
        return PointF(x, y)
    }

    fun depth(point: NativeVec3): Float {
        return (point - camera.position).dot(forward)
    }

    fun scaleForDepth(depth: Float): Float {
        return (focalLength / max(depth, 0.4f)) * 0.34f
    }
}
