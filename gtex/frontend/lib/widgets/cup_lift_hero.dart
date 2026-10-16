import 'dart:async';

import 'package:flutter/material.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:video_player/video_player.dart';

class CupLiftHero extends StatefulWidget {
  const CupLiftHero({
    super.key,
    this.enableVideo = true,
    this.videoAsset = 'assets/media/gtex_cup_lift_hero.mp4',
    this.posterAsset = 'assets/media/gtex_cup_lift_poster.webp',
  });

  final bool enableVideo;
  final String videoAsset;
  final String posterAsset;

  @override
  State<CupLiftHero> createState() => _CupLiftHeroState();
}

class _CupLiftHeroState extends State<CupLiftHero> {
  VideoPlayerController? _controller;
  bool _videoReady = false;

  @override
  void initState() {
    super.initState();
    if (widget.enableVideo) {
      unawaited(_initializeVideo());
    }
  }

  @override
  void didUpdateWidget(covariant CupLiftHero oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.videoAsset != widget.videoAsset ||
        oldWidget.enableVideo != widget.enableVideo) {
      _disposeVideo();
      _videoReady = false;
      if (widget.enableVideo) {
        unawaited(_initializeVideo());
      }
    }
  }

  Future<void> _initializeVideo() async {
    final VideoPlayerController controller = VideoPlayerController.asset(
      widget.videoAsset,
      videoPlayerOptions: VideoPlayerOptions(mixWithOthers: true),
    );
    _controller = controller;
    try {
      await controller.initialize();
      await controller.setLooping(true);
      await controller.setVolume(0);
      await controller.play();
      if (!mounted || !identical(_controller, controller)) {
        await controller.dispose();
        return;
      }
      setState(() {
        _videoReady = true;
      });
    } catch (_) {
      await controller.dispose();
      if (!mounted || !identical(_controller, controller)) {
        return;
      }
      setState(() {
        _controller = null;
        _videoReady = false;
      });
    }
  }

  void _disposeVideo() {
    final VideoPlayerController? controller = _controller;
    _controller = null;
    unawaited(controller?.dispose());
  }

  @override
  void dispose() {
    _disposeVideo();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final VideoPlayerController? controller = _controller;
    return LayoutBuilder(
      key: const Key('cup-lift-hero'),
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool compact = constraints.maxWidth < 560;
        final TextStyle? titleStyle =
            compact
                ? Theme.of(context).textTheme.headlineSmall
                : Theme.of(context).textTheme.displaySmall;
        return ClipRRect(
          borderRadius: BorderRadius.circular(tokens.radiusLarge),
          child: AspectRatio(
            aspectRatio: compact ? 16 / 11 : 16 / 7,
            child: Stack(
              fit: StackFit.expand,
              children: <Widget>[
                if (_videoReady && controller != null)
                  FittedBox(
                    fit: BoxFit.cover,
                    child: SizedBox(
                      width: controller.value.size.width,
                      height: controller.value.size.height,
                      child: VideoPlayer(controller),
                    ),
                  )
                else
                  Image.asset(
                    widget.posterAsset,
                    key: const Key('cup-lift-hero-poster'),
                    fit: BoxFit.cover,
                  ),
                DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.centerLeft,
                      end: Alignment.centerRight,
                      colors: <Color>[
                        Colors.black.withValues(alpha: 0.68),
                        Colors.black.withValues(alpha: 0.18),
                        Colors.black.withValues(alpha: 0.54),
                      ],
                    ),
                  ),
                ),
                Positioned(
                  left: compact ? 16 : 24,
                  right: compact ? 16 : 24,
                  bottom: compact ? 14 : 22,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      Container(
                        padding: EdgeInsets.symmetric(
                          horizontal: compact ? 10 : 12,
                          vertical: compact ? 6 : 7,
                        ),
                        decoration: BoxDecoration(
                          color: tokens.accent.withValues(alpha: 0.14),
                          borderRadius: BorderRadius.circular(
                            tokens.radiusPill,
                          ),
                          border: Border.all(
                            color: tokens.accent.withValues(alpha: 0.36),
                          ),
                        ),
                        child: Text(
                          'LIVE FOOTBALL ECONOMY',
                          style: Theme.of(
                            context,
                          ).textTheme.labelLarge?.copyWith(
                            color: tokens.accent,
                            fontSize: compact ? 11 : null,
                          ),
                        ),
                      ),
                      SizedBox(height: compact ? 8 : 12),
                      Text(
                        'The trophy lift starts in the market.',
                        maxLines: compact ? 2 : 3,
                        overflow: TextOverflow.ellipsis,
                        style: titleStyle?.copyWith(color: tokens.textPrimary),
                      ),
                      SizedBox(height: compact ? 4 : 6),
                      Text(
                        'Scout, sign, trade, compete, and build a club people can feel moving.',
                        maxLines: compact ? 2 : 3,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                          color: tokens.textMuted,
                          fontSize: compact ? 13 : null,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
