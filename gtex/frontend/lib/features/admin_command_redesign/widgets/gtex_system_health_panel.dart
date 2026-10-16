import 'package:flutter/material.dart';

import '../models/gtex_admin_command_models.dart';
import 'gtex_admin_visuals.dart';

class GtexSystemHealthPanel extends StatelessWidget {
  const GtexSystemHealthPanel({
    super.key,
    required this.signals,
  });

  final List<GtexSystemHealthSignal> signals;

  @override
  Widget build(BuildContext context) {
    return GtexAdminPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const GtexAdminSectionHeader(
            title: 'System health',
            subtitle: 'Deploys, API, web, ingestion, Redis/BullMQ, and payment health.',
          ),
          const SizedBox(height: 14),
          ...signals.map((signal) {
            final color = gtexAdminSeverityColor(signal.severity);
            return Container(
              margin: const EdgeInsets.only(bottom: 9),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFF0B1220),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.white.withOpacity(.06)),
              ),
              child: Row(
                children: [
                  Icon(Icons.circle, color: color, size: 10),
                  const SizedBox(width: 10),
                  Expanded(child: Text(signal.name, style: const TextStyle(fontWeight: FontWeight.w800))),
                  const SizedBox(width: 8),
                  Text(signal.detail, style: const TextStyle(color: Colors.white60, fontSize: 12)),
                  const SizedBox(width: 8),
                  GtexAdminStatusPill(label: signal.status, severity: signal.severity),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }
}
