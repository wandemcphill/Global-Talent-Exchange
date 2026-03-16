import 'dart:async';

import 'package:flutter/material.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';
import 'package:gte_frontend/widgets/gtex_branding.dart';

class GteMatchHighlightsScreen extends StatefulWidget {
  const GteMatchHighlightsScreen({
    super.key,
    required this.competition,
    this.isAuthenticated = false,
  });

  final CompetitionSummary competition;
  final bool isAuthenticated;

  @override
  State<GteMatchHighlightsScreen> createState() =>
      _GteMatchHighlightsScreenState();
}

class _GteMatchHighlightsScreenState extends State<GteMatchHighlightsScreen> {
  late Future<LiveMatchSnapshot> _snapshotFuture;
  Timer? _ticker;
  DateTime _now = DateTime.now().toUtc();

  @override
  void initState() {
    super.initState();
    _snapshotFuture = loadLiveMatchSnapshot(widget.competition);
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      setState(() {
        _now = DateTime.now().toUtc();
      });
    });
  }

  void _reload() {
    setState(() {
      _snapshotFuture = loadLiveMatchSnapshot(widget.competition);
      _now = DateTime.now().toUtc();
    });
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Match highlights'),
        ),
        body: FutureBuilder<LiveMatchSnapshot>(
          future: _snapshotFuture,
          builder: (BuildContext context,
              AsyncSnapshot<LiveMatchSnapshot> snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Padding(
                padding: EdgeInsets.all(20),
                child: GteStatePanel(
                  eyebrow: 'HIGHLIGHTS',
                  title: 'Loading highlights',
                  message:
                      'Gathering clips, expiry windows, and download eligibility.',
                  icon: Icons.play_circle_outline,
                  accentColor: GteShellTheme.accentArena,
                  isLoading: true,
                ),
              );
            }
            if (!snapshot.hasData) {
              return Padding(
                padding: const EdgeInsets.all(20),
                child: GteStatePanel(
                  title: 'Highlights unavailable',
                  message:
                      'Unable to load the highlight archive right now.',
                  icon: Icons.warning_amber_outlined,
                  actionLabel: 'Retry',
                  onAction: _reload,
                ),
              );
            }

            final LiveMatchSnapshot match = snapshot.data!;
            final Duration standardRemaining =
                match.standardHighlightExpiresAt.difference(_now);
            final String standardCountdown =
                _formatCountdown(standardRemaining);

            return ListView(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
              children: <Widget>[
                GteSurfacePanel(
                  accentColor: GteShellTheme.accentArena,
                  emphasized: true,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Post-match highlights',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        '${match.homeTeam} ${match.homeScore} - ${match.awayScore} ${match.awayTeam}',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: <Widget>[
                          _HighlightBadge(
                            label: match.isFinal ? 'FINAL' : 'ARCHIVE',
                            color: GteShellTheme.accentArena,
                          ),
                          const SizedBox(width: 10),
                          _HighlightBadge(
                            label: 'DOWNLOAD READY',
                            color: GteShellTheme.accentWarm,
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Standard highlights',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        standardRemaining.isNegative
                            ? 'Standard highlights expired.'
                            : 'Standard highlights expire in $standardCountdown.',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 12),
                      if (match.highlights.isEmpty)
                        Text(
                          'No highlights yet. Clips will appear after the first key moments.',
                          style: Theme.of(context).textTheme.bodySmall,
                        )
                      else
                        ...match.highlights.map(
                          (LiveMatchHighlightClip clip) => _HighlightTile(
                            clip: clip,
                            now: _now,
                            isAuthenticated: widget.isAuthenticated,
                          ),
                        ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Key-moment video',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Premium key moments stay live for 3 hours after the final whistle.',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 12),
                      if (match.keyMoments.isEmpty)
                        Text(
                          'Premium key moments will appear once the match produces its first major incidents.',
                          style: Theme.of(context).textTheme.bodySmall,
                        )
                      else
                        ...match.keyMoments.map(
                          (LiveMatchHighlightClip clip) => _HighlightTile(
                            clip: clip,
                            now: _now,
                            isAuthenticated: widget.isAuthenticated,
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  String _formatCountdown(Duration duration) {
    if (duration.isNegative) {
      return '00:00';
    }
    final int totalSeconds = duration.inSeconds;
    final int minutes = totalSeconds ~/ 60;
    final int seconds = totalSeconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }
}

class _HighlightBadge extends StatelessWidget {
  const _HighlightBadge({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: color.withValues(alpha: 0.16),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(color: color),
      ),
    );
  }
}

class _HighlightTile extends StatelessWidget {
  const _HighlightTile({
    required this.clip,
    required this.now,
    required this.isAuthenticated,
  });

  final LiveMatchHighlightClip clip;
  final DateTime now;
  final bool isAuthenticated;

  @override
  Widget build(BuildContext context) {
    final bool expired = clip.expiresAt.isBefore(now);
    final bool locked = clip.isPremium && !isAuthenticated;
    final bool canDownload = clip.downloadEligible && !expired && !locked;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          color: Colors.white.withValues(alpha: 0.04),
          border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
        ),
        child: Row(
          children: <Widget>[
            Icon(locked ? Icons.lock_outline : Icons.play_circle_outline),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    clip.title,
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${clip.minute}\' • ${clip.durationLabel}',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    expired
                        ? 'Archive badge applied'
                        : clip.downloadEligible
                            ? 'Download eligible'
                            : 'Streaming only',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            FilledButton.tonal(
              onPressed: canDownload ? () {} : null,
              child: Text(canDownload ? 'Download' : 'Locked'),
            ),
          ],
        ),
      ),
    );
  }
}
