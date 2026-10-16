import 'package:flutter/material.dart';

import '../../data/jackpot_admin_api.dart';
import '../../features/admin_command_redesign/widgets/gtex_admin_visuals.dart';
import '../../features/admin_command_redesign/widgets/gtex_jackpot_admin_panel.dart';

class GtexAdminJackpotScreenV2 extends StatelessWidget {
  const GtexAdminJackpotScreenV2({super.key, this.api});

  /// Live admin jackpot client. Null fails closed inside the panel.
  final JackpotAdminApi? api;

  @override
  Widget build(BuildContext context) {
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
            children: <Widget>[
              GtexAdminPanel(
                child: Row(
                  children: <Widget>[
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            'Jackpot admin',
                            style: Theme.of(context).textTheme.headlineMedium
                                ?.copyWith(fontWeight: FontWeight.w900),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            api == null
                                ? 'Authenticated admin jackpot API required for live pool controls.'
                                : 'Monitor the live pool, edit runtime settings, set balance, trigger settlement, and review winner history.',
                            style: const TextStyle(color: Colors.white70),
                          ),
                        ],
                      ),
                    ),
                    GtexAdminStatusPill(
                      label: api == null ? 'API required' : 'Live',
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              GtexJackpotAdminPanel(api: api),
              const SizedBox(height: 16),
              const GtexAdminPanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    GtexAdminSectionHeader(
                      title: 'Operator notes',
                      subtitle:
                          'Manual trigger settles the current round immediately. There is no separate create-pool or claim-approval route — payouts settle through the runtime.',
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
