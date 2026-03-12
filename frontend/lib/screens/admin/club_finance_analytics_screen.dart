import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/screens/clubs/club_ops_screen_host.dart';
import 'package:gte_frontend/widgets/clubs/budget_breakdown_card.dart';
import 'package:gte_frontend/widgets/clubs/cashflow_trend_card.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_formatters.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ClubFinanceAnalyticsScreen extends StatelessWidget {
  const ClubFinanceAnalyticsScreen({
    super.key,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.mode = GteBackendMode.liveThenFixture,
    this.api,
    this.controller,
  });

  final String baseUrl;
  final GteBackendMode mode;
  final ClubOpsApi? api;
  final ClubOpsController? controller;

  @override
  Widget build(BuildContext context) {
    return ClubOpsScreenHost(
      title: 'Finance analytics',
      subtitle: 'Operating margin, category mix, and quarterly movement.',
      baseUrl: baseUrl,
      mode: mode,
      api: api,
      controller: controller,
      adminData: true,
      builder: (BuildContext context, ClubOpsController controller) {
        if (controller.isLoadingAdminData && !controller.hasAdminData) {
          return const Padding(
            padding: EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Loading finance analytics',
              message: 'Preparing margin, category mix, and quarterly cashflow.',
              icon: Icons.insights_outlined,
            ),
          );
        }
        final analytics = controller.financeAnalytics!;
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          children: <Widget>[
            GteSurfacePanel(
              emphasized: true,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(clubOpsFormatCurrency(analytics.averageMonthlyBalance),
                      style: Theme.of(context).textTheme.headlineSmall),
                  const SizedBox(height: 8),
                  Text(
                    '${analytics.operatingMarginPercent.toStringAsFixed(1)}% margin · ${analytics.revenueReliabilityLabel}',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            BudgetBreakdownCard(
              title: 'Category mix',
              items: analytics.categoryMix,
            ),
            const SizedBox(height: 16),
            CashflowTrendCard(
              title: 'Quarterly cashflow',
              cashflow: analytics.quarterlyCashflow,
            ),
          ],
        );
      },
    );
  }
}
