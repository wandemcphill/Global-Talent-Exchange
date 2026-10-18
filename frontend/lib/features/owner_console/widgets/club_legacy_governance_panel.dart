import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

class ClubLegacyGovernancePanelData {
  const ClubLegacyGovernancePanelData({
    required this.cases,
    required this.stakes,
    required this.reviews,
    required this.personalAssets,
    required this.clubAssets,
    required this.minorityStakes,
    this.distribution = '',
  });

  factory ClubLegacyGovernancePanelData.fromJson(Map<String, dynamic> json) {
    final Map<String, dynamic> worth = json['net_worth'] is Map ? Map<String, dynamic>.from(json['net_worth'] as Map) : <String, dynamic>{};
    return ClubLegacyGovernancePanelData(
      cases: _rows(json['cases']),
      stakes: _rows(json['stakes']),
      reviews: _rows(json['reviews']),
      personalAssets: '${worth['personal_assets'] ?? json['personal_assets'] ?? '0'}',
      clubAssets: '${worth['club_assets'] ?? json['club_assets'] ?? '0'}',
      minorityStakes: '${worth['minority_stakes'] ?? json['minority_stakes'] ?? '0'}',
      distribution: '${json['distribution'] ?? ''}',
    );
  }

  final List<Map<String, dynamic>> cases;
  final List<Map<String, dynamic>> stakes;
  final List<Map<String, dynamic>> reviews;
  final String personalAssets;
  final String clubAssets;
  final String minorityStakes;
  final String distribution;
}

List<Map<String, dynamic>> _rows(Object? value) => (value is List ? value : const <dynamic>[])
    .whereType<Map>()
    .map((Map row) => Map<String, dynamic>.from(row))
    .toList();

class ClubLegacyGovernancePanel extends StatelessWidget {
  const ClubLegacyGovernancePanel({super.key, required this.data, required this.onAction});

  final ClubLegacyGovernancePanelData data;
  final void Function(String action) onAction;

  @override
  Widget build(BuildContext context) {
    return ListView(
      key: const Key('club-legacy-governance-panel'),
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        GtexPanel(
          title: 'Cases',
          subtitle: 'Rule, evidence, sanction, and appeal',
          accent: GtexColors.cyan,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              if (data.cases.isEmpty) const Text('No sporting case', style: TextStyle(color: GtexColors.textSecondary)),
              for (final Map<String, dynamic> item in data.cases) ...<Widget>[
                Text('${item['rule_code']}', key: const Key('case-rule')),
                Text('${item['allegation']}', key: const Key('case-allegation')),
                Text('${item['evidence']}', key: const Key('case-evidence')),
                Text('${item['status']}', key: const Key('case-status')),
                Text('${item['sanction'] ?? ''} · ${item['reason'] ?? ''}', key: const Key('case-sanction')),
                Text('${item['appeal_outcome'] ?? ''}', key: const Key('case-appeal')),
              ],
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(key: const Key('governance-case'), label: 'Open case', icon: Icons.gavel_rounded, compact: true, onPressed: () => onAction('case')),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Stakes',
          subtitle: 'Voting rights are not the economic percentage',
          accent: GtexColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              if (data.stakes.isEmpty) const Text('No stakes', style: TextStyle(color: GtexColors.textSecondary)),
              for (final Map<String, dynamic> stake in data.stakes)
                Text(
                  '${stake['holder']} · economic ${stake['percentage']}% · votes ${stake['voting_rights']}%',
                  key: const Key('stake-line'),
                ),
              if (data.distribution.isNotEmpty) Text(data.distribution, key: const Key('distribution-line')),
              const SizedBox(height: GtexSpacing.sm),
              Wrap(
                spacing: GtexSpacing.xs,
                children: <Widget>[
                  GtexActionButton(key: const Key('governance-stake'), label: 'Set stake', icon: Icons.pie_chart_rounded, compact: true, onPressed: () => onAction('stake')),
                  GtexActionButton(key: const Key('governance-distribute'), label: 'Distribute', icon: Icons.payments_rounded, compact: true, onPressed: () => onAction('distribute')),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Reviews',
          subtitle: 'Related-party and sister-club trades stay reviewable',
          accent: GtexColors.cyan,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              if (data.reviews.isEmpty) const Text('Nothing to review', style: TextStyle(color: GtexColors.textSecondary)),
              for (final Map<String, dynamic> review in data.reviews)
                Text('${review['kind']} · ${review['status']}', key: Key('review-${review['kind']}')),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Net worth',
          subtitle: 'Personal assets, club assets, and minority stakes stay apart',
          accent: GtexColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Personal assets ${data.personalAssets}', key: const Key('worth-personal')),
              Text('Club assets ${data.clubAssets}', key: const Key('worth-club')),
              Text('Minority stakes ${data.minorityStakes}', key: const Key('worth-minority')),
            ],
          ),
        ),
      ],
    );
  }
}
