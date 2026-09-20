import 'package:flutter/material.dart';

import '../components/gtex_panel.dart';
import '../components/gtex_status_chip.dart';
import '../components/gtex_value_display.dart';
import '../models/gtex_freshness.dart';
import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';
import 'gtex_player_card.dart';

/// Wraps the canonical [GtexPlayerCard] with reusable ownership telemetry
/// badges, cost basis, valuation movement, and matchday context.
///
/// It strictly renders only the fields that are actually available in the
/// passed position or market profile, adhering to GTEX Truth in Design.
class GtexOwnershipTelemetryCard extends StatelessWidget {
  const GtexOwnershipTelemetryCard({
    super.key,
    required this.name,
    required this.position,
    required this.clubName,
    required this.nationality,
    required this.priceLabel,
    this.imageUrl,
    this.gsiLabel,
    this.gsiTierLabel,
    this.ratingLabel,
    this.ageLabel,
    this.countryCode,
    this.formResults = const <String>[],
    this.valueDeltaLabel,
    this.valuationLabel,
    this.valueState = GtexValueState.recent,
    this.sharesHeld,
    this.costBasisLabel,
    this.currentValueLabel,
    this.unrealizedPlLabel,
    this.unrealizedPlPercent,
    this.isInProfit,
    this.upcomingMatchLabel,
    this.ownershipStatusLabel,
    this.isWatchlisted = false,
    this.isOwned = false,
    this.isSelected = false,
    this.scale = GtexPlayerCardScale.compact,
    this.onTap,
    this.onToggleWatchlist,
    this.onBuyNow,
    this.buyNowLabel = 'Buy',
  });

  final String name;
  final String position;
  final String clubName;
  final String nationality;
  final String priceLabel;
  final String? imageUrl;
  final String? gsiLabel;
  final String? gsiTierLabel;
  final String? ratingLabel;
  final String? ageLabel;
  final String? countryCode;
  final List<String> formResults;
  final String? valueDeltaLabel;
  final String? valuationLabel;
  final GtexValueState valueState;

  // Telemetry fields
  final double? sharesHeld;
  final String? costBasisLabel;
  final String? currentValueLabel;
  final String? unrealizedPlLabel;
  final double? unrealizedPlPercent;
  final bool? isInProfit;
  final String? upcomingMatchLabel;
  final String? ownershipStatusLabel;
  final bool isWatchlisted;
  final bool isOwned;
  final bool isSelected;
  final GtexPlayerCardScale scale;

  final VoidCallback? onTap;
  final VoidCallback? onToggleWatchlist;
  final VoidCallback? onBuyNow;
  final String buyNowLabel;

  bool get _hasTelemetryBar =>
      sharesHeld != null ||
      costBasisLabel != null ||
      unrealizedPlLabel != null ||
      upcomingMatchLabel != null;

  @override
  Widget build(BuildContext context) {
    final Color plColor = isInProfit == true
        ? GtexColors.pitch
        : (isInProfit == false ? GtexColors.red : GtexColors.textMuted);

    return GtexPanel(
      accent: isOwned ? GtexColors.pitch : (isWatchlisted ? GtexColors.gold : GtexColors.surfaceBorder),
      padding: const EdgeInsets.all(GtexSpacing.xs),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          GtexPlayerCard(
            name: name,
            position: position,
            clubName: clubName,
            nationality: nationality,
            countryCode: countryCode,
            priceLabel: priceLabel,
            imageUrl: imageUrl,
            gsiLabel: gsiLabel,
            gsiTierLabel: gsiTierLabel,
            ratingLabel: ratingLabel,
            ageLabel: ageLabel,
            formResults: formResults,
            valueDeltaLabel: valueDeltaLabel,
            valuationLabel: valuationLabel,
            valueState: valueState,
            scale: scale,
            isOwned: isOwned,
            isSelected: isSelected,
            ownershipLabel: ownershipStatusLabel ??
                (sharesHeld != null && sharesHeld! > 0
                    ? '${sharesHeld == sharesHeld!.roundToDouble() ? sharesHeld!.toStringAsFixed(0) : sharesHeld!.toStringAsFixed(2)} shares owned'
                    : null),
            onTap: onTap,
            onAddToShortlist: onToggleWatchlist,
            onBuyNow: onBuyNow,
            buyNowLabel: buyNowLabel,
          ),
          if (_hasTelemetryBar) ...<Widget>[
            const SizedBox(height: GtexSpacing.xs),
            Container(
              padding: const EdgeInsets.all(GtexSpacing.xs),
              decoration: BoxDecoration(
                color: GtexColors.surfaceOverlay,
                borderRadius: BorderRadius.circular(GtexSpacing.radiusSm),
                border: Border.all(color: GtexColors.surfaceBorder),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Wrap(
                    spacing: GtexSpacing.md,
                    runSpacing: GtexSpacing.xs,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: <Widget>[
                      if (costBasisLabel != null)
                        _TelemetryStat(label: 'Avg Cost', value: costBasisLabel!),
                      if (currentValueLabel != null)
                        _TelemetryStat(
                          label: 'Hold Value',
                          value: currentValueLabel!,
                          valueColor: GtexColors.gold,
                        ),
                      if (unrealizedPlLabel != null)
                        _TelemetryStat(
                          label: 'Return',
                          value:
                              '$unrealizedPlLabel${unrealizedPlPercent != null ? ' (${unrealizedPlPercent! >= 0 ? '+' : ''}${unrealizedPlPercent!.toStringAsFixed(1)}%)' : ''}',
                          valueColor: plColor,
                        ),
                      if (upcomingMatchLabel != null)
                        GtexStatusChip(
                          label: 'MATCH: $upcomingMatchLabel',
                          color: GtexColors.cyan,
                          compact: true,
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _TelemetryStat extends StatelessWidget {
  const _TelemetryStat({
    required this.label,
    required this.value,
    this.valueColor,
  });

  final String label;
  final String value;
  final Color? valueColor;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Text(
          label.toUpperCase(),
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: GtexColors.textMuted,
                fontWeight: FontWeight.w800,
                fontSize: 9,
                letterSpacing: 0.4,
              ),
        ),
        Text(
          value,
          style: Theme.of(context).textTheme.labelMedium?.copyWith(
                color: valueColor ?? GtexColors.text,
                fontWeight: FontWeight.w900,
              ),
        ),
      ],
    );
  }
}
