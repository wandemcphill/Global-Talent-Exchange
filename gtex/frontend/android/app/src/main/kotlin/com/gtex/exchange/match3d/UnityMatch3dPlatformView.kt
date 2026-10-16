package com.gtex.exchange.match3d

import android.content.Context
import android.graphics.Color
import android.view.View
import android.widget.FrameLayout
import io.flutter.plugin.platform.PlatformView

internal class UnityMatch3dPlatformView(context: Context) : PlatformView {
    private val container =
        object : FrameLayout(context) {
            override fun onAttachedToWindow() {
                super.onAttachedToWindow()
                UnityMatch3dRuntime.attachPlatformView(this)
            }

            override fun onDetachedFromWindow() {
                UnityMatch3dRuntime.detachPlatformView(this)
                super.onDetachedFromWindow()
            }
        }.apply {
            setBackgroundColor(Color.BLACK)
            layoutParams =
                FrameLayout.LayoutParams(
                    FrameLayout.LayoutParams.MATCH_PARENT,
                    FrameLayout.LayoutParams.MATCH_PARENT,
                )
        }

    override fun getView(): View = container

    override fun dispose() {
        UnityMatch3dRuntime.detachPlatformView(container)
        container.removeAllViews()
    }
}
