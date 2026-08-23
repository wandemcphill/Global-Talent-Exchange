import 'package:flutter/material.dart';

import '../data/gtex_match_feed.dart';
import 'gtex_match_visual_tokens.dart';

/// Persistent strip that tells the viewer whether what they are looking at is
/// actually live.
///
/// Rendered only when the feed is not cleanly live, so a healthy match centre
/// stays uncluttered while a degraded one is never silently wrong.
class GtexMatchConnectionBanner extends StatelessWidget {
  const GtexMatchConnectionBanner({
    super.key,
    required this.status,
    this.onRetry,
    this.compact = false,
  });

  final GtexMatchConnectionStatus status;
  final VoidCallback? onRetry;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final _BannerSpec? spec = _specFor(status);
    if (spec == null) {
      return const SizedBox.shrink();
    }
    return Semantics(
      liveRegion: true,
      label: 'Live feed status: ${spec.semanticLabel}',
      child: Container(
        width: double.infinity,
        padding: EdgeInsets.symmetric(
          horizontal: compact ? 10 : 14,
          vertical: compact ? 8 : 10,
        ),
        decoration: BoxDecoration(
          color: spec.accent.withValues(alpha: .10),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: spec.accent.withValues(alpha: .40)),
        ),
        child: Row(
          children: <Widget>[
            spec.showSpinner
                ? SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: spec.accent,
                  ),
                )
                : Icon(spec.icon, size: 18, color: spec.accent),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  Text(
                    spec.title,
                    style: TextStyle(
                      color: spec.accent,
                      fontWeight: FontWeight.w900,
                      fontSize: 12,
                      letterSpacing: .5,
                    ),
                  ),
                  if (!compact) ...<Widget>[
                    const SizedBox(height: 2),
                    Text(
                      spec.message,
                      style: const TextStyle(
                        color: GtexMatchVisualTokens.textSecondary,
                        fontSize: 11,
                        height: 1.3,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            if (spec.allowRetry && onRetry != null) ...<Widget>[
              const SizedBox(width: 8),
              TextButton(
                onPressed: onRetry,
                style: TextButton.styleFrom(
                  foregroundColor: spec.accent,
                  // Keep the tap target at the 48dp accessibility floor.
                  minimumSize: const Size(72, 48),
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                ),
                child: const Text(
                  'Retry',
                  style: TextStyle(fontWeight: FontWeight.w900),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  static _BannerSpec? _specFor(GtexMatchConnectionStatus status) {
    switch (status) {
      case GtexMatchConnectionStatus.reconnecting:
        return const _BannerSpec(
          title: 'RECONNECTING',
          message:
              'Showing the last confirmed state while the live feed recovers.',
          semanticLabel: 'reconnecting, showing last confirmed state',
          icon: Icons.sync,
          accent: Color(0xFFFFB800),
          showSpinner: true,
          allowRetry: false,
        );
      case GtexMatchConnectionStatus.offline:
        return const _BannerSpec(
          title: 'FEED OFFLINE',
          message:
              'The live feed could not be restored. Data below may be behind.',
          semanticLabel: 'feed offline, data may be out of date',
          icon: Icons.cloud_off_outlined,
          accent: Color(0xFFFF3D3D),
          allowRetry: true,
        );
      case GtexMatchConnectionStatus.connecting:
        return const _BannerSpec(
          title: 'CONNECTING',
          message: 'Attaching to the live match authority.',
          semanticLabel: 'connecting to live match feed',
          icon: Icons.podcasts_outlined,
          accent: Color(0xFF2F80ED),
          showSpinner: true,
          allowRetry: false,
        );
      case GtexMatchConnectionStatus.finished:
        // Describes the *feed*, not the match. The post-match panel already
        // announces "FULL TIME"; repeating it here read as a duplicate.
        return const _BannerSpec(
          title: 'FEED CLOSED',
          message: 'This match has finished. The result below is final.',
          semanticLabel: 'match finished, live feed closed, result is final',
          icon: Icons.verified_outlined,
          accent: Color(0xFF00E87A),
          allowRetry: false,
        );
      case GtexMatchConnectionStatus.live:
      case GtexMatchConnectionStatus.idle:
        return null;
    }
  }
}

@immutable
class _BannerSpec {
  const _BannerSpec({
    required this.title,
    required this.message,
    required this.semanticLabel,
    required this.icon,
    required this.accent,
    this.showSpinner = false,
    this.allowRetry = false,
  });

  final String title;
  final String message;
  final String semanticLabel;
  final IconData icon;
  final Color accent;
  final bool showSpinner;
  final bool allowRetry;
}
