package com.gtex.exchange.match3d

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.view.ViewGroup.LayoutParams.MATCH_PARENT
import android.widget.FrameLayout

internal class UnityMatchActivity : Activity() {
    private lateinit var container: FrameLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        UnityMatch3dRuntime.attachHostActivity(this)
        container =
            FrameLayout(this).apply {
                layoutParams = FrameLayout.LayoutParams(MATCH_PARENT, MATCH_PARENT)
                setBackgroundColor(Color.BLACK)
            }
        setContentView(container)
    }

    override fun onResume() {
        super.onResume()
        UnityMatch3dRuntime.attachHostActivity(this)
        UnityMatch3dRuntime.attachPlatformView(container)
        UnityMatch3dRuntime.onHostResumed()
    }

    override fun onPause() {
        UnityMatch3dRuntime.detachPlatformView(container)
        UnityMatch3dRuntime.onHostPaused()
        super.onPause()
    }

    override fun onDestroy() {
        UnityMatch3dRuntime.onHostDestroyed(this)
        super.onDestroy()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        UnityMatch3dRuntime.dispatchPendingCommands()
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) {
            UnityMatch3dRuntime.onHostResumed()
        } else {
            UnityMatch3dRuntime.onHostPaused()
        }
    }

    companion object {
        private const val EXTRA_MATCH_ID = "com.gtex.exchange.match3d.MATCH_ID"
        private const val EXTRA_SESSION_ID = "com.gtex.exchange.match3d.SESSION_ID"

        fun createIntent(
            context: Context,
            sessionId: String,
            matchId: String,
        ): Intent {
            return Intent(context, UnityMatchActivity::class.java).apply {
                putExtra(EXTRA_SESSION_ID, sessionId)
                putExtra(EXTRA_MATCH_ID, matchId)
                addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP)
            }
        }
    }
}
