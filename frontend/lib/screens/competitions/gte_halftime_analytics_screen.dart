import 'package:flutter/material.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';
import 'package:gte_frontend/widgets/gtex_branding.dart';

class GteHalftimeAnalyticsScreen extends StatefulWidget {
  const GteHalftimeAnalyticsScreen({
    super.key,
    required this.competition,
  });

  final CompetitionSummary competition;

  @override
  State<GteHalftimeAnalyticsScreen> createState() =>
      _GteHalftimeAnalyticsScreenState();
}

class _GteHalftimeAnalyticsScreenState
    extends State<GteHalftimeAnalyticsScreen> {
  late Future<LiveMatchSnapshot> _snapshotFuture;
  final Set<String> _selectedChanges = <String>{};

  @override
  void initState() {
    super.initState();
    _snapshotFuture = loadLiveMatchSnapshot(widget.competition);
  }

  void _reload() {
    setState(() {
      _snapshotFuture = loadLiveMatchSnapshot(widget.competition);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Halftime analytics'),
        ),
        body: FutureBuilder<LiveMatchSnapshot>(
          future: _snapshotFuture,
          builder: (BuildContext context,
              AsyncSnapshot<LiveMatchSnapshot> snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Padding(
                padding: EdgeInsets.all(20),
                child: GteStatePanel(
                  eyebrow: 'HALFTIME',
                  title: 'Building analytics desk',
                  message:
                      'Pulling tactical summary, momentum, and suggested changes.',
                  icon: Icons.analytics_outlined,
                  accentColor: GteShellTheme.accentArena,
                  isLoading: true,
                ),
              );
            }
            if (!snapshot.hasData) {
              return Padding(
                padding: const EdgeInsets.all(20),
                child: GteStatePanel(
                  title: 'Halftime analytics unavailable',
                  message:
                      'Unable to load the halftime dashboard right now.',
                  icon: Icons.warning_amber_outlined,
                  actionLabel: 'Retry',
                  onAction: _reload,
                ),
              );
            }

            final LiveMatchSnapshot match = snapshot.data!;
            return ListView(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
              children: <Widget>[
                if (!match.halftimeAnalyticsAvailable) ...<Widget>[
                  GteSurfacePanel(
                    child: Row(
                      children: <Widget>[
                        const Icon(Icons.info_outline, size: 20),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            'Live halftime analytics are not available yet. Showing a fallback snapshot.',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                ],
                GteSurfacePanel(
                  accentColor: GteShellTheme.accentArena,
                  emphasized: true,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Halftime report',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        '${match.homeTeam} ${match.homeScore} - ${match.awayScore} ${match.awayTeam}',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 10,
                        runSpacing: 10,
                        children: <Widget>[
                          GteMetricChip(label: 'Momentum', value: 'Swinging'),
                          GteMetricChip(label: 'High press', value: 'Active'),
                          GteMetricChip(label: 'Transition speed', value: 'Fast'),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                const GtexSectionHeader(
                  eyebrow: 'ANALYTICS DESK',
                  title: 'A tactical summary tuned for live adjustments.',
                  description:
                      'Suggested changes apply immediately without pausing the match.',
                  accent: GteShellTheme.accentArena,
                ),
                const SizedBox(height: 12),
                GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Tactical summary',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'The home side are winning the first duel but leaving space behind the right back. Expected threat rises on the opposite flank.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 14),
                      Text(
                        'Suggested changes',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      ...match.tacticalSuggestions.map(
                        (LiveMatchTacticalSuggestion suggestion) {
                          return CheckboxListTile(
                            value: _selectedChanges
                                .contains(suggestion.title),
                            onChanged: (bool? value) {
                              setState(() {
                                if (value == true) {
                                  _selectedChanges.add(suggestion.title);
                                } else {
                                  _selectedChanges.remove(suggestion.title);
                                }
                              });
                            },
                            title: Text(suggestion.title),
                            subtitle: Text(
                              '${suggestion.detail} • ${suggestion.impactLabel}',
                            ),
                            contentPadding: EdgeInsets.zero,
                          );
                        },
                      ),
                      const SizedBox(height: 12),
                      FilledButton.icon(
                        onPressed: _selectedChanges.isEmpty
                            ? null
                            : () {
                                AppFeedback.showSuccess(
                                  context,
                                  'Halftime changes applied instantly.',
                                );
                              },
                        icon: const Icon(Icons.tune_outlined),
                        label: const Text('Apply halftime changes'),
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
}
