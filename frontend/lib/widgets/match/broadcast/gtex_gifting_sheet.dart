import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../../data/match_gift_api.dart';
import '../../../ui_gtex/ui_gtex.dart';

typedef MatchGiftSelectionHandler =
    Future<void> Function(MatchGiftCatalogItem gift);
typedef MatchGiftCatalogLoader = Future<List<MatchGiftCatalogItem>> Function();

/// Premium live gifting picker. Prices and unlock status always come from the
/// canonical gift catalogue when [catalogLoader] is provided.
class GtexGiftingSheet extends StatefulWidget {
  const GtexGiftingSheet({
    super.key,
    required this.onSelected,
    this.unitLabel = 'Fan Coin',
    this.recipientLabel = 'the recipient',
    this.catalogLoader,
  });

  final MatchGiftSelectionHandler onSelected;
  final String unitLabel;
  final String recipientLabel;
  final MatchGiftCatalogLoader? catalogLoader;

  static Future<void> show(
    BuildContext context, {
    required MatchGiftSelectionHandler onSelected,
    String unitLabel = 'Fan Coin',
    String recipientLabel = 'the recipient',
    MatchGiftCatalogLoader? catalogLoader,
  }) {
    return showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      useSafeArea: true,
      enableDrag: true,
      builder: (BuildContext context) => GtexGiftingSheet(
        onSelected: onSelected,
        unitLabel: unitLabel,
        recipientLabel: recipientLabel,
        catalogLoader: catalogLoader,
      ),
    );
  }

  @override
  State<GtexGiftingSheet> createState() => _GtexGiftingSheetState();
}

class _GtexGiftingSheetState extends State<GtexGiftingSheet> {
  late Future<List<MatchGiftCatalogItem>> _catalogFuture;
  MatchGiftCatalogItem? _selected;
  String _rarityFilter = 'all';
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    _catalogFuture = _loadCatalog();
  }

  Future<List<MatchGiftCatalogItem>> _loadCatalog() async {
    final MatchGiftCatalogLoader? loader = widget.catalogLoader;
    if (loader == null) return kMatchGiftCatalog;
    try {
      final List<MatchGiftCatalogItem> items = await loader();
      final List<MatchGiftCatalogItem> usable = items
          .where((MatchGiftCatalogItem gift) => gift.key.isNotEmpty)
          .toList(growable: false);
      return usable.isEmpty ? kMatchGiftCatalog : usable;
    } catch (_) {
      // The picker remains usable during a temporary catalogue outage; send
      // attempts still go through the server's canonical validation.
      return kMatchGiftCatalog;
    }
  }

  List<MatchGiftCatalogItem> _filtered(List<MatchGiftCatalogItem> items) {
    if (_rarityFilter == 'all') return items;
    return items.where((MatchGiftCatalogItem gift) {
      final String rarity = gift.rarity.trim().toLowerCase();
      return rarity == _rarityFilter;
    }).toList(growable: false);
  }

  Future<void> _send(MatchGiftCatalogItem gift) async {
    if (_sending || gift.requiresReview) return;
    setState(() => _sending = true);
    Navigator.of(context).pop();
    await widget.onSelected(gift);
  }

  @override
  Widget build(BuildContext context) {
    final double height = MediaQuery.sizeOf(context).height;
    final Color gold = GtexColors.gold;
    return Container(
      height: math.min(height * 0.90, 820.0).toDouble(),
      decoration: BoxDecoration(
        color: const Color(0xFF080F1B),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(30)),
        border: Border.all(color: gold.withValues(alpha: 0.32)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: gold.withValues(alpha: 0.12),
            blurRadius: 34,
            spreadRadius: 1,
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: FutureBuilder<List<MatchGiftCatalogItem>>(
          future: _catalogFuture,
          builder: (BuildContext context, AsyncSnapshot<List<MatchGiftCatalogItem>> snapshot) {
            final List<MatchGiftCatalogItem> catalog =
                snapshot.data ?? kMatchGiftCatalog;
            final MatchGiftCatalogItem? firstSendable = catalog.isEmpty
                ? null
                : catalog.firstWhere(
                    (MatchGiftCatalogItem gift) => !gift.requiresReview,
                    orElse: () => catalog.first,
                  );
            final MatchGiftCatalogItem? selected = _selected ?? firstSendable;
            final List<MatchGiftCatalogItem> gifts = _filtered(catalog);
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                Center(
                  child: Container(
                    width: 44,
                    height: 4,
                    margin: const EdgeInsets.only(top: 10, bottom: 14),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.24),
                      borderRadius: BorderRadius.circular(9),
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 0, 20, 14),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Container(
                        width: 54,
                        height: 54,
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            colors: <Color>[
                              gold.withValues(alpha: 0.30),
                              const Color(0xFF17243A),
                            ],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ),
                          borderRadius: BorderRadius.circular(18),
                          border: Border.all(color: gold.withValues(alpha: 0.58)),
                        ),
                        child: Icon(Icons.card_giftcard_rounded, color: gold, size: 28),
                      ),
                      const SizedBox(width: 13),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            const Text(
                              'THE GIFT LOUNGE',
                              style: TextStyle(
                                color: Color(0xFFE8C979),
                                fontSize: 10,
                                letterSpacing: 2.4,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Make the moment legendary',
                              maxLines: 2,
                              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                color: Colors.white,
                                fontWeight: FontWeight.w900,
                                height: 1.08,
                              ),
                            ),
                            const SizedBox(height: 5),
                            Text(
                              'Sending to ${widget.recipientLabel}',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(color: Color(0xFFAAB7CA), fontSize: 12),
                            ),
                            const SizedBox(height: 3),
                            Text(
                              'Wallet context · ${widget.unitLabel}',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(color: Color(0xFF7F90A7), fontSize: 10),
                            ),
                          ],
                        ),
                      ),
                      IconButton(
                        tooltip: 'Close gift picker',
                        onPressed: () => Navigator.of(context).pop(),
                        icon: const Icon(Icons.close_rounded, color: Colors.white70),
                      ),
                    ],
                  ),
                ),
                SizedBox(
                  height: 40,
                  child: ListView(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    scrollDirection: Axis.horizontal,
                    children: <Widget>[
                      for (final String rarity in <String>[
                        'all', 'common', 'rare', 'epic', 'legendary', 'mythic',
                      ])
                        Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: ChoiceChip(
                            key: Key('gift-filter-$rarity'),
                            label: Text(rarity == 'all' ? 'All gifts' : _title(rarity)),
                            selected: _rarityFilter == rarity,
                            onSelected: (_) => setState(() => _rarityFilter = rarity),
                            selectedColor: gold.withValues(alpha: 0.25),
                            backgroundColor: const Color(0xFF111D2D),
                            labelStyle: TextStyle(
                              color: _rarityFilter == rarity ? gold : const Color(0xFFB6C2D4),
                              fontWeight: FontWeight.w800,
                              fontSize: 11,
                            ),
                            side: BorderSide(
                              color: _rarityFilter == rarity
                                  ? gold.withValues(alpha: 0.8)
                                  : Colors.white.withValues(alpha: 0.08),
                            ),
                            showCheckmark: false,
                          ),
                        ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                if (snapshot.connectionState != ConnectionState.done)
                  const LinearProgressIndicator(minHeight: 2)
                else
                  const SizedBox(height: 2),
                Expanded(
                  child: GridView.builder(
                    key: const Key('gtex-gift-catalog-grid'),
                    padding: const EdgeInsets.fromLTRB(16, 10, 16, 14),
                    itemCount: gifts.length,
                    gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                      maxCrossAxisExtent: 230,
                      mainAxisExtent: 158,
                      crossAxisSpacing: 10,
                      mainAxisSpacing: 10,
                    ),
                    itemBuilder: (BuildContext context, int index) {
                      final MatchGiftCatalogItem gift = gifts[index];
                      return _GiftCard(
                        gift: gift,
                        selected: selected?.key == gift.key,
                        onTap: () => setState(() => _selected = gift),
                      );
                    },
                  ),
                ),
                if (selected != null)
                  Container(
                    padding: const EdgeInsets.fromLTRB(18, 12, 18, 16),
                    decoration: BoxDecoration(
                      color: const Color(0xFF101B2C),
                      border: Border(top: BorderSide(color: gold.withValues(alpha: 0.18))),
                    ),
                    child: Row(
                      children: <Widget>[
                        _GiftGlyph(gift: selected, size: 50),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisSize: MainAxisSize.min,
                            children: <Widget>[
                              Text(
                                selected.label,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900),
                              ),
                              const SizedBox(height: 3),
                              Text(
                                selected.priceLabel,
                                style: TextStyle(color: _rarityColor(selected.rarity), fontWeight: FontWeight.w800),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 8),
                        FilledButton.icon(
                          key: const Key('gtex-gift-send-button'),
                          onPressed: _sending || selected.requiresReview ? null : () => _send(selected),
                          style: FilledButton.styleFrom(
                            backgroundColor: gold,
                            foregroundColor: const Color(0xFF16120A),
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                          ),
                          icon: const Icon(Icons.send_rounded, size: 17),
                          label: Text(selected.requiresReview ? 'Under review' : 'Send gift'),
                        ),
                      ],
                    ),
                  ),
                if (selected?.requiresReview == true)
                  const Padding(
                    padding: EdgeInsets.fromLTRB(20, 0, 20, 10),
                    child: Text(
                      'This item is not available for sending until GTEX completes its review.',
                      style: TextStyle(color: Color(0xFFFFC66D), fontSize: 11),
                    ),
                  ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _GiftCard extends StatelessWidget {
  const _GiftCard({required this.gift, required this.selected, required this.onTap});

  final MatchGiftCatalogItem gift;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final Color accent = _rarityColor(gift.rarity);
    return Semantics(
      button: true,
      selected: selected,
      label: '${gift.label}, ${gift.priceLabel}, ${gift.rarity}',
      child: InkWell(
        key: Key('gtex-gift-card-${gift.key}'),
        onTap: onTap,
        borderRadius: BorderRadius.circular(18),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOutCubic,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[
                accent.withValues(alpha: selected ? 0.22 : 0.10),
                const Color(0xFF101B2B),
                const Color(0xFF0B1321),
              ],
            ),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(
              color: selected ? accent : accent.withValues(alpha: 0.34),
              width: selected ? 1.8 : 1,
            ),
            boxShadow: selected
                ? <BoxShadow>[BoxShadow(color: accent.withValues(alpha: 0.13), blurRadius: 16)]
                : const <BoxShadow>[],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  _GiftGlyph(gift: gift, size: 43),
                  const Spacer(),
                  if (selected)
                    Icon(Icons.check_circle_rounded, color: accent, size: 19),
                ],
              ),
              const Spacer(),
              Text(
                gift.label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 12),
              ),
              const SizedBox(height: 3),
              Text(
                _title(gift.rarity),
                style: TextStyle(color: accent, fontSize: 9, fontWeight: FontWeight.w900, letterSpacing: 1.2),
              ),
              const SizedBox(height: 4),
              Row(
                children: <Widget>[
                  Expanded(
                    child: Text(
                      gift.priceLabel,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Color(0xFFE8DDBD), fontSize: 11, fontWeight: FontWeight.w800),
                    ),
                  ),
                  if (gift.requiresReview)
                    const Icon(Icons.lock_clock_rounded, size: 14, color: Color(0xFFFFC66D)),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _GiftGlyph extends StatelessWidget {
  const _GiftGlyph({required this.gift, this.size = 48});

  final MatchGiftCatalogItem gift;
  final double size;

  @override
  Widget build(BuildContext context) {
    final Color accent = _rarityColor(gift.rarity);
    return AnimatedContainer(
      duration: const Duration(milliseconds: 220),
      width: size,
      height: size,
      decoration: BoxDecoration(
        gradient: RadialGradient(
          colors: <Color>[accent.withValues(alpha: 0.25), const Color(0xFF121F32)],
        ),
        borderRadius: BorderRadius.circular(size * 0.32),
        border: Border.all(color: accent.withValues(alpha: 0.66)),
      ),
      child: Icon(_giftIconFor(gift.key), size: size * 0.52, color: accent),
    );
  }
}

String _title(String value) {
  final String normalized = value.replaceAll('_', ' ').trim();
  if (normalized.isEmpty) return 'Gift';
  return normalized.split(' ').map((String word) {
    if (word.isEmpty) return word;
    return '${word[0].toUpperCase()}${word.substring(1)}';
  }).join(' ');
}

Color _rarityColor(String rarity) {
  switch (rarity.trim().toLowerCase()) {
    case 'common':
      return const Color(0xFFB4C2D5);
    case 'rare':
      return const Color(0xFF69C7FF);
    case 'epic':
      return const Color(0xFFC29BFF);
    case 'legendary':
      return const Color(0xFFFFC96B);
    case 'mythic':
      return const Color(0xFFFF8EAB);
    default:
      return GtexColors.gold;
  }
}

IconData _giftIconFor(String key) {
  if (key.contains('whistle')) return Icons.sports;
  if (key.contains('chant')) return Icons.campaign_rounded;
  if (key.contains('goal') || key.contains('boot')) return Icons.sports_soccer_rounded;
  if (key.contains('legend') || key.contains('award') || key.contains('dor')) return Icons.workspace_premium_rounded;
  if (key.contains('tactic') || key.contains('midfield')) return Icons.auto_awesome_motion_rounded;
  if (key.contains('trainer') || key.contains('manager')) return Icons.sports_handball_rounded;
  if (key.contains('hands')) return Icons.back_hand_rounded;
  if (key.contains('player_of_the_match')) return Icons.stars_rounded;
  return Icons.card_giftcard_rounded;
}
