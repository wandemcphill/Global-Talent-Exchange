import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../data/gte_api_repository.dart';
import '../../ui_gtex/layout/gtex_production_flow_scaffold.dart';
import '../../ui_gtex/ui_gtex.dart';
import 'matchday_economy_widgets.dart';

class GtexMatchdayEconomyAdminScreen extends StatelessWidget {
  const GtexMatchdayEconomyAdminScreen({
    super.key,
    required this.baseUrl,
    required this.backendMode,
    required this.accessToken,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String accessToken;

  @override
  Widget build(BuildContext context) {
    return GtexProductionFlowScaffold(
      title: 'Matchday economy operations',
      subtitle:
          'Federation, fan, broadcast, ticketing, and collectible card signals in one admin surface.',
      icon: Icons.query_stats_outlined,
      accent: GtexColors.mint,
      statusLabel: 'Admin economy',
      actions: <Widget>[
        IconButton(
          tooltip: 'Back to admin command center',
          onPressed: () => context.go('/admin'),
          icon: const Icon(Icons.arrow_back_outlined),
        ),
      ],
      child: ListView(
        padding: const EdgeInsets.fromLTRB(
          GtexSpacing.lg,
          0,
          GtexSpacing.lg,
          GtexSpacing.xxl,
        ),
        children: <Widget>[
          GtexMatchdayEconomyPanel(
            baseUrl: baseUrl,
            backendMode: backendMode,
            accessToken: accessToken,
            admin: true,
          ),
        ],
      ),
    );
  }
}
