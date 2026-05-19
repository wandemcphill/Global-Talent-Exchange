import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/app_spacing.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_motion.dart';
import '../../../core/utils/app_formatters.dart';
import '../../../core/widgets/app_press_scale.dart';
import '../../../core/widgets/app_shake.dart';
import '../../../core/widgets/player_card.dart';
import '../../../core/widgets/gtex_surface_card.dart';
import '../../../shared/providers/transfer_provider.dart';
import '../../../shared/widgets/metric_pill.dart';
import '../../../widgets/player_card_avatar.dart';

String formatBidCountdown(int seconds) {
  final int minutes = seconds ~/ 60;
  final int remainingSeconds = seconds % 60;
  return '${minutes.toString().padLeft(2, '0')}:${remainingSeconds.toString().padLeft(2, '0')}';
}

class TransferMarketFilterBar extends StatelessWidget {
  const TransferMarketFilterBar({
    super.key,
    required this.activeFilter,
    required this.onSelected,
  });

  final TransferMarketFilter activeFilter;
  final ValueChanged<TransferMarketFilter> onSelected;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      physics: const BouncingScrollPhysics(
        parent: AlwaysScrollableScrollPhysics(),
      ),
      child: Row(
        children:
            TransferMarketFilter.values
                .map(
                  (TransferMarketFilter filter) => Padding(
                    padding: const EdgeInsets.only(right: spacingSM),
                    child: ChoiceChip(
                      key: Key('transfer-filter-${filter.name}'),
                      label: Text(filter.label),
                      selected: filter == activeFilter,
                      onSelected: (_) => onSelected(filter),
                    ),
                  ),
                )
                .toList(),
      ),
    );
  }
}

class TransferPlayerCard extends StatelessWidget {
  const TransferPlayerCard({
    super.key,
    required this.listing,
    required this.shortlisted,
    required this.onShortlist,
    required this.onTap,
  });

  final TransferMarketListing listing;
  final bool shortlisted;
  final VoidCallback onShortlist;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final bool userLeading = listing.userIsHighestBidder;
    final Color glowColor =
        userLeading
            ? AppColors.primary
            : listing.player.isHot
            ? AppColors.gold
            : AppColors.divider;

    return KeyedSubtree(
      key: Key('transfer-card-${listing.player.id}'),
      child: PlayerCard(
        name: listing.player.name,
        rating: listing.player.rating,
        image: listing.player.image,
        position: listing.player.position,
        subtitle: listing.player.country,
        highlighted: userLeading || listing.player.isHot,
        onTap: onTap,
        accentColor: glowColor,
        avatarSize: 64,
        layout: PlayerCardLayout.horizontal,
        badgeLabels: <String>[listing.player.position],
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            _LiveStatusPill(
              label: userLeading ? 'Leading' : 'Live Bid',
              color: userLeading ? AppColors.primary : AppColors.gold,
              icon:
                  userLeading
                      ? Icons.workspace_premium_rounded
                      : Icons.bolt_rounded,
            ),
            const SizedBox(width: spacingSM),
            AppPressScale(
              child: IconButton(
                tooltip:
                    shortlisted ? 'Remove from shortlist' : 'Add to shortlist',
                onPressed: onShortlist,
                style: IconButton.styleFrom(
                  backgroundColor: AppColors.background.withValues(alpha: 0.55),
                  foregroundColor:
                      shortlisted ? AppColors.gold : AppColors.textSecondary,
                  side: const BorderSide(color: AppColors.divider),
                ),
                icon: Icon(
                  shortlisted
                      ? Icons.bookmark_rounded
                      : Icons.bookmark_add_outlined,
                ),
              ),
            ),
          ],
        ),
        metrics: <PlayerCardMetric>[
          PlayerCardMetric(label: 'Role', value: listing.player.position),
          PlayerCardMetric(label: 'Age', value: '${listing.player.age}'),
          PlayerCardMetric(label: 'OVR', value: '${listing.player.rating}'),
        ],
        footer: _TransferAuctionFooter(
          listing: listing,
          accent: glowColor,
          userLeading: userLeading,
        ),
      ),
    );
  }
}

class _TransferAuctionFooter extends StatelessWidget {
  const _TransferAuctionFooter({
    required this.listing,
    required this.accent,
    required this.userLeading,
  });

  final TransferMarketListing listing;
  final Color accent;
  final bool userLeading;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        AnimatedContainer(
          duration: AppMotion.medium,
          curve: AppMotion.easeOut,
          padding: const EdgeInsets.all(spacingMD),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(cardRadius),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[
                accent.withValues(alpha: 0.14),
                AppColors.surfaceMuted.withValues(alpha: 0.82),
                AppColors.card.withValues(alpha: 0.92),
              ],
            ),
            border: Border.all(color: accent.withValues(alpha: 0.22)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Current Bid', style: Theme.of(context).textTheme.bodySmall),
              const SizedBox(height: spacingXS),
              _AnimatedValueText(
                keyValue:
                    'bid-${listing.player.id}-${listing.currentBidInMillions}',
                text: AppFormatters.money(listing.currentBidInMillions),
                flashColor: AppColors.success,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: spacingMD),
              Row(
                children: <Widget>[
                  Expanded(
                    child: _MetaBlock(
                      label: 'Timer',
                      child: Row(
                        children: <Widget>[
                          Icon(
                            Icons.schedule_rounded,
                            size: 16,
                            color:
                                listing.secondsRemaining <= 15
                                    ? AppColors.gold
                                    : AppColors.textSecondary,
                          ),
                          const SizedBox(width: spacingXS),
                          Expanded(
                            child: _AnimatedValueText(
                              keyValue:
                                  'timer-${listing.player.id}-${listing.secondsRemaining}',
                              text: formatBidCountdown(
                                listing.secondsRemaining,
                              ),
                              flashColor:
                                  listing.secondsRemaining <= 15
                                      ? AppColors.gold
                                      : null,
                              style: Theme.of(
                                context,
                              ).textTheme.titleLarge?.copyWith(
                                color:
                                    listing.secondsRemaining <= 15
                                        ? AppColors.gold
                                        : AppColors.textPrimary,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(width: spacingSM),
                  Expanded(
                    child: _MetaBlock(
                      label: 'Watchers',
                      child: Text(
                        AppFormatters.compact(listing.watcherCount),
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: spacingMD),
        AnimatedContainer(
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOutCubic,
          padding: const EdgeInsets.all(spacingMD),
          decoration: BoxDecoration(
            color:
                userLeading
                    ? AppColors.primary.withValues(alpha: 0.12)
                    : AppColors.gold.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(cardRadius),
            border: Border.all(
              color:
                  userLeading
                      ? AppColors.primary.withValues(alpha: 0.45)
                      : AppColors.gold.withValues(alpha: 0.28),
            ),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Icon(
                userLeading
                    ? Icons.verified_rounded
                    : Icons.local_fire_department_rounded,
                color: userLeading ? AppColors.primary : AppColors.gold,
                size: 18,
              ),
              const SizedBox(width: spacingSM),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      userLeading
                          ? 'GTEX holds the highest bid'
                          : 'Highest bidder',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    const SizedBox(height: spacingXS),
                    Text(
                      listing.leadingBidder.clubName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: userLeading ? AppColors.primary : AppColors.gold,
                      ),
                    ),
                    const SizedBox(height: spacingXS),
                    Text(
                      '${listing.player.country} | Potential ${listing.player.potential}',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class TransferBidSheet extends ConsumerStatefulWidget {
  const TransferBidSheet({super.key, required this.playerId});

  final String playerId;

  @override
  ConsumerState<TransferBidSheet> createState() => _TransferBidSheetState();
}

class _TransferBidSheetState extends ConsumerState<TransferBidSheet> {
  late final TextEditingController _bidController;
  late final FocusNode _bidFocusNode;
  int _inputErrorCount = 0;

  @override
  void initState() {
    super.initState();
    final double minimumBid = ref
        .read(transferProvider.notifier)
        .minimumBidFor(widget.playerId);
    _bidController = TextEditingController(
      text: minimumBid > 0 ? minimumBid.toStringAsFixed(1) : '',
    );
    _bidFocusNode = FocusNode();
  }

  @override
  void dispose() {
    _bidController.dispose();
    _bidFocusNode.dispose();
    super.dispose();
  }

  Future<void> _placeBid(TransferMarketListing listing) async {
    final TransferMarketNotifier notifier = ref.read(transferProvider.notifier);
    final double minimumBid = notifier.minimumBidFor(widget.playerId);
    final double? parsedBid = double.tryParse(_bidController.text.trim());

    if (parsedBid == null || parsedBid < minimumBid) {
      setState(() {
        _inputErrorCount += 1;
      });
      HapticFeedback.mediumImpact();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Bid must be at least ${AppFormatters.money(minimumBid)}.',
          ),
        ),
      );
      return;
    }

    final double? placedBid = await notifier.submitBid(
      widget.playerId,
      parsedBid,
    );
    if (!mounted) {
      return;
    }
    if (placedBid == null) {
      HapticFeedback.heavyImpact();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Bid could not be submitted. Refresh and try again.'),
        ),
      );
      return;
    }
    final double nextMinimum = notifier.minimumBidFor(widget.playerId);

    _bidController
      ..text = nextMinimum.toStringAsFixed(1)
      ..selection = TextSelection.fromPosition(
        TextPosition(offset: _bidController.text.length),
      );

    FocusScope.of(context).unfocus();
    HapticFeedback.selectionClick();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          'Bid placed on ${listing.player.name} at ${AppFormatters.money(placedBid)}.',
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final TransferMarketState state = ref.watch(transferProvider);
    final TransferMarketListing? listing = state.listingFor(widget.playerId);

    if (listing == null) {
      return const SizedBox.shrink();
    }

    final double minimumBid = ref
        .read(transferProvider.notifier)
        .minimumBidFor(widget.playerId);
    if (_bidController.text.isEmpty && !_bidFocusNode.hasFocus) {
      _bidController.text = minimumBid.toStringAsFixed(1);
    }

    final List<MarketBidEntry> recentBids =
        listing.bidHistory.reversed.take(6).toList();

    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.8,
      minChildSize: 0.56,
      maxChildSize: 0.92,
      builder: (BuildContext context, ScrollController scrollController) {
        return Container(
          key: const Key('transfer-bid-sheet'),
          decoration: BoxDecoration(
            color: AppColors.card,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
            border: Border.all(color: AppColors.divider),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.42),
                blurRadius: 32,
                offset: const Offset(0, -10),
              ),
            ],
          ),
          child: SafeArea(
            top: false,
            child: ListView(
              controller: scrollController,
              padding: const EdgeInsets.fromLTRB(
                spacingLG,
                spacingMD,
                spacingLG,
                spacingLG,
              ),
              children: <Widget>[
                Center(
                  child: Container(
                    width: 56,
                    height: 5,
                    decoration: BoxDecoration(
                      color: AppColors.divider,
                      borderRadius: BorderRadius.circular(999),
                    ),
                  ),
                ),
                const SizedBox(height: spacingLG),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    _PlayerAvatar(imageAsset: listing.player.image, size: 76),
                    const SizedBox(width: spacingMD),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            listing.player.name,
                            style: Theme.of(context).textTheme.headlineSmall,
                          ),
                          const SizedBox(height: spacingSM),
                          Text(
                            '${listing.player.position} | ${listing.player.country} | Age ${listing.player.age}',
                            style: Theme.of(context).textTheme.bodyMedium
                                ?.copyWith(color: AppColors.textSecondary),
                          ),
                          const SizedBox(height: spacingMD),
                          Wrap(
                            spacing: spacingSM,
                            runSpacing: spacingSM,
                            children: <Widget>[
                              MetricPill(
                                label: 'OVR',
                                value: '${listing.player.rating}',
                                highlight: true,
                              ),
                              MetricPill(
                                label: 'Potential',
                                value: '${listing.player.potential}',
                              ),
                              MetricPill(
                                label: 'Timer',
                                value: formatBidCountdown(
                                  listing.secondsRemaining,
                                ),
                                highlight: listing.secondsRemaining <= 15,
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: spacingLG),
                LayoutBuilder(
                  builder: (BuildContext context, BoxConstraints constraints) {
                    final bool stacked = constraints.maxWidth < 720;
                    final Widget bidSummary = _BidSummaryCard(
                      title: 'Current Bid',
                      value: AppFormatters.money(listing.currentBidInMillions),
                      caption:
                          'Minimum next bid ${AppFormatters.money(minimumBid)}',
                      color: AppColors.primary,
                    );
                    final Widget leaderSummary = _BidSummaryCard(
                      title: 'Highest Bidder',
                      value: listing.leadingBidder.clubName,
                      caption:
                          listing.userIsHighestBidder
                              ? 'GTEX is leading this race.'
                              : 'Rival club pressure is active.',
                      color:
                          listing.userIsHighestBidder
                              ? AppColors.primary
                              : AppColors.gold,
                    );

                    if (stacked) {
                      return Column(
                        children: <Widget>[
                          bidSummary,
                          const SizedBox(height: spacingMD),
                          leaderSummary,
                        ],
                      );
                    }

                    return Row(
                      children: <Widget>[
                        Expanded(child: bidSummary),
                        const SizedBox(width: spacingMD),
                        Expanded(child: leaderSummary),
                      ],
                    );
                  },
                ),
                const SizedBox(height: spacingLG),
                Text(
                  'Place Bid',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: spacingSM),
                Text(
                  'Stay above the market floor and force rival clubs to respond in real time.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
                const SizedBox(height: spacingMD),
                AppShake(
                  trigger: _inputErrorCount,
                  child: TextField(
                    key: const Key('transfer-bid-input'),
                    controller: _bidController,
                    focusNode: _bidFocusNode,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    inputFormatters: <TextInputFormatter>[
                      FilteringTextInputFormatter.allow(RegExp(r'[0-9.]')),
                    ],
                    decoration: InputDecoration(
                      labelText: 'Bid amount (millions)',
                      prefixText: '\$',
                      suffixText: 'M',
                      helperText:
                          'Suggested minimum ${AppFormatters.money(minimumBid)}',
                    ),
                  ),
                ),
                const SizedBox(height: spacingMD),
                SizedBox(
                  width: double.infinity,
                  child: AppPressScale(
                    child: FilledButton.icon(
                      key: const Key('transfer-place-bid'),
                      onPressed: () => _placeBid(listing),
                      icon: const Icon(Icons.gavel_rounded),
                      label: const Text('Place Bid'),
                    ),
                  ),
                ),
                const SizedBox(height: spacingLG),
                Text(
                  'Bid Activity',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: spacingMD),
                ...recentBids.map(
                  (MarketBidEntry entry) => Padding(
                    padding: const EdgeInsets.only(bottom: spacingSM),
                    child: _BidHistoryTile(
                      entry: entry,
                      isLeading:
                          entry.amountInMillions ==
                              listing.leadingBidder.amountInMillions &&
                          entry.clubName == listing.leadingBidder.clubName &&
                          entry.tick == listing.leadingBidder.tick,
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _BidSummaryCard extends StatelessWidget {
  const _BidSummaryCard({
    required this.title,
    required this.value,
    required this.caption,
    required this.color,
  });

  final String title;
  final String value;
  final String caption;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: AppMotion.medium,
      curve: AppMotion.easeOut,
      padding: const EdgeInsets.all(spacingMD),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(cardRadius),
        border: Border.all(color: color.withValues(alpha: 0.32)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: spacingSM),
          Text(
            value,
            style: Theme.of(
              context,
            ).textTheme.headlineSmall?.copyWith(color: color),
          ),
          const SizedBox(height: spacingSM),
          Text(
            caption,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }
}

class _BidHistoryTile extends StatelessWidget {
  const _BidHistoryTile({required this.entry, required this.isLeading});

  final MarketBidEntry entry;
  final bool isLeading;

  @override
  Widget build(BuildContext context) {
    final Color accent =
        entry.isUser
            ? AppColors.primary
            : isLeading
            ? AppColors.gold
            : AppColors.textSecondary;

    return AnimatedContainer(
      duration: AppMotion.medium,
      curve: AppMotion.easeOut,
      padding: const EdgeInsets.all(spacingMD),
      decoration: BoxDecoration(
        color:
            entry.isUser
                ? AppColors.primary.withValues(alpha: 0.12)
                : isLeading
                ? AppColors.gold.withValues(alpha: 0.1)
                : AppColors.surfaceMuted.withValues(alpha: 0.75),
        borderRadius: BorderRadius.circular(cardRadius),
        border: Border.all(
          color:
              entry.isUser
                  ? AppColors.primary.withValues(alpha: 0.34)
                  : isLeading
                  ? AppColors.gold.withValues(alpha: 0.26)
                  : AppColors.divider,
        ),
      ),
      child: Row(
        children: <Widget>[
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: accent.withValues(alpha: 0.14),
            ),
            child: Icon(
              entry.isUser ? Icons.shield_rounded : Icons.flag_rounded,
              color: accent,
              size: 20,
            ),
          ),
          const SizedBox(width: spacingMD),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  entry.clubName,
                  style: Theme.of(
                    context,
                  ).textTheme.titleLarge?.copyWith(color: accent),
                ),
                const SizedBox(height: spacingXS),
                Text(
                  entry.isUser
                      ? 'GTEX pushed a new offer into the live market.'
                      : isLeading
                      ? 'Current highest bidder.'
                      : 'Rival club remains in contention.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
          const SizedBox(width: spacingSM),
          Text(
            AppFormatters.money(entry.amountInMillions),
            style: Theme.of(context).textTheme.titleLarge,
          ),
        ],
      ),
    );
  }
}

class _MetaBlock extends StatelessWidget {
  const _MetaBlock({required this.label, required this.child});

  final String label;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(spacingSM),
      decoration: BoxDecoration(
        color: AppColors.background.withValues(alpha: 0.45),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: spacingXS),
          child,
        ],
      ),
    );
  }
}

class _PlayerAvatar extends StatelessWidget {
  const _PlayerAvatar({required this.imageAsset, this.size = 64});

  final String imageAsset;
  final double size;

  @override
  Widget build(BuildContext context) {
    return PlayerCardAvatar(avatar: null, imageUrl: imageAsset, size: size);
  }
}

class _AnimatedValueText extends StatelessWidget {
  const _AnimatedValueText({
    required this.keyValue,
    required this.text,
    required this.style,
    this.flashColor,
  });

  final String keyValue;
  final String text;
  final TextStyle? style;
  final Color? flashColor;

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      key: ValueKey<String>(keyValue),
      tween: Tween<double>(begin: 0, end: 1),
      duration: AppMotion.slow,
      curve: flashColor == null ? AppMotion.easeOut : AppMotion.elasticOut,
      builder: (BuildContext context, double value, Widget? child) {
        final double progress = value.clamp(0, 1).toDouble();
        final double pulse = flashColor == null ? 0 : (1 - progress) * 0.08;
        final List<Shadow>? shadows =
            flashColor == null
                ? style?.shadows
                : <Shadow>[
                  Shadow(
                    color: flashColor!.withValues(alpha: 0.42 * (1 - progress)),
                    blurRadius: 16 + ((1 - progress) * 8),
                  ),
                ];

        return Transform.scale(
          scale: 1 + pulse,
          child: Opacity(
            opacity: 0.72 + (progress * 0.28),
            child: Text(text, style: style?.copyWith(shadows: shadows)),
          ),
        );
      },
    );
  }
}

class _LiveStatusPill extends StatelessWidget {
  const _LiveStatusPill({
    required this.label,
    required this.color,
    required this.icon,
  });

  final String label;
  final Color color;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: spacingSM,
        vertical: spacingXS,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.32)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(icon, size: 14, color: color),
          const SizedBox(width: spacingXS),
          Text(
            label,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: color),
          ),
        ],
      ),
    );
  }
}
