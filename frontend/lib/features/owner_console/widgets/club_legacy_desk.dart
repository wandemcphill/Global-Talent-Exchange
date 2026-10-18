import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

class ClubLegacyDeskData {
  const ClubLegacyDeskData({
    required this.staff,
    required this.policies,
    required this.clubValuation,
    required this.equity,
    required this.preseason,
    required this.sponsors,
    required this.offers,
    required this.cases,
    this.market = const <Map<String, dynamic>>[],
  });

  factory ClubLegacyDeskData.fromJson(Map<String, dynamic> json) {
    final Map<String, dynamic> finance = json['finance'] is Map ? Map<String, dynamic>.from(json['finance'] as Map) : <String, dynamic>{};
    return ClubLegacyDeskData(
      staff: _rows(json['staff']),
      policies: _rows(json['policies']),
      clubValuation: '${finance['club_valuation'] ?? '0'}',
      equity: '${finance['equity'] ?? '0'}',
      preseason: _rows(json['preseason']),
      sponsors: _rows(json['sponsors']),
      offers: _rows(json['offers']),
      cases: _rows(json['cases']),
      market: _rows(json['market']),
    );
  }

  final List<Map<String, dynamic>> staff;
  final List<Map<String, dynamic>> policies;
  final String clubValuation;
  final String equity;
  final List<Map<String, dynamic>> preseason;
  final List<Map<String, dynamic>> sponsors;
  final List<Map<String, dynamic>> offers;
  final List<Map<String, dynamic>> cases;
  final List<Map<String, dynamic>> market;
}

List<Map<String, dynamic>> _rows(Object? value) => (value is List ? value : const <dynamic>[])
    .whereType<Map>()
    .map((Map row) => Map<String, dynamic>.from(row))
    .toList();

class ClubLegacyDesk extends StatelessWidget {
  const ClubLegacyDesk({super.key, required this.data, required this.onAction});

  final ClubLegacyDeskData data;
  final void Function(String action) onAction;

  @override
  Widget build(BuildContext context) {
    return ListView(
      key: const Key('club-legacy-desk'),
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        _panel('Staff', data.staff.map((Map<String, dynamic> row) => '${row['role']}: ${row['name']}').toList(), 'Hire GM', 'hire', const Key('club-desk-hire')),
        _panel('Authority', data.policies.map((Map<String, dynamic> row) => '${row['task_key']} · ${row['mode']}').toList(), 'Balanced preset', 'preset', const Key('club-desk-preset')),
        GtexPanel(
          key: const Key('club-desk-finance'),
          title: 'Finance',
          subtitle: 'Equity is not the whole club',
          accent: GtexColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Club value ${data.clubValuation}', key: const Key('club-desk-valuation')),
              Text('Your equity ${data.equity}', key: const Key('club-desk-equity')),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        _panel('Pre-season', data.preseason.map((Map<String, dynamic> row) => '${row['match_on']} · ${row['status']}').toList(), null, null, null),
        _panel('Sponsors', data.sponsors.map((Map<String, dynamic> row) => '${row['sponsor_name']} · ${row['placement']} · ${row['status']}').toList(), 'Offer front sponsor', 'sponsor', const Key('club-desk-sponsor')),
        _panel('Manager talks', data.offers.map((Map<String, dynamic> row) => '${row['candidate_name']} · ${row['outcome']}').toList(), 'Make offer', 'manager', const Key('club-desk-manager')),
        _panel('Governance', data.cases.map((Map<String, dynamic> row) => '${row['rule_code']} · ${row['status']}').toList(), 'Open case', 'case', const Key('club-desk-case')),
        _market(),
      ],
    );
  }

  Widget _market() {
    final List<String> lines = data.market
        .map((Map<String, dynamic> row) {
          final String bid = '${row['leading_bid'] ?? ''}'.trim();
          final String price = '${row['name']} · ${row['status']} · ${row['price']}';
          return bid.isEmpty ? price : '$price · bid $bid';
        })
        .toList();
    return Padding(
      padding: const EdgeInsets.only(bottom: GtexSpacing.md),
      child: GtexPanel(
        key: const Key('club-desk-market'),
        title: 'Market',
        subtitle: 'Auctions stay in escrow until the leading bid is paid',
        accent: GtexColors.gold,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            if (lines.isEmpty) const Text('Nothing listed', style: TextStyle(color: GtexColors.textSecondary)),
            for (final String line in lines) Text(line, style: const TextStyle(color: GtexColors.text)),
            const SizedBox(height: GtexSpacing.sm),
            Wrap(
              spacing: GtexSpacing.xs,
              children: <Widget>[
                GtexActionButton(
                  key: const Key('club-desk-auction'),
                  label: 'Auction an asset',
                  icon: Icons.gavel_rounded,
                  compact: true,
                  onPressed: () => onAction('list_auction'),
                ),
                GtexActionButton(
                  key: const Key('club-desk-bid'),
                  label: 'Place bid',
                  icon: Icons.price_change_rounded,
                  compact: true,
                  secondary: true,
                  onPressed: () => onAction('place_bid'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _panel(String title, List<String> lines, String? button, String? action, Key? buttonKey) {
    return Padding(
      padding: const EdgeInsets.only(bottom: GtexSpacing.md),
      child: GtexPanel(
        title: title,
        accent: GtexColors.cyan,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            if (lines.isEmpty) const Text('Nothing here yet', style: TextStyle(color: GtexColors.textSecondary)),
            for (final String line in lines) Text(line, style: const TextStyle(color: GtexColors.text)),
            if (button != null && action != null) ...<Widget>[
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(key: buttonKey, label: button, icon: Icons.play_arrow_rounded, compact: true, onPressed: () => onAction(action)),
            ],
          ],
        ),
      ),
    );
  }
}
