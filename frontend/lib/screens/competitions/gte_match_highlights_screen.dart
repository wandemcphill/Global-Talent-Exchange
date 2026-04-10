import 'package:flutter/material.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

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
  late Future<_MatchHighlightsSnapshot> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_MatchHighlightsSnapshot> _load() async {
    final GteAppConfig config = GteAppConfig.fromEnvironment();
    if (config.activeShellBackendMode == GteBackendMode.fixture) {
      throw const GteApiException(
        type: GteApiErrorType.unavailable,
        message: 'Match highlights require live backend mode.',
      );
    }
    final GteExchangeApiClient client = GteExchangeApiClient.standard(
      baseUrl: config.apiBaseUrl,
      mode: config.activeShellBackendMode,
    );
    final List<Map<String, Object?>> payload =
        await Future.wait<Map<String, Object?>>(<Future<Map<String, Object?>>>[
          client.fetchMatchLiveFeed(widget.competition.id),
          client.fetchMatchHighlights(widget.competition.id),
        ]);
    return _MatchHighlightsSnapshot.fromPayloads(
      competition: widget.competition,
      liveFeed: payload[0],
      manifest: payload[1],
    );
  }

  Future<void> _refresh() async {
    final Future<_MatchHighlightsSnapshot> next = _load();
    setState(() {
      _future = next;
    });
    await next;
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(title: const Text('Match highlights')),
        body: FutureBuilder<_MatchHighlightsSnapshot>(
          future: _future,
          builder: (
            BuildContext context,
            AsyncSnapshot<_MatchHighlightsSnapshot> snapshot,
          ) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError) {
              return Padding(
                padding: const EdgeInsets.all(20),
                child: GteStatePanel(
                  title: 'Match highlights unavailable',
                  message: _highlightsErrorMessage(
                    snapshot.error,
                    isAuthenticated: widget.isAuthenticated,
                  ),
                  icon: Icons.play_circle_outline,
                ),
              );
            }
            final _MatchHighlightsSnapshot data = snapshot.data!;
            return RefreshIndicator(
              onRefresh: _refresh,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                children: <Widget>[
                  _HighlightsHero(data: data),
                  const SizedBox(height: 18),
                  if (data.highlights.isEmpty)
                    const GteStatePanel(
                      title: 'No archived highlights yet',
                      message:
                          'The backend has not published a clip manifest for this match yet. Replay availability is being reported honestly instead of falling back to mock recap cards.',
                      icon: Icons.video_library_outlined,
                    )
                  else
                    ...data.highlights.map(
                      (_HighlightClip item) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _HighlightCard(item: item),
                      ),
                    ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }
}

class _HighlightsHero extends StatelessWidget {
  const _HighlightsHero({required this.data});

  final _MatchHighlightsSnapshot data;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            data.competition.name,
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Text(
            '${data.homeTeam} ${data.homeScore}-${data.awayScore} ${data.awayTeam}',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            '${data.highlightCountLabel} - ${data.phaseLabel}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              _StatusChip(
                label:
                    data.archiveAvailable ? 'Archive ready' : 'Archive pending',
                icon:
                    data.archiveAvailable
                        ? Icons.archive_outlined
                        : Icons.schedule_outlined,
              ),
              _StatusChip(
                label:
                    data.replayAvailable
                        ? 'Replay available'
                        : 'Replay pending',
                icon:
                    data.replayAvailable
                        ? Icons.replay_outlined
                        : Icons.hourglass_bottom_outlined,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _HighlightCard extends StatelessWidget {
  const _HighlightCard({required this.item});

  final _HighlightClip item;

  @override
  Widget build(BuildContext context) {
    final bool available = item.accessState == 'available';
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      item.title,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      "${item.minute}' - ${item.eventTypeLabel}${item.label == null ? '' : ' - ${item.label}'}",
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              _StatusChip(
                label: available ? 'Ready' : item.renderStatusLabel,
                icon:
                    available
                        ? Icons.play_arrow_outlined
                        : Icons.pending_outlined,
              ),
            ],
          ),
          if (item.subtitle != null && item.subtitle!.isNotEmpty) ...<Widget>[
            const SizedBox(height: 12),
            Text(item.subtitle!, style: Theme.of(context).textTheme.bodyMedium),
          ],
          const SizedBox(height: 12),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              _StatusChip(
                label: item.durationLabel,
                icon: Icons.timer_outlined,
              ),
              if (item.scorelineLabel != null &&
                  item.scorelineLabel!.isNotEmpty)
                _StatusChip(
                  label: item.scorelineLabel!,
                  icon: Icons.scoreboard_outlined,
                ),
              _StatusChip(
                label: item.archiveAvailable ? 'Archived' : 'Archive pending',
                icon:
                    item.archiveAvailable
                        ? Icons.cloud_done_outlined
                        : Icons.cloud_off_outlined,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.label, required this.icon});

  final String label;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: Colors.white.withValues(alpha: 0.06),
        border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(icon, size: 16),
            const SizedBox(width: 8),
            Text(label),
          ],
        ),
      ),
    );
  }
}

class _MatchHighlightsSnapshot {
  const _MatchHighlightsSnapshot({
    required this.competition,
    required this.homeTeam,
    required this.awayTeam,
    required this.homeScore,
    required this.awayScore,
    required this.phaseLabel,
    required this.highlights,
    required this.replayAvailable,
    required this.archiveAvailable,
  });

  factory _MatchHighlightsSnapshot.fromPayloads({
    required CompetitionSummary competition,
    required Map<String, Object?> liveFeed,
    required Map<String, Object?> manifest,
  }) {
    final List<dynamic> items =
        manifest['highlights'] as List<dynamic>? ?? const <dynamic>[];
    return _MatchHighlightsSnapshot(
      competition: competition,
      homeTeam: _stringValue(
        liveFeed['home_team_name'],
        fallback: competition.name,
      ),
      awayTeam: _stringValue(liveFeed['away_team_name'], fallback: 'Away'),
      homeScore: _intValue(liveFeed['home_score']),
      awayScore: _intValue(liveFeed['away_score']),
      phaseLabel: _phaseLabel(
        _stringValue(
          liveFeed['phase'],
          fallback: liveFeed['status']?.toString() ?? '',
        ),
      ),
      highlights: items
          .whereType<Map<dynamic, dynamic>>()
          .map(
            (Map<dynamic, dynamic> item) =>
                _HighlightClip.fromJson(Map<String, Object?>.from(item)),
          )
          .toList(growable: false),
      replayAvailable: manifest['replay_available'] == true,
      archiveAvailable: manifest['archive_available'] == true,
    );
  }

  final CompetitionSummary competition;
  final String homeTeam;
  final String awayTeam;
  final int homeScore;
  final int awayScore;
  final String phaseLabel;
  final List<_HighlightClip> highlights;
  final bool replayAvailable;
  final bool archiveAvailable;

  String get highlightCountLabel =>
      highlights.length == 1
          ? '1 highlight published'
          : '${highlights.length} highlights published';
}

class _HighlightClip {
  const _HighlightClip({
    required this.title,
    required this.minute,
    required this.eventTypeLabel,
    required this.accessState,
    required this.archiveAvailable,
    required this.durationLabel,
    required this.renderStatusLabel,
    this.label,
    this.subtitle,
    this.scorelineLabel,
  });

  factory _HighlightClip.fromJson(Map<String, Object?> json) {
    final int? durationSeconds = json['duration_seconds'] as int?;
    final String renderStatus = _stringValue(
      json['render_status'],
      fallback: 'pending',
    ).replaceAll('_', ' ');
    return _HighlightClip(
      title: _stringValue(
        json['overlay_title'],
        fallback: _stringValue(json['title'], fallback: 'Highlight'),
      ),
      minute: _intValue(json['minute']),
      eventTypeLabel: _titleCase(
        _stringValue(
          json['event_type'],
          fallback: 'highlight',
        ).replaceAll('_', ' '),
      ),
      accessState: _stringValue(json['access_state'], fallback: 'unavailable'),
      archiveAvailable: json['archive_available'] == true,
      durationLabel:
          durationSeconds == null
              ? 'Clip duration pending'
              : '$durationSeconds sec',
      renderStatusLabel:
          renderStatus.isEmpty ? 'Pending' : _titleCase(renderStatus),
      label: (json['label'] as String?)?.trim(),
      subtitle: (json['overlay_subtitle'] as String?)?.trim(),
      scorelineLabel: (json['scoreline_label'] as String?)?.trim(),
    );
  }

  final String title;
  final int minute;
  final String eventTypeLabel;
  final String accessState;
  final bool archiveAvailable;
  final String durationLabel;
  final String renderStatusLabel;
  final String? label;
  final String? subtitle;
  final String? scorelineLabel;
}

String _highlightsErrorMessage(Object? error, {required bool isAuthenticated}) {
  if (error is GteApiException) {
    switch (error.type) {
      case GteApiErrorType.unauthorized:
        return isAuthenticated
            ? 'Your session does not have access to this match highlight manifest.'
            : 'Sign in to load match highlights from the live backend.';
      case GteApiErrorType.notFound:
        return 'The backend has not published a highlight manifest for this match yet.';
      default:
        return error.message;
    }
  }
  return 'The live backend could not load this match highlight manifest.';
}

String _phaseLabel(String raw) {
  final String normalized = raw.trim().toLowerCase();
  switch (normalized) {
    case 'scheduled':
      return 'Scheduled';
    case 'live':
      return 'Live';
    case 'fulltime':
      return 'Full time';
    default:
      return normalized.isEmpty ? 'Status unavailable' : _titleCase(normalized);
  }
}

int _intValue(Object? value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  return int.tryParse(value?.toString() ?? '') ?? 0;
}

String _stringValue(Object? value, {required String fallback}) {
  final String resolved = value?.toString().trim() ?? '';
  return resolved.isEmpty ? fallback : resolved;
}

String _titleCase(String value) {
  final List<String> parts = value
      .split(RegExp(r'[_\s-]+'))
      .where((String part) => part.trim().isNotEmpty)
      .toList(growable: false);
  if (parts.isEmpty) {
    return '';
  }
  return parts
      .map(
        (String part) =>
            '${part.substring(0, 1).toUpperCase()}${part.substring(1).toLowerCase()}',
      )
      .join(' ');
}
