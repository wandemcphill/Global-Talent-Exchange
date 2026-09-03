import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../models/gtex_club_ownership_models.dart';

/// The user's club-ownership book, expressed in football terms: "I own part of
/// this club", not "I hold a financial record".
///
/// Honesty rules (PHASE4 P5/P6):
///   * an unknown ratio renders as an em dash, never `0%`;
///   * the share-price "why" strip only claims performance is driving the value
///     when [GtexClubShareHolding.hasPerformanceHistory] is true.
class GtexClubOwnershipPanel extends StatelessWidget {
  const GtexClubOwnershipPanel({
    super.key,
    required this.portfolio,
    this.isLoading = false,
    this.errorMessage,
    this.onRetry,
    this.onOpenClub,
    this.onBrowseClubMarket,
  });

  final GtexClubOwnershipPortfolio portfolio;
  final bool isLoading;
  final String? errorMessage;
  final VoidCallback? onRetry;
  final ValueChanged<String>? onOpenClub;
  final VoidCallback? onBrowseClubMarket;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      accent: GtexColors.coinGtex,
      title: 'Club ownership',
      subtitle:
          'Clubs you hold shares in, valued at the live club-share price. '
          'Share price moves with the club’s settled match performance.',
      child: _body(context),
    );
  }

  Widget _body(BuildContext context) {
    if (errorMessage != null && portfolio.isEmpty) {
      return GtexBlockedState(
        title: 'Club ownership unavailable',
        reason: errorMessage!,
        severity: GtexBlockedSeverity.error,
        ctaLabel: onRetry == null ? null : 'Retry',
        ctaAction: onRetry,
      );
    }
    if (isLoading && portfolio.isEmpty) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: GtexSpacing.lg),
        child: LinearProgressIndicator(),
      );
    }
    if (portfolio.isEmpty) {
      return GtexEmptyState(
        title: 'You don’t own part of any club yet',
        message:
            'Buy shares in a club and it appears here with your stake, its live '
            'share price, and how its results are moving that price.',
        icon: Icons.shield_outlined,
        accent: GtexColors.coinGtex,
        actionLabel: onBrowseClubMarket == null ? null : 'Browse the club market',
        onAction: onBrowseClubMarket,
      );
    }

    final Color plTone =
        portfolio.totalUnrealizedPlCoin >= 0
            ? GtexColors.accentPrimary
            : GtexColors.accentRed;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Wrap(
          spacing: GtexSpacing.sm,
          runSpacing: GtexSpacing.sm,
          children: <Widget>[
            SizedBox(
              width: 180,
              child: GtexMetricTile(
                label: 'Clubs owned',
                value: portfolio.clubCount.toString(),
                icon: Icons.groups_2_outlined,
                accent: GtexColors.coinGtex,
              ),
            ),
            SizedBox(
              width: 180,
              child: GtexMetricTile(
                label: 'Book value',
                value: _coin(portfolio.totalMarketValueCoin),
                helper: 'Cost ${_coin(portfolio.totalCostBasisCoin)}',
                icon: Icons.account_balance_outlined,
                accent: GtexColors.coinGtex,
              ),
            ),
            SizedBox(
              width: 180,
              child: GtexMetricTile(
                label: 'Unrealised P/L',
                value: _signedCoin(portfolio.totalUnrealizedPlCoin),
                icon: Icons.trending_up,
                accent: plTone,
              ),
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.md),
        ...portfolio.holdings.map(
          (GtexClubShareHolding holding) => Padding(
            padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
            child: _ClubShareCard(
              holding: holding,
              onTap:
                  onOpenClub == null
                      ? null
                      : () => onOpenClub!(holding.clubId),
            ),
          ),
        ),
      ],
    );
  }
}

class _ClubShareCard extends StatelessWidget {
  const _ClubShareCard({required this.holding, this.onTap});

  final GtexClubShareHolding holding;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final TextTheme textTheme = Theme.of(context).textTheme;
    final Color plTone =
        holding.unrealizedPlCoin >= 0
            ? GtexColors.accentPrimary
            : GtexColors.accentRed;
    final String ownership =
        holding.ownershipPercent == null
            ? '—'
            : '${holding.ownershipPercent!.toStringAsFixed(holding.ownershipPercent! >= 10 ? 0 : 1)}%';

    return GtexPanel(
      accent: GtexColors.coinGtex,
      padding: const EdgeInsets.all(GtexSpacing.sm),
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      holding.clubName,
                      style: textTheme.titleMedium?.copyWith(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'You own ${holding.sharesOwned} '
                      '${holding.sharesOwned == 1 ? 'share' : 'shares'} '
                      '· $ownership of the club',
                      style: textTheme.bodySmall?.copyWith(
                        color: GtexColors.textMuted,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: GtexSpacing.sm),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: <Widget>[
                  Text(
                    _coin(holding.marketValueCoin),
                    style: textTheme.titleMedium?.copyWith(
                      color: GtexColors.text,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    _signedCoin(holding.unrealizedPlCoin) +
                        (holding.unrealizedPlPercent == null
                            ? ''
                            : ' (${holding.unrealizedPlPercent! >= 0 ? '+' : ''}${holding.unrealizedPlPercent!.toStringAsFixed(1)}%)'),
                    style: textTheme.labelMedium?.copyWith(
                      color: plTone,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: GtexSpacing.sm),
          Wrap(
            spacing: GtexSpacing.xs,
            runSpacing: GtexSpacing.xs,
            children: <Widget>[
              GtexStatusChip(
                label: 'Share price ${_coin(holding.sharePriceCoin)}',
                color: GtexColors.coinGtex,
              ),
              GtexStatusChip(
                label: 'Your avg ${_coin(holding.averagePriceCoin)}',
                color: GtexColors.accentBlue,
              ),
              GtexStatusChip(
                label: '${holding.holderCount} '
                    '${holding.holderCount == 1 ? 'owner' : 'owners'}',
                color: GtexColors.textSecondary,
              ),
              if (holding.governanceEnabled)
                const GtexStatusChip(
                  label: 'Voting rights',
                  icon: Icons.how_to_vote_outlined,
                  color: GtexColors.accentPrimary,
                ),
            ],
          ),
          const SizedBox(height: GtexSpacing.xs),
          _WhyStrip(holding: holding),
        ],
      ),
    );
  }
}

/// The one-line "why is the share price what it is" affordance. It refuses to
/// imply performance is driving the price when the club has no settled matches.
class _WhyStrip extends StatelessWidget {
  const _WhyStrip({required this.holding});

  final GtexClubShareHolding holding;

  @override
  Widget build(BuildContext context) {
    final TextStyle? style = Theme.of(
      context,
    ).textTheme.bodySmall?.copyWith(color: GtexColors.textMuted);

    if (!holding.hasPerformanceHistory) {
      return Text(
        'No settled GTEX matches yet — the share price sits at its base.',
        style: style,
      );
    }

    final List<String> parts = <String>[];
    final double? win = holding.winRate;
    if (win != null) {
      parts.add('win rate ${(win * 100).toStringAsFixed(0)}%');
    }
    final double? perf = holding.performanceScore;
    if (perf != null) {
      parts.add('form ${perf >= 0 ? '+' : ''}${perf.toStringAsFixed(2)}');
    }
    final double? demand = holding.fanDemandScore;
    if (demand != null && demand != 0) {
      parts.add('fan demand ${demand >= 0 ? '+' : ''}${demand.toStringAsFixed(2)}');
    }
    return Text(
      'Share price is moving on ${parts.join(' · ')}.',
      style: style,
    );
  }
}

String _coin(double value) => '${value.toStringAsFixed(2)} coin';

String _signedCoin(double value) =>
    '${value >= 0 ? '+' : '-'}${value.abs().toStringAsFixed(2)} coin';
