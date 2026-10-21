import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:gte_frontend/data/public_pulse_api.dart';

import 'gtex_home_models.dart';
import 'gtex_home_shared_widgets.dart';

class GtexHomeNav extends StatelessWidget implements PreferredSizeWidget {
  const GtexHomeNav({
    super.key,
    this.onLogin,
    this.onSignup,
    this.pulse,
    this.jackpotLabel,
    this.onScrollToSection,
  });

  final VoidCallback? onLogin;
  final VoidCallback? onSignup;
  final GtexLiveWorldPulse? pulse;
  final String? jackpotLabel;
  final ValueChanged<String>? onScrollToSection;

  @override
  Size get preferredSize => const Size.fromHeight(64);

  @override
  Widget build(BuildContext context) {
    final double width = MediaQuery.sizeOf(context).width;
    final bool isWideDesktop = width >= 1260;
    final bool isDesktop = width >= 980;
    final bool isTablet = width >= 680;

    return Container(
      decoration: const BoxDecoration(
        color: Color(0xF20B1626), // 95% opacity GTEX Navy
        border: Border(
          bottom: BorderSide(color: kNavyLine, width: 1),
        ),
      ),
      child: SafeArea(
        bottom: false,
        child: Container(
          padding: EdgeInsets.symmetric(
            horizontal: isTablet ? 24 : 14,
            vertical: 10,
          ),
          child: Row(
            children: <Widget>[
              // GTEX Brand Mark
              InkWell(
                onTap: () => onScrollToSection?.call('hero'),
                borderRadius: BorderRadius.circular(6),
                child: Row(
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
                    if (isTablet) ...<Widget>[
                      const SizedBox(width: 8),
                      SvgPicture.asset(
                        'assets/branding/gtex_wordmark_22.svg',
                        width: 90,
                        height: 22,
                        semanticsLabel: 'GTEX 2027',
                      ),
                    ],
                  ],
                ),
              ),

              const SizedBox(width: 12),

              // Live Pulse Chip
              if (pulse != null && isTablet) ...<Widget>[
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: kPitchGreen.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(color: kPitchGreen.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      Container(
                        width: 6,
                        height: 6,
                        decoration: const BoxDecoration(
                          color: kPitchGreenBright,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        '${pulse!.usersOnlineLabel} live',
                        style: const TextStyle(
                          color: kTextPrimary,
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                ),
              ],

              const Spacer(),

              // Desktop Navigation Links
              if (isDesktop) ...<Widget>[
                _NavTextButton(
                  label: 'World',
                  onTap: () => onScrollToSection?.call('world'),
                ),
                _NavTextButton(
                  label: 'Clubs',
                  onTap: () => onScrollToSection?.call('ownership'),
                ),
                _NavTextButton(
                  label: 'TV Money',
                  onTap: () => onScrollToSection?.call('finance'),
                ),
                _NavTextButton(
                  label: 'Regens',
                  onTap: () => onScrollToSection?.call('regens'),
                ),
                _NavTextButton(
                  label: 'Tournaments',
                  onTap: () => onScrollToSection?.call('competitions'),
                ),
                if (isWideDesktop) ...<Widget>[
                  _NavTextButton(
                    label: 'Universe',
                    onTap: () => onScrollToSection?.call('universe'),
                  ),
                  _NavTextButton(
                    label: 'Trust',
                    onTap: () => onScrollToSection?.call('trust'),
                  ),
                ],
                const SizedBox(width: 8),
              ],

              // Sign in button
              TextButton(
                onPressed: onLogin,
                style: TextButton.styleFrom(
                  foregroundColor: kTextSecondary,
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  minimumSize: Size.zero,
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
                child: const Text(
                  'Sign in',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),

              const SizedBox(width: 8),

              // Enter GTEX / Found Club
              GtexGlowButton(
                label: isTablet ? 'Enter GTEX' : 'Enter',
                onPressed: onSignup,
                glowColor: kGoldPrimary,
                large: false,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _NavTextButton extends StatelessWidget {
  const _NavTextButton({
    required this.label,
    required this.onTap,
  });

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(6),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
          child: Text(
            label,
            style: const TextStyle(
              color: kTextSecondary,
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ),
    );
  }
}
