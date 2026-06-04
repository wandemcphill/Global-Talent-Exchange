import 'package:flutter/material.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/capital/wallet/data/capital_wallet_api.dart';
import 'package:gte_frontend/features/capital/wallet/data/capital_wallet_availability.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/widgets/gte_formatters.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class GtexJackpotRouteScreen extends StatefulWidget {
  const GtexJackpotRouteScreen({
    super.key,
    required this.dependencies,
    this.onOpenLogin,
  });

  final GteNavigationDependencies dependencies;
  final VoidCallback? onOpenLogin;

  @override
  State<GtexJackpotRouteScreen> createState() => _GtexJackpotRouteScreenState();
}

class _GtexJackpotRouteScreenState extends State<GtexJackpotRouteScreen> {
  final TextEditingController _contributionAmountController =
      TextEditingController(text: '50');
  final TextEditingController _thresholdController = TextEditingController();
  final TextEditingController _probabilityLimitController =
      TextEditingController();
  final TextEditingController _probabilityCapController =
      TextEditingController();
  final TextEditingController _contributionRateController =
      TextEditingController();
  final TextEditingController _failsafeHoursController =
      TextEditingController();
  final TextEditingController _topSplitPercentController =
      TextEditingController();
  final TextEditingController _minActivityScoreController =
      TextEditingController();

  _JackpotState? _state;
  _JackpotRuntime? _adminRuntime;
  List<_JackpotHistoryItem> _history = const <_JackpotHistoryItem>[];
  CapitalWalletAvailability? _walletAvailability;
  String? _error;
  bool _loading = true;
  bool _submittingContribution = false;
  bool _savingRuntime = false;
  bool _triggeringRound = false;
  bool _adminFieldsHydrated = false;
  String _distributionMode = 'single_winner';

  bool get _isAuthenticated => widget.dependencies.isAuthenticated;
  bool get _isAdmin => widget.dependencies.isAdminRole;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _contributionAmountController.dispose();
    _thresholdController.dispose();
    _probabilityLimitController.dispose();
    _probabilityCapController.dispose();
    _contributionRateController.dispose();
    _failsafeHoursController.dispose();
    _topSplitPercentController.dispose();
    _minActivityScoreController.dispose();
    super.dispose();
  }

  Future<void> _load({bool hydrateAdminFields = false}) async {
    setState(() {
      _loading = true;
      _error = null;
      if (_isAuthenticated) {
        _walletAvailability = null;
      }
    });
    try {
      final Map<String, Object?> payload = await _loadPayload();
      final _JackpotState state = _JackpotState.fromJson(
        _mapFrom(payload['state']),
      );
      final List<_JackpotHistoryItem> history = _listFrom(payload['history'])
          .map((Object? item) => _JackpotHistoryItem.fromJson(_mapFrom(item)))
          .toList(growable: false);
      final CapitalWalletAvailability? walletAvailability =
          payload['wallet'] == null
              ? null
              : _walletAvailabilityFrom(payload['wallet']);
      final _JackpotRuntime? adminRuntime =
          payload['admin'] == null
              ? null
              : _JackpotRuntime.fromJson(_mapFrom(payload['admin']));
      if (!mounted) {
        return;
      }
      setState(() {
        _state = state;
        _history = history;
        _walletAvailability = walletAvailability;
        _adminRuntime = adminRuntime;
        _loading = false;
      });
      if (adminRuntime != null &&
          (!_adminFieldsHydrated || hydrateAdminFields)) {
        _hydrateAdminFields(adminRuntime);
      }
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = AppFeedback.messageFor(error);
        _loading = false;
      });
    }
  }

  Future<Map<String, Object?>> _loadPayload() async {
    final GteAuthedApi api = widget.dependencies.createAuthedApi();
    final CapitalWalletApi walletApi = capitalWalletApiForClient(api);
    final List<Future<Object?>> calls = <Future<Object?>>[
      api.getMap('/jackpot/state', auth: false),
      api.getList(
        '/jackpot/history',
        auth: false,
        query: const <String, Object?>{'limit': 8},
      ),
    ];
    if (_isAuthenticated) {
      calls.add(walletApi.fetchAvailability());
    }
    if (_isAdmin) {
      calls.add(api.getMap('/admin/jackpot/runtime', auth: true));
    }
    final List<Object?> results = await Future.wait<Object?>(calls);
    int index = 0;
    return <String, Object?>{
      'state': results[index++],
      'history': results[index++],
      'wallet': _isAuthenticated ? results[index++] : null,
      'admin': _isAdmin ? results[index++] : null,
    };
  }

  void _hydrateAdminFields(_JackpotRuntime runtime) {
    _thresholdController.text = _decimalInput(runtime.thresholdAmount);
    _probabilityLimitController.text = _decimalInput(runtime.probabilityLimit);
    _probabilityCapController.text = _decimalInput(runtime.probabilityCap);
    _contributionRateController.text = _decimalInput(runtime.contributionRate);
    _failsafeHoursController.text = runtime.failsafeHours.toString();
    _topSplitPercentController.text = _decimalInput(runtime.topSplitPercent);
    _minActivityScoreController.text = _decimalInput(runtime.minActivityScore);
    _distributionMode = runtime.distributionMode;
    _adminFieldsHydrated = true;
  }

  Future<void> _openLogin() async {
    widget.onOpenLogin?.call();
  }

  Future<void> _submitContribution() async {
    final double? amount = _parsePositiveDouble(
      _contributionAmountController.text,
    );
    if (amount == null) {
      AppFeedback.showError(context, 'Enter a valid GTEX Coin amount.');
      return;
    }
    if (!_isAuthenticated) {
      await _openLogin();
      return;
    }
    final CapitalWalletAvailability? walletAvailability = _walletAvailability;
    if (walletAvailability == null) {
      AppFeedback.showError(
        context,
        'Wallet availability is still syncing. Try again after refresh.',
      );
      return;
    }
    if (!walletAvailability.coversCoinAmount(amount)) {
      AppFeedback.showError(
        context,
        walletAvailability.blockedReason ??
            'Wallet does not have enough available GTEX Coin for this contribution.',
      );
      return;
    }
    setState(() {
      _submittingContribution = true;
    });
    try {
      final GteAuthedApi api = widget.dependencies.createAuthedApi();
      await api.post(
        '/jackpot/contribute',
        auth: true,
        body: <String, Object?>{
          'source_type': 'platform_activity',
          'source_id': 'jackpot-ui-${DateTime.now().millisecondsSinceEpoch}',
          'entry_fee': _decimalString(amount),
          'contribution_amount': _decimalString(amount),
          'eligibility_score': '1.0000',
          'metadata': <String, Object?>{
            'source': 'gtex_jackpot_route_screen',
            'manual': true,
          },
        },
      );
      if (!mounted) {
        return;
      }
      AppFeedback.showSuccess(
        context,
        'Jackpot contribution submitted from wallet.',
      );
      await _load();
    } catch (error) {
      if (!mounted) {
        return;
      }
      AppFeedback.showError(context, AppFeedback.messageFor(error));
    } finally {
      if (mounted) {
        setState(() {
          _submittingContribution = false;
        });
      }
    }
  }

  Future<void> _saveRuntime() async {
    final double? threshold = _parsePositiveDouble(_thresholdController.text);
    final double? probabilityLimit = _parsePositiveDouble(
      _probabilityLimitController.text,
    );
    final double? probabilityCap = _parsePositiveDouble(
      _probabilityCapController.text,
    );
    final double? contributionRate = _parsePositiveDouble(
      _contributionRateController.text,
    );
    final int? failsafeHours = int.tryParse(
      _failsafeHoursController.text.trim(),
    );
    final double? topSplitPercent = _parsePositiveDouble(
      _topSplitPercentController.text,
    );
    final double? minActivityScore = _parsePositiveDouble(
      _minActivityScoreController.text,
    );
    if (threshold == null ||
        probabilityLimit == null ||
        probabilityCap == null ||
        contributionRate == null ||
        failsafeHours == null ||
        failsafeHours < 1 ||
        topSplitPercent == null ||
        minActivityScore == null) {
      AppFeedback.showError(
        context,
        'Enter valid runtime values before saving jackpot controls.',
      );
      return;
    }
    setState(() {
      _savingRuntime = true;
    });
    try {
      final GteAuthedApi api = widget.dependencies.createAuthedApi();
      await api.post(
        '/admin/jackpot/runtime',
        auth: true,
        body: <String, Object?>{
          'threshold_amount': _decimalString(threshold),
          'probability_limit': _decimalString(probabilityLimit),
          'probability_cap': _decimalString(probabilityCap),
          'failsafe_hours': failsafeHours,
          'contribution_rate': _decimalString(contributionRate),
          'distribution_mode': _distributionMode,
          'top_split_percent': _decimalString(topSplitPercent),
          'min_activity_score': _decimalString(minActivityScore),
        },
      );
      if (!mounted) {
        return;
      }
      AppFeedback.showSuccess(context, 'Jackpot runtime updated.');
      await _load(hydrateAdminFields: true);
    } catch (error) {
      if (!mounted) {
        return;
      }
      AppFeedback.showError(context, AppFeedback.messageFor(error));
    } finally {
      if (mounted) {
        setState(() {
          _savingRuntime = false;
        });
      }
    }
  }

  Future<void> _triggerRound() async {
    setState(() {
      _triggeringRound = true;
    });
    try {
      final GteAuthedApi api = widget.dependencies.createAuthedApi();
      final Object? payload = await api.post(
        '/admin/jackpot/trigger',
        auth: true,
        body: const <String, Object?>{},
      );
      if (!mounted) {
        return;
      }
      final String detail =
          _mapFrom(payload)['detail']?.toString() ?? 'Jackpot round triggered.';
      AppFeedback.showSuccess(context, detail);
      await _load(hydrateAdminFields: true);
    } catch (error) {
      if (!mounted) {
        return;
      }
      AppFeedback.showError(context, AppFeedback.messageFor(error));
    } finally {
      if (mounted) {
        setState(() {
          _triggeringRound = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('GTEX jackpot'),
          actions: <Widget>[
            IconButton(
              onPressed:
                  _loading ? null : () => _load(hydrateAdminFields: false),
              icon: const Icon(Icons.refresh),
            ),
          ],
        ),
        body: _buildBody(context),
      ),
    );
  }

  Widget _buildBody(BuildContext context) {
    if (_loading && _state == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null && _state == null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 620),
            child: GteStatePanel(
              title: 'GTEX jackpot unavailable',
              message: _error!,
              actionLabel: 'Retry',
              onAction: _load,
              icon: Icons.celebration_outlined,
              accentColor: GteShellTheme.accentWarm,
            ),
          ),
        ),
      );
    }

    final _JackpotState state = _state!;
    return RefreshIndicator(
      onRefresh: () => _load(hydrateAdminFields: false),
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 120),
        children: <Widget>[
          GteSurfacePanel(
            emphasized: true,
            accentColor: GteShellTheme.accentWarm,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'GTEX JACKPOT',
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: GteShellTheme.accentWarm,
                    letterSpacing: 1.1,
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  'Round ${state.roundNumber} is ${_humanize(state.status)}',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 8),
                Text(
                  'This is the dedicated GTEX jackpot runtime. It is separate from competition prize-pool jackpot labels.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: <Widget>[
                    GteMetricChip(
                      label: 'Balance',
                      value: gteFormatCredits(state.balance),
                      positive: state.balance > 0,
                    ),
                    GteMetricChip(
                      label: 'Participants',
                      value: state.participantCount.toString(),
                    ),
                    GteMetricChip(
                      label: 'Threshold',
                      value: gteFormatCredits(state.thresholdAmount),
                    ),
                    GteMetricChip(
                      label: 'Distribution',
                      value: _humanize(state.distributionMode),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                Text(
                  'Trigger profile: ${gteFormatCredits(state.thresholdAmount)} threshold, ${_percentLabel(state.probabilityCap)} probability cap, ${gteFormatCredits(state.probabilityLimit)} probability ceiling, failsafe ${gteFormatDateTime(state.failsafeAt)}.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          GteSurfacePanel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Live signal',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: <Widget>[
                    GteMetricChip(
                      label: 'Contribution rate',
                      value: _percentLabel(state.contributionRate),
                    ),
                    GteMetricChip(
                      label: 'Last trigger',
                      value: _humanize(state.lastTriggerMode ?? 'none'),
                    ),
                    GteMetricChip(
                      label: 'Last winner',
                      value: state.lastWinnerUserId ?? 'No winner yet',
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          _buildContributionPanel(context, state),
          if (_isAdmin && _adminRuntime != null) ...<Widget>[
            const SizedBox(height: 18),
            _buildAdminPanel(context, _adminRuntime!),
          ],
          const SizedBox(height: 18),
          GteSurfacePanel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Recent rounds',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 12),
                if (_history.isEmpty)
                  const Text('No jackpot rounds have settled yet.')
                else
                  ..._history.map(
                    (_JackpotHistoryItem item) => _HistoryTile(item: item),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildContributionPanel(BuildContext context, _JackpotState state) {
    if (!_isAuthenticated) {
      return GteSurfacePanel(
        accentColor: GteShellTheme.accentCapital,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Join the pool',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 10),
            const Text(
              'Sign in to contribute GTEX Coin directly from your wallet and appear in the current jackpot participant set.',
            ),
            const SizedBox(height: 14),
            FilledButton.icon(
              onPressed: _openLogin,
              icon: const Icon(Icons.login_outlined),
              label: const Text('Sign in to contribute'),
            ),
          ],
        ),
      );
    }
    return GteSurfacePanel(
      accentColor: GteShellTheme.accentCapital,
      emphasized: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Contribute from wallet',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 10),
          if (_walletAvailability == null) ...<Widget>[
            const GteStatePanel(
              title: 'Wallet availability syncing',
              message:
                  'Capital wallet availability has not arrived yet. Contributions stay blocked until the backend confirms available GTEX Coin.',
              icon: Icons.sync_problem_outlined,
            ),
          ] else if (!_walletAvailability!.isAvailable) ...<Widget>[
            GteStatePanel(
              title: 'Wallet contribution blocked',
              message:
                  _walletAvailability!.blockedReason ??
                  'Capital reports this wallet as unavailable for direct jackpot contributions.',
              icon: Icons.lock_outline,
            ),
          ] else ...<Widget>[
            Text(
              'Wallet available: ${gteFormatCredits(_walletAvailability!.availableBalanceCoin)}. Direct contributions use the exact GTEX Coin amount you enter and settle immediately into the live jackpot pool.',
            ),
            const SizedBox(height: 14),
            TextField(
              controller: _contributionAmountController,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              decoration: const InputDecoration(
                labelText: 'Contribution amount (GTEX Coin)',
                hintText: '50',
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'Current round threshold: ${gteFormatCredits(state.thresholdAmount)}. Contribution rate remains visible for system-driven activity, but direct wallet contributions are now explicit.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 14),
            FilledButton.icon(
              onPressed: _submittingContribution ? null : _submitContribution,
              icon: const Icon(Icons.account_balance_wallet_outlined),
              label: Text(
                _submittingContribution ? 'Submitting...' : 'Contribute now',
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildAdminPanel(BuildContext context, _JackpotRuntime runtime) {
    return GteSurfacePanel(
      accentColor: GteShellTheme.accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Admin controls', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          const Text(
            'These controls update the live jackpot runtime and the current open round. Use them to tune thresholds and force settlement when the pool needs intervention.',
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              SizedBox(
                width: 220,
                child: _PanelField(
                  controller: _thresholdController,
                  label: 'Threshold',
                ),
              ),
              SizedBox(
                width: 220,
                child: _PanelField(
                  controller: _probabilityLimitController,
                  label: 'Probability limit',
                ),
              ),
              SizedBox(
                width: 220,
                child: _PanelField(
                  controller: _probabilityCapController,
                  label: 'Probability cap',
                ),
              ),
              SizedBox(
                width: 220,
                child: _PanelField(
                  controller: _contributionRateController,
                  label: 'Contribution rate',
                ),
              ),
              SizedBox(
                width: 220,
                child: _PanelField(
                  controller: _topSplitPercentController,
                  label: 'Top split percent',
                ),
              ),
              SizedBox(
                width: 220,
                child: _PanelField(
                  controller: _minActivityScoreController,
                  label: 'Min activity score',
                ),
              ),
              SizedBox(
                width: 220,
                child: _PanelField(
                  controller: _failsafeHoursController,
                  label: 'Failsafe hours',
                  keyboardType: TextInputType.number,
                ),
              ),
              SizedBox(
                width: 220,
                child: DropdownButtonFormField<String>(
                  value: _distributionMode,
                  isExpanded: true,
                  items: const <DropdownMenuItem<String>>[
                    DropdownMenuItem(
                      value: 'single_winner',
                      child: Text('Single winner'),
                    ),
                    DropdownMenuItem(
                      value: 'top_split',
                      child: Text('Top split'),
                    ),
                    DropdownMenuItem(
                      value: 'activity_weighted',
                      child: Text('Activity weighted'),
                    ),
                  ],
                  onChanged: (String? value) {
                    if (value == null) {
                      return;
                    }
                    setState(() {
                      _distributionMode = value;
                    });
                  },
                  decoration: const InputDecoration(
                    labelText: 'Distribution mode',
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.icon(
                onPressed: _savingRuntime ? null : _saveRuntime,
                icon: const Icon(Icons.save_outlined),
                label: Text(_savingRuntime ? 'Saving...' : 'Save runtime'),
              ),
              FilledButton.tonalIcon(
                onPressed: _triggeringRound ? null : _triggerRound,
                icon: const Icon(Icons.bolt_outlined),
                label: Text(
                  _triggeringRound ? 'Triggering...' : 'Manual trigger',
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'Live runtime snapshot: threshold ${gteFormatCredits(runtime.thresholdAmount)}, contribution ${_percentLabel(runtime.contributionRate)}, failsafe ${runtime.failsafeHours}h, min activity ${_decimalInput(runtime.minActivityScore)}.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}

class _PanelField extends StatelessWidget {
  const _PanelField({
    required this.controller,
    required this.label,
    this.keyboardType = const TextInputType.numberWithOptions(decimal: true),
  });

  final TextEditingController controller;
  final String label;
  final TextInputType keyboardType;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      keyboardType: keyboardType,
      decoration: InputDecoration(labelText: label),
    );
  }
}

class _HistoryTile extends StatelessWidget {
  const _HistoryTile({required this.item});

  final _JackpotHistoryItem item;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: GteSurfacePanel(
        accentColor:
            item.status == 'settled'
                ? GteShellTheme.positive
                : GteShellTheme.accentWarm,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Round ${item.roundNumber} | ${_humanize(item.status)}',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 6),
            Text(
              'Trigger: ${_humanize(item.triggerMode ?? 'n/a')} | Balance ${gteFormatCredits(item.currentBalance)}',
            ),
            if (item.winningUserId != null) ...<Widget>[
              const SizedBox(height: 4),
              Text('Winner: ${item.winningUserId}'),
            ],
            if (item.triggeredAt != null) ...<Widget>[
              const SizedBox(height: 4),
              Text('Triggered: ${gteFormatDateTime(item.triggeredAt)}'),
            ],
            if (item.payouts.isNotEmpty) ...<Widget>[
              const SizedBox(height: 10),
              for (
                int index = 0;
                index < item.payouts.length && index < 3;
                index++
              ) ...<Widget>[
                Text(
                  'Rank ${item.payouts[index].rank}: ${gteFormatCredits(item.payouts[index].payoutAmount)} to ${item.payouts[index].userId}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                if (index < item.payouts.length - 1 && index < 2)
                  const SizedBox(height: 4),
              ],
            ],
          ],
        ),
      ),
    );
  }
}

class _JackpotState {
  const _JackpotState({
    required this.roundId,
    required this.roundNumber,
    required this.status,
    required this.balance,
    required this.thresholdAmount,
    required this.probabilityLimit,
    required this.probabilityCap,
    required this.contributionRate,
    required this.participantCount,
    required this.failsafeAt,
    required this.distributionMode,
    required this.lastWinnerUserId,
    required this.lastTriggerMode,
  });

  factory _JackpotState.fromJson(Map<String, Object?> json) {
    return _JackpotState(
      roundId: _stringFrom(json, const <String>['round_id', 'roundId']),
      roundNumber: _intFrom(json, const <String>[
        'round_number',
        'roundNumber',
      ]),
      status: _stringFrom(json, const <String>['status']),
      balance: _doubleFrom(json, const <String>['balance']),
      thresholdAmount: _doubleFrom(json, const <String>[
        'threshold_amount',
        'thresholdAmount',
      ]),
      probabilityLimit: _doubleFrom(json, const <String>[
        'probability_limit',
        'probabilityLimit',
      ]),
      probabilityCap: _doubleFrom(json, const <String>[
        'probability_cap',
        'probabilityCap',
      ]),
      contributionRate: _doubleFrom(json, const <String>[
        'contribution_rate',
        'contributionRate',
      ]),
      participantCount: _intFrom(json, const <String>[
        'participant_count',
        'participantCount',
      ]),
      failsafeAt: _dateTimeFrom(json, const <String>[
        'failsafe_at',
        'failsafeAt',
      ]),
      distributionMode: _stringFrom(json, const <String>[
        'distribution_mode',
        'distributionMode',
      ]),
      lastWinnerUserId: _optionalStringFrom(json, const <String>[
        'last_winner_user_id',
        'lastWinnerUserId',
      ]),
      lastTriggerMode: _optionalStringFrom(json, const <String>[
        'last_trigger_mode',
        'lastTriggerMode',
      ]),
    );
  }

  final String roundId;
  final int roundNumber;
  final String status;
  final double balance;
  final double thresholdAmount;
  final double probabilityLimit;
  final double probabilityCap;
  final double contributionRate;
  final int participantCount;
  final DateTime? failsafeAt;
  final String distributionMode;
  final String? lastWinnerUserId;
  final String? lastTriggerMode;
}

class _JackpotRuntime extends _JackpotState {
  const _JackpotRuntime({
    required super.roundId,
    required super.roundNumber,
    required super.status,
    required super.balance,
    required super.thresholdAmount,
    required super.probabilityLimit,
    required super.probabilityCap,
    required super.contributionRate,
    required super.participantCount,
    required super.failsafeAt,
    required super.distributionMode,
    required super.lastWinnerUserId,
    required super.lastTriggerMode,
    required this.topSplitPercent,
    required this.minActivityScore,
    required this.failsafeHours,
  });

  factory _JackpotRuntime.fromJson(Map<String, Object?> json) {
    final _JackpotState base = _JackpotState.fromJson(json);
    return _JackpotRuntime(
      roundId: base.roundId,
      roundNumber: base.roundNumber,
      status: base.status,
      balance: base.balance,
      thresholdAmount: base.thresholdAmount,
      probabilityLimit: base.probabilityLimit,
      probabilityCap: base.probabilityCap,
      contributionRate: base.contributionRate,
      participantCount: base.participantCount,
      failsafeAt: base.failsafeAt,
      distributionMode: base.distributionMode,
      lastWinnerUserId: base.lastWinnerUserId,
      lastTriggerMode: base.lastTriggerMode,
      topSplitPercent: _doubleFrom(json, const <String>[
        'top_split_percent',
        'topSplitPercent',
      ]),
      minActivityScore: _doubleFrom(json, const <String>[
        'min_activity_score',
        'minActivityScore',
      ]),
      failsafeHours: _intFrom(json, const <String>[
        'failsafe_hours',
        'failsafeHours',
      ]),
    );
  }

  final double topSplitPercent;
  final double minActivityScore;
  final int failsafeHours;
}

class _JackpotHistoryItem {
  const _JackpotHistoryItem({
    required this.roundNumber,
    required this.status,
    required this.triggerMode,
    required this.currentBalance,
    required this.winningUserId,
    required this.triggeredAt,
    required this.payouts,
  });

  factory _JackpotHistoryItem.fromJson(Map<String, Object?> json) {
    return _JackpotHistoryItem(
      roundNumber: _intFrom(json, const <String>[
        'round_number',
        'roundNumber',
      ]),
      status: _stringFrom(json, const <String>['status']),
      triggerMode: _optionalStringFrom(json, const <String>[
        'trigger_mode',
        'triggerMode',
      ]),
      currentBalance: _doubleFrom(json, const <String>[
        'current_balance',
        'currentBalance',
      ]),
      winningUserId: _optionalStringFrom(json, const <String>[
        'winning_user_id',
        'winningUserId',
      ]),
      triggeredAt: _dateTimeFrom(json, const <String>[
        'triggered_at',
        'triggeredAt',
      ]),
      payouts: _listFrom(json['payouts'])
          .map((Object? item) => _JackpotPayout.fromJson(_mapFrom(item)))
          .toList(growable: false),
    );
  }

  final int roundNumber;
  final String status;
  final String? triggerMode;
  final double currentBalance;
  final String? winningUserId;
  final DateTime? triggeredAt;
  final List<_JackpotPayout> payouts;
}

class _JackpotPayout {
  const _JackpotPayout({
    required this.userId,
    required this.rank,
    required this.payoutAmount,
  });

  factory _JackpotPayout.fromJson(Map<String, Object?> json) {
    return _JackpotPayout(
      userId: _stringFrom(json, const <String>['user_id', 'userId']),
      rank: _intFrom(json, const <String>['rank']),
      payoutAmount: _doubleFrom(json, const <String>[
        'payout_amount',
        'payoutAmount',
      ]),
    );
  }

  final String userId;
  final int rank;
  final double payoutAmount;
}

Map<String, Object?> _mapFrom(Object? value) {
  if (value is Map<String, Object?>) {
    return value;
  }
  if (value is Map) {
    return value.map(
      (Object? key, Object? entryValue) =>
          MapEntry<String, Object?>(key.toString(), entryValue),
    );
  }
  return <String, Object?>{};
}

List<Object?> _listFrom(Object? value) {
  if (value is List<Object?>) {
    return value;
  }
  if (value is List) {
    return value.cast<Object?>();
  }
  return const <Object?>[];
}

String _stringFrom(Map<String, Object?> json, List<String> keys) {
  return _optionalStringFrom(json, keys) ?? '';
}

String? _optionalStringFrom(Map<String, Object?> json, List<String> keys) {
  for (final String key in keys) {
    final Object? value = json[key];
    if (value == null) {
      continue;
    }
    final String resolved = value.toString().trim();
    if (resolved.isNotEmpty) {
      return resolved;
    }
  }
  return null;
}

double _doubleFrom(Map<String, Object?> json, List<String> keys) {
  for (final String key in keys) {
    final Object? value = json[key];
    if (value is num) {
      return value.toDouble();
    }
    final double? parsed = double.tryParse(value?.toString() ?? '');
    if (parsed != null) {
      return parsed;
    }
  }
  return 0;
}

int _intFrom(Map<String, Object?> json, List<String> keys) {
  for (final String key in keys) {
    final Object? value = json[key];
    if (value is int) {
      return value;
    }
    if (value is num) {
      return value.toInt();
    }
    final int? parsed = int.tryParse(value?.toString() ?? '');
    if (parsed != null) {
      return parsed;
    }
  }
  return 0;
}

DateTime? _dateTimeFrom(Map<String, Object?> json, List<String> keys) {
  final String? value = _optionalStringFrom(json, keys);
  if (value == null) {
    return null;
  }
  return DateTime.tryParse(value)?.toUtc();
}

CapitalWalletAvailability? _walletAvailabilityFrom(Object? value) {
  if (value is CapitalWalletAvailability) {
    return value;
  }
  final Map<String, Object?> json = _mapFrom(value);
  if (json.isEmpty) {
    return null;
  }
  return CapitalWalletAvailability.fromJson(json);
}

double? _parsePositiveDouble(String raw) {
  final double? value = double.tryParse(raw.trim());
  if (value == null || value <= 0) {
    return null;
  }
  return value;
}

String _decimalString(double value) {
  return value.toStringAsFixed(4);
}

String _decimalInput(double value) {
  final bool whole = value == value.roundToDouble();
  return value.toStringAsFixed(whole ? 0 : 4);
}

String _percentLabel(double value) {
  return '${(value * 100).toStringAsFixed(value == value.roundToDouble() ? 0 : 2)}%';
}

String _humanize(String raw) {
  final String trimmed = raw.trim();
  if (trimmed.isEmpty) {
    return '--';
  }
  return trimmed
      .split(RegExp(r'[_\s-]+'))
      .where((String part) => part.isNotEmpty)
      .map(
        (String part) =>
            '${part[0].toUpperCase()}${part.substring(1).toLowerCase()}',
      )
      .join(' ');
}
