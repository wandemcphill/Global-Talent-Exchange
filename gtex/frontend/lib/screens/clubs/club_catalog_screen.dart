import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/models/club_catalog_models.dart';
import 'package:gte_frontend/screens/clubs/club_purchase_history_screen.dart';
import 'package:gte_frontend/widgets/clubs/catalog_item_card.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ClubCatalogScreen extends StatelessWidget {
  const ClubCatalogScreen({
    super.key,
    required this.controller,
  });

  final ClubController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (BuildContext context, _) {
        return Container(
          decoration: gteBackdropDecoration(),
          child: Scaffold(
            backgroundColor: Colors.transparent,
            appBar: AppBar(
              title: const Text('Cosmetic catalog'),
              actions: <Widget>[
                IconButton(
                  onPressed: () => Navigator.of(context).push<void>(
                    MaterialPageRoute<void>(
                      builder: (BuildContext context) =>
                          ClubPurchaseHistoryScreen(controller: controller),
                    ),
                  ),
                  icon: const Icon(Icons.receipt_long_outlined),
                ),
              ],
            ),
            body: controller.catalog.isEmpty
                ? const Padding(
                    padding: EdgeInsets.all(20),
                    child: GteStatePanel(
                      title: 'Catalog unavailable',
                      message:
                          'Cosmetic catalog data will appear here when the club profile is loaded.',
                      icon: Icons.storefront_outlined,
                    ),
                  )
                : ListView(
                    padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                    children: <Widget>[
                      GteSurfacePanel(
                        emphasized: true,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(
                              'Transparent cosmetic catalog',
                              style: Theme.of(context).textTheme.headlineSmall,
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Every purchase shows a fixed price, a clear cosmetic outcome, and equipped versus owned status.',
                              style: Theme.of(context).textTheme.bodyMedium,
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 18),
                      Wrap(
                        spacing: 10,
                        runSpacing: 10,
                        children: controller.catalogCategories.map((category) {
                          return ChoiceChip(
                            label: Text(category),
                            selected: controller.catalogCategory == category,
                            onSelected: (_) => controller.setCatalogCategory(category),
                          );
                        }).toList(growable: false),
                      ),
                      const SizedBox(height: 18),
                      ...controller.filteredCatalog.map(
                        (ClubCatalogItem item) => Padding(
                          padding: const EdgeInsets.only(bottom: 14),
                          child: CatalogItemCard(
                            item: item,
                            busy: controller.isProcessingCatalog,
                            onDetails: () => _showDetails(context, item),
                            onPurchase: () => _confirmPurchase(context, item),
                            onEquip: () => controller.equipCatalogItem(item),
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

  Future<void> _showDetails(BuildContext context, ClubCatalogItem item) {
    return showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (BuildContext context) {
        return Padding(
          padding: const EdgeInsets.all(16),
          child: GteSurfacePanel(
            emphasized: true,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  item.title,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 10),
                Text(
                  item.description,
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
                const SizedBox(height: 10),
                Text(
                  item.transparencyNote,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _confirmPurchase(BuildContext context, ClubCatalogItem item) async {
    final bool? confirmed = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Purchase confirmation'),
          content: Text(
            'Purchase ${item.title} for ${item.priceCredits.toStringAsFixed(0)} credits?\n\n${item.transparencyNote}',
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Confirm purchase'),
            ),
          ],
        );
      },
    );
    if (confirmed == true) {
      await controller.purchaseCatalogItem(item);
    }
  }
}
