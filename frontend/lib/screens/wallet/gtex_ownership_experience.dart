import 'package:flutter/material.dart';

import '../../data/gte_exchange_models.dart';
import '../../data/gte_models.dart';
import '../../domain/ownership/gtex_ownership_models.dart';
import '../../features/club_redesign/models/gtex_club_ownership_models.dart';
import '../../ui_gtex/ui_gtex.dart';
import '../../widgets/gte_formatters.dart';

/// PHASE4-B — the capital desk's ownership experience.
///
/// The holdings module used to read as a ledger: an icon, a name, a quantity, a
/// percent. This renders the same positions as a football squad — grouped by
/// club, each player carried by the canonical [GtexPlayerCard], each one tap
/// from the canonical Player Detail — plus the user's club-share interests.
///
/// Every number traces to `/api/portfolio`, `/api/portfolio/snapshot` or
/// `/api/portfolio/clubs`. Where a value is genuinely unknown it is stated, not
/// shown as zero (P6).
class GtexOwnershipExperience extends StatelessWidget {
  const GtexOwnershipExperience({
    super.key,
    required this.book,
    this.summary,
    this.walletSummary,
    this.snapshot,
    this.clubOwnership,
    this.isLoadingClubs = false,
    this.clubError,
    this.portfolioError,
    this.ownerName,
    this.identityLookup,
    this.onOpenPlayer,
    this.onRetry,
    this.onBrowseMarket,
  });

  final GtexOwnershipBook book;
  final GtePortfolioSummary? summary;
  final GteWalletSummary? walletSummary;
  final GtePortfolioSnapshot? snapshot;
  final GtexClubOwnershipPortfolio? clubOwnership;
  final bool isLoadingClubs;
  final String? clubError;
  final String? portfolioError;
  final String? ownerName;
  final GteMarketPlayerListItem? Function(String playerId)? identityLookup;
  final ValueChanged<String>? onOpenPlayer;
  final Future<void> Function()? onRetry;
  final VoidCallback? onBrowseMarket;

  bool get _hasClubBook =>
      (clubOwnership?.holdings.isNotEmpty ?? false) || isLoadingClubs;

  double get _investedValue =>
      book.stakes.fold<double>(0, (double sum, GtexOwnershipStake s) => sum + s.marketValue);

  double get _costBasis =>
      book.stakes.fold<double>(0, (double sum, GtexOwnershipStake s) => sum + s.costBasis);

  double get _unrealized =>
      book.stakes.fold<double>(0, (double sum, GtexOwnershipStake s) => sum + s.unrealizedPl);

  @override
  Widget build(BuildContext context) {
    final bool squadEmpty = book.isEmpty;

    if (squadEmpty && !_hasClubBook) {
      if (portfolioError != null) {
        return _ScrollBody(
          children: <Widget>[
            GtexBlockedState(
              severity: GtexBlockedSeverity.error,
              title: 'Squad could not be loaded',
              reason: portfolioError!,
              resolution: 'Your positions are safe. Retry to resync.',
              ctaLabel: onRetry == null ? null : 'Retry',
              ctaAction: onRetry == null ? null : () => onRetry!(),
            ),
          ],
        );
      }
      return _ScrollBody(
        children: <Widget>[
          GtexEmptyState(
            title: 'Your squad is empty',
            message:
                'Players you sign on the Transfer Hub land here as your squad — '
                'with what you paid, what they are worth now, and how each '
                'position is moving.',
            icon: Icons.groups_2_outlined,
            actionLabel: onBrowseMarket == null ? null : 'Open Transfer Hub',
            onAction: onBrowseMarket,
          ),
        ],
      );
    }

    final List<_ClubGroup> groups = _buildGroups();

    return _ScrollBody(
      children: <Widget>[
        _PositionHeader(
          ownerName: ownerName,
          squadSize: book.length,
          investedValue: _investedValue,
          costBasis: _costBasis,
          unrealized: _unrealized,
          summary: summary,
          walletSummary: walletSummary,
          snapshot: snapshot,
          clubOwnership: clubOwnership,
        ),
        if (portfolioError != null && book.isNotEmpty) ...<Widget>[
          const SizedBox(height: GtexSpacing.md),
          GtexBlockedState(
            severity: GtexBlockedSeverity.warning,
            title: 'Showing the last good squad snapshot',
            reason: portfolioError!,
            ctaLabel: onRetry == null ? null : 'Retry',
            ctaAction: onRetry == null ? null : () => onRetry!(),
            compact: true,
          ),
        ],
        if (book.isNotEmpty) ...<Widget>[
          const SizedBox(height: GtexSpacing.lg),
          _SectionLabel('MY SQUAD'),
          const SizedBox(height: GtexSpacing.xs),
          for (final _ClubGroup group in groups) ...<Widget>[
            _ClubGroupHeader(group: group, investedTotal: _investedValue),
            const SizedBox(height: GtexSpacing.sm),
            for (final GtexOwnershipStake stake in group.stakes)
              Padding(
                padding: const EdgeInsets.only(bottom: GtexSpacing.md),
                child: _SquadMemberCard(
                  stake: stake,
                  identity: identityLookup?.call(stake.playerId),
                  investedTotal: _investedValue,
                  onOpenPlayer: onOpenPlayer,
                ),
              ),
            const SizedBox(height: GtexSpacing.sm),
          ],
        ],
        const SizedBox(height: GtexSpacing.lg),
        _SectionLabel('MY CLUB INTERESTS'),
        const SizedBox(height: GtexSpacing.xs),
        _ClubShareSection(
          portfolio: clubOwnership,
          isLoading: isLoadingClubs,
          error: clubError,
        ),
      ],
    );
  }

  List<_ClubGroup> _buildGroups() {
    final Map<String, List<GtexOwnershipStake>> byClub =
        <String, List<GtexOwnershipStake>>{};
    for (final GtexOwnershipStake stake in book.stakes) {
      final GteMarketPlayerListItem? id = identityLookup?.call(stake.playerId);
      final String club = (id?.currentClubName?.trim().isNotEmpty ?? false)
          ? id!.currentClubName!.trim()
          : (stake.clubName?.trim().isNotEmpty ?? false)
              ? stake.clubName!.trim()
              : 'Club unknown';
      byClub.putIfAbsent(club, () => <GtexOwnershipStake>[]).add(stake);
    }
    final List<_ClubGroup> groups = byClub.entries
        .map(
          (MapEntry<String, List<GtexOwnershipStake>> e) => _ClubGroup(
            clubName: e.key,
            stakes: e.value
              ..sort(
                (GtexOwnershipStake a, GtexOwnershipStake b) =>
                    b.marketValue.compareTo(a.marketValue),
              ),
          ),
        )
        .toList(growable: false)
      ..sort((_ClubGroup a, _ClubGroup b) => b.value.compareTo(a.value));
    return groups;
  }
}

class _ClubGroup {
  _ClubGroup({required this.clubName, required this.stakes});

  final String clubName;
  final List<GtexOwnershipStake> stakes;

  double get value =>
      stakes.fold<double>(0, (double sum, GtexOwnershipStake s) => sum + s.marketValue);
  double get unrealized =>
      stakes.fold<double>(0, (double sum, GtexOwnershipStake s) => sum + s.unrealizedPl);
}

class _ScrollBody extends StatelessWidget {
  const _ScrollBody({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.only(bottom: GtexSpacing.xl),
      children: children,
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.label);

  final String label;

  @override
  Widget build(BuildContext context) {
    return Text(
      label,
      style: Theme.of(context).textTheme.labelSmall?.copyWith(
            color: GtexColors.textMuted,
            fontWeight: FontWeight.w900,
            letterSpacing: 1.2,
          ),
    );
  }
}

class _PositionHeader extends StatelessWidget {
  const _PositionHeader({
    required this.ownerName,
    required this.squadSize,
    required this.investedValue,
    required this.costBasis,
    required this.unrealized,
    required this.summary,
    required this.walletSummary,
    required this.snapshot,
    required this.clubOwnership,
  });

  final String? ownerName;
  final int squadSize;
  final double investedValue;
  final double costBasis;
  final double unrealized;
  final GtePortfolioSummary? summary;
  final GteWalletSummary? walletSummary;
  final GtePortfolioSnapshot? snapshot;
  final GtexClubOwnershipPortfolio? clubOwnership;

  @override
  Widget build(BuildContext context) {
    // Prefer the backend-aggregated summary; fall back to summing the squad
    // (a documented client derivation, §9.1) when the summary has not loaded.
    final double invested = (summary?.totalMarketValue ?? 0) > 0
        ? summary!.totalMarketValue
        : investedValue;
    final double unrealizedPl = summary?.unrealizedPlTotal ?? unrealized;
    final double? unrealizedPct =
        costBasis > 0 ? (unrealizedPl / costBasis) * 100 : null;
    final Color plColor =
        unrealizedPl > 0 ? GtexColors.pitch : (unrealizedPl < 0 ? GtexColors.red : GtexColors.textMuted);

    final double? available =
        snapshot?.availableBalance ?? walletSummary?.availableBalance;
    final double? reserved =
        snapshot?.reservedBalance ?? walletSummary?.reservedBalance;

    final double clubValue = clubOwnership?.totalMarketValueCoin ?? 0;

    return GtexPanel(
      title: 'My Position',
      subtitle: ownerName == null || ownerName!.trim().isEmpty
          ? '$squadSize player asset${squadSize == 1 ? '' : 's'} owned'
          : "${ownerName!.trim()} · $squadSize player asset${squadSize == 1 ? '' : 's'}",
      accent: GtexColors.pitch,
      child: Wrap(
        spacing: GtexSpacing.md,
        runSpacing: GtexSpacing.md,
        children: <Widget>[
          _tile('Squad value', gteFormatGtc(invested), Icons.groups_2_outlined,
              GtexColors.pitch),
          _tile('Cost basis', costBasis > 0 ? gteFormatGtc(costBasis) : '—',
              Icons.receipt_long_outlined, GtexColors.cyan),
          _tile(
            'Unrealized P/L',
            costBasis > 0
                ? '${unrealizedPl >= 0 ? '+' : ''}${gteFormatGtc(unrealizedPl)}'
                    '${unrealizedPct == null ? '' : '  (${unrealizedPct >= 0 ? '+' : ''}${unrealizedPct.toStringAsFixed(1)}%)'}'
                : 'No cost basis yet',
            unrealizedPl >= 0 ? Icons.trending_up : Icons.trending_down,
            plColor,
          ),
          // UNKNOWN != ZERO - see GtePortfolioSummary.realizedPlAvailable.
          if (summary != null && summary!.realizedPlAvailable)
            _tile(
              'Realized P/L',
              '${summary!.realizedPlTotal >= 0 ? '+' : ''}${gteFormatGtc(summary!.realizedPlTotal)}',
              Icons.savings_outlined,
              summary!.realizedPlTotal >= 0 ? GtexColors.pitch : GtexColors.red,
            )
          else if (summary != null)
            _tile(
              'Realized P/L',
              'Not calculated',
              Icons.savings_outlined,
              GtexColors.textMuted,
            ),
          if (available != null)
            _tile('Cash ready', gteFormatGtc(available), Icons.account_balance_wallet_outlined,
                GtexColors.gold),
          if (reserved != null && reserved > 0)
            _tile('Held by orders', gteFormatGtc(reserved), Icons.lock_clock_outlined,
                GtexColors.gold),
          if (clubValue > 0)
            _tile('Club interests', gteFormatGtc(clubValue), Icons.apartment_outlined,
                GtexColors.purple),
        ],
      ),
    );
  }

  Widget _tile(String label, String value, IconData icon, Color accent) {
    return SizedBox(
      width: 200,
      child: GtexMetricTile(
        label: label,
        value: value,
        icon: icon,
        accent: accent,
      ),
    );
  }
}

class _ClubGroupHeader extends StatelessWidget {
  const _ClubGroupHeader({required this.group, required this.investedTotal});

  final _ClubGroup group;
  final double investedTotal;

  @override
  Widget build(BuildContext context) {
    final double weight = investedTotal <= 0 ? 0 : group.value / investedTotal;
    final Color plColor = group.unrealized > 0
        ? GtexColors.pitch
        : (group.unrealized < 0 ? GtexColors.red : GtexColors.textMuted);
    return Padding(
      padding: const EdgeInsets.only(top: GtexSpacing.sm),
      child: Row(
        children: <Widget>[
          const Icon(Icons.shield_outlined, size: 18, color: GtexColors.textMuted),
          const SizedBox(width: GtexSpacing.xs),
          Expanded(
            child: Text(
              group.clubName,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                  ),
            ),
          ),
          const SizedBox(width: GtexSpacing.sm),
          Text(
            '${group.stakes.length} · ${gteFormatGtc(group.value)}'
            ' · ${(weight * 100).toStringAsFixed(0)}%',
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: plColor,
                  fontWeight: FontWeight.w800,
                ),
          ),
        ],
      ),
    );
  }
}

class _SquadMemberCard extends StatelessWidget {
  const _SquadMemberCard({
    required this.stake,
    required this.identity,
    required this.investedTotal,
    required this.onOpenPlayer,
  });

  final GtexOwnershipStake stake;
  final GteMarketPlayerListItem? identity;
  final double investedTotal;
  final ValueChanged<String>? onOpenPlayer;

  @override
  Widget build(BuildContext context) {
    final GteMarketPlayerListItem? id = identity;
    final String name = (id?.playerName.trim().isNotEmpty ?? false)
        ? id!.playerName.trim()
        : (stake.playerName?.trim().isNotEmpty ?? false)
            ? stake.playerName!.trim()
            : stake.playerId;
    final String position =
        (id?.position?.trim().isNotEmpty ?? false) ? id!.position!.trim() : '—';
    final String club = (id?.currentClubName?.trim().isNotEmpty ?? false)
        ? id!.currentClubName!.trim()
        : (stake.clubName?.trim().isNotEmpty ?? false)
            ? stake.clubName!.trim()
            : 'Club unknown';
    final double? movement = id?.movementPct;
    final double? rating = id?.averageRating;
    final bool markPending = stake.currentPrice == null;

    final double weight = investedTotal <= 0 ? 0 : stake.marketValue / investedTotal;
    final Color plColor = stake.isInProfit
        ? GtexColors.pitch
        : (stake.unrealizedPl < 0 ? GtexColors.red : GtexColors.textMuted);

    return GtexPanel(
      accent: markPending
          ? GtexColors.textMuted
          : (stake.isInProfit ? GtexColors.pitch : GtexColors.red),
      padding: const EdgeInsets.all(GtexSpacing.sm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          GtexPlayerCard(
            name: name,
            position: position,
            clubName: club,
            nationality: id?.nationality ?? '',
            countryCode: id?.nationalityCode,
            priceLabel: gteFormatGtc(stake.marketValue),
            imageUrl: id?.imageUrl,
            ratingLabel: rating == null ? null : 'OVR ${rating.toStringAsFixed(0)}',
            valueDeltaLabel:
                movement == null ? null : gteFormatMovement(movement / 100),
            valueState:
                movement == null ? GtexValueState.recent : GtexValueState.live,
            scale: GtexPlayerCardScale.compact,
            isOwned: true,
            ownershipLabel: stake.ownershipLabel,
            onTap: onOpenPlayer == null
                ? null
                : () => onOpenPlayer!(stake.playerId),
          ),
          const SizedBox(height: GtexSpacing.sm),
          if (markPending)
            const GtexBlockedState(
              severity: GtexBlockedSeverity.info,
              title: 'Mark pending',
              reason:
                  'The market has not priced this position yet. Value and P/L '
                  'appear once a live mark is available.',
              compact: true,
            )
          else
            Row(
              children: <Widget>[
                Expanded(
                  child: _StakeStat(
                    label: 'Cost basis',
                    value: gteFormatGtc(stake.costBasis),
                  ),
                ),
                Expanded(
                  child: _StakeStat(
                    label: 'Unrealized P/L',
                    value:
                        '${stake.unrealizedPl >= 0 ? '+' : ''}${gteFormatGtc(stake.unrealizedPl)}',
                    valueColor: plColor,
                  ),
                ),
                Expanded(
                  child: _StakeStat(
                    label: 'Return',
                    value: stake.unrealizedPlPercent == null
                        ? '—'
                        : '${stake.unrealizedPlPercent! >= 0 ? '+' : ''}${stake.unrealizedPlPercent!.toStringAsFixed(1)}%',
                    valueColor: plColor,
                  ),
                ),
              ],
            ),
          const SizedBox(height: GtexSpacing.sm),
          ClipRRect(
            borderRadius: BorderRadius.circular(GtexSpacing.radiusPill),
            child: LinearProgressIndicator(
              value: weight.clamp(0, 1),
              minHeight: 6,
              backgroundColor: GtexColors.surfaceOverlay,
              valueColor: AlwaysStoppedAnimation<Color>(plColor),
            ),
          ),
          const SizedBox(height: GtexSpacing.xxs),
          Text(
            '${(weight * 100).toStringAsFixed(0)}% of squad value'
            ' · tap for the value story',
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: GtexColors.textMuted,
                ),
          ),
        ],
      ),
    );
  }
}

class _StakeStat extends StatelessWidget {
  const _StakeStat({required this.label, required this.value, this.valueColor});

  final String label;
  final String value;
  final Color? valueColor;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          label.toUpperCase(),
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: GtexColors.textMuted,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.4,
              ),
        ),
        const SizedBox(height: 2),
        Text(
          value,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                color: valueColor ?? GtexColors.text,
                fontWeight: FontWeight.w900,
              ),
        ),
      ],
    );
  }
}

class _ClubShareSection extends StatelessWidget {
  const _ClubShareSection({
    required this.portfolio,
    required this.isLoading,
    required this.error,
  });

  final GtexClubOwnershipPortfolio? portfolio;
  final bool isLoading;
  final String? error;

  @override
  Widget build(BuildContext context) {
    if (error != null) {
      return GtexBlockedState(
        severity: GtexBlockedSeverity.warning,
        title: 'Club interests unavailable',
        reason: error!,
        resolution: 'Player holdings above are unaffected.',
        compact: true,
      );
    }
    if (isLoading && portfolio == null) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: GtexSpacing.md),
        child: LinearProgressIndicator(),
      );
    }
    final GtexClubOwnershipPortfolio book =
        portfolio ?? GtexClubOwnershipPortfolio.empty();
    if (book.holdings.isEmpty) {
      return const GtexEmptyState(
        title: 'No club shares yet',
        message:
            'When you buy ownership tokens in a club, your stake, its live '
            'share price, and the match results moving it show up here.',
        icon: Icons.apartment_outlined,
      );
    }

    final Color totalPl = book.totalUnrealizedPlCoin > 0
        ? GtexColors.pitch
        : (book.totalUnrealizedPlCoin < 0 ? GtexColors.red : GtexColors.textMuted);

    return GtexPanel(
      title: 'Club shares',
      subtitle:
          '${book.clubCount} club${book.clubCount == 1 ? '' : 's'} · ${gteFormatGtc(book.totalMarketValueCoin)}',
      accent: GtexColors.purple,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Unrealized P/L '
            '${book.totalUnrealizedPlCoin >= 0 ? '+' : ''}${gteFormatGtc(book.totalUnrealizedPlCoin)}',
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: totalPl,
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: GtexSpacing.sm),
          for (final GtexClubShareHolding h in book.holdings)
            Padding(
              padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
              child: _ClubShareTile(holding: h),
            ),
        ],
      ),
    );
  }
}

class _ClubShareTile extends StatelessWidget {
  const _ClubShareTile({required this.holding});

  final GtexClubShareHolding holding;

  @override
  Widget build(BuildContext context) {
    final Color plColor = holding.isInProfit
        ? GtexColors.pitch
        : (holding.unrealizedPlCoin < 0 ? GtexColors.red : GtexColors.textMuted);
    return GtexPanel(
      accent: plColor,
      padding: const EdgeInsets.all(GtexSpacing.sm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              const Icon(Icons.apartment_outlined,
                  size: 18, color: GtexColors.purple),
              const SizedBox(width: GtexSpacing.xs),
              Expanded(
                child: Text(
                  holding.clubName,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w900,
                      ),
                ),
              ),
              Text(
                gteFormatGtc(holding.marketValueCoin),
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      color: GtexColors.text,
                      fontWeight: FontWeight.w900,
                    ),
              ),
            ],
          ),
          const SizedBox(height: GtexSpacing.xs),
          Text(
            <String>[
              '${holding.sharesOwned} share${holding.sharesOwned == 1 ? '' : 's'}',
              'Price ${gteFormatGtc(holding.sharePriceCoin)}',
              'Avg ${gteFormatGtc(holding.averagePriceCoin)}',
              if (holding.ownershipPercent != null)
                '${holding.ownershipPercent!.toStringAsFixed(2)}% of club',
            ].join('  ·  '),
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: GtexColors.textMuted,
                ),
          ),
          const SizedBox(height: GtexSpacing.xs),
          Text(
            'Unrealized P/L '
            '${holding.unrealizedPlCoin >= 0 ? '+' : ''}${gteFormatGtc(holding.unrealizedPlCoin)}'
            '${holding.unrealizedPlPercent == null ? '' : '  (${holding.unrealizedPlPercent! >= 0 ? '+' : ''}${holding.unrealizedPlPercent!.toStringAsFixed(1)}%)'}',
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: plColor,
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: GtexSpacing.xxs),
          Text(
            holding.hasPerformanceHistory
                ? 'Share price is tracking settled-match performance.'
                : 'No settled GTEX matches behind this price yet.',
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: GtexColors.textMuted,
                  fontStyle: FontStyle.italic,
                ),
          ),
        ],
      ),
    );
  }
}
