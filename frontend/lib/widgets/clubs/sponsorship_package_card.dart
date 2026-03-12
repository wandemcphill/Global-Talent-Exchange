import 'package:flutter/material.dart';
import 'package:gte_frontend/models/sponsorship_models.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_formatters.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class SponsorshipPackageCard extends StatelessWidget {
  const SponsorshipPackageCard({
    super.key,
    required this.package,
    this.onOpen,
  });

  final SponsorshipPackage package;
  final VoidCallback? onOpen;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: package.isFeatured,
      onTap: onOpen,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(package.name, style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 6),
                    Text(package.tierLabel, style: Theme.of(context).textTheme.bodyMedium),
                  ],
                ),
              ),
              Text(
                clubOpsFormatCurrency(package.value),
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(package.description, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 12),
          Text(
            '${package.durationMonths} months · ${package.assetCount} asset slots',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 6),
          Text(package.inventorySummary, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: package.deliverables
                .map((String item) => Chip(label: Text(item)))
                .toList(growable: false),
          ),
        ],
      ),
    );
  }
}
