import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

class ClubLegacySponsorData {
  const ClubLegacySponsorData({
    required this.zones,
    required this.sponsorName,
    required this.contractZones,
    required this.fee,
    required this.previewPublished,
    required this.suggestion,
    required this.kitStatus,
    required this.impressions,
    required this.note,
    required this.renewedFrom,
  });

  final List<String> zones;
  final String sponsorName;
  final List<String> contractZones;
  final String fee;
  final bool previewPublished;
  final String suggestion;
  final String kitStatus;
  final int impressions;
  final String note;
  final String renewedFrom;
}

class ClubLegacySponsorPanel extends StatelessWidget {
  const ClubLegacySponsorPanel({super.key, required this.data, required this.onAction});

  final ClubLegacySponsorData data;
  final void Function(String action) onAction;

  @override
  Widget build(BuildContext context) {
    final String previewLabel = data.previewPublished ? 'Published' : 'Preview only';
    return ListView(
      key: const Key('club-legacy-sponsor-panel'),
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        GtexPanel(
          title: 'Commercial inventory',
          subtitle: 'Shirt front, sleeve, and board',
          accent: GtexColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              for (final String zone in data.zones) Text(zone, key: Key('club-sponsor-zone-$zone')),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: data.sponsorName,
          subtitle: 'Contract zones and fee',
          accent: GtexColors.cyan,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(data.contractZones.join(', '), key: const Key('club-sponsor-contract-zones')),
              Text('Fee ${data.fee}', key: const Key('club-sponsor-fee')),
              Text(previewLabel, key: const Key('club-sponsor-preview')),
              Text(data.suggestion, key: const Key('club-sponsor-suggestion')),
              Text(data.kitStatus, key: const Key('club-sponsor-kit')),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Delivery',
          subtitle: 'Impressions and a note',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('${data.impressions} impressions', key: const Key('club-sponsor-impressions')),
              Text(data.note, key: const Key('club-sponsor-note')),
              Text('Renewed from ${data.renewedFrom}', key: const Key('club-sponsor-renewal')),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        Wrap(
          spacing: GtexSpacing.xs,
          children: <Widget>[
            GtexActionButton(key: const Key('club-sponsor-preview-action'), label: 'Preview', icon: Icons.visibility_outlined, compact: true, onPressed: () => onAction('preview')),
            GtexActionButton(key: const Key('club-sponsor-suggest'), label: 'Suggest', icon: Icons.auto_awesome, compact: true, secondary: true, onPressed: () => onAction('suggest')),
            GtexActionButton(key: const Key('club-sponsor-approve'), label: 'Approve', icon: Icons.verified_outlined, compact: true, onPressed: () => onAction('approve')),
            GtexActionButton(key: const Key('club-sponsor-publish'), label: 'Publish', icon: Icons.publish, compact: true, onPressed: () => onAction('publish')),
            GtexActionButton(key: const Key('club-sponsor-deliver'), label: 'Report delivery', icon: Icons.insights, compact: true, secondary: true, onPressed: () => onAction('deliver')),
            GtexActionButton(key: const Key('club-sponsor-renew'), label: 'Renew', icon: Icons.autorenew, compact: true, secondary: true, onPressed: () => onAction('renew')),
          ],
        ),
      ],
    );
  }
}
