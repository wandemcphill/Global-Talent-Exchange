import 'dart:async';

import 'package:flutter/material.dart';

/// GTEX-only flash (≤5s) and split-screen (≤10s, game ≥60%) match ads.
class GtexFlashSplitAdOverlay extends StatefulWidget {
  const GtexFlashSplitAdOverlay({
    super.key,
    required this.child,
    this.flashBrand,
    this.splitBrand,
    this.enableFlash = true,
    this.enableSplit = false,
    this.flashSeconds = 5,
    this.splitSeconds = 10,
  });

  final Widget child;
  final String? flashBrand;
  final String? splitBrand;
  final bool enableFlash;
  final bool enableSplit;
  final int flashSeconds;
  final int splitSeconds;

  @override
  State<GtexFlashSplitAdOverlay> createState() =>
      _GtexFlashSplitAdOverlayState();
}

class _GtexFlashSplitAdOverlayState extends State<GtexFlashSplitAdOverlay> {
  bool _showFlash = false;
  bool _showSplit = false;
  Timer? _flashTimer;
  Timer? _splitTimer;

  @override
  void initState() {
    super.initState();
    if (widget.enableFlash && (widget.flashBrand?.trim().isNotEmpty ?? false)) {
      _showFlash = true;
      _flashTimer = Timer(
        Duration(seconds: widget.flashSeconds.clamp(1, 5)),
        () {
          if (mounted) {
            setState(() => _showFlash = false);
          }
        },
      );
    }
    if (widget.enableSplit && (widget.splitBrand?.trim().isNotEmpty ?? false)) {
      _splitTimer = Timer(const Duration(seconds: 20), () {
        if (!mounted) {
          return;
        }
        setState(() => _showSplit = true);
        Timer(Duration(seconds: widget.splitSeconds.clamp(1, 10)), () {
          if (mounted) {
            setState(() => _showSplit = false);
          }
        });
      });
    }
  }

  @override
  void dispose() {
    _flashTimer?.cancel();
    _splitTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_showFlash) {
      return Stack(
        fit: StackFit.expand,
        children: <Widget>[
          widget.child,
          ColoredBox(
            color: Colors.black.withValues(alpha: 0.82),
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  Text(
                    widget.flashBrand!,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 28,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'GTEX flash · auto-dismiss',
                    style: TextStyle(color: Color(0xFFAEB9C4)),
                  ),
                ],
              ),
            ),
          ),
        ],
      );
    }
    if (_showSplit) {
      return Row(
        children: <Widget>[
          Expanded(flex: 6, child: widget.child),
          Expanded(
            flex: 4,
            child: ColoredBox(
              color: const Color(0xFF101820),
              child: Center(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      Text(
                        widget.splitBrand!,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 20,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Split ad · match continues',
                        style: TextStyle(color: Color(0xFFAEB9C4), fontSize: 12),
                      ),
                      TextButton(
                        onPressed: () => setState(() => _showSplit = false),
                        child: const Text('Dismiss'),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      );
    }
    return widget.child;
  }
}
