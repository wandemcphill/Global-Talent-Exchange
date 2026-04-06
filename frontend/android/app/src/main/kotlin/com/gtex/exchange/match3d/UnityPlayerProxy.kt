package com.gtex.exchange.match3d

import android.app.Activity
import android.content.Context
import android.view.View

internal object UnityPlayerProxy {
    private const val UNITY_PLAYER_CLASS_NAME = "com.unity3d.player.UnityPlayer"
    private const val UNITY_PLAYER_LIFECYCLE_EVENTS_CLASS_NAME =
        "com.unity3d.player.IUnityPlayerLifecycleEvents"

    fun isAvailable(): Boolean {
        return runCatching {
            Class.forName(UNITY_PLAYER_CLASS_NAME)
        }.isSuccess
    }

    fun create(activity: Activity): Any? {
        val unityPlayerClass =
            runCatching {
                Class.forName(UNITY_PLAYER_CLASS_NAME)
            }.getOrNull() ?: return null
        val lifecycleEventsClass =
            runCatching {
                Class.forName(UNITY_PLAYER_LIFECYCLE_EVENTS_CLASS_NAME)
            }.getOrNull()

        if (lifecycleEventsClass != null) {
            runCatching {
                unityPlayerClass
                    .getConstructor(Context::class.java, lifecycleEventsClass)
                    .newInstance(activity, null)
            }.getOrNull()?.let { return it }

            runCatching {
                unityPlayerClass
                    .getConstructor(Activity::class.java, lifecycleEventsClass)
                    .newInstance(activity, null)
            }.getOrNull()?.let { return it }
        }

        return runCatching {
            unityPlayerClass.getConstructor(Context::class.java).newInstance(activity)
        }.getOrNull()
    }

    fun asView(instance: Any?): View? = instance as? View

    fun requestFocus(instance: Any?) {
        invoke(instance, "requestFocus")
    }

    fun resume(instance: Any?) {
        invoke(instance, "resume")
    }

    fun pause(instance: Any?) {
        invoke(instance, "pause")
    }

    fun windowFocusChanged(instance: Any?, hasFocus: Boolean) {
        invoke(instance, "windowFocusChanged", hasFocus)
    }

    fun destroy(instance: Any?) {
        if (!invoke(instance, "destroy")) {
            invoke(instance, "quit")
        }
    }

    fun sendMessage(gameObject: String, methodName: String, payload: String): Boolean {
        val unityPlayerClass =
            runCatching {
                Class.forName(UNITY_PLAYER_CLASS_NAME)
            }.getOrNull() ?: return false
        return runCatching {
            unityPlayerClass
                .getMethod(
                    "UnitySendMessage",
                    String::class.java,
                    String::class.java,
                    String::class.java,
                ).invoke(null, gameObject, methodName, payload)
        }.isSuccess
    }

    private fun invoke(instance: Any?, methodName: String, vararg args: Any?): Boolean {
        if (instance == null) {
            return false
        }
        val parameterTypes =
            args.map { argument ->
                when (argument) {
                    is Boolean -> java.lang.Boolean.TYPE
                    is Int -> java.lang.Integer.TYPE
                    is Float -> java.lang.Float.TYPE
                    is Double -> java.lang.Double.TYPE
                    else -> argument?.javaClass ?: Any::class.java
                }
            }.toTypedArray()
        return runCatching {
            instance.javaClass.getMethod(methodName, *parameterTypes).invoke(instance, *args)
        }.isSuccess
    }
}
