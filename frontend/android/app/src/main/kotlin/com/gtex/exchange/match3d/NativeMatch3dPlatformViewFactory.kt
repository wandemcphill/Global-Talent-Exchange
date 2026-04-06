package com.gtex.exchange.match3d

import android.content.Context
import io.flutter.plugin.common.StandardMessageCodec
import io.flutter.plugin.platform.PlatformView
import io.flutter.plugin.platform.PlatformViewFactory

internal class NativeMatch3dPlatformViewFactory :
    PlatformViewFactory(StandardMessageCodec.INSTANCE) {
    override fun create(context: Context, viewId: Int, args: Any?): PlatformView {
        return NativeMatch3dPlatformView(context)
    }

    companion object {
        const val viewType = "match_3d/native_view"
    }
}
