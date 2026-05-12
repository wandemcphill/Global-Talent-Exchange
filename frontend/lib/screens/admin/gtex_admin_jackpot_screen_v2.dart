import 'package:flutter/material.dart';

import '../../features/admin_command_redesign/models/gtex_admin_command_models.dart';
import '../../features/admin_command_redesign/widgets/gtex_admin_visuals.dart';
import '../../features/admin_command_redesign/widgets/gtex_jackpot_admin_panel.dart';

class GtexAdminJackpotScreenV2 extends StatelessWidget {
  const GtexAdminJackpotScreenV2({super.key});

  @override
  Widget build(BuildContext context) {
    final snapshot = GtexAdminCommandSnapshot.demo();
    return Theme(
      data: Theme.of(context).copyWith(
        scaffoldBackgroundColor: const Color(0xFF070B12),
        textTheme: Theme.of(context).textTheme.apply(bodyColor: Colors.white, displayColor: Colors.white),
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
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('Jackpot admin', style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w900)),
                        const SizedBox(height: 6),
                        const Text('Create pools, monitor entries, review winners and approve claims.', style: TextStyle(color: Colors.white70)),
                      ]),
                    ),
                    const GtexAdminStatusPill(label: 'Restricted'),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              GtexJackpotAdminPanel(rounds: snapshot.jackpots),
              const SizedBox(height: 16),
              GtexAdminPanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const GtexAdminSectionHeader(
                      title: 'Winner verification checklist',
                      subtitle: 'Do not release winnings until fraud, KYC and wallet checks pass.',
                    ),
                    const SizedBox(height: 12),
                    ...[
                      'Winner account KYC verified',
                      'Entry source is valid',
                      'No abnormal device/IP pattern',
                      'Wallet status active',
                      'Admin approval audit created',
                    ].map((item) => Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: Row(children: [
                            const Icon(Icons.check_circle_outline_rounded, color: Color(0xFF2DFF87)),
                            const SizedBox(width: 10),
                            Expanded(child: Text(item)),
                          ]),
                        )),
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
