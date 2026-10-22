import 'package:flutter/material.dart';

import 'gtex_home_shared_widgets.dart';

class GtexTvAndFinanceSection extends StatefulWidget {
  const GtexTvAndFinanceSection({super.key});

  @override
  State<GtexTvAndFinanceSection> createState() => _GtexTvAndFinanceSectionState();
}

class _GtexTvAndFinanceSectionState extends State<GtexTvAndFinanceSection> {
  // 0: Foundation, 1: Growing, 2: Established, 3: Elite, 4: Legacy
  int _selectedTierIndex = 2; // Default to Established

  static const List<_TierFinancialBreakdown> _tiers = <_TierFinancialBreakdown>[
    _TierFinancialBreakdown(
      tierName: 'Foundation Tier',
      developmentScore: '< 20 Pts',
      tvRatePercentage: 30,
      annualRevenueEstimate: '180,000 GTC',
      tvRevenue: 54000,
      sponsorshipRevenue: 45000,
      matchdayRevenue: 36000,
      playerTradingRevenue: 45000,
      hostCutPercentage: 40,
      summary: 'At foundation level, 30% television shares provide initial operating capital to maintain wages and conduct academy trials.',
    ),
    _TierFinancialBreakdown(
      tierName: 'Growing Contender',
      developmentScore: '20–39 Pts',
      tvRatePercentage: 40,
      annualRevenueEstimate: '520,000 GTC',
      tvRevenue: 208000,
      sponsorshipRevenue: 130000,
      matchdayRevenue: 78000,
      playerTradingRevenue: 104000,
      hostCutPercentage: 40,
      summary: 'With 40% TV share and regional sponsors, contenders reinvest broadcast income into hybrid training pitches and sports science.',
    ),
    _TierFinancialBreakdown(
      tierName: 'Established Club',
      developmentScore: '40–59 Pts',
      tvRatePercentage: 50,
      annualRevenueEstimate: '1,650,000 GTC',
      tvRevenue: 825000,
      sponsorshipRevenue: 412500,
      matchdayRevenue: 165000,
      playerTradingRevenue: 247500,
      hostCutPercentage: 40,
      summary: 'At 50% TV share, broadcast cashflows match commercial partnerships, financing top-tier manager appointments and stadium maintenance.',
    ),
    _TierFinancialBreakdown(
      tierName: 'Elite Contender',
      developmentScore: '60–79 Pts',
      tvRatePercentage: 60,
      annualRevenueEstimate: '5,400,000 GTC',
      tvRevenue: 3240000,
      sponsorshipRevenue: 1080000,
      matchdayRevenue: 432000,
      playerTradingRevenue: 648000,
      hostCutPercentage: 40,
      summary: 'Elite clubs capture 60% TV distribution across continental cups, funding Apex Campus upgrades and Vanguard XII team coaches.',
    ),
    _TierFinancialBreakdown(
      tierName: 'Legacy Institution',
      developmentScore: '80+ Pts',
      tvRatePercentage: 70,
      annualRevenueEstimate: '18,500,000 GTC',
      tvRevenue: 12950000,
      sponsorshipRevenue: 2775000,
      matchdayRevenue: 1110000,
      playerTradingRevenue: 1665000,
      hostCutPercentage: 40,
      summary: 'Legacy giants retain 70% of broadcast distributions. Broadcast revenue powers global scouting satellites and Sovereign 900X aviation.',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final double width = MediaQuery.sizeOf(context).width;
    final bool isNarrow = width < 760;
    final _TierFinancialBreakdown activeTier = _tiers[_selectedTierIndex];

    return Container(
      color: kNavyInset,
      padding: EdgeInsets.symmetric(
        horizontal: isNarrow ? 20 : 64,
        vertical: 64,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          // Section Masthead
          const GtexSectionHeader(
            eyebrow: 'The Business of Owning a Club',
            title: 'Television Revenue & Club Financial Engine',
            subtitle: 'Broadcast rights are not an afterthought — they are the economic core of GTEX club ownership. Clubs capture progressively higher television distribution percentages as their development stage expands, funding facilities, squad payroll, and global ambition.',
            accentColor: kPitchGreenBright,
          ),

          const SizedBox(height: 32),

          // The Verified Rules Callout Box
          Container(
            decoration: BoxDecoration(
              color: kNavyRaised,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: kPitchGreen.withValues(alpha: 0.35)),
            ),
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: const <Widget>[
                    Icon(Icons.rule_folder_rounded, size: 18, color: kPitchGreenBright),
                    SizedBox(width: 8),
                    Flexible(
                      child: Text(
                        'VERIFIED GTEX TELEVISION DISTRIBUTION FORMULA',
                        style: TextStyle(
                          color: kPitchGreenBright,
                          fontSize: 12,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 1.2,
                          fontFamily: kFontCondensed,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                const Text(
                  'GTEX broadcast revenue is governed by authoritative platform contracts. Foundation clubs retain 30% of television income, scaling to 40% (Growing), 50% (Established), 60% (Elite), and 70% (Legacy). In tournament fixtures, the host club receives 40% of the clubs\' pool, and participants share the remaining 60%, with the platform retaining the balance.',
                  style: TextStyle(
                    color: kTextPrimary,
                    fontSize: 13,
                    height: 1.45,
                  ),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 10,
                  runSpacing: 6,
                  children: const <Widget>[
                    GtexTagPill(label: 'Foundation: 30% TV Cut', color: Color(0xFF6B7A93)),
                    GtexTagPill(label: 'Growing: 40% TV Cut', color: Color(0xFF3B82F6)),
                    GtexTagPill(label: 'Established: 50% TV Cut', color: Color(0xFF10B981)),
                    GtexTagPill(label: 'Elite: 60% TV Cut', color: Color(0xFF8B5CF6)),
                    GtexTagPill(label: 'Legacy: 70% TV Cut', color: Color(0xFFD4AF37)),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: 36),

          // Interactive Financial Breakdown Simulator Header
          Wrap(
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: 10,
            runSpacing: 6,
            children: <Widget>[
              Wrap(
                crossAxisAlignment: WrapCrossAlignment.center,
                spacing: 8,
                children: const <Widget>[
                  Icon(Icons.query_stats_rounded, color: kGoldPrimary, size: 20),
                  Text(
                    'INTERACTIVE CLUB REVENUE BREAKDOWN',
                    style: TextStyle(
                      color: kGoldPrimary,
                      fontSize: 14,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.5,
                      fontFamily: kFontCondensed,
                    ),
                  ),
                ],
              ),
              const Text(
                'SELECT TIER TO SIMULATE',
                style: TextStyle(
                  color: kTextTertiary,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1,
                  fontFamily: kFontCondensed,
                ),
              ),
            ],
          ),

          const SizedBox(height: 14),

          // Tier Tabs
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: List<Widget>.generate(_tiers.length, (int index) {
                final _TierFinancialBreakdown item = _tiers[index];
                final bool isSelected = index == _selectedTierIndex;
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: FilterChip(
                    label: Text('${item.tierName} (${item.tvRatePercentage}%)'),
                    selected: isSelected,
                    onSelected: (_) => setState(() => _selectedTierIndex = index),
                    selectedColor: kPitchGreen.withValues(alpha: 0.2),
                    backgroundColor: kNavyRaised,
                    labelStyle: TextStyle(
                      color: isSelected ? kPitchGreenBright : kTextSecondary,
                      fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
                      fontSize: 12,
                    ),
                    side: BorderSide(
                      color: isSelected ? kPitchGreenBright : kNavyLine,
                    ),
                  ),
                );
              }),
            ),
          ),

          const SizedBox(height: 20),

          // Financial Visualization Card
          Container(
            decoration: BoxDecoration(
              color: kNavyRaised,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: kNavyLineStrong),
            ),
            padding: EdgeInsets.all(isNarrow ? 18 : 28),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Wrap(
                  alignment: WrapAlignment.spaceBetween,
                  crossAxisAlignment: WrapCrossAlignment.start,
                  spacing: 14,
                  runSpacing: 10,
                  children: <Widget>[
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          activeTier.tierName.toUpperCase(),
                          style: const TextStyle(
                            color: kTextPrimary,
                            fontSize: 20,
                            fontWeight: FontWeight.w900,
                            fontFamily: kFontCondensed,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'Development Score: ${activeTier.developmentScore}',
                          style: const TextStyle(
                            color: kTextTertiary,
                            fontSize: 12,
                            fontFamily: kFontMono,
                          ),
                        ),
                      ],
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: <Widget>[
                        const Text(
                          'INDICATIVE ANNUAL TURNOVER',
                          style: TextStyle(
                            color: kTextTertiary,
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 1,
                            fontFamily: kFontCondensed,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          activeTier.annualRevenueEstimate,
                          style: const TextStyle(
                            color: kGoldLight,
                            fontSize: 18,
                            fontWeight: FontWeight.w900,
                            fontFamily: kFontMono,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),

                const SizedBox(height: 16),
                Text(
                  activeTier.summary,
                  style: const TextStyle(
                    color: kTextSecondary,
                    fontSize: 13,
                    height: 1.45,
                  ),
                ),
                const SizedBox(height: 24),

                // 4 Revenue Stream Progress Bars
                _RevenueBar(
                  streamName: 'Television & Match Broadcasts (${activeTier.tvRatePercentage}%)',
                  amountLabel: '${activeTier.tvRevenue} GTC',
                  percentage: (activeTier.tvRevenue / _totalRevenue(activeTier)),
                  barColor: kPitchGreenBright,
                  icon: Icons.tv_rounded,
                ),
                const SizedBox(height: 14),

                _RevenueBar(
                  streamName: 'Commercial Sponsorships & LED Pitch-Side',
                  amountLabel: '${activeTier.sponsorshipRevenue} GTC',
                  percentage: (activeTier.sponsorshipRevenue / _totalRevenue(activeTier)),
                  barColor: kGoldPrimary,
                  icon: Icons.handshake_rounded,
                ),
                const SizedBox(height: 14),

                _RevenueBar(
                  streamName: 'Player Trading & Regen Value Gains',
                  amountLabel: '${activeTier.playerTradingRevenue} GTC',
                  percentage: (activeTier.playerTradingRevenue / _totalRevenue(activeTier)),
                  barColor: kSkyBlue,
                  icon: Icons.trending_up_rounded,
                ),
                const SizedBox(height: 14),

                _RevenueBar(
                  streamName: 'Matchday Gate Receipts & Penthouse Hospitality',
                  amountLabel: '${activeTier.matchdayRevenue} GTC',
                  percentage: (activeTier.matchdayRevenue / _totalRevenue(activeTier)),
                  barColor: const Color(0xFFA855F7),
                  icon: Icons.confirmation_number_rounded,
                ),

                const SizedBox(height: 24),
                const Divider(color: kNavyLine),
                const SizedBox(height: 12),

                // Truth & Accuracy Note
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: const <Widget>[
                    Icon(Icons.info_outline_rounded, size: 15, color: kTextTertiary),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Illustrative economic model based on active GTEX Phase 5 TV rules and verified game ledger formulas. Club revenue is determined by actual match attendance, tournament progression, and player transfer market liquidity; never guaranteed returns.',
                        style: TextStyle(
                          color: kTextTertiary,
                          fontSize: 11,
                          height: 1.35,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  static double _totalRevenue(_TierFinancialBreakdown item) {
    return (item.tvRevenue + item.sponsorshipRevenue + item.playerTradingRevenue + item.matchdayRevenue).toDouble();
  }
}

class _TierFinancialBreakdown {
  const _TierFinancialBreakdown({
    required this.tierName,
    required this.developmentScore,
    required this.tvRatePercentage,
    required this.annualRevenueEstimate,
    required this.tvRevenue,
    required this.sponsorshipRevenue,
    required this.matchdayRevenue,
    required this.playerTradingRevenue,
    required this.hostCutPercentage,
    required this.summary,
  });

  final String tierName;
  final String developmentScore;
  final int tvRatePercentage;
  final String annualRevenueEstimate;
  final int tvRevenue;
  final int sponsorshipRevenue;
  final int matchdayRevenue;
  final int playerTradingRevenue;
  final int hostCutPercentage;
  final String summary;
}

class _RevenueBar extends StatelessWidget {
  const _RevenueBar({
    required this.streamName,
    required this.amountLabel,
    required this.percentage,
    required this.barColor,
    required this.icon,
  });

  final String streamName;
  final String amountLabel;
  final double percentage;
  final Color barColor;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final int displayPct = (percentage * 100).round();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Icon(icon, size: 14, color: barColor),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                streamName,
                style: const TextStyle(
                  color: kTextPrimary,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(width: 6),
            Text(
              amountLabel,
              style: TextStyle(
                color: barColor,
                fontSize: 12,
                fontWeight: FontWeight.w800,
                fontFamily: kFontMono,
              ),
            ),
            const SizedBox(width: 6),
            Text(
              '($displayPct%)',
              style: const TextStyle(
                color: kTextTertiary,
                fontSize: 11,
                fontFamily: kFontMono,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: percentage.clamp(0.0, 1.0),
            minHeight: 6,
            backgroundColor: kNavyInset,
            valueColor: AlwaysStoppedAnimation<Color>(barColor),
          ),
        ),
      ],
    );
  }
}
