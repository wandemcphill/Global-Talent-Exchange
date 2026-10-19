import 'dart:async';
import 'dart:js_interop';
import 'dart:ui_web' as ui_web;
import 'package:web/web.dart' as web;

import 'package:flutter/material.dart';

@JS('turnstile')
external JSObject? get _turnstile;

@JS('turnstile.render')
external JSAny? _turnstileRender(web.HTMLElement container, JSAny options);

@JS('turnstile.remove')
external void _turnstileRemove(JSString widgetId);

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
      final container = web.HTMLDivElement()
        ..style.width = '100%'
        ..style.minHeight = '65px';
      scheduleMicrotask(() => _render(container));
      return container;
    });
  }

  Future<void> _render(web.HTMLDivElement container) async {
    if (widget.siteKey.trim().isEmpty) {
      widget.onTokenChanged(null);
      return;
    }

    try {
      await _ensureScriptLoaded();
      if (!mounted) return;
      if (_turnstile == null) {
        widget.onTokenChanged(null);
        return;
      }

      final options = <String, Object>{
        'sitekey': widget.siteKey.trim(),
        'theme': 'dark',
        'size': 'normal',
        'callback': ((JSString token) {
          if (mounted) widget.onTokenChanged(token.toDart);
        }).toJS,
        'expired-callback': (() {
          if (mounted) widget.onTokenChanged(null);
        }).toJS,
        'error-callback': (() {
          if (mounted) widget.onTokenChanged(null);
        }).toJS,
      }.jsify();

      final id = _turnstileRender(container, options!);
      _widgetId = id?.dartify()?.toString();
    } catch (_) {
      if (mounted) widget.onTokenChanged(null);
    }
  }

  static Future<void> _ensureScriptLoaded() async {
    if (_turnstile != null) return;
    if (_scriptReady != null) {
      await _scriptReady;
      return;
    }

    final completer = Completer<void>();
    _scriptReady = completer.future;
    final existing = web.document.getElementById(_scriptId);
    final script = existing is web.HTMLScriptElement
        ? existing
        : web.HTMLScriptElement()
          ..id = _scriptId
          ..src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'
          ..async = true
          ..defer = true;

    script.addEventListener(
      'load',
      ((web.Event _) {
        if (!completer.isCompleted) completer.complete();
      }).toJS,
    );
    script.addEventListener(
      'error',
      ((web.Event _) {
        if (!completer.isCompleted) {
          completer.completeError(StateError('Unable to load Turnstile.'));
        }
      }).toJS,
    );
    if (existing == null) web.document.head?.append(script);
    await completer.future;
  }

  @override
  Widget build(BuildContext context) {
    if (widget.siteKey.trim().isEmpty) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 8),
        child: Text(
          'Turnstile site key is missing. Configure GTE_TURNSTILE_SITE_KEY for the web build.',
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
    if (widgetId != null && _turnstile != null) {
      try {
        _turnstileRemove(widgetId.toJS);
      } catch (_) {
        // Removal is best-effort; server-side verification remains enforced.
      }
    }
    super.dispose();
  }
}
