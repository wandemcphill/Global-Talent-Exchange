import 'package:flutter/material.dart';

import '../models/gtex_admin_command_models.dart';
import 'gtex_admin_visuals.dart';

class GtexCoinEconomyPanel extends StatelessWidget {
  const GtexCoinEconomyPanel({super.key, required this.snapshot});

  final GtexCoinEconomySnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    return GtexAdminPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const GtexAdminSectionHeader(
            title: 'Coin economy',
            subtitle: 'Top-ups, withdrawals, treasury and anomaly controls.',
          ),
          const SizedBox(height: 16),
          _Row(label: 'Circulating supply', value: snapshot.circulatingSupply),
          _Row(label: 'Treasury balance', value: snapshot.treasuryBalance),
          _Row(label: 'Top-up volume today', value: snapshot.topupVolumeToday),
          _Row(
            label: 'Pending withdrawals',
            value: snapshot.pendingWithdrawals,
          ),
          const SizedBox(height: 10),
          GtexAdminStatusPill(label: 'Risk: ${snapshot.riskStatus}'),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: _Action(
                  label: 'Freeze wallet',
                  icon: Icons.lock_rounded,
                  unavailableMessage:
                      'Wallet freeze requires a targeted wallet id and mounted risk endpoint.',
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _Action(
                  label: 'Audit ledger',
                  icon: Icons.manage_search_rounded,
                  unavailableMessage:
                      'Ledger audit is not mounted from this summary panel.',
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _Row extends StatelessWidget {
  const _Row({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 11),
      child: Row(
        children: [
          Expanded(
            child: Text(label, style: const TextStyle(color: Colors.white60)),
          ),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w900)),
        ],
      ),
    );
  }
}

class _Action extends StatelessWidget {
  const _Action({
    required this.label,
    required this.icon,
    required this.unavailableMessage,
  });

  final String label;
  final IconData icon;
  final String unavailableMessage;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: unavailableMessage,
      child: OutlinedButton.icon(
        onPressed: () {
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(SnackBar(content: Text(unavailableMessage)));
        },
        icon: Icon(icon, size: 18),
        label: Text(label),
        style: OutlinedButton.styleFrom(
          disabledForegroundColor: Colors.white54,
          side: BorderSide(color: Colors.white.withOpacity(.12)),
          padding: const EdgeInsets.symmetric(vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
        ),
      ),
    );
  }
}
