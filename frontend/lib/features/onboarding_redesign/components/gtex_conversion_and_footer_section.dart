import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import 'gtex_home_shared_widgets.dart';

class GtexConversionAndFooterSection extends StatelessWidget {
  const GtexConversionAndFooterSection({
    super.key,
    this.onSignup,
    this.onTraderSignup,
    this.onCreatorSignup,
    this.onExploreMarket,
  });

  final VoidCallback? onSignup;
  final VoidCallback? onTraderSignup;
  final VoidCallback? onCreatorSignup;
  final VoidCallback? onExploreMarket;

  @override
  Widget build(BuildContext context) {
    final double width = MediaQuery.sizeOf(context).width;
    final bool isNarrow = width < 760;

    return Container(
      color: kNavyBase,
      child: Column(
        children: <Widget>[
          // Final Conversion Banner
          Padding(
            padding: EdgeInsets.symmetric(
              horizontal: isNarrow ? 18 : 64,
              vertical: 56,
            ),
            child: Container(
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: <Color>[
                    Color(0xFF13233A),
                    Color(0xFF0F1E33),
                    Color(0xFF0B1626),
                  ],
                ),
                borderRadius: BorderRadius.circular(24),
                border: Border.all(color: kGoldPrimary.withValues(alpha: 0.4), width: 1.5),
                boxShadow: <BoxShadow>[
                  BoxShadow(
                    color: kGoldPrimary.withValues(alpha: 0.08),
                    blurRadius: 32,
                    offset: const Offset(0, 8),
                  ),
                ],
              ),
              padding: EdgeInsets.all(isNarrow ? 20 : 44),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: <Widget>[
                  const GtexTagPill(
                    label: 'YOUR LEGACY BEGINS NOW',
                    color: kGoldPrimary,
                    icon: Icons.stars_rounded,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Step Onto the Pitch in 2027.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: kTextPrimary,
                      fontSize: isNarrow ? 30 : 46,
                      fontWeight: FontWeight.w900,
                      letterSpacing: -1,
                      fontFamily: kFontCondensed,
                    ),
                  ),
                  const SizedBox(height: 10),
                  ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 640),
                    child: const Text(
                      'Whether you aspire to build an institutional football dynasty, scout the next generation of regens, or compete for the four scheduled daily jackpots — GTEX is your stage.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: kTextSecondary,
                        fontSize: 14,
                        height: 1.5,
                      ),
                    ),
                  ),
                  const SizedBox(height: 32),

                  // 3 Audience Pathways
                  Wrap(
                    spacing: 14,
                    runSpacing: 14,
                    alignment: WrapAlignment.center,
                    children: <Widget>[
                      _ConversionPathCard(
                        roleTitle: 'CLUB OWNER',
                        headline: 'Found a Football Club',
                        body: 'Own up to 3 clubs, build Arena facilities, capture TV money, and unlock VIP jets.',
                        buttonLabel: 'Found Your Club',
                        onPressed: onSignup,
                        accentColor: kGoldPrimary,
                        icon: Icons.stadium_rounded,
                      ),
                      _ConversionPathCard(
                        roleTitle: 'TALENT SCOUT & TRADER',
                        headline: 'Enter the Player Exchange',
                        body: 'Scout 17,000+ players, recruit breakout regens, and negotiate high-value transfers.',
                        buttonLabel: 'Start Scouting',
                        onPressed: onTraderSignup ?? onSignup,
                        accentColor: kSkyBlue,
                        icon: Icons.person_search_rounded,
                      ),
                      _ConversionPathCard(
                        roleTitle: 'CREATOR & FAN',
                        headline: 'Join Fan Tribes & Tournaments',
                        body: 'Wage matchday Fan Wars, back your clubs, and compete for 4 daily jackpot drops.',
                        buttonLabel: 'Join the Universe',
                        onPressed: onCreatorSignup ?? onSignup,
                        accentColor: kPitchGreenBright,
                        icon: Icons.sports_soccer_rounded,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),

          const Divider(color: kNavyLine, height: 1),

          // Footer
          Padding(
            padding: EdgeInsets.symmetric(
              horizontal: isNarrow ? 20 : 64,
              vertical: 36,
            ),
            child: Column(
              children: <Widget>[
                Wrap(
                  alignment: WrapAlignment.spaceBetween,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  spacing: 16,
                  runSpacing: 12,
                  children: <Widget>[
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: <Widget>[
                            const Text(
                              'GTEX',
                              style: TextStyle(
                                color: kTextPrimary,
                                fontSize: 20,
                                fontWeight: FontWeight.w900,
                                letterSpacing: 2,
                                fontFamily: kFontCondensed,
                              ),
                            ),
                            const SizedBox(width: 8),
                            SvgPicture.asset(
                              'assets/branding/gtex_wordmark_22.svg',
                              width: 100,
                              height: 24,
                              semanticsLabel: 'GTEX',
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          'The Living Football Universe • 2027 Edition',
                          style: TextStyle(
                            color: kTextTertiary,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                    Wrap(
                      spacing: 8,
                      runSpacing: 4,
                      children: const <Widget>[
                        _FooterLink(label: 'Competitions'),
                        _FooterLink(label: 'Showroom'),
                        _FooterLink(label: 'Rentals'),
                        _FooterLink(label: 'Managers'),
                        _FooterLink(label: 'Trust & Rules'),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                const Divider(color: kNavyLine, height: 1),
                const SizedBox(height: 16),
                Row(
                  children: const <Widget>[
                    Expanded(
                      child: Text(
                        '© 2027 Global Talent Exchange (GTEX). All rights reserved. Age 18+ required for real-money transactions. In-game earnings reflect platform simulation rules and are not guaranteed returns.',
                        style: TextStyle(
                          color: kTextTertiary,
                          fontSize: 11,
                          height: 1.4,
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
}

class _ConversionPathCard extends StatelessWidget {
  const _ConversionPathCard({
    required this.roleTitle,
    required this.headline,
    required this.body,
    required this.buttonLabel,
    required this.onPressed,
    required this.accentColor,
    required this.icon,
  });

  final String roleTitle;
  final String headline;
  final String body;
  final String buttonLabel;
  final VoidCallback? onPressed;
  final Color accentColor;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(maxWidth: 270, minWidth: 200),
      decoration: BoxDecoration(
        color: kNavyRaised,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: kNavyLine),
      ),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Wrap(
            spacing: 6,
            runSpacing: 4,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: <Widget>[
              Icon(icon, size: 15, color: accentColor),
              Text(
                roleTitle,
                style: TextStyle(
                  color: accentColor,
                  fontSize: 10,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1.2,
                  fontFamily: kFontCondensed,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            headline,
            style: const TextStyle(
              color: kTextPrimary,
              fontSize: 17,
              fontWeight: FontWeight.w800,
              fontFamily: kFontCondensed,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            body,
            style: const TextStyle(
              color: kTextSecondary,
              fontSize: 12,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 18),
          SizedBox(
            width: double.infinity,
            child: GtexGhostButton(
              label: buttonLabel,
              onPressed: onPressed,
              borderColor: accentColor.withValues(alpha: 0.5),
              textColor: accentColor,
            ),
          ),
        ],
      ),
    );
  }
}

class _FooterLink extends StatelessWidget {
  const _FooterLink({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      child: Text(
        label,
        style: const TextStyle(
          color: kTextTertiary,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
