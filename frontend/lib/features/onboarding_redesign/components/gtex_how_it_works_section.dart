import 'package:flutter/material.dart';

import 'gtex_home_shared_widgets.dart';

class GtexHowItWorksSection extends StatelessWidget {
  const GtexHowItWorksSection({super.key});

  @override
  Widget build(BuildContext context) {
    final double width = MediaQuery.sizeOf(context).width;
    final bool isNarrow = width < 760;

    return Container(
      color: kNavyBase,
      padding: EdgeInsets.symmetric(
        horizontal: isNarrow ? 20 : 64,
        vertical: 72,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          // Section Masthead
          const GtexSectionHeader(
            eyebrow: 'Platform Architecture & Mechanics',
            title: 'How GTEX Works: Currencies, Ledgers & Withdrawals',
            subtitle: 'GTEX maintains complete institutional clarity between in-game sporting assets, executive owner capital, and real-money financial transactions.',
            accentColor: kSkyBlue,
          ),

          const SizedBox(height: 36),

          // Ledger Architecture Comparison (Sporting vs Executive vs Real-Money)
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool wide = constraints.maxWidth > 850;
              final double colWidth = wide ? (constraints.maxWidth - 32) / 3 : constraints.maxWidth;

              return wide
                  ? Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        SizedBox(width: colWidth, child: const _LedgerCard(
                          title: 'Sporting Operations',
                          subtitle: 'GTC & FNC Ledgers',
                          description: 'Powering on-pitch sporting operations. GTC credits fund player contracts, youth scouting, and transfer fees. FNC coins power matchday fan engagement.',
                          badge: 'SPORTING LEDGER',
                          badgeColor: kSkyBlue,
                          points: <String>[
                            'GTC Credits for player market trading',
                            'FNC Fan Coins for matchday votes',
                            'In-game simulation assets',
                          ],
                        )),
                        const SizedBox(width: 16),
                        SizedBox(width: colWidth, child: const _LedgerCard(
                          title: 'Boardroom Capital',
                          subtitle: 'GTX & FAN Tokens',
                          description: 'Powers executive owner decisions. GTX funds facility upgrades, Apex Performance Campus construction, Sovereign 900X aviation, and showroom luxury purchases.',
                          badge: 'EXECUTIVE LEDGER',
                          badgeColor: kGoldPrimary,
                          points: <String>[
                            'GTX for luxury asset acquisitions',
                            'Prestige point bonuses on purchase',
                            'Sister-club capital transfers',
                          ],
                        )),
                        const SizedBox(width: 16),
                        SizedBox(width: colWidth, child: const _LedgerCard(
                          title: 'Real-Money Transactions',
                          subtitle: 'Deposits & Withdrawals',
                          description: 'Regulated fiat gateways and withdrawable balances. Gated by strict KYC Tier 2 verification, 48-hour risk-ops review, and anti-collusion fraud prevention.',
                          badge: 'COMPLIANCE GATE',
                          badgeColor: kPitchGreenBright,
                          points: <String>[
                            'Mandatory KYC Tier 2 identity checks',
                            '48-hour risk-ops settlement buffer',
                            'Clear virtual vs cash boundaries',
                          ],
                        )),
                      ],
                    )
                  : Column(
                      children: const <Widget>[
                        _LedgerCard(
                          title: 'Sporting Operations',
                          subtitle: 'GTC & FNC Ledgers',
                          description: 'Powering on-pitch sporting operations. GTC credits fund player contracts, youth scouting, and transfer fees. FNC coins power matchday fan engagement.',
                          badge: 'SPORTING LEDGER',
                          badgeColor: kSkyBlue,
                          points: <String>[
                            'GTC Credits for player market trading',
                            'FNC Fan Coins for matchday votes',
                            'In-game simulation assets',
                          ],
                        ),
                        SizedBox(height: 16),
                        _LedgerCard(
                          title: 'Boardroom Capital',
                          subtitle: 'GTX & FAN Tokens',
                          description: 'Powers executive owner decisions. GTX funds facility upgrades, Apex Performance Campus construction, Sovereign 900X aviation, and showroom luxury purchases.',
                          badge: 'EXECUTIVE LEDGER',
                          badgeColor: kGoldPrimary,
                          points: <String>[
                            'GTX for luxury asset acquisitions',
                            'Prestige point bonuses on purchase',
                            'Sister-club capital transfers',
                          ],
                        ),
                        SizedBox(height: 16),
                        _LedgerCard(
                          title: 'Real-Money Transactions',
                          subtitle: 'Deposits & Withdrawals',
                          description: 'Regulated fiat gateways and withdrawable balances. Gated by strict KYC Tier 2 verification, 48-hour risk-ops review, and anti-collusion fraud prevention.',
                          badge: 'COMPLIANCE GATE',
                          badgeColor: kPitchGreenBright,
                          points: <String>[
                            'Mandatory KYC Tier 2 identity checks',
                            '48-hour risk-ops settlement buffer',
                            'Clear virtual vs cash boundaries',
                          ],
                        ),
                      ],
                    );
            },
          ),
        ],
      ),
    );
  }
}

class _LedgerCard extends StatelessWidget {
  const _LedgerCard({
    required this.title,
    required this.subtitle,
    required this.description,
    required this.badge,
    required this.badgeColor,
    required this.points,
  });

  final String title;
  final String subtitle;
  final String description;
  final String badge;
  final Color badgeColor;
  final List<String> points;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: kNavyRaised,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: kNavyLine),
      ),
      padding: const EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          GtexTagPill(label: badge, color: badgeColor),
          const SizedBox(height: 14),
          Text(
            title,
            style: const TextStyle(
              color: kTextPrimary,
              fontSize: 20,
              fontWeight: FontWeight.w800,
              fontFamily: kFontCondensed,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            subtitle,
            style: TextStyle(
              color: badgeColor,
              fontSize: 12,
              fontWeight: FontWeight.w700,
              fontFamily: kFontMono,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            description,
            style: const TextStyle(
              color: kTextSecondary,
              fontSize: 13,
              height: 1.45,
            ),
          ),
          const SizedBox(height: 18),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: kNavyInset,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: kNavyLine),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: points
                  .map((String point) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 3),
                        child: Row(
                          children: <Widget>[
                            Icon(Icons.check_rounded, size: 13, color: badgeColor),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                point,
                                style: const TextStyle(
                                  color: kTextPrimary,
                                  fontSize: 11,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ))
                  .toList(),
            ),
          ),
        ],
      ),
    );
  }
}
