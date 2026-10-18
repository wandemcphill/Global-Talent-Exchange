import 'dart:async';
import 'dart:html' as html;
import 'dart:js' as js;
import 'dart:js_util' as js_util;
import 'dart:ui_web' as ui_web;

import 'package:flutter/material.dart';

class TurnstileChallenge extends StatefulWidget {
  const TurnstileChallenge({
    super.key,
    required this.siteKey,
    required this.onTokenChanged,
  });

  final String siteKey;
  final ValueChanged<String?> onTokenChanged;

  @override
  State<TurnstileChallenge> createState() => _TurnstileChallengeState();
}

class _TurnstileChallengeState extends State<TurnstileChallenge> {
  static const String _scriptId = 'gtex-cloudflare-turnstile-script';
  static Future<void>? _scriptReady;

  late final String _viewType = 'gtex-turnstile-${identityHashCode(this)}';
  String? _widgetId;

  @override
  void initState() {
    super.initState();
    ui_web.platformViewRegistry.registerViewFactory(_viewType, (int _) {
      final container = html.DivElement()
        ..style.width = '100%'
        ..style.minHeight = '65px';
      scheduleMicrotask(() => _render(container));
      return container;
    });
  }

  Future<void> _render(html.DivElement container) async {
    if (widget.siteKey.trim().isEmpty) return;
    try {
      await _ensureScriptLoaded();
      if (!mounted) return;
      final Object? turnstile = js_util.getProperty(html.window, 'turnstile');
      if (turnstile == null) {
        widget.onTokenChanged(null);
        return;
      }

      final Object? rawOptions = js_util.jsify(<String, Object?>{
        'sitekey': widget.siteKey.trim(),
        'theme': 'dark',
        'size': 'normal',
      });
      if (rawOptions == null) {
        widget.onTokenChanged(null);
        return;
      }
      final Object options = rawOptions;
      js_util.setProperty(
        options,
        'callback',
        js.allowInterop((dynamic token) {
          if (mounted) widget.onTokenChanged(token?.toString());
        }),
      );
      js_util.setProperty(
        options,
        'expired-callback',
        js.allowInterop(() {
          if (mounted) widget.onTokenChanged(null);
        }),
      );
      js_util.setProperty(
        options,
        'error-callback',
        js.allowInterop(() {
          if (mounted) widget.onTokenChanged(null);
        }),
      );
      final dynamic id = js_util.callMethod<Object?>(
        turnstile,
        'render',
        <Object?>[container, options],
      );
      _widgetId = id?.toString();
    } catch (_) {
      if (mounted) widget.onTokenChanged(null);
    }
  }

  static Future<void> _ensureScriptLoaded() async {
    if (js_util.hasProperty(html.window, 'turnstile')) return;
    if (_scriptReady != null) {
      await _scriptReady;
      return;
    }

    final completer = Completer<void>();
    _scriptReady = completer.future;
    final existing = html.document.getElementById(_scriptId);
    final script = existing is html.ScriptElement
        ? existing
        : html.ScriptElement()
          ..id = _scriptId
          ..src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'
          ..async = true
          ..defer = true;

    script.onLoad.listen((_) {
      if (!completer.isCompleted) completer.complete();
    });
    script.onError.listen((_) {
      if (!completer.isCompleted) {
        completer.completeError(StateError('Unable to load Turnstile.'));
      }
    });
    if (existing == null) html.document.head?.append(script);
    await completer.future;
  }

  @override
  Widget build(BuildContext context) {
    if (widget.siteKey.trim().isEmpty) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 8),
        child: Text(
          'Turnstile site key is missing. Set GTE_TURNSTILE_SITE_KEY for the Flutter web build.',
          style: TextStyle(color: Color(0xFF93A0AA), fontSize: 12),
        ),
      );
    }
    return SizedBox(
      height: 72,
      child: HtmlElementView(viewType: _viewType),
    );
  }

  @override
  void dispose() {
    final String? widgetId = _widgetId;
    if (widgetId != null && js_util.hasProperty(html.window, 'turnstile')) {
      try {
        final dynamic turnstile = js_util.getProperty(html.window, 'turnstile');
        js_util.callMethod<void>(turnstile, 'remove', <Object?>[widgetId]);
      } catch (_) {
        // Widget removal is best-effort; verification remains server-enforced.
      }
    }
    super.dispose();
  }
}

