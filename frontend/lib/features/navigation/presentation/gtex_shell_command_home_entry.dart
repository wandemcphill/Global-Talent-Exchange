import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/components/gtex_button.dart';
import 'package:gte_frontend/ui_gtex/components/gtex_metric_tile.dart';
import 'package:gte_frontend/ui_gtex/components/gtex_panel.dart';
import 'package:gte_frontend/ui_gtex/theme/gtex_colors.dart';
import 'package:gte_frontend/ui_gtex/theme/gtex_spacing.dart';

/// Extracted command-home onboarding entry shown in the Club lane when the
/// user has not yet created or bound a club (Phase B1 shell decomposition).
class GtexCommandHomeEntry extends StatelessWidget {
  const GtexCommandHomeEntry({
    super.key,
    required this.isAuthenticated,
    required this.userLabel,
    required this.onSignIn,
    required this.onCreateClub,
    required this.onOpenMarket,
    required this.onOpenCompetitions,
    required this.onOpenWorld,
  });

  final bool isAuthenticated;
  final String userLabel;
  final VoidCallback onSignIn;
  final VoidCallback onCreateClub;
  final VoidCallback onOpenMarket;
  final VoidCallback onOpenCompetitions;
  final VoidCallback onOpenWorld;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool compact = constraints.maxWidth < 760;
        final double metricWidth = compact ? constraints.maxWidth : 210;
        return SingleChildScrollView(
          padding: EdgeInsets.fromLTRB(
            compact ? GtexSpacing.md : GtexSpacing.xl,
            GtexSpacing.lg,
            compact ? GtexSpacing.md : GtexSpacing.xl,
            120,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Container(
                width: double.infinity,
                padding: EdgeInsets.all(compact ? GtexSpacing.lg : 30),
                decoration: BoxDecoration(
                  gradient: GtexColors.panelGlow(accent: GtexColors.pitch),
                  borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
                  border: Border.all(
                    color: GtexColors.pitch.withValues(alpha: 0.34),
                  ),
                  boxShadow: <BoxShadow>[
                    GtexColors.glow(GtexColors.pitch, opacity: 0.14),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'THE GLOBAL FOOTBALL TALENT MARKETPLACE',
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: GtexColors.pitch,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0.8,
                      ),
                    ),
                    const SizedBox(height: GtexSpacing.sm),
                    Text(
                      isAuthenticated
                          ? 'Build your club command center'
                          : 'Enter the football operating system',
                      maxLines: compact ? 3 : 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.displaySmall?.copyWith(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: GtexSpacing.sm),
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 860),
                      child: Text(
                        isAuthenticated
                            ? '$userLabel, create your club to unlock squad ownership, transfer trading, finances, competitions, news, and regen world activity from one GTEX command surface.'
                            : 'Create and own clubs, discover real players, browse the transfer universe, rent national-team talent, follow tournaments, and watch the GTEX news world move around the market.',
                        style: Theme.of(
                          context,
                        ).textTheme.titleMedium?.copyWith(
                          color: GtexColors.textSecondary,
                          height: 1.42,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    const SizedBox(height: GtexSpacing.lg),
                    Wrap(
                      spacing: GtexSpacing.sm,
                      runSpacing: GtexSpacing.sm,
                      children: <Widget>[
                        if (!isAuthenticated)
                          GtexButton(
                            label: 'Sign in',
                            icon: Icons.login,
                            onPressed: onSignIn,
                          ),
                        GtexButton(
                          label:
                              isAuthenticated
                                  ? 'Create club'
                                  : 'Create or join club',
                          icon: Icons.shield_outlined,
                          variant:
                              isAuthenticated
                                  ? GtexButtonVariant.primary
                                  : GtexButtonVariant.secondary,
                          onPressed: onCreateClub,
                        ),
                        GtexButton(
                          label: 'Transfer Hub',
                          icon: Icons.storefront_outlined,
                          variant: GtexButtonVariant.secondary,
                          onPressed: onOpenMarket,
                        ),
                        GtexButton(
                          label: 'Matchday',
                          icon: Icons.emoji_events_outlined,
                          variant: GtexButtonVariant.ghost,
                          onPressed: onOpenCompetitions,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: GtexSpacing.lg),
              Wrap(
                spacing: GtexSpacing.md,
                runSpacing: GtexSpacing.md,
                children: <Widget>[
                  SizedBox(
                    width: metricWidth,
                    child: const GtexMetricTile(
                      label: 'Player universe',
                      value: '17K+',
                      helper: 'Tradeable real players',
                      icon: Icons.groups_2_outlined,
                      accent: GtexColors.pitch,
                    ),
                  ),
                  SizedBox(
                    width: metricWidth,
                    child: const GtexMetricTile(
                      label: 'Transfer route',
                      value: 'Live',
                      helper: 'Country to club browsing',
                      icon: Icons.account_tree_outlined,
                      accent: GtexColors.cyan,
                    ),
                  ),
                  SizedBox(
                    width: metricWidth,
                    child: const GtexMetricTile(
                      label: 'Club layer',
                      value: 'Owner',
                      helper: 'Squad, wallet, orders',
                      icon: Icons.shield_outlined,
                      accent: GtexColors.gold,
                    ),
                  ),
                  SizedBox(
                    width: metricWidth,
                    child: const GtexMetricTile(
                      label: 'World state',
                      value: 'Active',
                      helper: 'Regens, news, awards',
                      icon: Icons.public_outlined,
                      accent: GtexColors.mint,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: GtexSpacing.lg),
              Wrap(
                spacing: GtexSpacing.md,
                runSpacing: GtexSpacing.md,
                children: <Widget>[
                  GtexHomeLanePanel(
                    width: compact ? constraints.maxWidth : 360,
                    title: 'Transfer room',
                    subtitle:
                        'Browse country, league, division, club, then shortlist real football assets.',
                    icon: Icons.compare_arrows_outlined,
                    accent: GtexColors.pitch,
                    onTap: onOpenMarket,
                  ),
                  GtexHomeLanePanel(
                    width: compact ? constraints.maxWidth : 360,
                    title: 'Club ownership',
                    subtitle:
                        'Create a badge, build a squad, manage finances, and enter competitions.',
                    icon: Icons.stadium_outlined,
                    accent: GtexColors.gold,
                    onTap: onCreateClub,
                  ),
                  GtexHomeLanePanel(
                    width: compact ? constraints.maxWidth : 360,
                    title: 'GTEX world',
                    subtitle:
                        'Follow regens, creator activity, football news, awards, and community signals.',
                    icon: Icons.auto_awesome_outlined,
                    accent: GtexColors.mint,
                    onTap: onOpenWorld,
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }
}

class GtexHomeLanePanel extends StatelessWidget {
  const GtexHomeLanePanel({
    super.key,
    required this.width,
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.accent,
    required this.onTap,
  });

  final double width;
  final String title;
  final String subtitle;
  final IconData icon;
  final Color accent;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: width,
      child: GtexPanel(
        title: title,
        subtitle: subtitle,
        accent: accent,
        onTap: onTap,
        trailing: Icon(icon, color: accent),
        child: Row(
          children: <Widget>[
            Text(
              'Open lane',
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: accent,
                fontWeight: FontWeight.w900,
              ),
            ),
            const Spacer(),
            Icon(Icons.arrow_forward, color: accent, size: 18),
          ],
        ),
      ),
    );
  }
}
