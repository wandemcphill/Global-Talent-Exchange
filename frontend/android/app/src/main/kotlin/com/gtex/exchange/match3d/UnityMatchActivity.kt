package com.gtex.exchange.match3d

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.view.ViewGroup.LayoutParams.MATCH_PARENT

internal class UnityMatchActivity : Activity() {
    private var unityPlayer: Any? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val player = UnityPlayerProxy.create(this)
        val unityView = UnityPlayerProxy.asView(player)
        if (player == null || unityView == null) {
            UnityMatch3dRuntime.onUnityLaunchFailed()
            finish()
            return
        }

        unityPlayer = player
        unityView.layoutParams =
            android.view.ViewGroup.LayoutParams(MATCH_PARENT, MATCH_PARENT)
        unityView.setBackgroundColor(Color.BLACK)
        setContentView(unityView)
        UnityPlayerProxy.requestFocus(player)
        UnityMatch3dRuntime.registerUnityActivity(this)
    }

    override fun onResume() {
        super.onResume()
        UnityPlayerProxy.resume(unityPlayer)
        UnityPlayerProxy.windowFocusChanged(unityPlayer, true)
        UnityMatch3dRuntime.onUnityActivityResumed(this)
    }

    override fun onPause() {
        UnityMatch3dRuntime.onUnityActivityPaused(this)
        UnityPlayerProxy.windowFocusChanged(unityPlayer, false)
        UnityPlayerProxy.pause(unityPlayer)
        super.onPause()
    }

    override fun onDestroy() {
        UnityMatch3dRuntime.onUnityActivityDestroyed(this)
        UnityPlayerProxy.destroy(unityPlayer)
        unityPlayer = null
        super.onDestroy()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        UnityMatch3dRuntime.dispatchPendingCommands()
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        UnityPlayerProxy.windowFocusChanged(unityPlayer, hasFocus)
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
