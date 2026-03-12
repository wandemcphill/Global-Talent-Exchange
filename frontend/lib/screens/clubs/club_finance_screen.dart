import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/club_finance_models.dart';
import 'package:gte_frontend/screens/clubs/club_budget_screen.dart';
import 'package:gte_frontend/screens/clubs/club_cashflow_screen.dart';
import 'package:gte_frontend/screens/clubs/club_ops_screen_host.dart';
import 'package:gte_frontend/widgets/clubs/budget_breakdown_card.dart';
import 'package:gte_frontend/widgets/clubs/cashflow_trend_card.dart';
import 'package:gte_frontend/widgets/clubs/finance_summary_card.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_scaffold.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ClubFinanceScreen extends StatelessWidget {
  const ClubFinanceScreen({
    super.key,
    this.clubId = 'royal-lagos-fc',
    this.clubName,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.mode = GteBackendMode.liveThenFixture,
    this.api,
    this.controller,
  });

  final String clubId;
  final String? clubName;
  final String baseUrl;
  final GteBackendMode mode;
  final ClubOpsApi? api;
  final ClubOpsController? controller;

  @override
  Widget build(BuildContext context) {
    return ClubOpsScreenHost(
      title: 'Club finances',
      subtitle: 'Operating budget, ledger movement, and cash planning.',
      clubId: clubId,
      clubName: clubName,
      baseUrl: baseUrl,
      mode: mode,
      api: api,
      controller: controller,
      builder: (BuildContext context, ClubOpsController controller) {
        if (controller.isLoadingClubData && !controller.hasClubData) {
          return const Padding(
            padding: EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Loading club finances',
              message: 'Preparing balance summary, budget allocation, and recent ledger movement.',
              icon: Icons.account_balance_outlined,
            ),
          );
        }
        if (controller.clubErrorMessage != null && !controller.hasClubData) {
          return Padding(
            padding: const EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Club finances unavailable',
              message: controller.clubErrorMessage!,
              actionLabel: 'Retry',
              onAction: controller.refreshClubData,
              icon: Icons.error_outline,
            ),
          );
        }

        final ClubFinanceSnapshot finance = controller.finance!;
        return RefreshIndicator(
          onRefresh: controller.refreshClubData,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
            children: <Widget>[
              FinanceSummaryCard(finance: finance),
              const SizedBox(height: 16),
              ClubOpsSectionHeader(
                title: 'Planning views',
                subtitle: 'Move between budget allocation and day-to-day cash movement.',
                action: Wrap(
                  spacing: 8,
                  children: <Widget>[
                    FilledButton.tonal(
                      onPressed: () => Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (BuildContext context) => ClubBudgetScreen(
                            controller: controller,
                            clubId: clubId,
                            clubName: clubName,
                          ),
                        ),
                      ),
                      child: const Text('Budget'),
                    ),
                    FilledButton.tonal(
                      onPressed: () => Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (BuildContext context) => ClubCashflowScreen(
                            controller: controller,
                            clubId: clubId,
                            clubName: clubName,
                          ),
                        ),
                      ),
                      child: const Text('Cashflow'),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              BudgetBreakdownCard(
                title: 'Operating budget',
                subtitle: 'Planned spend stays weighted toward payroll, pathway support, and facilities.',
                items: finance.budgetAllocations,
              ),
              const SizedBox(height: 16),
              CashflowTrendCard(
                title: 'Recent cashflow',
                subtitle: 'Monthly inflow and outflow are shown as transparent operating movement.',
                cashflow: finance.cashflow,
              ),
              const SizedBox(height: 16),
              GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text('Finance notes',
                        style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 12),
                    for (final String note in finance.financeNotes) ...<Widget>[
                      Text(note, style: Theme.of(context).textTheme.bodyMedium),
                      if (note != finance.financeNotes.last)
                        const SizedBox(height: 8),
                    ],
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
