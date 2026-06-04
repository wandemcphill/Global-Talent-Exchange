import 'package:flutter/material.dart';
import 'package:gte_frontend/features/match_center/data/live_match_fixtures.dart';
import 'package:video_player/video_player.dart';

typedef GteHighlightControllerFactory =
    VideoPlayerController Function(String url);

Future<void> showGteMatchHighlightPlayerSheet(
  BuildContext context, {
  required LiveMatchHighlightClip clip,
  VoidCallback? onWatchReplay,
  GteHighlightControllerFactory controllerFactory =
      _defaultHighlightControllerFactory,
}) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (BuildContext context) {
      return _GteMatchHighlightPlayerSheet(
        clip: clip,
        onWatchReplay: onWatchReplay,
        controllerFactory: controllerFactory,
      );
    },
  );
}

VideoPlayerController _defaultHighlightControllerFactory(String url) {
  return VideoPlayerController.networkUrl(Uri.parse(url));
}

class _GteMatchHighlightPlayerSheet extends StatefulWidget {
  const _GteMatchHighlightPlayerSheet({
    required this.clip,
    required this.controllerFactory,
    this.onWatchReplay,
  });

  final LiveMatchHighlightClip clip;
  final VoidCallback? onWatchReplay;
  final GteHighlightControllerFactory controllerFactory;

  @override
  State<_GteMatchHighlightPlayerSheet> createState() =>
      _GteMatchHighlightPlayerSheetState();
}

class _GteMatchHighlightPlayerSheetState
    extends State<_GteMatchHighlightPlayerSheet> {
  VideoPlayerController? _controller;
  bool _loading = false;
  String? _errorMessage;

  bool get _hasStream => widget.clip.hasPlayableStream;

  @override
  void initState() {
    super.initState();
    _initializePlayer();
  }

  Future<void> _initializePlayer() async {
    if (!_hasStream) {
      return;
    }
    setState(() {
      _loading = true;
      _errorMessage = null;
    });
    final VideoPlayerController controller = widget.controllerFactory(
      widget.clip.streamUrl!.trim(),
    );
    try {
      await controller.initialize();
      await controller.setLooping(true);
      await controller.play();
      if (!mounted) {
        await controller.dispose();
        return;
      }
      setState(() {
        _controller = controller;
        _loading = false;
      });
    } catch (_) {
      await controller.dispose();
      if (!mounted) {
        return;
      }
      setState(() {
        _loading = false;
        _errorMessage = 'Unable to open the highlight stream right now.';
      });
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  Future<void> _togglePlayback() async {
    final VideoPlayerController? controller = _controller;
    if (controller == null) {
      return;
    }
    if (controller.value.isPlaying) {
      await controller.pause();
    } else {
      await controller.play();
    }
    if (mounted) {
      setState(() {});
    }
  }

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return SafeArea(
      top: false,
      child: Container(
        margin: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        padding: const EdgeInsets.fromLTRB(18, 18, 18, 20),
        decoration: BoxDecoration(
          color: const Color(0xFF08111B),
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              widget.clip.title,
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              "${widget.clip.minute}' • ${widget.clip.durationLabel}",
              style: theme.textTheme.bodySmall?.copyWith(color: Colors.white70),
            ),
            if (widget.clip.subtitle?.trim().isNotEmpty == true) ...<Widget>[
              const SizedBox(height: 8),
              Text(
                widget.clip.subtitle!,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: Colors.white70,
                ),
              ),
            ],
            const SizedBox(height: 16),
            ClipRRect(
              borderRadius: BorderRadius.circular(18),
              child: Container(
                width: double.infinity,
                color: Colors.black,
                child: AspectRatio(
                  aspectRatio:
                      _controller?.value.isInitialized == true
                          ? _controller!.value.aspectRatio
                          : 16 / 9,
                  child: _buildPlayerState(theme),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: <Widget>[
                FilledButton.icon(
                  onPressed: _controller == null ? null : _togglePlayback,
                  icon: Icon(
                    _controller?.value.isPlaying == true
                        ? Icons.pause_rounded
                        : Icons.play_arrow_rounded,
                  ),
                  label: Text(
                    _controller?.value.isPlaying == true ? 'Pause' : 'Play',
                  ),
                ),
                if (widget.onWatchReplay != null)
                  OutlinedButton.icon(
                    onPressed: widget.onWatchReplay,
                    icon: const Icon(Icons.sports_soccer_rounded),
                    label: const Text('Watch Replay'),
                  ),
              ],
            ),
            if (widget.clip.cameraSequence.isNotEmpty) ...<Widget>[
              const SizedBox(height: 14),
              Text(
                widget.clip.cameraSequence.join(' • '),
                style: theme.textTheme.bodySmall?.copyWith(
                  color: Colors.white60,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildPlayerState(ThemeData theme) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_controller?.value.isInitialized == true) {
      return Stack(
        fit: StackFit.expand,
        children: <Widget>[
          VideoPlayer(_controller!),
          Positioned.fill(
            child: Material(
              color: Colors.transparent,
              child: InkWell(onTap: _togglePlayback),
            ),
          ),
          if (_controller?.value.isPlaying != true)
            Center(
              child: Container(
                width: 68,
                height: 68,
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: 0.45),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.play_arrow_rounded,
                  color: Colors.white,
                  size: 40,
                ),
              ),
            ),
        ],
      );
    }
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            Icon(
              Icons.play_circle_outline,
              color: Colors.white.withValues(alpha: 0.8),
              size: 42,
            ),
            const SizedBox(height: 12),
            Text(
              _errorMessage ??
                  (_hasStream
                      ? 'Preparing the highlight stream.'
                      : 'This clip is still rendering. Replay is available immediately.'),
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: Colors.white70,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
