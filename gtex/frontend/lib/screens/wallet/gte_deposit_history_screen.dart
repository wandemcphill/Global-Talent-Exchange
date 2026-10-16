import 'package:flutter/material.dart';

import '../../data/gte_models.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import 'gte_funding_flow_screen.dart';
import 'gte_wallet_flow_scaffold.dart';

class GteDepositHistoryScreen extends StatefulWidget {
  const GteDepositHistoryScreen({super.key, required this.controller});

  final GteExchangeController controller;

  @override
  State<GteDepositHistoryScreen> createState() =>
      _GteDepositHistoryScreenState();
}

class _GteDepositHistoryScreenState extends State<GteDepositHistoryScreen> {
  late Future<List<GteWalletTransactionRecord>> _transactionsFuture;
  String _activeFilter = 'all';

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
    return GteWalletFlowScaffold(
      title: 'Transaction History',
      subtitle:
          'Audit deposits, withdrawals, references, and wallet status changes from the live GTEX ledger.',
      icon: Icons.receipt_long_outlined,
      statusLabel: 'LIVE WALLET LEDGER',
      actions: <Widget>[
        IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh)),
      ],
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openDeposit,
        icon: const Icon(Icons.add),
        label: const Text('Deposit'),
      ),
      child: FutureBuilder<List<GteWalletTransactionRecord>>(
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
          final List<GteWalletTransactionRecord> filteredTransactions =
              _filterTransactions(transactions, _activeFilter);
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
              itemCount:
                  filteredTransactions.isEmpty
                      ? 2
                      : filteredTransactions.length + 1,
              separatorBuilder: (_, index) => const SizedBox(height: 12),
              itemBuilder: (BuildContext context, int index) {
                if (index == 0) {
                  return _TransactionFilterRail(
                    activeFilter: _activeFilter,
                    onChanged:
                        (String filter) =>
                            setState(() => _activeFilter = filter),
                  );
                }
                if (filteredTransactions.isEmpty) {
                  return GteStatePanel(
                    title: 'No ${_titleCase(_activeFilter)} activity',
                    message:
                        'The live ledger has no transactions in this category yet.',
                    icon: Icons.receipt_long_outlined,
                  );
                }
                final GteWalletTransactionRecord transaction =
                    filteredTransactions[index - 1];
                return _HistoryTransactionCard(transaction: transaction);
              },
            ),
          );
        },
      ),
    );
  }
}

class _TransactionFilterRail extends StatelessWidget {
  const _TransactionFilterRail({
    required this.activeFilter,
    required this.onChanged,
  });

  static const List<String> filters = <String>[
    'all',
    'deposits',
    'withdrawals',
    'transfers',
    'purchases',
    'rentals',
    'trades',
  ];

  final String activeFilter;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 44,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: filters.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (BuildContext context, int index) {
          final String filter = filters[index];
          return ChoiceChip(
            label: Text(_titleCase(filter)),
            selected: activeFilter == filter,
            onSelected: (_) => onChanged(filter),
          );
        },
      ),
    );
  }
}

class _HistoryTransactionCard extends StatelessWidget {
  const _HistoryTransactionCard({required this.transaction});

  final GteWalletTransactionRecord transaction;

  @override
  Widget build(BuildContext context) {
    final String type = transaction.type.toLowerCase();
    final bool isCredit = type == 'credit' || type.contains('deposit');
    final Color statusColor = _statusColor(transaction.status);
    final Color amountColor =
        isCredit ? GteShellTheme.positive : GteShellTheme.negative;
    return GteSurfacePanel(
      accentColor: statusColor,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: statusColor.withValues(alpha: 0.12),
              border: Border.all(color: statusColor.withValues(alpha: 0.22)),
            ),
            child: Icon(_transactionIcon(type), color: statusColor),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  _transactionTitle(type, isCredit),
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 5),
                Text(
                  '${transaction.createdAt == null ? 'Time unavailable' : gteFormatDateTime(transaction.createdAt)} - ${_truncateId(transaction.reference)}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(999),
                    color: statusColor.withValues(alpha: 0.12),
                    border: Border.all(
                      color: statusColor.withValues(alpha: 0.2),
                    ),
                  ),
                  child: Text(
                    _titleCase(transaction.status),
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: statusColor,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Text(
            gteFormatGtc(isCredit ? transaction.amount : -transaction.amount),
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: amountColor,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

List<GteWalletTransactionRecord> _filterTransactions(
  List<GteWalletTransactionRecord> transactions,
  String filter,
) {
  if (filter == 'all') {
    return transactions;
  }
  return transactions
      .where((GteWalletTransactionRecord transaction) {
        final String type = transaction.type.toLowerCase();
        return switch (filter) {
          'deposits' => type.contains('deposit') || type == 'credit',
          'withdrawals' => type.contains('withdraw'),
          'transfers' => type.contains('transfer') || type.contains('send'),
          'purchases' => type.contains('purchase') || type.contains('player'),
          'rentals' => type.contains('rent'),
          'trades' => type.contains('trade'),
          _ => true,
        };
      })
      .toList(growable: false);
}

Color _statusColor(String status) {
  switch (status.toLowerCase()) {
    case 'verified':
    case 'confirmed':
    case 'completed':
    case 'success':
      return GteShellTheme.positive;
    case 'failed':
    case 'rejected':
    case 'expired':
      return GteShellTheme.negative;
    default:
      return GteShellTheme.accentWarm;
  }
}

IconData _transactionIcon(String type) {
  if (type.contains('withdraw')) {
    return Icons.account_balance_outlined;
  }
  if (type.contains('trade')) {
    return Icons.currency_exchange_outlined;
  }
  if (type.contains('purchase') || type.contains('player')) {
    return Icons.person_search_outlined;
  }
  if (type.contains('rent')) {
    return Icons.flag_outlined;
  }
  if (type.contains('transfer') || type.contains('send')) {
    return Icons.swap_horiz_outlined;
  }
  return type.contains('credit') || type.contains('deposit')
      ? Icons.south_west_outlined
      : Icons.north_east_outlined;
}

String _transactionTitle(String type, bool isCredit) {
  if (type.contains('deposit')) {
    return 'Wallet deposit';
  }
  if (type.contains('withdraw')) {
    return 'Withdrawal request';
  }
  if (type.contains('trade')) {
    return 'Coin trade settlement';
  }
  if (type.contains('purchase')) {
    return 'Player purchase';
  }
  if (type.contains('rent')) {
    return 'National rental payment';
  }
  if (type.contains('transfer') || type.contains('send')) {
    return 'Wallet transfer';
  }
  return isCredit ? 'Wallet credit' : 'Wallet debit';
}

String _truncateId(String value) {
  if (value.length <= 18) {
    return value;
  }
  return '${value.substring(0, 8)}...${value.substring(value.length - 6)}';
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
