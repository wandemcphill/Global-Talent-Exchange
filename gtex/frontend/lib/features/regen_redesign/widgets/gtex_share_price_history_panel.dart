import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../data/gtex_share_market_api.dart';

const List<String> _ranges = <String>['7d', '30d', 'all'];

/// Share price movement for one player, from
/// `GET /players/{id}/shares/price-history` (share events + daily closes).
class GtexSharePriceHistoryPanel extends StatefulWidget {
  const GtexSharePriceHistoryPanel({
    super.key,
    required this.reader,
    required this.playerId,
  });

  final GtexShareMarketReader reader;
  final String playerId;

  @override
  State<GtexSharePriceHistoryPanel> createState() =>
      _GtexSharePriceHistoryPanelState();
}

class _GtexSharePriceHistoryPanelState
    extends State<GtexSharePriceHistoryPanel> {
  String _range = '30d';
  late Future<GtexSharePriceHistory> _future;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(GtexSharePriceHistoryPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.playerId != widget.playerId) {
      _load();
    }
  }

  void _load() {
    _future = widget.reader.fetchPriceHistory(widget.playerId, range: _range);
  }

  void _setRange(String range) {
    setState(() {
      _range = range;
      _load();
    });
  }

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      key: const Key('gtex-price-history-panel'),
      title: 'Price history',
      subtitle: 'Share price in GTX',
      accent: GtexColors.cyan,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Wrap(
            spacing: 6,
            children: _ranges
                .map(
                  (String r) => ChoiceChip(
                    key: Key('gtex-price-history-range-$r'),
                    label: Text(r.toUpperCase()),
                    selected: _range == r,
                    onSelected: (_) => _setRange(r),
                    selectedColor: GtexColors.cyan.withValues(alpha: 0.24),
                    backgroundColor: GtexColors.panelStrong,
                    labelStyle: TextStyle(
                      color:
                          _range == r
                              ? GtexColors.text
                              : GtexColors.textSecondary,
                      fontWeight: FontWeight.w800,
                      fontSize: 11,
                    ),
                  ),
                )
                .toList(growable: false),
          ),
          const SizedBox(height: GtexSpacing.sm),
          FutureBuilder<GtexSharePriceHistory>(
            future: _future,
            builder: (
              BuildContext context,
              AsyncSnapshot<GtexSharePriceHistory> snapshot,
            ) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const GtexSkeleton.box(height: 140);
              }
              final Object? error = snapshot.error;
              if (error is GteApiException && error.statusCode == 404) {
                return const _Note(
                  key: Key('gtex-price-history-no-market'),
                  text: 'This player has no issued share market yet.',
                );
              }
              if (error != null || !snapshot.hasData) {
                return GtexBlockedState(
                  title: 'Price history unavailable',
                  reason: '${error ?? 'no response'}',
                  severity: GtexBlockedSeverity.warning,
                  icon: Icons.cloud_off_rounded,
                  ctaLabel: 'Retry',
                  ctaAction: () => setState(_load),
                );
              }
              return _HistoryBody(history: snapshot.data!);
            },
          ),
        ],
      ),
    );
  }
}

class _HistoryBody extends StatelessWidget {
  const _HistoryBody({required this.history});

  final GtexSharePriceHistory history;

  @override
  Widget build(BuildContext context) {
    final double change = history.changePct;
    final Color tone =
        change > 0
            ? GtexColors.pitch
            : change < 0
            ? GtexColors.red
            : GtexColors.textSecondary;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Text(
              '${change > 0 ? '+' : ''}${change.toStringAsFixed(2)}%',
              key: const Key('gtex-price-history-change'),
              style: TextStyle(color: tone, fontWeight: FontWeight.w900),
            ),
            const SizedBox(width: GtexSpacing.sm),
            Expanded(
              child: Text(
                'H ${history.highPrice.toStringAsFixed(4)} · '
                'L ${history.lowPrice.toStringAsFixed(4)} · '
                '${history.tradeCount} trades',
                key: const Key('gtex-price-history-meta'),
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: GtexColors.textMuted,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.sm),
        SizedBox(
          key: const Key('gtex-price-history-chart'),
          height: 140,
          child: _PriceLine(points: history.points, color: tone),
        ),
        if (history.tradeCount == 0)
          const _Note(
            key: Key('gtex-price-history-untraded'),
            text: 'No trades yet. Daily closes are recorded from here on.',
          ),
      ],
    );
  }
}

class _PriceLine extends StatelessWidget {
  const _PriceLine({required this.points, required this.color});

  final List<GtexSharePricePoint> points;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final List<FlSpot> spots = points
        .map(
          (GtexSharePricePoint p) =>
              FlSpot(p.at.millisecondsSinceEpoch.toDouble(), p.price),
        )
        .toList();
    if (spots.isEmpty) {
      return const _Note(text: 'No price points recorded.');
    }
    if (spots.length == 1) {
      spots.insert(0, FlSpot(spots.first.x - 86400000, spots.first.y));
    }
    final List<double> ys = spots.map((FlSpot s) => s.y).toList();
    final double low = ys.reduce((double a, double b) => a < b ? a : b);
    final double high = ys.reduce((double a, double b) => a > b ? a : b);
    final double pad =
        high == low ? (high.abs() * 0.05).clamp(0.0001, 1e9) : (high - low) * 0.15;
    final Color stroke = color == GtexColors.textSecondary ? GtexColors.cyan : color;
    return LineChart(
      LineChartData(
        minX: spots.first.x,
        maxX: spots.last.x,
        minY: low - pad,
        maxY: high + pad,
        gridData: const FlGridData(show: false),
        titlesData: const FlTitlesData(show: false),
        borderData: FlBorderData(show: false),
        lineTouchData: LineTouchData(
          touchTooltipData: LineTouchTooltipData(
            getTooltipItems:
                (List<LineBarSpot> touched) => touched
                    .map(
                      (LineBarSpot s) => LineTooltipItem(
                        '${s.y.toStringAsFixed(4)} GTX',
                        const TextStyle(
                          color: GtexColors.text,
                          fontWeight: FontWeight.w800,
                          fontSize: 11,
                        ),
                      ),
                    )
                    .toList(),
          ),
        ),
        lineBarsData: <LineChartBarData>[
          LineChartBarData(
            spots: spots,
            isStepLineChart: true,
            color: stroke,
            barWidth: 2,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              color: stroke.withValues(alpha: 0.16),
            ),
          ),
        ],
      ),
    );
  }
}

class _Note extends StatelessWidget {
  const _Note({super.key, required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: GtexSpacing.xs),
      child: Text(
        text,
        style: const TextStyle(
          color: GtexColors.textMuted,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
