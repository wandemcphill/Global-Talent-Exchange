import 'package:flutter/material.dart';

import '../data/gtex_match_models.dart';

class GtexMatchLineups extends StatelessWidget {
  const GtexMatchLineups({super.key, required this.home, required this.away});

  final GtexMatchTeam home;
  final GtexMatchTeam away;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _LineupTeam(team: home),
        const SizedBox(height: 18),
        _LineupTeam(team: away),
      ],
    );
  }
}

class _LineupTeam extends StatelessWidget {
  const _LineupTeam({required this.team});
  final GtexMatchTeam team;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white.withOpacity(.045), borderRadius: BorderRadius.circular(18), border: Border.all(color: Colors.white.withOpacity(.08))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('${team.name}  •  ${team.formation}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900)),
          const SizedBox(height: 12),
          for (final p in team.players)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 5),
              child: Row(
                children: [
                  SizedBox(width: 30, child: Text('#${p.shirtNumber}', style: const TextStyle(color: Color(0xFF18FF88), fontWeight: FontWeight.w900))),
                  Expanded(child: Text(p.name, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700))),
                  if (p.isRegen)
                    Container(
                      margin: const EdgeInsets.only(right: 8),
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(color: const Color(0xFFFFD166).withOpacity(.14), borderRadius: BorderRadius.circular(999)),
                      child: const Text('REGEN', style: TextStyle(color: Color(0xFFFFD166), fontSize: 10, fontWeight: FontWeight.w900)),
                    ),
                  Text(p.position, style: TextStyle(color: Colors.white.withOpacity(.58))),
                  const SizedBox(width: 10),
                  Text(p.rating.toStringAsFixed(1), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900)),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
