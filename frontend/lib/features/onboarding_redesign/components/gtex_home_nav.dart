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
              if (!isDesktop) ...<Widget>[
                const SizedBox(width: 2),
                IconButton(
                  tooltip: 'Open homepage navigation',
                  onPressed: () {
                    showModalBottomSheet<void>(
                      context: context,
                      useSafeArea: true,
                      isScrollControlled: true,
                      backgroundColor: kNavyBase,
                      shape: const RoundedRectangleBorder(
                        borderRadius: BorderRadius.vertical(
                          top: Radius.circular(22),
                        ),
                        side: BorderSide(color: kNavyLineStrong),
                      ),
                      builder: (BuildContext _) => _MobileNavigationSheet(
                        onNavigate: (String section) {
                          onScrollToSection?.call(section);
                        },
                      ),
                    );
                  },
                  icon: const Icon(
                    Icons.menu_rounded,
                    color: kTextPrimary,
                    size: 22,
                  ),
                ),
              ],
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


class _MobileNavigationSheet extends StatelessWidget {
  const _MobileNavigationSheet({required this.onNavigate});

  final ValueChanged<String> onNavigate;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 24),
        child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Text(
            'EXPLORE GTEX',
            style: TextStyle(
              color: kGoldPrimary,
              fontSize: 12,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.8,
              fontFamily: kFontCondensed,
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Your football world, one destination at a time.',
            style: TextStyle(
              color: kTextSecondary,
              fontSize: 13,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 14),
          const Divider(color: kNavyLine),
          _MobileNavItem(
            icon: Icons.public_rounded,
            title: 'The living world',
            subtitle: 'News, milestones and broadcasts',
            onTap: () => _go(context, 'world'),
          ),
          _MobileNavItem(
            icon: Icons.shield_rounded,
            title: 'Club ownership',
            subtitle: 'Build your club and prestige',
            onTap: () => _go(context, 'ownership'),
          ),
          _MobileNavItem(
            icon: Icons.tv_rounded,
            title: 'TV money & club finance',
            subtitle: 'Broadcast revenue and club economics',
            onTap: () => _go(context, 'finance'),
          ),
          _MobileNavItem(
            icon: Icons.person_search_rounded,
            title: 'Regens & player development',
            subtitle: 'Discover and develop future stars',
            onTap: () => _go(context, 'regens'),
          ),
          _MobileNavItem(
            icon: Icons.emoji_events_rounded,
            title: 'Competitions & jackpots',
            subtitle: 'Tournaments, rules and prize events',
            onTap: () => _go(context, 'competitions'),
          ),
          _MobileNavItem(
            icon: Icons.groups_rounded,
            title: 'The wider football universe',
            subtitle: 'Managers and national-team rentals',
            onTap: () => _go(context, 'universe'),
          ),
          _MobileNavItem(
            icon: Icons.verified_user_rounded,
            title: 'Trust & rules',
            subtitle: 'Currencies, eligibility and disclosures',
            onTap: () => _go(context, 'trust'),
          ),
        ],
      ),
      ),
    );
  }

  void _go(BuildContext context, String section) {
    Navigator.of(context).pop();
    onNavigate(section);
  }
}

class _MobileNavItem extends StatelessWidget {
  const _MobileNavItem({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
      leading: Container(
        width: 38,
        height: 38,
        decoration: BoxDecoration(
          color: kNavyOverlay,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: kNavyLine),
        ),
        child: Icon(icon, color: kGoldPrimary, size: 19),
      ),
      title: Text(
        title,
        style: const TextStyle(
          color: kTextPrimary,
          fontSize: 14,
          fontWeight: FontWeight.w700,
        ),
      ),
      subtitle: Text(
        subtitle,
        style: const TextStyle(color: kTextTertiary, fontSize: 11),
      ),
      trailing: const Icon(Icons.arrow_forward_ios_rounded, size: 14, color: kTextTertiary),
      onTap: onTap,
    );
  }
}
