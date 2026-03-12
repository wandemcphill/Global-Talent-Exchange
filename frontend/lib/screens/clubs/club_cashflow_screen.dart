import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/club_finance_models.dart';
import 'package:gte_frontend/screens/clubs/club_ops_screen_host.dart';
import 'package:gte_frontend/widgets/clubs/cashflow_trend_card.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_formatters.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ClubCashflowScreen extends StatelessWidget {
  const ClubCashflowScreen({
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
      title: 'Cashflow summary',
      subtitle: 'Operating movement and ledger detail.',
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
              title: 'Loading cashflow',
              message: 'Preparing monthly movement and ledger entries.',
              icon: Icons.show_chart_outlined,
            ),
          );
        }
        final ClubFinanceSnapshot finance = controller.finance!;
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          children: <Widget>[
            CashflowTrendCard(
              title: 'Cashflow trend',
              subtitle: 'Monthly net movement and closing balance.',
              cashflow: finance.cashflow,
            ),
            const SizedBox(height: 16),
            GteSurfacePanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Ledger', style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 16),
                  for (final LedgerEntry entry in finance.ledgerEntries) ...<Widget>[
                    _LedgerRow(entry: entry),
                    if (entry != finance.ledgerEntries.last)
                      const Divider(height: 22),
                  ],
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}

class _LedgerRow extends StatelessWidget {
  const _LedgerRow({
    required this.entry,
  });

  final LedgerEntry entry;

  @override
  Widget build(BuildContext context) {
    final bool income = entry.type == LedgerEntryType.income;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(entry.title, style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 4),
              Text(
                '${entry.category} · ${entry.counterparty} · ${clubOpsFormatDate(entry.occurredAt)}',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 4),
              Text(entry.note, style: Theme.of(context).textTheme.bodyMedium),
            ],
          ),
        ),
        const SizedBox(width: 12),
        Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: <Widget>[
            Text(
              clubOpsFormatSignedCurrency(income ? entry.amount : -entry.amount),
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 4),
            Text(
              'Balance ${clubOpsFormatCurrency(entry.runningBalance)}',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ],
    );
  }
}
