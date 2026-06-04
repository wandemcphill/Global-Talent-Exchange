import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../domain/gtex_surface_state.dart';
import '../widgets/gtex_async_surface.dart';
import '../widgets/gtex_live_ticker.dart';
import '../widgets/gtex_state_panel.dart';

class GtexPublicHomeScreen extends StatelessWidget {
  const GtexPublicHomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: CustomScrollView(
          slivers: <Widget>[
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 18, 20, 10),
                child: Row(
                  children: <Widget>[
                    Container(
                      width: 42,
                      height: 42,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: theme.colorScheme.primary.withValues(
                          alpha: 0.12,
                        ),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: theme.colorScheme.primary.withValues(
                            alpha: 0.28,
                          ),
                        ),
                      ),
                      child: Text(
                        'G',
                        style: theme.textTheme.titleLarge?.copyWith(
                          color: theme.colorScheme.primary,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'GTEX',
                        style: theme.textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ),
                    TextButton(
                      onPressed: () => context.go('/auth/login'),
                      child: const Text('Sign in'),
                    ),
                    const SizedBox(width: 8),
                    FilledButton(
                      onPressed: () => context.go('/auth/signup'),
                      child: const Text('Create account'),
                    ),
                  ],
                ),
              ),
            ),
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(20, 28, 20, 20),
              sliver: SliverToBoxAdapter(
                child: LayoutBuilder(
                  builder: (BuildContext context, BoxConstraints constraints) {
                    final bool narrow = constraints.maxWidth < 760;
                    final Widget lead = _PublicLead(theme: theme);
                    final Widget pulse = const GtexAsyncSurface(
                      state: GtexSurfaceState.syncing,
                      eyebrow: 'PUBLIC STATUS',
                      title: 'Public data waits for confirmed services',
                      message:
                          'Guest views only show confirmed club, fixture, and player-market context. Private account and review details open after sign-in.',
                      child: SizedBox.shrink(),
                    );
                    if (narrow) {
                      return Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          lead,
                          const SizedBox(height: 28),
                          pulse,
                        ],
                      );
                    }
                    return Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Expanded(flex: 3, child: lead),
                        const SizedBox(width: 28),
                        Expanded(flex: 2, child: pulse),
                      ],
                    );
                  },
                ),
              ),
            ),
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 28),
              sliver: SliverToBoxAdapter(
                child: GtexLiveTicker(
                  items: const <String>[
                    'Live ecosystem pulse',
                    'Public competitions',
                    'Public newsroom',
                    'Account signup and role review',
                    'Club, fixture, and player records',
                    'Creator and trader access gated by approval',
                  ],
                  label: 'Production status',
                ),
              ),
            ),
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 32),
              sliver: SliverGrid.count(
                crossAxisCount: MediaQuery.sizeOf(context).width < 720 ? 1 : 3,
                mainAxisSpacing: 12,
                crossAxisSpacing: 12,
                childAspectRatio:
                    MediaQuery.sizeOf(context).width < 720 ? 2.8 : 1.42,
                children: const <Widget>[
                  _RoleCard(
                    icon: Icons.shield_outlined,
                    title: 'Football accounts',
                    message:
                        'Create a club identity, scout players, follow competitions, and prepare matchday workflows.',
                  ),
                  _RoleCard(
                    icon: Icons.campaign_outlined,
                    title: 'Creator roles',
                    message:
                        'Request reviewed creator access for football content, communities, and approved creator tools.',
                  ),
                  _RoleCard(
                    icon: Icons.verified_user_outlined,
                    title: 'Verified traders',
                    message:
                        'Use approved market workflows only after identity, region, and compliance checks pass.',
                  ),
                  _RoleCard(
                    icon: Icons.emoji_events_outlined,
                    title: 'Public competitions',
                    message:
                        'Browse public football competitions only when GTEX has confirmed competition records to show.',
                  ),
                  _RoleCard(
                    icon: Icons.newspaper_outlined,
                    title: 'Public newsroom',
                    message:
                        'Read confirmed football economy stories without exposing private club, wallet, or review data.',
                  ),
                  _RoleCard(
                    icon: Icons.sensors_outlined,
                    title: 'Ecosystem pulse',
                    message:
                        'Public status surfaces show what changed without inventing rankings, balances, transfers, or match states.',
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PublicLead extends StatelessWidget {
  const _PublicLead({required this.theme});

  final ThemeData theme;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          'GTEX starts with a football account.',
          style: theme.textTheme.displaySmall?.copyWith(
            fontWeight: FontWeight.w900,
            height: 1.02,
          ),
        ),
        const SizedBox(height: 14),
        Text(
          'Create an account to build a club, scout players, follow competitions, request creator access, or apply for verified trader tools. Guest screens stay limited to confirmed public context.',
          style: theme.textTheme.titleMedium?.copyWith(
            color: theme.colorScheme.onSurface.withValues(alpha: 0.72),
            height: 1.35,
          ),
        ),
        const SizedBox(height: 24),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: <Widget>[
            FilledButton.icon(
              onPressed: () => context.go('/auth/signup'),
              icon: const Icon(Icons.person_add_alt_1),
              label: const Text('Create account'),
            ),
            OutlinedButton.icon(
              onPressed: () => context.go('/auth/signup'),
              icon: const Icon(Icons.campaign_outlined),
              label: const Text('Creator role'),
            ),
            OutlinedButton.icon(
              onPressed: () => context.go('/auth/signup'),
              icon: const Icon(Icons.candlestick_chart),
              label: const Text('Trader role'),
            ),
          ],
        ),
      ],
    );
  }
}

class GtexRegionSelectionScreen extends StatelessWidget {
  const GtexRegionSelectionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: GtexStatePanel(
            state: GtexSurfaceState.pending,
            eyebrow: 'REGION',
            title: 'Region selection waits for account policy',
            message:
                'GTEX confirms region eligibility through identity and compliance services before role-specific account actions open.',
            icon: Icons.public_outlined,
            actionLabel: 'Create account',
            onAction: () => context.go('/auth/signup'),
          ),
        ),
      ),
    );
  }
}

class _RoleCard extends StatelessWidget {
  const _RoleCard({
    required this.icon,
    required this.title,
    required this.message,
  });

  final IconData icon;
  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface.withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: theme.colorScheme.outline.withValues(alpha: 0.22),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(icon, color: theme.colorScheme.primary),
          const SizedBox(height: 12),
          Text(
            title,
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 8),
          Expanded(
            child: Text(
              message,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurface.withValues(alpha: 0.68),
                height: 1.32,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
