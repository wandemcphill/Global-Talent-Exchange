import 'package:flutter/material.dart';

import '../../../core/app_feedback.dart';
import '../../../data/admin_command_center_api.dart';
import '../../../widgets/gte_shell_theme.dart';
import '../../../widgets/gte_surface_panel.dart';

class GtexAdminEconomyOperationsPanel extends StatefulWidget {
  const GtexAdminEconomyOperationsPanel({
    super.key,
    required this.api,
    this.onCompleted,
  });

  final AdminCommandCenterApi api;
  final Future<void> Function()? onCompleted;

  @override
  State<GtexAdminEconomyOperationsPanel> createState() =>
      _GtexAdminEconomyOperationsPanelState();
}

class _GtexAdminEconomyOperationsPanelState
    extends State<GtexAdminEconomyOperationsPanel> {
  // Credit wallet state
  final TextEditingController _creditUserIdController = TextEditingController();
  final TextEditingController _creditAmountController = TextEditingController();
  final TextEditingController _creditReasonController = TextEditingController(
    text: 'Admin ecosystem wallet credit',
  );
  String _creditUnit = 'coin';
  bool _runningCredit = false;
  AdminGodModeWalletCreditResult? _creditResult;

  // Transfer wallet state
  final TextEditingController _fromUserIdController = TextEditingController();
  final TextEditingController _toUserIdController = TextEditingController();
  final TextEditingController _transferAmountController =
      TextEditingController();
  final TextEditingController _transferReasonController = TextEditingController(
    text: 'Admin verified desk wallet transfer',
  );
  String _transferUnit = 'coin';
  bool _runningTransfer = false;
  AdminGodModeWalletTransferResult? _transferResult;

  // Grant personal points state
  final TextEditingController _pointsUserIdController = TextEditingController();
  final TextEditingController _pointsAmountController = TextEditingController();
  final TextEditingController _pointsReasonController = TextEditingController(
    text: 'Admin personal reward points grant',
  );
  bool _runningPointsGrant = false;
  bool _loadingPointsBalance = false;
  AdminUserPointsBalance? _pointsBalance;
  AdminPointGrantResult? _pointsGrantResult;

  @override
  void dispose() {
    _creditUserIdController.dispose();
    _creditAmountController.dispose();
    _creditReasonController.dispose();
    _fromUserIdController.dispose();
    _toUserIdController.dispose();
    _transferAmountController.dispose();
    _transferReasonController.dispose();
    _pointsUserIdController.dispose();
    _pointsAmountController.dispose();
    _pointsReasonController.dispose();
    super.dispose();
  }

  String _makeIdempotencyKey(String prefix) {
    return '$prefix-${DateTime.now().microsecondsSinceEpoch}';
  }

  double? _parsePositiveAmount(String raw) {
    final double? parsed = double.tryParse(raw.trim());
    if (parsed == null || parsed <= 0) {
      return null;
    }
    return parsed;
  }

  Future<void> _submitDirectCredit() async {
    final String userId = _creditUserIdController.text.trim();
    final double? amount = _parsePositiveAmount(_creditAmountController.text);
    final String reason = _creditReasonController.text.trim();
    if (userId.isEmpty || amount == null || reason.length < 4) {
      AppFeedback.showError(
        context,
        'Select a user ID, positive amount, and a reason (min 4 chars).',
      );
      return;
    }
    setState(() => _runningCredit = true);
    try {
      final AdminGodModeWalletCreditResult result = await widget.api
          .adminCreditUserWallet(
            userId: userId,
            unit: _creditUnit,
            amount: amount,
            reason: reason,
            idempotencyKey: _makeIdempotencyKey('flutter-credit'),
          );
      if (!mounted) return;
      setState(() => _creditResult = result);
      AppFeedback.showSuccess(
        context,
        'Credited ${result.amount} ${_creditUnit == 'coin' ? 'GTC' : 'FNC'} (${result.balanceBefore} -> ${result.balanceAfter}).',
      );
      await widget.onCompleted?.call();
    } catch (error) {
      if (mounted) {
        AppFeedback.showError(context, error);
      }
    } finally {
      if (mounted) {
        setState(() => _runningCredit = false);
      }
    }
  }

  Future<void> _submitTransfer() async {
    final String fromUserId = _fromUserIdController.text.trim();
    final String toUserId = _toUserIdController.text.trim();
    final double? amount = _parsePositiveAmount(_transferAmountController.text);
    final String reason = _transferReasonController.text.trim();
    if (fromUserId.isEmpty ||
        toUserId.isEmpty ||
        fromUserId == toUserId ||
        amount == null ||
        reason.length < 4) {
      AppFeedback.showError(
        context,
        'Select distinct source/destination users, positive amount, and a reason (min 4 chars).',
      );
      return;
    }
    setState(() => _runningTransfer = true);
    try {
      final AdminGodModeWalletTransferResult result = await widget.api
          .adminTransferUserWallet(
            fromUserId: fromUserId,
            toUserId: toUserId,
            unit: _transferUnit,
            amount: amount,
            reason: reason,
            idempotencyKey: _makeIdempotencyKey('flutter-transfer'),
          );
      if (!mounted) return;
      setState(() => _transferResult = result);
      AppFeedback.showSuccess(
        context,
        'Transferred ${result.amount} ${_transferUnit == 'coin' ? 'GTC' : 'FNC'}.',
      );
      await widget.onCompleted?.call();
    } catch (error) {
      if (mounted) {
        AppFeedback.showError(context, error);
      }
    } finally {
      if (mounted) {
        setState(() => _runningTransfer = false);
      }
    }
  }

  Future<void> _loadUserPoints(String userId) async {
    final String trimmed = userId.trim();
    if (trimmed.isEmpty) return;
    setState(() => _loadingPointsBalance = true);
    try {
      final AdminUserPointsBalance balance = await widget.api.fetchUserPoints(
        trimmed,
      );
      if (!mounted) return;
      setState(() => _pointsBalance = balance);
    } catch (_) {
      if (mounted) {
        setState(() => _pointsBalance = null);
      }
    } finally {
      if (mounted) {
        setState(() => _loadingPointsBalance = false);
      }
    }
  }

  Future<void> _submitPointGrant() async {
    final String userId = _pointsUserIdController.text.trim();
    final double? amount = _parsePositiveAmount(_pointsAmountController.text);
    final String reason = _pointsReasonController.text.trim();
    if (userId.isEmpty || amount == null || reason.length < 4) {
      AppFeedback.showError(
        context,
        'Select a user ID, positive point amount, and a reason (min 4 chars).',
      );
      return;
    }
    setState(() => _runningPointsGrant = true);
    try {
      final AdminPointGrantResult result = await widget.api
          .adminGrantUserPoints(
            userId: userId,
            amount: amount,
            reason: reason,
            idempotencyKey: _makeIdempotencyKey('flutter-points'),
          );
      if (!mounted) return;
      setState(() => _pointsGrantResult = result);
      AppFeedback.showSuccess(
        context,
        'Granted ${result.amount} personal reward points (Balance: ${result.balanceAfter}).',
      );
      await _loadUserPoints(userId);
      await widget.onCompleted?.call();
    } catch (error) {
      if (mounted) {
        AppFeedback.showError(context, error);
      }
    } finally {
      if (mounted) {
        setState(() => _runningPointsGrant = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return GtexColumnGap(
      children: <Widget>[
        GtexSurfacePanel(
          accentColor: GteShellTheme.positive,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Give someone coin (GTEX Coin & Fan Coin)',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 6),
              const Text(
                'Double-entry God Mode credit for GTEX Coin (GTC) or Fan Coin (FNC). Searches accounts by email, username or ID.',
              ),
              const SizedBox(height: 12),
              _AdminUserSearchPicker(
                api: widget.api,
                labelText: 'Recipient user ID',
                controller: _creditUserIdController,
              ),
              const SizedBox(height: 12),
              _CoinUnitDropdown(
                value: _creditUnit,
                onChanged: (String value) => setState(() => _creditUnit = value),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _creditAmountController,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                decoration: const InputDecoration(labelText: 'Credit amount'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _creditReasonController,
                decoration: const InputDecoration(labelText: 'Audit reason'),
              ),
              const SizedBox(height: 14),
              FilledButton.icon(
                onPressed: _runningCredit ? null : _submitDirectCredit,
                icon: const Icon(Icons.account_balance_wallet_outlined),
                label: Text(
                  _runningCredit
                      ? 'Crediting...'
                      : 'Credit ${_creditUnit == 'coin' ? 'GTEX Coin (GTC)' : 'Fan Coin (FNC)'}',
                ),
              ),
              if (_creditResult != null) ...<Widget>[
                const SizedBox(height: 12),
                Text(
                  'Tx ${_creditResult!.transactionId} · Balance ${_creditResult!.balanceBefore} -> ${_creditResult!.balanceAfter} (${_creditResult!.unit.toUpperCase()})',
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 18),
        GtexSurfacePanel(
          accentColor: GteShellTheme.accent,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Transfer coin between users',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 6),
              const Text(
                'Atomic double-entry transfer between user wallets for GTEX Coin (GTC) or Fan Coin (FNC).',
              ),
              const SizedBox(height: 12),
              _AdminUserSearchPicker(
                api: widget.api,
                labelText: 'From user ID',
                controller: _fromUserIdController,
              ),
              const SizedBox(height: 12),
              _AdminUserSearchPicker(
                api: widget.api,
                labelText: 'To user ID',
                controller: _toUserIdController,
              ),
              const SizedBox(height: 12),
              _CoinUnitDropdown(
                value: _transferUnit,
                onChanged: (String value) =>
                    setState(() => _transferUnit = value),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _transferAmountController,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                decoration: const InputDecoration(labelText: 'Transfer amount'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _transferReasonController,
                decoration: const InputDecoration(labelText: 'Audit reason'),
              ),
              const SizedBox(height: 14),
              FilledButton.tonalIcon(
                onPressed: _runningTransfer ? null : _submitTransfer,
                icon: const Icon(Icons.swap_horiz_outlined),
                label: Text(
                  _runningTransfer
                      ? 'Transferring...'
                      : 'Transfer ${_transferUnit == 'coin' ? 'GTEX Coin (GTC)' : 'Fan Coin (FNC)'}',
                ),
              ),
              if (_transferResult != null) ...<Widget>[
                const SizedBox(height: 12),
                Text(
                  'Tx ${_transferResult!.transactionId} · From ${_transferResult!.fromBalanceBefore} -> ${_transferResult!.fromBalanceAfter} · To ${_transferResult!.toBalanceBefore} -> ${_transferResult!.toBalanceAfter}',
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 18),
        GtexSurfacePanel(
          accentColor: GteShellTheme.accentAdmin,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Grant personal user points',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 6),
              const Text(
                'Credits the dedicated UserPointAccount personal reward ledger (isolated from Fan War and Club Loyalty points).',
              ),
              const SizedBox(height: 12),
              _AdminUserSearchPicker(
                api: widget.api,
                labelText: 'Target user ID',
                controller: _pointsUserIdController,
                onUserSelected: (AdminDirectoryUser user) {
                  _loadUserPoints(user.id);
                },
              ),
              if (_loadingPointsBalance)
                const Padding(
                  padding: EdgeInsets.only(top: 8),
                  child: LinearProgressIndicator(),
                )
              else if (_pointsBalance != null)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                    'Current personal balance: ${_pointsBalance!.balance} pts (Lifetime earned: ${_pointsBalance!.lifetimeEarned})',
                  ),
                ),
              const SizedBox(height: 12),
              TextField(
                controller: _pointsAmountController,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                decoration: const InputDecoration(labelText: 'Points amount'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _pointsReasonController,
                decoration: const InputDecoration(labelText: 'Audit reason'),
              ),
              const SizedBox(height: 14),
              FilledButton.icon(
                onPressed: _runningPointsGrant ? null : _submitPointGrant,
                icon: const Icon(Icons.stars_outlined),
                label: Text(
                  _runningPointsGrant
                      ? 'Granting...'
                      : 'Grant personal points',
                ),
              ),
              if (_pointsGrantResult != null) ...<Widget>[
                const SizedBox(height: 12),
                Text(
                  'Ref ${_pointsGrantResult!.reference} · Balance ${_pointsGrantResult!.balanceBefore} -> ${_pointsGrantResult!.balanceAfter}',
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

class GtexColumnGap extends StatelessWidget {
  const GtexColumnGap({super.key, required this.children});
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: children,
    );
  }
}

class _CoinUnitDropdown extends StatelessWidget {
  const _CoinUnitDropdown({required this.value, required this.onChanged});

  final String value;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<String>(
      value: value,
      decoration: const InputDecoration(labelText: 'Currency unit'),
      items: const <DropdownMenuItem<String>>[
        DropdownMenuItem<String>(value: 'coin', child: Text('GTEX Coin (GTC)')),
        DropdownMenuItem<String>(
          value: 'credit',
          child: Text('Fan Coin (FNC)'),
        ),
      ],
      onChanged: (String? next) {
        if (next != null) {
          onChanged(next);
        }
      },
    );
  }
}

class _AdminUserSearchPicker extends StatefulWidget {
  const _AdminUserSearchPicker({
    required this.api,
    required this.labelText,
    required this.controller,
    this.onUserSelected,
  });

  final AdminCommandCenterApi api;
  final String labelText;
  final TextEditingController controller;
  final ValueChanged<AdminDirectoryUser>? onUserSelected;

  @override
  State<_AdminUserSearchPicker> createState() => _AdminUserSearchPickerState();
}

class _AdminUserSearchPickerState extends State<_AdminUserSearchPicker> {
  final TextEditingController _searchController = TextEditingController();
  bool _searching = false;
  List<AdminDirectoryUser> _matches = <AdminDirectoryUser>[];

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _search() async {
    setState(() => _searching = true);
    try {
      final List<AdminDirectoryUser> users = await widget.api.searchUsers(
        query: _searchController.text.trim(),
        limit: 8,
      );
      if (!mounted) return;
      setState(() => _matches = users);
    } catch (error) {
      if (mounted) {
        AppFeedback.showError(context, error);
      }
    } finally {
      if (mounted) {
        setState(() => _searching = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Expanded(
              child: TextField(
                controller: _searchController,
                decoration: const InputDecoration(
                  labelText: 'Search account (email, username, ID)',
                ),
              ),
            ),
            const SizedBox(width: 8),
            FilledButton.tonalIcon(
              onPressed: _searching ? null : _search,
              icon: const Icon(Icons.search),
              label: Text(_searching ? '...' : 'Find'),
            ),
          ],
        ),
        if (_matches.isNotEmpty) ...<Widget>[
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _matches
                .map(
                  (AdminDirectoryUser user) => ActionChip(
                    label: Text(user.label),
                    onPressed: () {
                      widget.controller.text = user.id;
                      widget.onUserSelected?.call(user);
                      setState(() => _matches = <AdminDirectoryUser>[]);
                    },
                  ),
                )
                .toList(growable: false),
          ),
        ],
        const SizedBox(height: 8),
        TextField(
          controller: widget.controller,
          decoration: InputDecoration(labelText: widget.labelText),
        ),
      ],
    );
  }
}
