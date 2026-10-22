import 'package:flutter/material.dart';
import 'package:gte_frontend/data/public_pulse_api.dart';

import 'gtex_home_shared_widgets.dart';

class GtexHeroSection extends StatelessWidget {
  const GtexHeroSection({
    super.key,
    this.onSignup,
    this.onExplore,
    this.pulse,
  });

  final VoidCallback? onSignup;
  final VoidCallback? onExplore;
  final GtexLiveWorldPulse? pulse;

  @override
  Widget build(BuildContext context) {
    final double width = MediaQuery.sizeOf(context).width;
    final bool isNarrow = width < 760;

    return Container(
      constraints: BoxConstraints(minHeight: isNarrow ? 460 : 640),
      color: kNavyBase,
      child: Stack(
        alignment: Alignment.centerLeft,
        children: <Widget>[
          // Cinematic Stadium Background Poster
          Positioned.fill(
            child: Image.asset(
              'assets/media/gtex_landing_single_poster.png',
              fit: BoxFit.cover,
              alignment: Alignment.centerRight,
              errorBuilder: (_, __, ___) => const SizedBox.shrink(),
            ),
          ),

          // Deep Navy Editorial Gradient Overlay
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.centerLeft,
                  end: Alignment.centerRight,
                  colors: <Color>[
                    kNavyBase,
                    kNavyBase.withValues(alpha: 0.94),
                    kNavyBase.withValues(alpha: 0.70),
                    kNavyBase.withValues(alpha: 0.35),
                  ],
                ),
              ),
            ),
          ),

          // Main Hero Editorial Content
          Padding(
            padding: EdgeInsets.fromLTRB(
              isNarrow ? 20 : 80,
              isNarrow ? 20 : 52,
              20,
              isNarrow ? 20 : 52,
            ),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 780),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  // Eyebrow with living green signal
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      Container(
                        width: 7,
                        height: 7,
                        decoration: const BoxDecoration(
                          color: kPitchGreenBright,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 8),
                      const Flexible(
                        child: Text(
                          'THE LIVING FOOTBALL UNIVERSE • 2027',
                          style: TextStyle(
                            color: kPitchGreenBright,
                            fontSize: 11,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 1.8,
                            fontFamily: kFontCondensed,
                          ),
                        ),
                      ),
                    ],
                  ),

                  SizedBox(height: isNarrow ? 10 : 18),

                  // Primary Editorial Headline (Preserving exact tested string)
                  Text(
                    'FOOTBALL,\nREBUILT.',
                    style: TextStyle(
                      color: kTextPrimary,
                      fontSize: isNarrow ? 40 : 84,
                      height: 0.88,
                      fontWeight: FontWeight.w900,
                      letterSpacing: -1.8,
                      fontFamily: kFontCondensed,
                    ),
                  ),

                  SizedBox(height: isNarrow ? 10 : 16),

                  // Narrative Tagline & Mission
                  Text(
                    'Build your club. Discover the next superstar. Compete for glory. Build your legacy.',
                    style: TextStyle(
                      color: kGoldLight,
                      fontSize: isNarrow ? 14 : 18,
                      fontWeight: FontWeight.w700,
                      height: 1.25,
                    ),
                  ),

                  const SizedBox(height: 6),

                  Text(
                    'Own up to three clubs, hire managers, develop regens, earn TV money, trade talent and compete for prizes in one living football world.',
                    style: TextStyle(
                      color: kTextSecondary,
                      fontSize: isNarrow ? 12 : 15,
                      height: 1.4,
                    ),
                  ),

                  SizedBox(height: isNarrow ? 14 : 24),

                  // Conversion Calls to Action (Contains exact 'Create free account')
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: <Widget>[
                      GtexGlowButton(
                        label: 'Create free account',
                        onPressed: onSignup,
                        large: !isNarrow,
                        glowColor: kGoldPrimary,
                        icon: Icons.stadium_rounded,
                      ),
                      GtexGhostButton(
                        label: 'Explore the universe',
                        onPressed: onExplore,
                        large: !isNarrow,
                        icon: Icons.public_rounded,
                      ),
                    ],
                  ),

                  SizedBox(height: isNarrow ? 12 : 20),

                  // Micro Badges
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: const <Widget>[
                      _HeroBadge(icon: Icons.shield_rounded, text: 'Own'),
                      _HeroBadge(icon: Icons.auto_awesome_rounded, text: 'Develop'),
                      _HeroBadge(icon: Icons.swap_horiz_rounded, text: 'Trade'),
                      _HeroBadge(icon: Icons.emoji_events_rounded, text: 'Compete'),
                    ],
                  ),
                ],
              ),
            ),
          ),

          // Live Signal Indicator (bottom right on wider screens)
          if (!isNarrow && pulse != null)
            Positioned(
              right: 32,
              bottom: 32,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                decoration: BoxDecoration(
                  color: kNavyRaised.withValues(alpha: 0.9),
                  borderRadius: BorderRadius.circular(30),
                  border: Border.all(color: kPitchGreen.withValues(alpha: 0.4)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    Container(
                      width: 8,
                      height: 8,
                      decoration: const BoxDecoration(
                        color: kPitchGreenBright,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 8),
                    const Text(
                      'WORLD PULSE • ${pulse!.clubsLabel} CLUBS',
                      style: TextStyle(
                        color: kTextPrimary,
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 1.5,
                        fontFamily: kFontCondensed,
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class GtexClarityStrip extends StatelessWidget {
  const GtexClarityStrip({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: const BoxDecoration(
        color: kNavyRaised,
        border: Border(
          top: BorderSide(color: kNavyLine, width: 1),
          bottom: BorderSide(color: kNavyLine, width: 1),
        ),
      ),
      child: Center(
        child: Wrap(
          alignment: WrapAlignment.center,
          spacing: 24,
          runSpacing: 10,
          children: const <Widget>[
            _Signal('PLAYERS', 'Discover & develop'),
            _Signal('CLUBS', 'Build & manage'),
            _Signal('MARKET', 'Trade & invest'),
            _Signal('MATCHDAY', 'Compete & win'),
            _Signal('COMMUNITY', 'Create & connect'),
          ],
        ),
      ),
    );
  }
}

class _Signal extends StatelessWidget {
  const _Signal(this.title, this.body);

  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      crossAxisAlignment: WrapCrossAlignment.center,
      spacing: 6,
      children: <Widget>[
        Text(
          title,
          style: const TextStyle(
            color: kGoldPrimary,
            fontSize: 11,
            fontWeight: FontWeight.w800,
            letterSpacing: 1.2,
            fontFamily: kFontCondensed,
          ),
        ),
        Text(
          body,
          style: const TextStyle(
            color: kTextSecondary,
            fontSize: 13,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }
}

class _HeroBadge extends StatelessWidget {
  const _HeroBadge({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: kNavyRaised.withValues(alpha: 0.8),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: kNavyLine),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(icon, size: 13, color: kGoldPrimary),
          const SizedBox(width: 5),
          Text(
            text,
            style: const TextStyle(
              color: kTextPrimary,
              fontSize: 11,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
