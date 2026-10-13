import 'package:flutter/material.dart';

import '../../../data/jackpot_admin_api.dart';
import '../../../models/jackpot_admin_models.dart';
import '../models/gtex_admin_command_models.dart';
import 'gtex_admin_visuals.dart';

class GtexJackpotAdminPanel extends StatefulWidget {
  const GtexJackpotAdminPanel({
    super.key,
    this.api,
    this.rounds = const <GtexJackpotRound>[],
  });

  /// Live admin jackpot client. When null, the panel fails closed.
  final JackpotAdminApi? api;
  final List<GtexJackpotRound> rounds;

  @override
  State<GtexJackpotAdminPanel> createState() => _GtexJackpotAdminPanelState();
}

class _GtexJackpotAdminPanelState extends State<GtexJackpotAdminPanel> {
  bool _loading = false;
  bool _busy = false;
  String? _error;
  String? _message;
  JackpotAdminRuntime? _runtime;
  List<JackpotHistoryItem> _history = const <JackpotHistoryItem>[];

  @override
  void initState() {
    super.initState();
    _reload();
  }

  @override
  void didUpdateWidget(covariant GtexJackpotAdminPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.api != widget.api) {
      _reload();
    }
  }

  Future<void> _reload() async {
    final JackpotAdminApi? api = widget.api;
    if (api == null) {
      setState(() {
        _runtime = null;
        _history = const <JackpotHistoryItem>[];
        _error =
            'Authenticated admin jackpot API is required for live pool controls.';
        _message = null;
        _loading = false;
      });
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final JackpotAdminRuntime runtime = await api.fetchRuntime();
      final List<JackpotHistoryItem> history = await api.fetchHistory();
      if (!mounted) {
        return;
      }
      setState(() {
        _runtime = runtime;
        _history = history;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = error.toString();
        _loading = false;
      });
    }
  }

  Future<void> _run(Future<String> Function() action) async {
    setState(() {
      _busy = true;
      _error = null;
      _message = null;
    });
    try {
      final String message = await action();
      if (!mounted) {
        return;
      }
      setState(() => _message = message);
      await _reload();
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() => _error = error.toString());
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  Future<void> _editSettings() async {
    final JackpotAdminApi? api = widget.api;
    final JackpotAdminRuntime? runtime = _runtime;
    if (api == null || runtime == null) {
      return;
    }
    final Map<String, Object?>? body = await showDialog<Map<String, Object?>>(
      context: context,
      builder: (BuildContext context) => _JackpotSettingsDialog(runtime: runtime),
    );
    if (body == null) {
      return;
    }
    await _run(() async {
      await api.updateRuntime(body);
      return 'Jackpot runtime settings saved.';
    });
  }

  Future<void> _setBalance() async {
    final JackpotAdminApi? api = widget.api;
    if (api == null) {
      return;
    }
    final ({String balance, String reason})? input =
        await showDialog<({String balance, String reason})>(
      context: context,
      builder: (BuildContext context) => _JackpotBalanceDialog(
        initialBalance: _runtime?.balance ?? '0',
      ),
    );
    if (input == null) {
      return;
    }
    await _run(() async {
      await api.updateBalance(balance: input.balance, reason: input.reason);
      return 'Jackpot balance updated.';
    });
  }

  Future<void> _triggerRound() async {
    final JackpotAdminApi? api = widget.api;
    if (api == null) {
      return;
    }
    final bool? confirmed = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          backgroundColor: const Color(0xFF121821),
          title: const Text('Trigger jackpot round?'),
          content: const Text(
            'This settles the current round now and pays out winners. This cannot be undone.',
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Trigger now'),
            ),
          ],
        );
      },
    );
    if (confirmed != true) {
      return;
    }
    await _run(() => api.triggerRound());
  }

  @override
  Widget build(BuildContext context) {
    final List<GtexJackpotRound> rounds = _runtime == null
        ? widget.rounds
        : <GtexJackpotRound>[_runtime!.toRoundTile()];
    return GtexAdminPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          GtexAdminSectionHeader(
            title: 'Jackpot control',
            subtitle:
                'Live pool runtime, balance, manual trigger, and winner history.',
            trailing: const GtexAdminStatusPill(label: 'Admin only'),
          ),
          const SizedBox(height: 14),
          if (_loading)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 18),
              child: Center(child: CircularProgressIndicator()),
            )
          else if (rounds.isEmpty)
            const _JackpotUnavailableState()
          else
            ...rounds.map(
              (GtexJackpotRound round) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _JackpotRoundTile(round: round),
              ),
            ),
          if (_runtime != null) ...<Widget>[
            const SizedBox(height: 4),
            Text(
              'Mode ${_runtime!.distributionMode} • threshold ${_runtime!.thresholdAmount} • cap ${_runtime!.probabilityCap} • rate ${_runtime!.contributionRate}',
              style: const TextStyle(color: Colors.white60, fontSize: 12),
            ),
            const SizedBox(height: 4),
            Text(
              _runtime!.toRoundTile().winnerLabel,
              style: const TextStyle(color: Colors.white70, fontSize: 12),
            ),
          ],
          if (_message != null) ...<Widget>[
            const SizedBox(height: 10),
            Text(_message!, style: const TextStyle(color: Color(0xFF2DFF87))),
          ],
          if (_error != null) ...<Widget>[
            const SizedBox(height: 10),
            Text(_error!, style: const TextStyle(color: Color(0xFFFF6B6B))),
          ],
          const SizedBox(height: 12),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              _ActionButton(
                label: 'Edit settings',
                icon: Icons.tune_rounded,
                onPressed: widget.api == null || _busy || _runtime == null
                    ? null
                    : _editSettings,
              ),
              _ActionButton(
                label: 'Set balance',
                icon: Icons.account_balance_wallet_outlined,
                onPressed: widget.api == null || _busy ? null : _setBalance,
              ),
              _ActionButton(
                label: _busy ? 'Working…' : 'Trigger round',
                icon: Icons.bolt_rounded,
                onPressed: widget.api == null || _busy ? null : _triggerRound,
              ),
              _ActionButton(
                label: 'Refresh',
                icon: Icons.refresh_rounded,
                onPressed: widget.api == null || _busy || _loading ? null : _reload,
              ),
            ],
          ),
          const SizedBox(height: 16),
          const GtexAdminSectionHeader(
            title: 'Winner history',
            subtitle: 'Settled and triggered rounds from /api/jackpot/history.',
          ),
          const SizedBox(height: 10),
          if (_history.isEmpty)
            const Text(
              'No jackpot history returned yet.',
              style: TextStyle(color: Colors.white54),
            )
          else
            ..._history.take(8).map(
              (JackpotHistoryItem item) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: _HistoryTile(item: item),
              ),
            ),
        ],
      ),
    );
  }
}

class _JackpotUnavailableState extends StatelessWidget {
  const _JackpotUnavailableState();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(.04),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(.12)),
      ),
      child: const Row(
        children: <Widget>[
          Icon(Icons.block_rounded, color: Colors.white54),
          SizedBox(width: 12),
          Expanded(
            child: Text(
              'Live jackpot rounds unavailable until the admin jackpot endpoint returns a persisted pool snapshot.',
              style: TextStyle(color: Colors.white70),
            ),
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
          colors: <Color>[Color(0xFF181327), Color(0xFF10201B)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFFFD166).withOpacity(.28)),
      ),
      child: Row(
        children: <Widget>[
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
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  round.title,
                  style: const TextStyle(fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 4),
                Text(
                  '${round.entriesLabel} • ${round.drawTimeLabel}',
                  style: const TextStyle(color: Colors.white60, fontSize: 12),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: <Widget>[
              Text(
                round.poolLabel,
                style: const TextStyle(
                  color: Color(0xFFFFD166),
                  fontWeight: FontWeight.w900,
                  fontSize: 18,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                round.status,
                style: const TextStyle(color: Colors.white70, fontSize: 12),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _HistoryTile extends StatelessWidget {
  const _HistoryTile({required this.item});

  final JackpotHistoryItem item;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(.04),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.white.withOpacity(.08)),
      ),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Round ${item.roundNumber} • ${item.status}',
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 4),
                Text(
                  item.winningUserId == null
                      ? 'No winner recorded'
                      : 'Winner ${item.winningUserId}',
                  style: const TextStyle(color: Colors.white60, fontSize: 12),
                ),
              ],
            ),
          ),
          Text(
            '${item.currentBalance} GTEX',
            style: const TextStyle(color: Color(0xFFFFD166)),
          ),
        ],
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  const _ActionButton({
    required this.label,
    required this.icon,
    required this.onPressed,
  });

  final String label;
  final IconData icon;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return ElevatedButton.icon(
      onPressed: onPressed,
      icon: Icon(icon, size: 18),
      label: Text(label),
      style: ElevatedButton.styleFrom(
        backgroundColor: const Color(0xFF2DFF87).withOpacity(.08),
        disabledBackgroundColor: const Color(0xFF2DFF87).withOpacity(.05),
        disabledForegroundColor: Colors.white38,
        foregroundColor: Colors.white,
        elevation: 0,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      ),
    );
  }
}

class _JackpotBalanceDialog extends StatefulWidget {
  const _JackpotBalanceDialog({required this.initialBalance});

  final String initialBalance;

  @override
  State<_JackpotBalanceDialog> createState() => _JackpotBalanceDialogState();
}

class _JackpotBalanceDialogState extends State<_JackpotBalanceDialog> {
  late final TextEditingController _balanceController;
  late final TextEditingController _reasonController;

  @override
  void initState() {
    super.initState();
    _balanceController = TextEditingController(text: widget.initialBalance);
    _reasonController = TextEditingController();
  }

  @override
  void dispose() {
    _balanceController.dispose();
    _reasonController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: const Color(0xFF121821),
      title: const Text('Set jackpot balance'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          TextField(
            controller: _balanceController,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(labelText: 'Balance'),
          ),
          TextField(
            controller: _reasonController,
            decoration: const InputDecoration(labelText: 'Reason (optional)'),
          ),
        ],
      ),
      actions: <Widget>[
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () {
            final String balance = _balanceController.text.trim();
            if (balance.isEmpty || double.tryParse(balance) == null) {
              return;
            }
            Navigator.of(context).pop((
              balance: balance,
              reason: _reasonController.text.trim(),
            ));
          },
          child: const Text('Save'),
        ),
      ],
    );
  }
}

class _JackpotSettingsDialog extends StatefulWidget {
  const _JackpotSettingsDialog({required this.runtime});

  final JackpotAdminRuntime runtime;

  @override
  State<_JackpotSettingsDialog> createState() => _JackpotSettingsDialogState();
}

class _JackpotSettingsDialogState extends State<_JackpotSettingsDialog> {
  late final TextEditingController _threshold;
  late final TextEditingController _probabilityLimit;
  late final TextEditingController _probabilityCap;
  late final TextEditingController _contributionRate;
  late final TextEditingController _failsafeHours;
  late final TextEditingController _topSplit;
  late final TextEditingController _minActivity;
  late String _distributionMode;

  @override
  void initState() {
    super.initState();
    final JackpotAdminRuntime runtime = widget.runtime;
    _threshold = TextEditingController(text: runtime.thresholdAmount);
    _probabilityLimit = TextEditingController(text: runtime.probabilityLimit);
    _probabilityCap = TextEditingController(text: runtime.probabilityCap);
    _contributionRate = TextEditingController(text: runtime.contributionRate);
    _failsafeHours = TextEditingController(text: '${runtime.failsafeHours}');
    _topSplit = TextEditingController(text: runtime.topSplitPercent);
    _minActivity = TextEditingController(text: runtime.minActivityScore);
    _distributionMode = runtime.distributionMode;
  }

  @override
  void dispose() {
    _threshold.dispose();
    _probabilityLimit.dispose();
    _probabilityCap.dispose();
    _contributionRate.dispose();
    _failsafeHours.dispose();
    _topSplit.dispose();
    _minActivity.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: const Color(0xFF121821),
      title: const Text('Edit jackpot settings'),
      content: SizedBox(
        width: 420,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              TextField(
                controller: _threshold,
                decoration: const InputDecoration(labelText: 'Threshold amount'),
              ),
              TextField(
                controller: _probabilityLimit,
                decoration: const InputDecoration(labelText: 'Probability limit'),
              ),
              TextField(
                controller: _probabilityCap,
                decoration: const InputDecoration(labelText: 'Probability cap'),
              ),
              TextField(
                controller: _contributionRate,
                decoration: const InputDecoration(labelText: 'Contribution rate'),
              ),
              TextField(
                controller: _failsafeHours,
                decoration: const InputDecoration(labelText: 'Failsafe hours'),
              ),
              TextField(
                controller: _topSplit,
                decoration: const InputDecoration(labelText: 'Top split percent'),
              ),
              TextField(
                controller: _minActivity,
                decoration: const InputDecoration(labelText: 'Min activity score'),
              ),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                value: _distributionMode,
                items: const <DropdownMenuItem<String>>[
                  DropdownMenuItem(
                    value: 'single_winner',
                    child: Text('single_winner'),
                  ),
                  DropdownMenuItem(
                    value: 'top_split',
                    child: Text('top_split'),
                  ),
                  DropdownMenuItem(
                    value: 'activity_weighted',
                    child: Text('activity_weighted'),
                  ),
                ],
                onChanged: (String? value) {
                  if (value == null) {
                    return;
                  }
                  setState(() => _distributionMode = value);
                },
                decoration: const InputDecoration(labelText: 'Distribution mode'),
              ),
            ],
          ),
        ),
      ),
      actions: <Widget>[
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () {
            final int? failsafeHours = int.tryParse(_failsafeHours.text.trim());
            if (failsafeHours == null || failsafeHours < 1) {
              return;
            }
            Navigator.of(context).pop(<String, Object?>{
              'threshold_amount': _threshold.text.trim(),
              'probability_limit': _probabilityLimit.text.trim(),
              'probability_cap': _probabilityCap.text.trim(),
              'failsafe_hours': failsafeHours,
              'contribution_rate': _contributionRate.text.trim(),
              'distribution_mode': _distributionMode,
              'top_split_percent': _topSplit.text.trim(),
              'min_activity_score': _minActivity.text.trim(),
            });
          },
          child: const Text('Save'),
        ),
      ],
    );
  }
}
