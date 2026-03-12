import 'package:flutter/material.dart';
import 'package:gte_frontend/models/club_catalog_models.dart';
import 'package:gte_frontend/widgets/gte_formatters.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class CatalogItemCard extends StatelessWidget {
  const CatalogItemCard({
    super.key,
    required this.item,
    this.onDetails,
    this.onPurchase,
    this.onEquip,
    this.busy = false,
  });

  final ClubCatalogItem item;
  final VoidCallback? onDetails;
  final VoidCallback? onPurchase;
  final VoidCallback? onEquip;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    final Color tone = item.ownershipStatus == CatalogOwnershipStatus.equipped
        ? GteShellTheme.positive
        : item.ownershipStatus == CatalogOwnershipStatus.owned
            ? GteShellTheme.accent
            : GteShellTheme.accentWarm;
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  item.title,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(999),
                  color: tone.withValues(alpha: 0.12),
                  border: Border.all(color: tone.withValues(alpha: 0.3)),
                ),
                child: Text(
                  item.ownershipStatus.label,
                  style: Theme.of(context)
                      .textTheme
                      .labelLarge
                      ?.copyWith(color: tone),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(item.category, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 12),
          Text(item.description, style: Theme.of(context).textTheme.bodyLarge),
          const SizedBox(height: 12),
          Text(
            '${gteFormatCredits(item.priceCredits)} • ${item.previewLabel}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              OutlinedButton(
                onPressed: onDetails,
                child: const Text('Details'),
              ),
              if (item.canPurchase)
                FilledButton(
                  onPressed: busy ? null : onPurchase,
                  child: const Text('Purchase'),
                )
              else if (item.canEquip)
                FilledButton.tonal(
                  onPressed: busy ? null : onEquip,
                  child: const Text('Equip'),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
