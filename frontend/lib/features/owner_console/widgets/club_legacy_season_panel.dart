import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

class ClubLegacySeasonPanelData {
  const ClubLegacySeasonPanelData({
    required this.seasons,
    required this.invitationCount,
    required this.acceptance,
    required this.settlementTotal,
    required this.supplyRemaining,
    required this.openCases,
    required this.showroomFailures,
    required this.flags,
  });

  factory ClubLegacySeasonPanelData.fromJson(Map<String, dynamic> json) {
    final Map<String, dynamic> metrics = json['metrics'] is Map ? Map<String, dynamic>.from(json['metrics'] as Map) : json;
    final Map<String, dynamic> flags = json['flags'] is Map ? Map<String, dynamic>.from(json['flags'] as Map) : <String, dynamic>{};
    return ClubLegacySeasonPanelData(
      seasons: _rows(json['seasons']),
      invitationCount: int.tryParse('${metrics['invitation_count'] ?? 0}') ?? 0,
      acceptance: int.tryParse('${metrics['acceptance'] ?? 0}') ?? 0,
      settlementTotal: '${metrics['settlement_total'] ?? '0'}',
      supplyRemaining: '${metrics['supply_remaining'] ?? '0'}',
      openCases: int.tryParse('${metrics['open_cases'] ?? 0}') ?? 0,
      showroomFailures: int.tryParse('${metrics['showroom_failure_count'] ?? 0}') ?? 0,
      flags: flags.map((String key, dynamic value) => MapEntry(key, value == true)),
    );
  }

  final List<Map<String, dynamic>> seasons;
  final int invitationCount;
  final int acceptance;
  final String settlementTotal;
  final String supplyRemaining;
  final int openCases;
  final int showroomFailures;
  final Map<String, bool> flags;
}

List<Map<String, dynamic>> _rows(Object? value) => (value is List ? value : const <dynamic>[])
    .whereType<Map>()
    .map((Map row) => Map<String, dynamic>.from(row))
    .toList();

class ClubLegacySeasonPanel extends StatelessWidget {
  const ClubLegacySeasonPanel({super.key, required this.data, required this.onAction});

  final ClubLegacySeasonPanelData data;
  final void Function(String action) onAction;

  @override
  Widget build(BuildContext context) {
    return ListView(
      key: const Key('club-legacy-season-panel'),
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        for (final Map<String, dynamic> season in data.seasons)
          Padding(
            padding: const EdgeInsets.only(bottom: GtexSpacing.md),
            child: GtexPanel(
              title: '${season['tier']}',
              subtitle: 'Reputation, revenue, youth, sanctions',
              accent: GtexColors.cyan,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Reputation ${season['reputation']}', key: Key('season-${season['tier']}-reputation')),
                  Text('Revenue ${season['revenue']}', key: Key('season-${season['tier']}-revenue')),
                  Text('Youth ${season['youth']}', key: Key('season-${season['tier']}-youth')),
                  Text('Sanctions ${season['sanctions']}', key: Key('season-${season['tier']}-sanctions')),
                ],
              ),
            ),
          ),
        GtexPanel(
          title: 'Metrics',
          subtitle: 'Invitations, acceptance, settlements, supply, cases',
          accent: GtexColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Invitations ${data.invitationCount}', key: const Key('metric-invitations')),
              Text('Acceptance ${data.acceptance}', key: const Key('metric-acceptance')),
              Text('Settlements ${data.settlementTotal}', key: const Key('metric-settlements')),
              Text('Supply ${data.supplyRemaining}', key: const Key('metric-supply')),
              Text('Open cases ${data.openCases}', key: const Key('metric-open-cases')),
              Text('Showroom failures ${data.showroomFailures}', key: const Key('metric-showroom-failures')),
              const SizedBox(height: GtexSpacing.sm),
              Wrap(
                spacing: GtexSpacing.xs,
                runSpacing: GtexSpacing.xs,
                children: <Widget>[
                  for (final MapEntry<String, bool> flag in data.flags.entries)
                    Text('${flag.key} ${flag.value ? 'on' : 'off'}', key: Key('flag-${flag.key}')),
                ],
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(key: const Key('season-simulate'), label: 'Simulate', icon: Icons.timeline_rounded, compact: true, onPressed: () => onAction('simulate')),
            ],
          ),
        ),
      ],
    );
  }
}
