import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/club_finance_models.dart';
import 'package:gte_frontend/screens/clubs/club_ops_screen_host.dart';
import 'package:gte_frontend/widgets/clubs/budget_breakdown_card.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

class ClubBudgetScreen extends StatelessWidget {
  const ClubBudgetScreen({
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
      title: 'Operating budget',
      subtitle: 'Category breakdowns across spend, income, and development support.',
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
              title: 'Loading budget view',
              message: 'Collecting category breakdowns for the operating plan.',
              icon: Icons.pie_chart_outline,
            ),
          );
        }
        final ClubFinanceSnapshot finance = controller.finance!;
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          children: <Widget>[
            BudgetBreakdownCard(
              title: 'Budget allocation',
              subtitle: 'Planned annual operating spend.',
              items: finance.budgetAllocations,
            ),
            const SizedBox(height: 16),
            BudgetBreakdownCard(
              title: 'Income mix',
              subtitle: 'Transparent monthly revenue sources.',
              items: finance.incomeBreakdown,
            ),
            const SizedBox(height: 16),
            BudgetBreakdownCard(
              title: 'Expense mix',
              subtitle: 'Monthly outgoings across football and commercial delivery.',
              items: finance.expenseBreakdown,
            ),
          ],
        );
      },
    );
  }
}
