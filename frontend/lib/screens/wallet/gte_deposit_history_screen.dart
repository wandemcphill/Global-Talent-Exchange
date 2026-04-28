import 'package:flutter/material.dart';

import '../../data/gte_models.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import 'gte_funding_flow_screen.dart';

class GteDepositHistoryScreen extends StatefulWidget {
  const GteDepositHistoryScreen({super.key, required this.controller});

  final GteExchangeController controller;

  @override
  State<GteDepositHistoryScreen> createState() =>
      _GteDepositHistoryScreenState();
}

class _GteDepositHistoryScreenState extends State<GteDepositHistoryScreen> {
  late Future<List<GteWalletTransactionRecord>> _transactionsFuture;

  @override
  void initState() {
    super.initState();
    _transactionsFuture = widget.controller.api.listWalletTransactions();
  }

  Future<void> _refresh() async {
    setState(() {
      _transactionsFuture = widget.controller.api.listWalletTransactions();
    });
  }

  Future<void> _openDeposit() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (_) => GteFundWalletScreen(controller: widget.controller),
      ),
    );
    await _refresh();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Transaction History'),
        actions: <Widget>[
          IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh)),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openDeposit,
        icon: const Icon(Icons.add),
        label: const Text('Deposit'),
      ),
      body: FutureBuilder<List<GteWalletTransactionRecord>>(
        future: _transactionsFuture,
        builder: (
          BuildContext context,
          AsyncSnapshot<List<GteWalletTransactionRecord>> snapshot,
        ) {
          if (snapshot.connectionState == ConnectionState.waiting &&
              !snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final List<GteWalletTransactionRecord> transactions =
              snapshot.data ?? <GteWalletTransactionRecord>[];
          if (transactions.isEmpty) {
            return const Center(
              child: GteStatePanel(
                title: 'No wallet activity yet',
                message:
                    'Deposit funds or request a withdrawal to start your wallet history.',
                icon: Icons.account_balance_wallet_outlined,
              ),
            );
          }
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView.separated(
              padding: const EdgeInsets.all(20),
              itemCount: transactions.length,
              separatorBuilder: (_, index) => const SizedBox(height: 12),
              itemBuilder: (BuildContext context, int index) {
                final GteWalletTransactionRecord transaction =
                    transactions[index];
                final bool isCredit =
                    transaction.type.toLowerCase() == 'credit';
                final Color statusColor =
                    transaction.status.toLowerCase() == 'verified'
                        ? GteShellTheme.positive
                        : transaction.status.toLowerCase() == 'failed'
                        ? GteShellTheme.negative
                        : GteShellTheme.accentWarm;
                return GteSurfacePanel(
                  accentColor: GteShellTheme.accentCapital,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        transaction.reference,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        '${_titleCase(transaction.type)} | ${_titleCase(transaction.status)}',
                        style: Theme.of(
                          context,
                        ).textTheme.bodySmall?.copyWith(color: statusColor),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        gteFormatCredits(
                          isCredit ? transaction.amount : -transaction.amount,
                        ),
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      if (transaction.createdAt != null) ...<Widget>[
                        const SizedBox(height: 6),
                        Text(
                          'Created ${gteFormatDateTime(transaction.createdAt)}',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ],
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}

String _titleCase(String value) {
  final List<String> parts = value
      .split(RegExp(r'[_\s-]+'))
      .map((String part) => part.trim())
      .where((String part) => part.isNotEmpty)
      .toList(growable: false);
  if (parts.isEmpty) {
    return value;
  }
  return parts
      .map(
        (String part) =>
            '${part[0].toUpperCase()}${part.substring(1).toLowerCase()}',
      )
      .join(' ');
}
