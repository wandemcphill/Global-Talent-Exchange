import 'package:flutter/material.dart';

import 'gtex_home_shared_widgets.dart';

class GtexTrustAndIntegritySection extends StatelessWidget {
  const GtexTrustAndIntegritySection({super.key});

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
            eyebrow: 'Integrity, Compliance & Security',
            title: 'Institutional Trust & Competitive Integrity',
            subtitle: 'GTEX operates under strict regulatory, mathematical, and sporting integrity standards. All match outcomes, jackpot distributions, and financial settlements are governed by verifiable server-authoritative code.',
            accentColor: kPitchGreenBright,
          ),

          const SizedBox(height: 36),

          // 4 Trust Pillar Panels
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool wide = constraints.maxWidth > 850;
              final double cardWidth = wide ? (constraints.maxWidth - 24) / 2 : constraints.maxWidth;

              return Wrap(
                spacing: 24,
                runSpacing: 20,
                children: const <Widget>[
                  _TrustCard(
                    title: 'Authoritative Spatial Match Engine',
                    description: 'All 3D matches run on deterministic server simulation authority. Player physics, spatial coordinates, referee decisions, and scoreline results are cryptographically verified and cannot be manipulated on client devices.',
                    icon: Icons.security_rounded,
                    tag: 'DETERMINISTIC SIMULATION',
                    accentColor: kPitchGreenBright,
                  ),
                  _TrustCard(
                    title: 'Surveillance & Anti-Collusion Engine',
                    description: 'Automated risk-ops algorithms monitor transfer marketplace activity, match results, and coin trading orders. Unusual pricing spikes or suspicious multi-account collusion trigger immediate review freezes.',
                    icon: Icons.shield_rounded,
                    tag: 'REAL-TIME SURVEILLANCE',
                    accentColor: kSkyBlue,
                  ),
                  _TrustCard(
                    title: 'KYC Tier 2 & AML Regulatory Verification',
                    description: 'Real-money deposits and withdrawals require mandatory government-issued ID identity verification, address proof, and automated sanctions screening before funds can be released.',
                    icon: Icons.verified_user_rounded,
                    tag: 'KYC COMPLIANCE',
                    accentColor: kGoldPrimary,
                  ),
                  _TrustCard(
                    title: 'Transparent Economic Disclosures',
                    description: 'GTEX strictly distinguishes virtual sporting value from withdrawable cash. Television revenues and tournament prizes are awarded based on actual platform results and active rules; earnings are never guaranteed.',
                    icon: Icons.gavel_rounded,
                    tag: 'LEGAL ACCURACY',
                    accentColor: Color(0xFFA855F7),
                  ),
                ].map((Widget card) => SizedBox(width: cardWidth, child: card)).toList(),
              );
            },
          ),
        ],
      ),
    );
  }
}

class _TrustCard extends StatelessWidget {
  const _TrustCard({
    required this.title,
    required this.description,
    required this.icon,
    required this.tag,
    required this.accentColor,
  });

  final String title;
  final String description;
  final IconData icon;
  final String tag;
  final Color accentColor;

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
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(icon, size: 20, color: accentColor),
              const SizedBox(width: 8),
              GtexTagPill(label: tag, color: accentColor),
            ],
          ),
          const SizedBox(height: 14),
          Text(
            title,
            style: const TextStyle(
              color: kTextPrimary,
              fontSize: 18,
              fontWeight: FontWeight.w800,
              fontFamily: kFontCondensed,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            description,
            style: const TextStyle(
              color: kTextSecondary,
              fontSize: 13,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }
}
