import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/widgets/clubs/purchase_summary_card.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

class ClubPurchaseHistoryScreen extends StatelessWidget {
  const ClubPurchaseHistoryScreen({
    super.key,
    required this.controller,
  });

  final ClubController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (BuildContext context, _) {
        final history = controller.purchaseHistory;
        return Container(
          decoration: gteBackdropDecoration(),
          child: Scaffold(
            backgroundColor: Colors.transparent,
            appBar: AppBar(
              title: const Text('Purchase history'),
            ),
            body: history.isEmpty
                ? const Padding(
                    padding: EdgeInsets.all(20),
                    child: GteStatePanel(
                      title: 'No cosmetic purchases yet',
                      message:
                          'Catalog purchases will appear here with transparent confirmation details and equipped status.',
                      icon: Icons.receipt_long_outlined,
                    ),
                  )
                : RefreshIndicator(
                    onRefresh: controller.refresh,
                    child: ListView.separated(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                      itemBuilder: (BuildContext context, int index) {
                        return PurchaseSummaryCard(record: history[index]);
                      },
                      separatorBuilder: (_, __) => const SizedBox(height: 14),
                      itemCount: history.length,
                    ),
                  ),
          ),
        );
      },
    );
  }
}
