import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

class ClubLegacyManagerPanelData {
  const ClubLegacyManagerPanelData({
    required this.name,
    required this.personality,
    required this.ambition,
    required this.wageExpectation,
    required this.relationshipScore,
    required this.offers,
    this.retention = '',
  });

  factory ClubLegacyManagerPanelData.fromJson(Map<String, dynamic> json) {
    return ClubLegacyManagerPanelData(
      name: '${json['name'] ?? ''}',
      personality: '${json['personality'] ?? ''}',
      ambition: int.tryParse('${json['ambition'] ?? 0}') ?? 0,
      wageExpectation: '${json['wage_expectation'] ?? '0'}',
      relationshipScore: int.tryParse('${json['relationship_score'] ?? 0}') ?? 0,
      offers: _rows(json['offers']),
      retention: '${json['retention'] ?? ''}',
    );
  }

  final String name;
  final String personality;
  final int ambition;
  final String wageExpectation;
  final int relationshipScore;
  final List<Map<String, dynamic>> offers;
  final String retention;
}

List<Map<String, dynamic>> _rows(Object? value) => (value is List ? value : const <dynamic>[])
    .whereType<Map>()
    .map((Map row) => Map<String, dynamic>.from(row))
    .toList();

class ClubLegacyManagerPanel extends StatelessWidget {
  const ClubLegacyManagerPanel({super.key, required this.data, required this.onAction});

  final ClubLegacyManagerPanelData data;
  final void Function(String action) onAction;

  @override
  Widget build(BuildContext context) {
    return ListView(
      key: const Key('club-legacy-manager-panel'),
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        GtexPanel(
          title: data.name,
          subtitle: 'Ambition, personality, and wage expectations',
          accent: GtexColors.cyan,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Personality ${data.personality}', key: const Key('manager-personality')),
              Text('Ambition ${data.ambition}', key: const Key('manager-ambition')),
              Text('Wage expectation ${data.wageExpectation}', key: const Key('manager-wage-expectation')),
              Text('Relationship ${data.relationshipScore}', key: const Key('manager-relationship')),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Term sheets',
          subtitle: 'A counter keeps the previous terms',
          accent: GtexColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              if (data.offers.isEmpty) const Text('No offers yet', style: TextStyle(color: GtexColors.textSecondary)),
              for (final Map<String, dynamic> offer in data.offers)
                Text(
                  '${offer['wage']} · ${offer['contract_length']} years · ${offer['role']} · ${offer['outcome']}',
                  key: Key('offer-${offer['outcome']}'),
                ),
              if (data.retention.isNotEmpty) Text(data.retention, key: const Key('manager-retention')),
              const SizedBox(height: GtexSpacing.sm),
              Wrap(
                spacing: GtexSpacing.xs,
                runSpacing: GtexSpacing.xs,
                children: <Widget>[
                  GtexActionButton(key: const Key('manager-offer'), label: 'Offer', icon: Icons.handshake_rounded, compact: true, onPressed: () => onAction('offer')),
                  GtexActionButton(key: const Key('manager-accept'), label: 'Accept', icon: Icons.check_rounded, compact: true, onPressed: () => onAction('accept')),
                  GtexActionButton(key: const Key('manager-reject'), label: 'Reject', icon: Icons.close_rounded, compact: true, secondary: true, onPressed: () => onAction('reject')),
                  GtexActionButton(key: const Key('manager-counter'), label: 'Counter', icon: Icons.reply_rounded, compact: true, onPressed: () => onAction('counter')),
                  GtexActionButton(key: const Key('manager-promise'), label: 'Promise', icon: Icons.flag_rounded, compact: true, onPressed: () => onAction('promise')),
                  GtexActionButton(key: const Key('manager-poach'), label: 'Poach', icon: Icons.swap_horiz_rounded, compact: true, onPressed: () => onAction('poach')),
                  GtexActionButton(key: const Key('manager-retain'), label: 'Retain', icon: Icons.shield_rounded, compact: true, onPressed: () => onAction('retain')),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }
}
