import 'package:flutter/material.dart';

import 'gtex_home_shared_widgets.dart';

class GtexClubValuationSection extends StatelessWidget {
  const GtexClubValuationSection({super.key});

  @override
  Widget build(BuildContext context) {
    final double width = MediaQuery.sizeOf(context).width;
    final bool isNarrow = width < 760;

    return Container(
      color: kNavyInset,
      padding: EdgeInsets.symmetric(
        horizontal: isNarrow ? 20 : 64,
        vertical: 72,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          // Section Masthead
          const GtexSectionHeader(
            eyebrow: 'Commercial Football & Equity',
            title: 'Club Valuations, Eligible Sales & Sponsorships',
            subtitle: 'Operate your club as a professional football enterprise. The GTEX valuation engine calculates club enterprise value using a verified six-pillar asset breakdown. Owners can list equity, trade clubs, and unlock commercial sponsorships.',
            accentColor: kGoldPrimary,
          ),

          const SizedBox(height: 36),

          // The 6-Pillar Formula Visual Panel
          Container(
            decoration: BoxDecoration(
              color: kNavyRaised,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: kNavyLineStrong),
            ),
            padding: EdgeInsets.all(isNarrow ? 20 : 32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: const <Widget>[
                    GtexTagPill(
                      label: 'OFFICIAL SIX-PILLAR VALUATION AUDIT',
                      color: kGoldPrimary,
                      icon: Icons.account_balance_rounded,
                    ),
                    Spacer(),
                    Text(
                      'ALGORITHM VERSION 2.0',
                      style: TextStyle(
                        color: kTextTertiary,
                        fontSize: 10,
                        fontWeight: FontWeight.w800,
                        fontFamily: kFontCondensed,
                        letterSpacing: 1,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                const Text(
                  'TOTAL CLUB VALUATION = 1st TEAM + RESERVES + U19 + ACADEMY + STADIUM + ENHANCEMENTS',
                  style: TextStyle(
                    color: kGoldLight,
                    fontSize: 14,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 1,
                    fontFamily: kFontCondensed,
                  ),
                ),
                const SizedBox(height: 24),
                // 6 Pillar Grid
                LayoutBuilder(
                  builder: (BuildContext context, BoxConstraints constraints) {
                    final int cols = constraints.maxWidth > 900 ? 3 : (constraints.maxWidth > 600 ? 2 : 1);
                    final double colWidth = (constraints.maxWidth - ((cols - 1) * 16)) / cols;

                    return Wrap(
                      spacing: 16,
                      runSpacing: 16,
                      children: const <Widget>[
                        _ValuationPillarCard(
                          pillarNum: '01',
                          title: 'First-Team Squad',
                          description: 'Aggregated market reference value of all active registered senior contracts.',
                          icon: Icons.group_rounded,
                          accentColor: kSkyBlue,
                        ),
                        _ValuationPillarCard(
                          pillarNum: '02',
                          title: 'Reserve Squad',
                          description: 'Second-tier squad depth and loanable squad members under active contract.',
                          icon: Icons.layers_rounded,
                          accentColor: kPitchGreenBright,
                        ),
                        _ValuationPillarCard(
                          pillarNum: '03',
                          title: 'U19 Squad Assets',
                          description: 'Competitive youth players competing in regional and continental cups.',
                          icon: Icons.child_care_rounded,
                          accentColor: kGoldPrimary,
                        ),
                        _ValuationPillarCard(
                          pillarNum: '04',
                          title: 'Academy & Regens',
                          description: 'Unpromoted intake candidates evaluated on scouted potential ceiling.',
                          icon: Icons.auto_awesome_rounded,
                          accentColor: Color(0xFFA855F7),
                        ),
                        _ValuationPillarCard(
                          pillarNum: '05',
                          title: 'Stadium Infrastructure',
                          description: 'Tiered venue evaluation based on capacity, hospitality boxes, and lighting.',
                          icon: Icons.stadium_rounded,
                          accentColor: Color(0xFFF59E0B),
                        ),
                        _ValuationPillarCard(
                          pillarNum: '06',
                          title: 'Paid Enhancements',
                          description: 'Performance campuses, medical suites, analytics labs, and fleet assets.',
                          icon: Icons.upgrade_rounded,
                          accentColor: Color(0xFFEC4899),
                        ),
                      ].map((Widget w) => SizedBox(width: colWidth, child: w)).toList(),
                    );
                  },
                ),
              ],
            ),
          ),

          const SizedBox(height: 40),

          // Commercial Sponsorship & Sale Market Grid
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool wide = constraints.maxWidth > 720;
              return wide
                  ? Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: const <Widget>[
                        Expanded(child: _CommercialInventoryCard()),
                        SizedBox(width: 24),
                        Expanded(child: _OwnershipMarketCard()),
                      ],
                    )
                  : Column(
                      children: const <Widget>[
                        _CommercialInventoryCard(),
                        SizedBox(height: 20),
                        _OwnershipMarketCard(),
                      ],
                    );
            },
          ),
        ],
      ),
    );
  }
}

class _ValuationPillarCard extends StatelessWidget {
  const _ValuationPillarCard({
    required this.pillarNum,
    required this.title,
    required this.description,
    required this.icon,
    required this.accentColor,
  });

  final String pillarNum;
  final String title;
  final String description;
  final IconData icon;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: kNavyInset,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: kNavyLine),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(icon, size: 16, color: accentColor),
              const SizedBox(width: 8),
              Text(
                'PILLAR $pillarNum',
                style: TextStyle(
                  color: accentColor,
                  fontSize: 10,
                  fontWeight: FontWeight.w800,
                  fontFamily: kFontCondensed,
                  letterSpacing: 1.2,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            title,
            style: const TextStyle(
              color: kTextPrimary,
              fontSize: 15,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            description,
            style: const TextStyle(
              color: kTextSecondary,
              fontSize: 12,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }
}

class _CommercialInventoryCard extends StatelessWidget {
  const _CommercialInventoryCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: kNavyRaised,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: kNavyLine),
      ),
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const <Widget>[
          GtexTagPill(
            label: 'SPONSORSHIP INVENTORY',
            color: kPitchGreenBright,
            icon: Icons.campaign_rounded,
          ),
          SizedBox(height: 16),
          Text(
            'Multi-Zone Sponsorship & LED Advertising',
            style: TextStyle(
              color: kTextPrimary,
              fontSize: 18,
              fontWeight: FontWeight.w800,
              fontFamily: kFontCondensed,
            ),
          ),
          SizedBox(height: 10),
          Text(
            'Monetize club identity across primary shirt zones (chest, sleeves, back), stadium naming rights, and virtual pitch-side LED boards seen by live match spectators.',
            style: TextStyle(color: kTextSecondary, fontSize: 13, height: 1.5),
          ),
        ],
      ),
    );
  }
}

class _OwnershipMarketCard extends StatelessWidget {
  const _OwnershipMarketCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: kNavyRaised,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: kNavyLine),
      ),
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const <Widget>[
          GtexTagPill(
            label: 'CLUB SALE MARKETPLACE',
            color: kGoldPrimary,
            icon: Icons.storefront_rounded,
          ),
          SizedBox(height: 16),
          Text(
            'Eligible Club Sales & Equity Divestment',
            style: TextStyle(
              color: kTextPrimary,
              fontSize: 18,
              fontWeight: FontWeight.w800,
              fontFamily: kFontCondensed,
            ),
          ),
          SizedBox(height: 10),
          Text(
            'Owners who satisfy competitive seasoning rules can list clubs or equity stakes on the official platform marketplace, transferring verified assets and facilities seamlessly.',
            style: TextStyle(color: kTextSecondary, fontSize: 13, height: 1.5),
          ),
        ],
      ),
    );
  }
}
