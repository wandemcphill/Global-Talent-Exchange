import 'package:flutter/material.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/features/compete/domain/competition_models.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class GteHalftimeAnalyticsScreen extends StatefulWidget {
  const GteHalftimeAnalyticsScreen({super.key, required this.competition});

  final CompetitionSummary competition;

  @override
  State<GteHalftimeAnalyticsScreen> createState() =>
      _GteHalftimeAnalyticsScreenState();
}

class _GteHalftimeAnalyticsScreenState
    extends State<GteHalftimeAnalyticsScreen> {
  late Future<_MatchAnalyticsSnapshot> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_MatchAnalyticsSnapshot> _load() async {
    final GteAppConfig config = GteAppConfig.fromRuntimeEnvironment();
    if (config.activeShellBackendMode == GteBackendMode.fixture) {
      throw const GteApiException(
        type: GteApiErrorType.unavailable,
        message: 'Halftime analytics require live backend mode.',
      );
    }
    final GteExchangeApiClient client = GteExchangeApiClient.standard(
      baseUrl: config.apiBaseUrl,
      mode: config.activeShellBackendMode,
    );
    final Map<String, Object?> liveFeed = await client.fetchMatchLiveFeed(
      widget.competition.id,
    );
    Map<String, Object?>? analytics;
    GteApiException? analyticsError;
    try {
      analytics = await client.fetchMatchAnalytics(widget.competition.id);
    } on GteApiException catch (error) {
      analyticsError = error;
    }
    return _MatchAnalyticsSnapshot.fromPayloads(
      competition: widget.competition,
      liveFeed: liveFeed,
      analytics: analytics,
      analyticsError: analyticsError,
    );
  }

  Future<void> _refresh() async {
    final Future<_MatchAnalyticsSnapshot> next = _load();
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
        appBar: AppBar(title: const Text('Halftime analytics')),
        body: FutureBuilder<_MatchAnalyticsSnapshot>(
          future: _future,
          builder: (
            BuildContext context,
            AsyncSnapshot<_MatchAnalyticsSnapshot> snapshot,
          ) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError) {
              return Padding(
                padding: const EdgeInsets.all(20),
                child: GteStatePanel(
                  title: 'Halftime analytics unavailable',
                  message: _analyticsLoadError(snapshot.error),
                  icon: Icons.analytics_outlined,
                ),
              );
            }
            final _MatchAnalyticsSnapshot data = snapshot.data!;
            return RefreshIndicator(
              onRefresh: _refresh,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                children: <Widget>[
                  _AnalyticsHero(data: data),
                  const SizedBox(height: 18),
                  if (!data.hasAnalytics)
                    GteStatePanel(
                      title: 'Analytics not generated yet',
                      message: data.unavailableReason,
                      icon: Icons.timeline_outlined,
                    )
                  else ...<Widget>[
                    _SummaryPanel(data: data),
                    const SizedBox(height: 14),
                    Wrap(
                      spacing: 14,
                      runSpacing: 14,
                      children: <Widget>[
                        _MetricPanel(
                          title: 'Expected goals',
                          home: data.xg.homeLabel,
                          away: data.xg.awayLabel,
                        ),
                        _MetricPanel(
                          title: 'Shots',
                          home: data.shots.homeLabel,
                          away: data.shots.awayLabel,
                        ),
                        _MetricPanel(
                          title: 'Shots on target',
                          home: data.shotsOnTarget.homeLabel,
                          away: data.shotsOnTarget.awayLabel,
                        ),
                        _MetricPanel(
                          title: 'Possession',
                          home: data.possession.percentHomeLabel,
                          away: data.possession.percentAwayLabel,
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    _LogPanel(
                      title: 'Tactical changes',
                      items: data.tacticalChanges,
                      emptyLabel: 'No tactical changes recorded.',
                    ),
                    const SizedBox(height: 14),
                    _LogPanel(
                      title: 'Substitutions',
                      items: data.substitutions,
                      emptyLabel: 'No substitutions recorded.',
                    ),
                  ],
                ],
              ),
            );
          },
        ),
      ),
    );
  }
}

class _AnalyticsHero extends StatelessWidget {
  const _AnalyticsHero({required this.data});

  final _MatchAnalyticsSnapshot data;

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
            '${data.phaseLabel} - ${data.minuteLabel}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              _StatusChip(
                label:
                    data.analyticsAvailable
                        ? 'Analytics published'
                        : 'Analytics pending',
                icon:
                    data.analyticsAvailable
                        ? Icons.analytics_outlined
                        : Icons.pending_outlined,
              ),
              _StatusChip(
                label: data.scoreLabel,
                icon: Icons.scoreboard_outlined,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SummaryPanel extends StatelessWidget {
  const _SummaryPanel({required this.data});

  final _MatchAnalyticsSnapshot data;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Summary', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          Text(data.summaryLine, style: Theme.of(context).textTheme.bodyLarge),
        ],
      ),
    );
  }
}

class _MetricPanel extends StatelessWidget {
  const _MetricPanel({
    required this.title,
    required this.home,
    required this.away,
  });

  final String title;
  final String home;
  final String away;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 230,
      child: GteSurfacePanel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 10),
            Text('Home: $home'),
            const SizedBox(height: 4),
            Text('Away: $away'),
          ],
        ),
      ),
    );
  }
}

class _LogPanel extends StatelessWidget {
  const _LogPanel({
    required this.title,
    required this.items,
    required this.emptyLabel,
  });

  final String title;
  final List<String> items;
  final String emptyLabel;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          if (items.isEmpty)
            Text(emptyLabel)
          else
            ...items.map(
              (String item) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text(item),
              ),
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

class _MatchAnalyticsSnapshot {
  const _MatchAnalyticsSnapshot({
    required this.competition,
    required this.homeTeam,
    required this.awayTeam,
    required this.homeScore,
    required this.awayScore,
    required this.phaseLabel,
    required this.minuteLabel,
    required this.analyticsAvailable,
    required this.summaryLine,
    required this.scoreLabel,
    required this.xg,
    required this.shots,
    required this.shotsOnTarget,
    required this.possession,
    required this.tacticalChanges,
    required this.substitutions,
    required this.unavailableReason,
  });

  factory _MatchAnalyticsSnapshot.fromPayloads({
    required CompetitionSummary competition,
    required Map<String, Object?> liveFeed,
    required Map<String, Object?>? analytics,
    required GteApiException? analyticsError,
  }) {
    final Map<String, Object?> availability = Map<String, Object?>.from(
      liveFeed['availability'] as Map? ?? const <String, Object?>{},
    );
    final bool feedClaimsAnalytics =
        availability['halftime_analytics_available'] == true;
    final bool analyticsAvailable = feedClaimsAnalytics && analytics != null;
    return _MatchAnalyticsSnapshot(
      competition: competition,
      homeTeam: _stringValue(liveFeed['home_team_name'], fallback: 'Home'),
      awayTeam: _stringValue(liveFeed['away_team_name'], fallback: 'Away'),
      homeScore: _intValue(liveFeed['home_score']),
      awayScore: _intValue(liveFeed['away_score']),
      phaseLabel: _phaseLabel(
        _stringValue(
          liveFeed['phase'],
          fallback: liveFeed['status']?.toString() ?? '',
        ),
      ),
      minuteLabel: _minuteLabel(liveFeed['minute']),
      analyticsAvailable: analyticsAvailable,
      summaryLine: _stringValue(analytics?['summary_line'], fallback: ''),
      scoreLabel: _stringValue(
        analytics?['score'],
        fallback:
            '${_intValue(liveFeed['home_score'])}-${_intValue(liveFeed['away_score'])}',
      ),
      xg: _RatioPair.fromJson(analytics?['xg']),
      shots: _RatioPair.fromJson(analytics?['shots']),
      shotsOnTarget: _RatioPair.fromJson(analytics?['shots_on_target']),
      possession: _RatioPair.fromJson(analytics?['possession']),
      tacticalChanges: _tacticalChangeLines(analytics?['tactical_changes']),
      substitutions: _substitutionLines(analytics?['substitutions']),
      unavailableReason: _unavailableReason(
        phase: _stringValue(liveFeed['phase'], fallback: ''),
        analyticsError: analyticsError,
        feedAvailability: feedClaimsAnalytics,
      ),
    );
  }

  final CompetitionSummary competition;
  final String homeTeam;
  final String awayTeam;
  final int homeScore;
  final int awayScore;
  final String phaseLabel;
  final String minuteLabel;
  final bool analyticsAvailable;
  final String summaryLine;
  final String scoreLabel;
  final _RatioPair xg;
  final _RatioPair shots;
  final _RatioPair shotsOnTarget;
  final _RatioPair possession;
  final List<String> tacticalChanges;
  final List<String> substitutions;
  final String unavailableReason;

  bool get hasAnalytics => analyticsAvailable;
}

class _RatioPair {
  const _RatioPair({required this.home, required this.away});

  factory _RatioPair.fromJson(Object? value) {
    final Map<String, Object?> json = Map<String, Object?>.from(
      value as Map? ?? const <String, Object?>{},
    );
    return _RatioPair(
      home: _doubleValue(json['home']),
      away: _doubleValue(json['away']),
    );
  }

  final double home;
  final double away;

  String get homeLabel =>
      home.toStringAsFixed(home.truncateToDouble() == home ? 0 : 1);
  String get awayLabel =>
      away.toStringAsFixed(away.truncateToDouble() == away ? 0 : 1);
  String get percentHomeLabel => '${home.toStringAsFixed(1)}%';
  String get percentAwayLabel => '${away.toStringAsFixed(1)}%';
}

String _analyticsLoadError(Object? error) {
  if (error is GteApiException) {
    return error.message;
  }
  return 'The live backend could not load match analytics.';
}

String _unavailableReason({
  required String phase,
  required GteApiException? analyticsError,
  required bool feedAvailability,
}) {
  if (feedAvailability && analyticsError == null) {
    return 'The backend marked analytics as available, but the analytics payload was empty.';
  }
  if (analyticsError != null) {
    if (analyticsError.type == GteApiErrorType.notFound) {
      return 'The replay analytics payload has not been stored for this match yet.';
    }
    return analyticsError.message;
  }
  final String normalized = phase.trim().toLowerCase();
  if (normalized == 'scheduled') {
    return 'This match has not started yet, so there is no halftime snapshot to show.';
  }
  if (normalized == 'live') {
    return 'The match is live, but the backend has not published an analytics snapshot yet.';
  }
  return 'No live analytics payload is available for this match yet.';
}

List<String> _tacticalChangeLines(Object? value) {
  final List<dynamic> items = value as List<dynamic>? ?? const <dynamic>[];
  return items
      .whereType<Map<dynamic, dynamic>>()
      .map((Map<dynamic, dynamic> raw) {
        final Map<String, Object?> item = Map<String, Object?>.from(raw);
        final String team = _stringValue(item['team_name'], fallback: 'Team');
        final int minute = _intValue(item['applied_minute']);
        final String changeType = _titleCase(
          _stringValue(
            item['change_type'],
            fallback: 'change',
          ).replaceAll('_', ' '),
        );
        final String urgency = _stringValue(item['urgency'], fallback: '');
        return urgency.isEmpty
            ? "$minute' $team: $changeType"
            : "$minute' $team: $changeType (${_titleCase(urgency)})";
      })
      .toList(growable: false);
}

List<String> _substitutionLines(Object? value) {
  final List<dynamic> items = value as List<dynamic>? ?? const <dynamic>[];
  return items
      .whereType<Map<dynamic, dynamic>>()
      .map((Map<dynamic, dynamic> raw) {
        final Map<String, Object?> item = Map<String, Object?>.from(raw);
        final String team = _stringValue(item['team_name'], fallback: 'Team');
        final int minute = _intValue(item['applied_minute']);
        final String reason = _stringValue(item['reason'], fallback: '');
        return reason.isEmpty
            ? "$minute' $team substitution recorded."
            : "$minute' $team substitution: $reason";
      })
      .toList(growable: false);
}

String _minuteLabel(Object? value) {
  final int minute = _intValue(value);
  return minute > 0 ? "$minute'" : 'Minute unavailable';
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

double _doubleValue(Object? value) {
  if (value is double) {
    return value;
  }
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value?.toString() ?? '') ?? 0;
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
