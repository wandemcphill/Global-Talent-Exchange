import 'package:flutter/material.dart';

import '../../features/admin_command_redesign/models/gtex_admin_command_models.dart';
import '../../features/admin_command_redesign/widgets/gtex_admin_metric_grid.dart';
import '../../features/admin_command_redesign/widgets/gtex_admin_visuals.dart';
import '../../features/admin_command_redesign/widgets/gtex_coin_economy_panel.dart';

class GtexAdminCoinEconomyScreenV2 extends StatelessWidget {
  const GtexAdminCoinEconomyScreenV2({super.key});

  @override
  Widget build(BuildContext context) {
    final snapshot = GtexAdminCommandSnapshot.liveUnavailable();
    return Theme(
      data: Theme.of(context).copyWith(
        scaffoldBackgroundColor: const Color(0xFF070B12),
        textTheme: Theme.of(
          context,
        ).textTheme.apply(bodyColor: Colors.white, displayColor: Colors.white),
      ),
      child: Scaffold(
        backgroundColor: const Color(0xFF070B12),
        body: SafeArea(
          child: ListView(
            padding: const EdgeInsets.all(22),
            children: [
              GtexAdminPanel(
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Coin economy',
                            style: Theme.of(context).textTheme.headlineMedium
                                ?.copyWith(fontWeight: FontWeight.w900),
                          ),
                          const SizedBox(height: 6),
                          const Text(
                            'Treasury, user balances, top-ups, withdrawals, risk controls and ledger audits.',
                            style: TextStyle(color: Colors.white70),
                          ),
                        ],
                      ),
                    ),
                    const GtexAdminStatusPill(
                      label: 'Ledger critical',
                      severity: GtexAdminSeverity.watch,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              GtexAdminMetricGrid(metrics: snapshot.metrics),
              const SizedBox(height: 16),
              GtexCoinEconomyPanel(snapshot: snapshot.coinEconomy),
              const SizedBox(height: 16),
              const GtexAdminPanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    GtexAdminSectionHeader(
                      title: 'Coin control rules',
                      subtitle:
                          'Every balance-impacting action must go through ledger/audit APIs.',
                    ),
                    SizedBox(height: 12),
                    Text(
                      'Codex must not directly mutate displayed balances from the frontend. The frontend should request an admin action, backend validates permissions, writes a ledger record, and returns a new balance snapshot.',
                      style: TextStyle(color: Colors.white70, height: 1.45),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
