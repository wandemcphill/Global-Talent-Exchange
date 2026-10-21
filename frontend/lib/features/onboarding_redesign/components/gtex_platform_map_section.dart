import 'dart:math' as math;
import 'package:flutter/material.dart';

import 'gtex_home_shared_widgets.dart';

class GtexPlatformMapSection extends StatelessWidget {
  const GtexPlatformMapSection({
    super.key,
    this.onSignup,
  });

  final VoidCallback? onSignup;

  @override
  Widget build(BuildContext context) {
    final double width = MediaQuery.sizeOf(context).width;
    final bool isNarrow = width < 760;

    final List<_PillarItem> items = <_PillarItem>[
      const _PillarItem(
        Icons.person_search_rounded,
        'Talent Exchange',
        'Find players, compare profiles, track value and move talent across the world.',
        kSkyBlue,
      ),
      const _PillarItem(
        Icons.account_balance_rounded,
        'Club Ownership',
        'Build a club identity, manage your squad, shape its legacy and compete.',
        kPitchGreenBright,
      ),
      const _PillarItem(
        Icons.analytics_rounded,
        'Football Intelligence',
        'Player data, scouting signals, performance, reports and market context.',
        Color(0xFF38BDF8),
      ),
      const _PillarItem(
        Icons.emoji_events_rounded,
        'Matches & Competitions',
        'Live matchday, leagues, tournaments, awards and progression.',
        kGoldPrimary,
      ),
      const _PillarItem(
        Icons.account_balance_wallet_rounded,
        'Wallet & Economy',
        'Wallet funding, P2P activity, withdrawals and football commerce.',
        Color(0xFFA855F7),
      ),
      const _PillarItem(
        Icons.forum_rounded,
        'Social Football',
        'Creators, fans, news, Fan Wars, gifting and a living community.',
        Color(0xFFFF5FA2),
      ),
    ];

    return Container(
      color: kNavyInset,
      padding: EdgeInsets.symmetric(
        horizontal: isNarrow ? 20 : 64,
        vertical: 64,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Text(
            'ONE PLATFORM. MANY WAYS TO PLAY.',
            style: TextStyle(
              color: kPitchGreenBright,
              fontSize: 11,
              letterSpacing: 1.7,
              fontWeight: FontWeight.w700,
              fontFamily: kFontCondensed,
            ),
          ),
          const SizedBox(height: 14),
          const Text(
            'Everything football.\nOne living system.',
            style: TextStyle(
              color: kTextPrimary,
              fontSize: 48,
              height: 0.95,
              fontWeight: FontWeight.w900,
              fontFamily: kFontCondensed,
            ),
          ),
          const SizedBox(height: 14),
          const Text(
            'GTEX brings talent, clubs, markets, matches, money and community into one connected football ecosystem.',
            style: TextStyle(
              color: kTextSecondary,
              fontSize: 15,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 32),
          _FeatureGrid(items: items),
          const SizedBox(height: 28),
          GtexGhostButton(
            label: 'See the football world',
            onPressed: onSignup,
          ),
        ],
      ),
    );
  }
}

class _PillarItem {
  const _PillarItem(this.icon, this.title, this.body, this.accent);

  final IconData icon;
  final String title;
  final String body;
  final Color accent;
}

class _FeatureGrid extends StatelessWidget {
  const _FeatureGrid({required this.items});

  final List<_PillarItem> items;
  static const double _gap = 14;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final int columns = constraints.maxWidth > 1050
            ? 3
            : constraints.maxWidth > 650
                ? 2
                : 1;

        final List<Widget> rows = <Widget>[];
        for (int start = 0; start < items.length; start += columns) {
          if (rows.isNotEmpty) {
            rows.add(const SizedBox(height: _gap));
          }
          final int end = math.min(start + columns, items.length);
          rows.add(
            IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: <Widget>[
                  for (int column = 0; column < columns; column++) ...<Widget>[
                    if (column > 0) const SizedBox(width: _gap),
                    Expanded(
                      child: start + column < end
                          ? _FeatureCard(item: items[start + column])
                          : const SizedBox.shrink(),
                    ),
                  ],
                ],
              ),
            ),
          );
        }
        return Column(children: rows);
      },
    );
  }
}

class _FeatureCard extends StatelessWidget {
  const _FeatureCard({required this.item});

  final _PillarItem item;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: kNavyRaised,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: kNavyLine),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: item.accent.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: item.accent.withValues(alpha: 0.3)),
            ),
            child: Icon(item.icon, color: item.accent, size: 22),
          ),
          const SizedBox(height: 14),
          Text(
            item.title,
            style: const TextStyle(
              color: kTextPrimary,
              fontSize: 20,
              fontWeight: FontWeight.w800,
              fontFamily: kFontCondensed,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            item.body,
            style: const TextStyle(
              color: kTextSecondary,
              fontSize: 13,
              height: 1.45,
            ),
          ),
        ],
      ),
    );
  }
}
