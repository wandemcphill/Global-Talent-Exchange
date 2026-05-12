import 'package:flutter/material.dart';

import '../models/gtex_admin_command_models.dart';
import 'gtex_admin_visuals.dart';

class GtexJackpotAdminPanel extends StatelessWidget {
  const GtexJackpotAdminPanel({
    super.key,
    required this.rounds,
  });

  final List<GtexJackpotRound> rounds;

  @override
  Widget build(BuildContext context) {
    return GtexAdminPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          GtexAdminSectionHeader(
            title: 'Jackpot control',
            subtitle: 'Pools, entries, draws, winners, claims, and fraud review.',
            trailing: GtexAdminStatusPill(label: 'Admin only'),
          ),
          const SizedBox(height: 14),
          ...rounds.map((round) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _JackpotRoundTile(round: round),
              )),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(child: _Button(label: 'Create pool', icon: Icons.add_rounded, onTap: () {})),
              const SizedBox(width: 10),
              Expanded(child: _Button(label: 'Winner review', icon: Icons.verified_rounded, onTap: () {})),
            ],
          ),
        ],
      ),
    );
  }
}

class _JackpotRoundTile extends StatelessWidget {
  const _JackpotRoundTile({required this.round});

  final GtexJackpotRound round;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF181327), Color(0xFF10201B)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFFFD166).withOpacity(.28)),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: const Color(0xFFFFD166).withOpacity(.14),
              borderRadius: BorderRadius.circular(16),
            ),
            child: const Icon(Icons.stars_rounded, color: Color(0xFFFFD166)),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(round.title, style: const TextStyle(fontWeight: FontWeight.w900)),
              const SizedBox(height: 4),
              Text('${round.entriesLabel} • ${round.drawTimeLabel}', style: const TextStyle(color: Colors.white60, fontSize: 12)),
            ]),
          ),
          Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
            Text(round.poolLabel, style: const TextStyle(color: Color(0xFFFFD166), fontWeight: FontWeight.w900, fontSize: 18)),
            const SizedBox(height: 4),
            Text(round.status, style: const TextStyle(color: Colors.white70, fontSize: 12)),
          ]),
        ],
      ),
    );
  }
}

class _Button extends StatelessWidget {
  const _Button({required this.label, required this.icon, required this.onTap});

  final String label;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ElevatedButton.icon(
      onPressed: onTap,
      icon: Icon(icon, size: 18),
      label: Text(label),
      style: ElevatedButton.styleFrom(
        backgroundColor: const Color(0xFF2DFF87).withOpacity(.14),
        foregroundColor: const Color(0xFF2DFF87),
        elevation: 0,
        padding: const EdgeInsets.symmetric(vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      ),
    );
  }
}
