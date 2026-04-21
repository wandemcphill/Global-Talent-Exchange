package com.gtex.exchange.match3d

import android.app.Activity
import android.content.Context
import io.flutter.plugin.common.BinaryMessenger
import io.flutter.plugin.common.StandardMessageCodec
import io.flutter.plugin.platform.PlatformView
import io.flutter.plugin.platform.PlatformViewFactory

internal class UnityMatch3dPlatformViewFactory(
    private val activity: Activity,
    @Suppress("unused")
    private val binaryMessenger: BinaryMessenger,
) : PlatformViewFactory(StandardMessageCodec.INSTANCE) {
    override fun create(context: Context, viewId: Int, args: Any?): PlatformView {
        UnityMatch3dRuntime.attachHostActivity(activity)
        return UnityMatch3dPlatformView(context)
    }

    companion object {
        const val viewType = "match_3d/native_view"
    }
}
