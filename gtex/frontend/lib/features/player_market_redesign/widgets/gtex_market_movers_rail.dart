import 'package:flutter/material.dart';

import '../../../data/gte_exchange_models.dart';
import '../../../ui_gtex/ui_gtex.dart';

/// The market's headline movement, straight from `GET /api/market/movers`.
///
/// Three lanes - risers, fallers, most traded - each a real list from the
/// pricing engine. When the backend has no movers yet the rail says so; it
/// never renders a "0.0%" placeholder (a fabricated zero was a proven P0
/// defect). Every row opens the canonical Player Detail.
///
/// The percentage each row carries is `day_change_percent`, which the pricing
/// engine computes against the *valuation* reference price - not against
/// `PlayerShareMarket.share_price_coin`. So the rail names it as a valuation
/// move: a bare percentage under a heading called "Market movers" reads as a
/// price move, and the tradable price is not what moved.
class GtexMarketMoversRail extends StatelessWidget {
  const GtexMarketMoversRail({
    super.key,
    required this.movers,
    required this.isLoading,
    required this.error,
    required this.onOpenPlayer,
  });

  final GteMarketMovers? movers;
  final bool isLoading;
  final String? error;
  final ValueChanged<String> onOpenPlayer;

  @override
  Widget build(BuildContext context) {
    final GteMarketMovers? data = movers;
    if (isLoading && data == null) {
      return const _MoversShell(
        child: LinearProgressIndicator(minHeight: 2),
      );
    }
    if (data == null || data.isEmpty) {
      return _MoversShell(
        child: Text(
          error != null
              ? 'Value movers are unavailable right now.'
              : 'Value movers will appear here once valuations move today.',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: GtexColors.textMuted,
            fontWeight: FontWeight.w700,
          ),
        ),
      );
    }
    return _MoversShell(
      child: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          final List<Widget> lanes = <Widget>[
            if (data.topGainers.isNotEmpty)
              _MoverLane(
                title: 'Risers',
                icon: Icons.trending_up,
                accent: GtexColors.pitch,
                items: data.topGainers,
                onOpenPlayer: onOpenPlayer,
              ),
            if (data.topLosers.isNotEmpty)
              _MoverLane(
                title: 'Fallers',
                icon: Icons.trending_down,
                accent: GtexColors.red,
                items: data.topLosers,
                onOpenPlayer: onOpenPlayer,
              ),
            if (data.mostTraded.isNotEmpty)
              _MoverLane(
                title: 'Most traded',
                icon: Icons.multiline_chart,
                accent: GtexColors.gold,
                items: data.mostTraded,
                onOpenPlayer: onOpenPlayer,
              ),
          ];
          final bool stack = constraints.maxWidth < 640;
          if (stack) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                for (int i = 0; i < lanes.length; i++) ...<Widget>[
                  if (i > 0) const SizedBox(height: GtexSpacing.sm),
                  lanes[i],
                ],
              ],
            );
          }
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              for (int i = 0; i < lanes.length; i++) ...<Widget>[
                if (i > 0) const SizedBox(width: GtexSpacing.md),
                Expanded(child: lanes[i]),
              ],
            ],
          );
        },
      ),
    );
  }
}

class _MoversShell extends StatelessWidget {
  const _MoversShell({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      title: 'Value movers',
      subtitle: 'Valuation movement from the pricing engine - not share price',
      accent: GtexColors.cyan,
      child: child,
    );
  }
}

class _MoverLane extends StatelessWidget {
  const _MoverLane({
    required this.title,
    required this.icon,
    required this.accent,
    required this.items,
    required this.onOpenPlayer,
  });

  final String title;
  final IconData icon;
  final Color accent;
  final List<GteMarketMoverItem> items;
  final ValueChanged<String> onOpenPlayer;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Row(
          children: <Widget>[
            Icon(icon, size: 15, color: accent),
            const SizedBox(width: GtexSpacing.xs),
            Text(
              title.toUpperCase(),
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: accent,
                fontWeight: FontWeight.w900,
                letterSpacing: 0.5,
              ),
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.xs),
        ...items.take(5).map(
          (GteMarketMoverItem item) =>
              _MoverRow(item: item, onTap: () => onOpenPlayer(item.playerId)),
        ),
      ],
    );
  }
}

class _MoverRow extends StatelessWidget {
  const _MoverRow({required this.item, required this.onTap});

  final GteMarketMoverItem item;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final Color changeColor = item.isUp
        ? GtexColors.pitch
        : item.isDown
        ? GtexColors.red
        : GtexColors.textMuted;
    final String sign = item.dayChangePercent > 0 ? '+' : '';
    return Semantics(
      button: true,
      label:
          'Open ${item.playerName}, value $sign'
          '${item.dayChangePercent.toStringAsFixed(1)} percent',
      child: InkWell(
        key: Key('gtex-mover-${item.playerId}'),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusSm),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 5),
          child: Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  item.playerName,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              const SizedBox(width: GtexSpacing.xs),
              Text(
                '$sign${item.dayChangePercent.toStringAsFixed(1)}%',
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: changeColor,
                  fontFamily: 'JetBrains Mono',
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
