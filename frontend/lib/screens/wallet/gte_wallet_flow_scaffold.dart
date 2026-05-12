import 'package:flutter/material.dart';

import '../../ui_gtex/layout/gtex_production_flow_scaffold.dart';
import '../../ui_gtex/theme/gtex_colors.dart';

class GteWalletFlowScaffold extends StatelessWidget {
  const GteWalletFlowScaffold({
    super.key,
    required this.title,
    required this.subtitle,
    required this.child,
    this.actions = const <Widget>[],
    this.floatingActionButton,
    this.icon = Icons.account_balance_wallet_outlined,
    this.accent = GtexColors.gold,
    this.statusLabel,
  });

  final String title;
  final String subtitle;
  final Widget child;
  final List<Widget> actions;
  final Widget? floatingActionButton;
  final IconData icon;
  final Color accent;
  final String? statusLabel;

  @override
  Widget build(BuildContext context) {
    return GtexProductionFlowScaffold(
      title: title,
      subtitle: subtitle,
      actions: actions,
      floatingActionButton: floatingActionButton,
      icon: icon,
      accent: accent,
      statusLabel: statusLabel,
      appBarTitle: statusLabel ?? 'GTEX Wallet',
      child: child,
    );
  }
}
