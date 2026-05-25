import 'package:flutter/material.dart';

import '../../ui_gtex/components/gtex_button.dart';
import '../../ui_gtex/theme/gtex_colors.dart';
import '../../ui_gtex/theme/gtex_spacing.dart';

class GtexPublicLandingScreenV2 extends StatelessWidget {
  const GtexPublicLandingScreenV2({
    super.key,
    this.onSignup,
    this.onLogin,
    this.onCreatorSignup,
    this.onExploreMarket,
  });

  static const String _posterAsset =
      'assets/media/gtex_landing_single_poster.png';

  final VoidCallback? onSignup;
  final VoidCallback? onLogin;
  final VoidCallback? onCreatorSignup;
  final VoidCallback? onExploreMarket;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: GtexColors.surfaceBase,
      body: Stack(
        children: <Widget>[
          const _LandingBackdrop(),
          _FootballOsLanding(
            posterAsset: _posterAsset,
            onSignup: onSignup,
            onCreatorSignup: onCreatorSignup,
            onExploreMarket: onExploreMarket,
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(
                GtexSpacing.lg,
                GtexSpacing.md,
                GtexSpacing.lg,
                0,
              ),
              child: _TopBar(onLogin: onLogin),
            ),
          ),
          Align(
            alignment: Alignment.bottomCenter,
            child: _LandingActionDock(
              onSignup: onSignup,
              onCreatorSignup: onCreatorSignup,
              onExploreMarket: onExploreMarket,
            ),
          ),
        ],
      ),
    );
  }
}

class _TopBar extends StatelessWidget {
  const _TopBar({this.onLogin});

  final VoidCallback? onLogin;

  @override
  Widget build(BuildContext context) {
    final bool compact = MediaQuery.sizeOf(context).width < 420;
    return Row(
      children: <Widget>[
        ClipRRect(
          borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
          child: Image.asset(
            'assets/branding/gtex_icon.png',
            width: 36,
            height: 36,
            fit: BoxFit.cover,
          ),
        ),
        const SizedBox(width: GtexSpacing.sm),
        Expanded(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Text(
                'GTEX',
                style: TextStyle(
                  color: GtexColors.textPrimary,
                  fontSize: 16,
                  fontWeight: FontWeight.w900,
                  height: 1,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                compact
                    ? 'Football economy OS'
                    : 'Live football economy operating system',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: GtexColors.textSecondary,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  height: 1,
                ),
              ),
            ],
          ),
        ),
        TextButton(
          onPressed: onLogin,
          child: const Text(
            'Login',
            style: TextStyle(
              color: GtexColors.textPrimary,
              fontWeight: FontWeight.w800,
            ),
          ),
        ),
      ],
    );
  }
}

class _FootballOsLanding extends StatelessWidget {
  const _FootballOsLanding({
    required this.posterAsset,
    this.onSignup,
    this.onCreatorSignup,
    this.onExploreMarket,
  });

  final String posterAsset;
  final VoidCallback? onSignup;
  final VoidCallback? onCreatorSignup;
  final VoidCallback? onExploreMarket;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool compact = constraints.maxWidth < GtexBreakpoints.mobile;
        final EdgeInsets padding = EdgeInsets.fromLTRB(
          compact ? GtexSpacing.md : GtexSpacing.xxl,
          compact ? 82 : 104,
          compact ? GtexSpacing.md : GtexSpacing.xxl,
          compact ? 150 : 132,
        );

        return SafeArea(
          child: Padding(
            padding: padding,
            child: Align(
              alignment: compact ? Alignment.topCenter : Alignment.center,
              child:
                  compact
                      ? ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 1180),
                        child: _CompactLandingStack(
                          posterAsset: posterAsset,
                          onSignup: onSignup,
                          onCreatorSignup: onCreatorSignup,
                          onExploreMarket: onExploreMarket,
                        ),
                      )
                      : SingleChildScrollView(
                        physics: const ClampingScrollPhysics(),
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 1180),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: <Widget>[
                              Row(
                                crossAxisAlignment: CrossAxisAlignment.center,
                                children: <Widget>[
                                  Expanded(
                                    flex: 11,
                                    child: _LandingCommandColumn(
                                      onExploreMarket: onExploreMarket,
                                    ),
                                  ),
                                  const SizedBox(width: GtexSpacing.xxl),
                                  Expanded(
                                    flex: 9,
                                    child: _LandingOperationsBoard(
                                      posterAsset: posterAsset,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: GtexSpacing.xxl),
                              _LandingExplainerStrip(
                                onExploreMarket: onExploreMarket,
                              ),
                              const SizedBox(height: GtexSpacing.lg),
                              const _LandingLiveActivitySection(),
                              const SizedBox(height: GtexSpacing.lg),
                              _LandingRoleEntrySection(
                                onSignup: onSignup,
                                onCreatorSignup: onCreatorSignup,
                                onExploreMarket: onExploreMarket,
                              ),
                              const SizedBox(height: GtexSpacing.lg),
                              const _LandingEconomyOverview(),
                              const SizedBox(height: GtexSpacing.xl),
                              const _LandingFooter(),
                              const SizedBox(height: GtexSpacing.xxl),
                            ],
                          ),
                        ),
                      ),
            ),
          ),
        );
      },
    );
  }
}

class _CompactLandingStack extends StatelessWidget {
  const _CompactLandingStack({
    required this.posterAsset,
    this.onSignup,
    this.onCreatorSignup,
    this.onExploreMarket,
  });

  final String posterAsset;
  final VoidCallback? onSignup;
  final VoidCallback? onCreatorSignup;
  final VoidCallback? onExploreMarket;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      physics: const ClampingScrollPhysics(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          _LandingCommandColumn(onExploreMarket: onExploreMarket),
          const SizedBox(height: GtexSpacing.lg),
          _LandingOperationsBoard(posterAsset: posterAsset),
          const SizedBox(height: GtexSpacing.lg),
          _LandingExplainerStrip(onExploreMarket: onExploreMarket),
          const SizedBox(height: GtexSpacing.lg),
          const _LandingLiveActivitySection(),
          const SizedBox(height: GtexSpacing.lg),
          _LandingRoleEntrySection(
            onSignup: onSignup,
            onCreatorSignup: onCreatorSignup,
            onExploreMarket: onExploreMarket,
          ),
          const SizedBox(height: GtexSpacing.lg),
          const _LandingEconomyOverview(),
          const SizedBox(height: GtexSpacing.xl),
          const _LandingFooter(),
        ],
      ),
    );
  }
}

class _LandingSectionTitle extends StatelessWidget {
  const _LandingSectionTitle({required this.title, required this.subtitle});

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          title,
          style: theme.textTheme.headlineSmall?.copyWith(
            color: GtexColors.textPrimary,
            fontFamily: 'Barlow Condensed',
            fontWeight: FontWeight.w900,
            letterSpacing: 0,
          ),
        ),
        const SizedBox(height: GtexSpacing.xs),
        ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 760),
          child: Text(
            subtitle,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: GtexColors.textSecondary,
              height: 1.45,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ],
    );
  }
}

class _LandingExplainerStrip extends StatelessWidget {
  const _LandingExplainerStrip({this.onExploreMarket});

  final VoidCallback? onExploreMarket;

  @override
  Widget build(BuildContext context) {
    final bool compact = MediaQuery.sizeOf(context).width < 760;
    final List<Widget> tiles = <Widget>[
      const _LandingInfoTile(
        icon: Icons.trending_up_rounded,
        title: 'Real Money Moves',
        body:
            'GTEX Coin powers transfers, rentals, bids, and settlement. Fan Coin carries club backing, gifts, and football activity.',
        color: GtexColors.accentAmber,
      ),
      const _LandingInfoTile(
        icon: Icons.shield_rounded,
        title: 'Run Your Club',
        body:
            'Open a club, manage the squad budget, sign players, enter competitions, and track ranking movement.',
        color: GtexColors.accentPrimary,
      ),
      const _LandingInfoTile(
        icon: Icons.person_search_rounded,
        title: 'Real Players. Regen DNA.',
        body:
            'Search the live player pool, follow market signals, and build with regens that carry traits, lineage, and awards.',
        color: GtexColors.textPrimary,
      ),
      const _LandingInfoTile(
        icon: Icons.emoji_events_rounded,
        title: 'Compete for Real',
        body:
            'Enter cups, hosted competitions, national rental tournaments, and 2D matches backed by live services.',
        color: GtexColors.accentBlue,
      ),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const _LandingSectionTitle(
          title: 'What GTEX Runs',
          subtitle:
              'A football operating system where clubs, players, coins, matches, and news all connect to live backend authority.',
        ),
        const SizedBox(height: GtexSpacing.md),
        compact
            ? SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: tiles
                    .map(
                      (Widget tile) => Padding(
                        padding: const EdgeInsets.only(right: GtexSpacing.sm),
                        child: SizedBox(width: 260, child: tile),
                      ),
                    )
                    .toList(growable: false),
              ),
            )
            : Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: tiles
                  .map(
                    (Widget tile) => Expanded(
                      child: Padding(
                        padding: const EdgeInsets.only(right: GtexSpacing.sm),
                        child: tile,
                      ),
                    ),
                  )
                  .toList(growable: false),
            ),
      ],
    );
  }
}

class _LandingInfoTile extends StatelessWidget {
  const _LandingInfoTile({
    required this.icon,
    required this.title,
    required this.body,
    required this.color,
  });

  final IconData icon;
  final String title;
  final String body;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minHeight: 188),
      padding: const EdgeInsets.all(GtexSpacing.md),
      decoration: BoxDecoration(
        color: GtexColors.surfaceRaised.withValues(alpha: 0.88),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
        border: Border.all(color: color.withValues(alpha: 0.26)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(icon, color: color, size: 28),
          const SizedBox(height: GtexSpacing.md),
          Text(
            title,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: GtexColors.textPrimary,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: GtexSpacing.xs),
          Text(
            body,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: GtexColors.textSecondary,
              height: 1.45,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _LandingLiveActivitySection extends StatelessWidget {
  const _LandingLiveActivitySection();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(GtexSpacing.md),
      decoration: BoxDecoration(
        color: GtexColors.surfaceOverlay.withValues(alpha: 0.88),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
        border: Border.all(color: GtexColors.surfaceBorderStrong),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const _LandingSectionTitle(
            title: 'Right Now on GTEX',
            subtitle:
                'Transfers, match starts, trades, gifts, and club operations appear here when the public activity feed is mounted.',
          ),
          const SizedBox(height: GtexSpacing.md),
          Container(
            padding: const EdgeInsets.all(GtexSpacing.md),
            decoration: BoxDecoration(
              color: GtexColors.surfaceBase.withValues(alpha: 0.62),
              borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
              border: Border.all(color: GtexColors.surfaceBorder),
            ),
            child: Row(
              children: <Widget>[
                const Icon(
                  Icons.radio_button_checked,
                  color: GtexColors.statusBlocked,
                ),
                const SizedBox(width: GtexSpacing.sm),
                Expanded(
                  child: Text(
                    'No public activity returned for this session. Sign in to operate live transfers, matches, rentals, gifts, and trading.',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: GtexColors.textSecondary,
                      height: 1.4,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _LandingRoleEntrySection extends StatelessWidget {
  const _LandingRoleEntrySection({
    this.onSignup,
    this.onCreatorSignup,
    this.onExploreMarket,
  });

  final VoidCallback? onSignup;
  final VoidCallback? onCreatorSignup;
  final VoidCallback? onExploreMarket;

  @override
  Widget build(BuildContext context) {
    final bool compact = MediaQuery.sizeOf(context).width < 880;
    final List<Widget> cards = <Widget>[
      _LandingRoleCard(
        title: 'Fan / Registered User',
        headline: 'Back a club. Track players. Spend Fan Coins.',
        body:
            'Follow transfers, save players, gift football moments, and read the newsroom with an account.',
        cta: 'Join Free',
        color: GtexColors.accentBlue,
        onPressed: onSignup,
      ),
      _LandingRoleCard(
        title: 'Club Owner',
        headline: 'Open a club. Build a squad. Enter the league.',
        body:
            'Manage budgets, sign players, set matchday readiness, and rent national team players.',
        cta: 'Open a Club',
        color: GtexColors.accentPrimary,
        onPressed: onSignup,
      ),
      _LandingRoleCard(
        title: 'Coin Trader',
        headline: 'Make markets for GTEX Coin and Fan Coin.',
        body:
            'List buy and sell offers, keep liquidity online, build reputation, and serve active users.',
        cta: 'Trade Coins',
        color: GtexColors.accentAmber,
        onPressed: onExploreMarket,
      ),
      _LandingRoleCard(
        title: 'Creator',
        headline: 'Cover the game. Publish news. Build an audience.',
        body:
            'Write transfer stories, react to live football activity, and earn from engagement.',
        cta: 'Apply as Creator',
        color: GtexColors.accentViolet,
        onPressed: onCreatorSignup,
      ),
      const _LandingRoleCard(
        title: 'Admin',
        headline: 'Platform operations stay gated.',
        body:
            'Payments, traders, competitions, settlement, and readiness require backend-issued admin authority.',
        cta: 'Admin gated',
        color: GtexColors.statusBlocked,
      ),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const _LandingSectionTitle(
          title: 'Find Your Role',
          subtitle:
              'GTEX changes shape depending on whether you are browsing, operating a club, trading coins, publishing football, or running platform ops.',
        ),
        const SizedBox(height: GtexSpacing.md),
        compact
            ? SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: cards
                    .map(
                      (Widget card) => Padding(
                        padding: const EdgeInsets.only(right: GtexSpacing.sm),
                        child: SizedBox(width: 282, child: card),
                      ),
                    )
                    .toList(growable: false),
              ),
            )
            : Wrap(
              spacing: GtexSpacing.sm,
              runSpacing: GtexSpacing.sm,
              children: cards
                  .map((Widget card) => SizedBox(width: 372, child: card))
                  .toList(growable: false),
            ),
      ],
    );
  }
}

class _LandingRoleCard extends StatelessWidget {
  const _LandingRoleCard({
    required this.title,
    required this.headline,
    required this.body,
    required this.cta,
    required this.color,
    this.onPressed,
  });

  final String title;
  final String headline;
  final String body;
  final String cta;
  final Color color;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minHeight: 226),
      padding: const EdgeInsets.all(GtexSpacing.md),
      decoration: BoxDecoration(
        color: GtexColors.surfaceRaised.withValues(alpha: 0.92),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
        border: Border.all(color: color.withValues(alpha: 0.32)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            title.toUpperCase(),
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: color,
              fontWeight: FontWeight.w900,
              letterSpacing: 0.8,
            ),
          ),
          const SizedBox(height: GtexSpacing.sm),
          Text(
            headline,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: GtexColors.textPrimary,
              fontWeight: FontWeight.w900,
              height: 1.15,
            ),
          ),
          const SizedBox(height: GtexSpacing.sm),
          Text(
            body,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: GtexColors.textSecondary,
              height: 1.45,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: GtexSpacing.sm),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              onPressed: onPressed,
              icon: const Icon(Icons.arrow_forward_rounded, size: 16),
              label: Text(cta),
            ),
          ),
        ],
      ),
    );
  }
}

class _LandingEconomyOverview extends StatelessWidget {
  const _LandingEconomyOverview();

  @override
  Widget build(BuildContext context) {
    final bool compact = MediaQuery.sizeOf(context).width < 760;
    final List<Widget> cards = <Widget>[
      const _EconomyCard(
        icon: Icons.toll_rounded,
        label: 'GTEX Coin (GTC)',
        body:
            'The operating coin for deposits, transfers, player purchases, national rentals, and treasury-backed settlement.',
        detail: 'Payment rails: KoraPay and manual payment only.',
        color: GtexColors.accentAmber,
      ),
      const _EconomyCard(
        icon: Icons.stars_rounded,
        label: 'Fan Coin (FNC)',
        body:
            'The fan economy unit for club rewards, gifts, reactions, engagement, and role-gated trading surfaces.',
        detail: 'Access and balances come from live backend wallet authority.',
        color: GtexColors.accentBlue,
      ),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const _LandingSectionTitle(
          title: 'The GTEX Economy',
          subtitle:
              'Two coin identities, one live football market. Numbers stay blank or blocked until backend authority returns them.',
        ),
        const SizedBox(height: GtexSpacing.md),
        compact
            ? Column(
              children: cards
                  .map(
                    (Widget card) => Padding(
                      padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
                      child: card,
                    ),
                  )
                  .toList(growable: false),
            )
            : Row(
              children: cards
                  .map(
                    (Widget card) => Expanded(
                      child: Padding(
                        padding: const EdgeInsets.only(right: GtexSpacing.sm),
                        child: card,
                      ),
                    ),
                  )
                  .toList(growable: false),
            ),
      ],
    );
  }
}

class _EconomyCard extends StatelessWidget {
  const _EconomyCard({
    required this.icon,
    required this.label,
    required this.body,
    required this.detail,
    required this.color,
  });

  final IconData icon;
  final String label;
  final String body;
  final String detail;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minHeight: 196),
      padding: const EdgeInsets.all(GtexSpacing.md),
      decoration: BoxDecoration(
        color: GtexColors.surfaceOverlay.withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
        border: Border.all(color: color.withValues(alpha: 0.32)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(icon, color: color, size: 32),
          const SizedBox(height: GtexSpacing.sm),
          Text(
            label,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
              color: GtexColors.textPrimary,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: GtexSpacing.sm),
          Text(
            body,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: GtexColors.textSecondary,
              height: 1.42,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: GtexSpacing.md),
          Text(
            detail,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: color,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

class _LandingFooter extends StatelessWidget {
  const _LandingFooter();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(GtexSpacing.md),
      decoration: BoxDecoration(
        color: GtexColors.surfaceRaised.withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
        border: Border.all(color: GtexColors.surfaceBorder),
      ),
      child: Wrap(
        spacing: GtexSpacing.lg,
        runSpacing: GtexSpacing.sm,
        alignment: WrapAlignment.spaceBetween,
        children: <Widget>[
          Text(
            'GTEX operates clubs, transfers, coin markets, competitions, regens, and football media from live services.',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: GtexColors.textSecondary,
              fontWeight: FontWeight.w700,
            ),
          ),
          Text(
            'KoraPay + Manual Payment. Paystack unavailable.',
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: GtexColors.accentAmber,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

class _LandingCommandColumn extends StatelessWidget {
  const _LandingCommandColumn({this.onExploreMarket});

  final VoidCallback? onExploreMarket;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final bool compact = MediaQuery.sizeOf(context).width < 420;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        const _LandingStatusStrip(),
        const SizedBox(height: GtexSpacing.lg),
        Text(
          'FOOTBALL HAS\nAN ECONOMY NOW.',
          style: theme.textTheme.displaySmall?.copyWith(
            color: GtexColors.textPrimary,
            fontFamily: 'Barlow Condensed',
            fontSize: compact ? 42 : 56,
            height: 0.95,
            fontWeight: FontWeight.w900,
            letterSpacing: 0,
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 620),
          child: Text(
            'GTEX runs real clubs, live player markets, coin trading, national rentals, regens, gifts, newsroom reactions, and 2D competitions inside one football operating system.',
            style: theme.textTheme.titleMedium?.copyWith(
              color: GtexColors.textSecondary,
              height: 1.45,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        const SizedBox(height: GtexSpacing.lg),
        Wrap(
          spacing: GtexSpacing.sm,
          runSpacing: GtexSpacing.sm,
          children: const <Widget>[
            _LandingCapabilityChip(
              label: 'STRICT LIVE',
              color: GtexColors.accentPrimary,
            ),
            _LandingCapabilityChip(
              label: 'COMPETITION OS',
              color: GtexColors.accentBlue,
            ),
            _LandingCapabilityChip(
              label: 'TREASURY CONTROL',
              color: GtexColors.accentAmber,
            ),
            _LandingCapabilityChip(
              label: 'REGEN UNIVERSE',
              color: GtexColors.accentViolet,
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.xl),
        _LandingMarketMatrix(onExploreMarket: onExploreMarket),
      ],
    );
  }
}

class _LandingStatusStrip extends StatelessWidget {
  const _LandingStatusStrip();

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: GtexSpacing.xs,
      runSpacing: GtexSpacing.xs,
      children: const <Widget>[
        _LandingStatusPill(
          label: 'LIVE RUNTIME ONLY',
          icon: Icons.radio_button_checked,
          color: GtexColors.statusLive,
        ),
        _LandingStatusPill(
          label: 'PAYSTACK BLOCKED',
          icon: Icons.block_rounded,
          color: GtexColors.statusBlocked,
        ),
        _LandingStatusPill(
          label: 'KORAPAY SERVER ENV',
          icon: Icons.verified_user_outlined,
          color: GtexColors.accentAmber,
        ),
      ],
    );
  }
}

class _LandingStatusPill extends StatelessWidget {
  const _LandingStatusPill({
    required this.label,
    required this.icon,
    required this.color,
  });

  final String label;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: GtexSpacing.sm,
        vertical: GtexSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: GtexColors.surfaceRaised.withValues(alpha: 0.82),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusSm),
        border: Border.all(color: color.withValues(alpha: 0.36)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(icon, size: 13, color: color),
          const SizedBox(width: GtexSpacing.xs),
          Text(
            label,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: GtexColors.textSecondary,
              fontWeight: FontWeight.w800,
              letterSpacing: 0.7,
            ),
          ),
        ],
      ),
    );
  }
}

class _LandingCapabilityChip extends StatelessWidget {
  const _LandingCapabilityChip({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.13),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusSm),
        border: Border.all(color: color.withValues(alpha: 0.34)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
          color: color,
          fontWeight: FontWeight.w900,
          letterSpacing: 0.8,
        ),
      ),
    );
  }
}

class _LandingMarketMatrix extends StatelessWidget {
  const _LandingMarketMatrix({this.onExploreMarket});

  final VoidCallback? onExploreMarket;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Container(
      constraints: const BoxConstraints(maxWidth: 650),
      decoration: BoxDecoration(
        color: GtexColors.surfaceRaised.withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
        border: Border.all(color: GtexColors.surfaceBorder),
        boxShadow: <BoxShadow>[GtexColors.glow(Colors.black, opacity: 0.32)],
      ),
      child: Column(
        children: <Widget>[
          Padding(
            padding: const EdgeInsets.all(GtexSpacing.md),
            child: Row(
              children: <Widget>[
                const _LiveDot(),
                const SizedBox(width: GtexSpacing.xs),
                Expanded(
                  child: Text(
                    'LIVE FOOTBALL ECONOMY LANES',
                    style: theme.textTheme.labelLarge?.copyWith(
                      color: GtexColors.textPrimary,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0.8,
                    ),
                  ),
                ),
                TextButton(
                  onPressed: onExploreMarket,
                  child: const Text('Operate market'),
                ),
              ],
            ),
          ),
          const Divider(height: 1, color: GtexColors.surfaceBorder),
          const _LandingMatrixRow(
            label: 'Transfers',
            value: 'Order books, offers, squad registration',
            color: GtexColors.accentBlue,
          ),
          const _LandingMatrixRow(
            label: 'Competitions',
            value: 'Hosted fixtures, prizes, standings, settlement',
            color: GtexColors.accentPrimary,
          ),
          const _LandingMatrixRow(
            label: 'National Rental',
            value: 'Eligibility, pools, cooldowns, authority validation',
            color: GtexColors.accentAmber,
          ),
          const _LandingMatrixRow(
            label: 'Regens',
            value: 'Lineage, cards, universe progression',
            color: GtexColors.accentViolet,
          ),
        ],
      ),
    );
  }
}

class _LandingMatrixRow extends StatelessWidget {
  const _LandingMatrixRow({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        GtexSpacing.md,
        GtexSpacing.sm,
        GtexSpacing.md,
        GtexSpacing.sm,
      ),
      child: Row(
        children: <Widget>[
          Container(width: 4, height: 30, color: color),
          const SizedBox(width: GtexSpacing.sm),
          SizedBox(
            width: 112,
            child: Text(
              label.toUpperCase(),
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                color: color,
                fontWeight: FontWeight.w900,
                letterSpacing: 0.7,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: GtexColors.textSecondary,
                height: 1.35,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _LandingOperationsBoard extends StatelessWidget {
  const _LandingOperationsBoard({required this.posterAsset});

  final String posterAsset;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(maxWidth: 500),
      padding: const EdgeInsets.all(GtexSpacing.md),
      decoration: BoxDecoration(
        color: GtexColors.surfaceOverlay.withValues(alpha: 0.92),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
        border: Border.all(color: GtexColors.surfaceBorderStrong),
        boxShadow: <BoxShadow>[GtexColors.glow(Colors.black, opacity: 0.42)],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          _BoardHeader(posterAsset: posterAsset),
          const SizedBox(height: GtexSpacing.md),
          const _RouteMapPreview(),
          const SizedBox(height: GtexSpacing.md),
          const Row(
            children: <Widget>[
              Expanded(
                child: _BoardSignalTile(
                  label: 'CLUB',
                  value: 'Authority',
                  color: GtexColors.accentPrimary,
                ),
              ),
              SizedBox(width: GtexSpacing.sm),
              Expanded(
                child: _BoardSignalTile(
                  label: 'MARKET',
                  value: 'Live',
                  color: GtexColors.accentBlue,
                ),
              ),
            ],
          ),
          const SizedBox(height: GtexSpacing.sm),
          const Row(
            children: <Widget>[
              Expanded(
                child: _BoardSignalTile(
                  label: 'TREASURY',
                  value: 'Audited',
                  color: GtexColors.accentAmber,
                ),
              ),
              SizedBox(width: GtexSpacing.sm),
              Expanded(
                child: _BoardSignalTile(
                  label: 'REGEN',
                  value: 'Lineage',
                  color: GtexColors.accentViolet,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _BoardHeader extends StatelessWidget {
  const _BoardHeader({required this.posterAsset});

  final String posterAsset;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        ClipRRect(
          borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
          child: Image.asset(
            posterAsset,
            width: 72,
            height: 96,
            fit: BoxFit.cover,
            alignment: Alignment.topCenter,
            filterQuality: FilterQuality.medium,
          ),
        ),
        const SizedBox(width: GtexSpacing.md),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'COMMAND VIEW',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: GtexColors.accentPrimary,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 0.9,
                ),
              ),
              const SizedBox(height: GtexSpacing.xs),
              Text(
                'Clubs, markets, matches, and settlement stay bound to live backend authority.',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: GtexColors.textSecondary,
                  height: 1.35,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _RouteMapPreview extends StatelessWidget {
  const _RouteMapPreview();

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 1.9,
      child: CustomPaint(
        painter: _RouteMapPainter(),
        child: const Align(
          alignment: Alignment.bottomLeft,
          child: Padding(
            padding: EdgeInsets.all(GtexSpacing.sm),
            child: Text(
              'TRANSFER ROUTE OVERLAY',
              style: TextStyle(
                color: GtexColors.textSecondary,
                fontSize: 11,
                fontWeight: FontWeight.w900,
                letterSpacing: 0.8,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _RouteMapPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final Paint borderPaint =
        Paint()
          ..color = GtexColors.surfaceBorder
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1;
    final Paint gridPaint =
        Paint()
          ..color = GtexColors.surfaceBorder.withValues(alpha: 0.58)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1;
    final Paint routePaint =
        Paint()
          ..color = GtexColors.accentPrimary
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.2;
    final Paint nodePaint = Paint()..color = GtexColors.accentPrimary;

    final RRect pitch = RRect.fromRectAndRadius(
      Offset.zero & size,
      const Radius.circular(GtexSpacing.radiusMd),
    );
    canvas.drawRRect(pitch, Paint()..color = GtexColors.surfaceBase);
    canvas.drawRRect(pitch, borderPaint);
    canvas.drawLine(
      Offset(size.width * 0.5, 0),
      Offset(size.width * 0.5, size.height),
      gridPaint,
    );
    canvas.drawCircle(
      Offset(size.width * 0.5, size.height * 0.5),
      size.height * 0.18,
      gridPaint,
    );

    final Path route =
        Path()
          ..moveTo(size.width * 0.12, size.height * 0.72)
          ..cubicTo(
            size.width * 0.32,
            size.height * 0.28,
            size.width * 0.62,
            size.height * 0.82,
            size.width * 0.86,
            size.height * 0.34,
          );
    canvas.drawPath(route, routePaint);

    for (final Offset point in <Offset>[
      Offset(size.width * 0.12, size.height * 0.72),
      Offset(size.width * 0.46, size.height * 0.48),
      Offset(size.width * 0.86, size.height * 0.34),
    ]) {
      canvas.drawCircle(point, 5, nodePaint);
      canvas.drawCircle(
        point,
        9,
        Paint()
          ..color = GtexColors.accentPrimary.withValues(alpha: 0.18)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2,
      );
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _BoardSignalTile extends StatelessWidget {
  const _BoardSignalTile({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(GtexSpacing.sm),
      decoration: BoxDecoration(
        color: GtexColors.surfaceRaised,
        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
        border: Border.all(color: color.withValues(alpha: 0.26)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            label,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: color,
              fontWeight: FontWeight.w900,
              letterSpacing: 0.9,
            ),
          ),
          const SizedBox(height: GtexSpacing.xs),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: GtexColors.textPrimary,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

class _LiveDot extends StatelessWidget {
  const _LiveDot();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 9,
      height: 9,
      decoration: const BoxDecoration(
        color: GtexColors.statusLive,
        shape: BoxShape.circle,
      ),
    );
  }
}

class _LandingBackdrop extends StatelessWidget {
  const _LandingBackdrop();

  @override
  Widget build(BuildContext context) {
    return const Stack(
      fit: StackFit.expand,
      children: <Widget>[
        DecoratedBox(decoration: BoxDecoration(color: GtexColors.surfaceBase)),
        CustomPaint(painter: _LandingGridPainter()),
        DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: <Color>[
                Color(0x8F0A0C0F),
                Color(0x1200E87A),
                Color(0xF20A0C0F),
              ],
              stops: <double>[0, 0.48, 1],
            ),
          ),
        ),
      ],
    );
  }
}

class _LandingGridPainter extends CustomPainter {
  const _LandingGridPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final Paint line =
        Paint()
          ..color = GtexColors.surfaceBorder.withValues(alpha: 0.28)
          ..strokeWidth = 1;
    for (double x = 0; x < size.width; x += 48) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), line);
    }
    for (double y = 0; y < size.height; y += 48) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), line);
    }
    final Paint glow =
        Paint()
          ..shader = RadialGradient(
            colors: <Color>[
              GtexColors.accentPrimary.withValues(alpha: 0.12),
              Colors.transparent,
            ],
          ).createShader(
            Rect.fromCircle(
              center: Offset(size.width * 0.72, size.height * 0.34),
              radius: size.shortestSide * 0.62,
            ),
          );
    canvas.drawRect(Offset.zero & size, glow);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _LandingActionDock extends StatelessWidget {
  const _LandingActionDock({
    this.onSignup,
    this.onCreatorSignup,
    this.onExploreMarket,
  });

  final VoidCallback? onSignup;
  final VoidCallback? onCreatorSignup;
  final VoidCallback? onExploreMarket;

  @override
  Widget build(BuildContext context) {
    final bool compact =
        MediaQuery.sizeOf(context).width < GtexBreakpoints.mobile;
    return SafeArea(
      top: false,
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          GtexSpacing.lg,
          GtexSpacing.sm,
          GtexSpacing.lg,
          compact ? GtexSpacing.lg : GtexSpacing.xl,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Wrap(
              alignment: WrapAlignment.center,
              spacing: GtexSpacing.sm,
              runSpacing: GtexSpacing.sm,
              children: <Widget>[
                GtexButton(label: 'Open a club', onPressed: onSignup),
                GtexButton(
                  label: 'Open transfer hub',
                  variant: GtexButtonVariant.secondary,
                  onPressed: onExploreMarket,
                ),
                if (!compact)
                  GtexButton(
                    label: 'Become a creator',
                    variant: GtexButtonVariant.ghost,
                    onPressed: onCreatorSignup,
                  ),
              ],
            ),
            if (compact) ...<Widget>[
              const SizedBox(height: GtexSpacing.xs),
              TextButton(
                onPressed: onCreatorSignup,
                child: const Text(
                  'Become a creator',
                  style: TextStyle(
                    color: GtexColors.textSecondary,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
