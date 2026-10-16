import 'package:flutter/material.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/shared/presentation/gte_feature_forms.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

import '../data/fan_prediction_models.dart';
import 'fan_prediction_controller.dart';

class FanPredictionScreen extends StatefulWidget {
  const FanPredictionScreen({
    super.key,
    required this.baseUrl,
    required this.backendMode,
    this.accessToken,
    this.currentUserRole,
    this.matchId,
    this.onOpenLogin,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final String? currentUserRole;
  final String? matchId;
  final VoidCallback? onOpenLogin;

  @override
  State<FanPredictionScreen> createState() => _FanPredictionScreenState();
}

class _FanPredictionScreenState extends State<FanPredictionScreen> {
  late final FanPredictionController _controller;
  String? _resolvedMatchId;

  bool get _isAuthenticated =>
      widget.accessToken != null && widget.accessToken!.trim().isNotEmpty;

  bool get _isAdmin => <String>{'admin', 'super_admin'}
      .contains((widget.currentUserRole ?? '').trim().toLowerCase());

  String? get _matchId {
    final String? value = _resolvedMatchId ?? widget.matchId;
    if (value == null) {
      return null;
    }
    final String trimmed = value.trim();
    if (trimmed.isEmpty || trimmed == 'featured') {
      return null;
    }
    return trimmed;
  }

  @override
  void initState() {
    super.initState();
    _controller = FanPredictionController.standard(
      baseUrl: widget.baseUrl,
      backendMode: widget.backendMode,
      accessToken: widget.accessToken,
    );
    _load();
  }

  Future<void> _load() async {
    await _controller.loadLeaderboards();
    if (_isAuthenticated) {
      await _controller.loadProfile();
    }
    final String? matchId = _matchId;
    if (matchId != null) {
      await _controller.loadFixture(matchId);
    }
  }

  Future<void> _run(Future<void> Function() action, String success) async {
    await action();
    if (!mounted) {
      return;
    }
    final String? error = _controller.actionError;
    if (error != null && error.trim().isNotEmpty) {
      AppFeedback.showError(context, error);
    } else {
      AppFeedback.showSuccess(context, success);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Fan predictions'),
          actions: <Widget>[
            IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
          ],
        ),
        body: AnimatedBuilder(
          animation: _controller,
          builder: (BuildContext context, Widget? child) {
            final FanPredictionFixture? fixture = _controller.fixture;
            final FanPredictionTokenSummary? tokens = _controller.tokenSummary;
            return RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
                children: <Widget>[
                  GteSurfacePanel(
                    accentColor: GteShellTheme.accentArena,
                    emphasized: true,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          fixture?.title ?? 'Match-scoped prediction deck',
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _matchId == null
                              ? 'This route will not guess a live match id. Resolve a canonical match id from live match context or enter one directly.'
                              : 'Prediction submissions, leaderboards, and admin settlement are running against the canonical match fixture.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: <Widget>[
                            GteMetricChip(
                              label: 'Match id',
                              value: _matchId ?? 'Unresolved',
                            ),
                            if (fixture != null)
                              GteMetricChip(
                                  label: 'Status', value: fixture.status),
                            if (tokens != null)
                              GteMetricChip(
                                label: 'Tokens',
                                value: tokens.availableTokens.toString(),
                              ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 12,
                          runSpacing: 12,
                          children: <Widget>[
                            FilledButton.tonalIcon(
                              onPressed: _resolveMatchId,
                              icon: const Icon(Icons.link_outlined),
                              label: Text(_matchId == null
                                  ? 'Resolve match id'
                                  : 'Change match id'),
                            ),
                            FilledButton.icon(
                              onPressed: !_isAuthenticated
                                  ? widget.onOpenLogin
                                  : fixture == null
                                      ? null
                                      : _submitPrediction,
                              icon: Icon(
                                _isAuthenticated
                                    ? Icons.send_outlined
                                    : Icons.login,
                              ),
                              label: Text(
                                _isAuthenticated
                                    ? 'Submit prediction'
                                    : 'Sign in to predict',
                              ),
                            ),
                            if (_isAdmin && fixture != null)
                              FilledButton.tonalIcon(
                                onPressed: _configureFixture,
                                icon: const Icon(Icons.tune_outlined),
                                label: const Text('Configure'),
                              ),
                            if (_isAdmin && fixture != null)
                              FilledButton.tonalIcon(
                                onPressed: _settleFixture,
                                icon: const Icon(Icons.rule_outlined),
                                label: const Text('Settle'),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  if (_matchId == null)
                    const GteStatePanel(
                      title: 'Canonical match id required',
                      message:
                          'Competition hub shortcuts do not supply a live match id yet. Open from the live match center or enter a backend match id here.',
                      icon: Icons.route_outlined,
                    )
                  else if (_controller.isLoadingFixture && fixture == null)
                    const GteStatePanel(
                      title: 'Loading fixture',
                      message:
                          'Prediction fixture and match leaderboard are syncing.',
                      icon: Icons.insights_outlined,
                      isLoading: true,
                    )
                  else if (_controller.fixtureError != null && fixture == null)
                    GteStatePanel(
                      title: 'Fixture unavailable',
                      message: _controller.fixtureError!,
                      icon: Icons.error_outline,
                      actionLabel: 'Resolve match id',
                      onAction: _resolveMatchId,
                    )
                  else if (fixture != null)
                    GteSurfacePanel(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text('Fixture',
                              style: Theme.of(context).textTheme.titleLarge),
                          const SizedBox(height: 10),
                          Text(fixture.title,
                              style: Theme.of(context).textTheme.titleMedium),
                          const SizedBox(height: 8),
                          Text(
                            'Status: ${fixture.status} • Token cost: ${fixture.tokenCost} • Reward winners: ${fixture.maxRewardWinners}',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                          if (fixture.mySubmission != null) ...<Widget>[
                            const SizedBox(height: 10),
                            Text(
                              'My submission: ${fixture.mySubmission!.winnerClubId} • goals ${fixture.mySubmission!.totalGoals} • MVP ${fixture.mySubmission!.mvpPlayerId}',
                              style: Theme.of(context).textTheme.bodyMedium,
                            ),
                          ],
                        ],
                      ),
                    ),
                  const SizedBox(height: 18),
                  _LeaderboardCard(
                    title: 'Match leaderboard',
                    entries: _controller.matchLeaderboard?.entries ??
                        const <Map<String, Object?>>[],
                  ),
                  const SizedBox(height: 18),
                  _LeaderboardCard(
                    title: 'Weekly leaderboard',
                    entries: _controller.weeklyLeaderboard?.entries ??
                        const <Map<String, Object?>>[],
                  ),
                  const SizedBox(height: 18),
                  GteSurfacePanel(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text('My prediction profile',
                            style: Theme.of(context).textTheme.titleLarge),
                        const SizedBox(height: 10),
                        if (!_isAuthenticated)
                          const Text(
                              'Sign in to load token summary and submission history.')
                        else if (_controller.isLoadingProfile && tokens == null)
                          const GteStatePanel(
                            title: 'Loading profile',
                            message:
                                'Token balance and prediction history are syncing.',
                            icon: Icons.account_circle_outlined,
                            isLoading: true,
                          )
                        else if (_controller.profileError != null &&
                            tokens == null)
                          GteStatePanel(
                            title: 'Profile unavailable',
                            message: _controller.profileError!,
                            icon: Icons.error_outline,
                          )
                        else
                          Text(
                            'Available tokens: ${tokens?.availableTokens ?? 0}\nDaily refill: ${tokens?.dailyRefillTokens ?? 0}\nSubmissions: ${_controller.mySubmissions.length}',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }

  Future<void> _resolveMatchId() async {
    final Map<String, String>? values = await showGteFormSheet(
      context,
      title: 'Resolve match id',
      fields: <GteFormFieldSpec>[
        GteFormFieldSpec(
          key: 'matchId',
          label: 'Canonical match id',
          initialValue: _matchId ?? '',
        ),
      ],
      onSubmit: (Map<String, String> values) async {
        final String matchId = values['matchId']?.trim() ?? '';
        if (matchId.isEmpty) {
          AppFeedback.showError(context, 'Enter a canonical match id.');
          return false;
        }
        setState(() => _resolvedMatchId = matchId);
        await _controller.loadFixture(matchId);
        return _controller.fixtureError == null;
      },
    );
    if (values != null && _isAuthenticated) {
      await _controller.loadProfile();
    }
  }

  Future<void> _submitPrediction() async {
    final String? matchId = _matchId;
    if (matchId == null) {
      return;
    }
    await showGteFormSheet(
      context,
      title: 'Submit prediction',
      fields: const <GteFormFieldSpec>[
        GteFormFieldSpec(key: 'winner', label: 'Winner club id'),
        GteFormFieldSpec(key: 'scorer', label: 'First goal scorer player id'),
        GteFormFieldSpec(
          key: 'goals',
          label: 'Total goals',
          keyboardType: TextInputType.number,
        ),
        GteFormFieldSpec(key: 'mvp', label: 'MVP player id'),
      ],
      onSubmit: (Map<String, String> values) async {
        final int? goals = int.tryParse(values['goals'] ?? '');
        if ((values['winner'] ?? '').isEmpty ||
            (values['scorer'] ?? '').isEmpty ||
            (values['mvp'] ?? '').isEmpty ||
            goals == null) {
          AppFeedback.showError(context, 'Complete all prediction fields.');
          return false;
        }
        await _run(
          () => _controller.submitPrediction(
            matchId,
            FanPredictionSubmissionRequest(
              winnerClubId: values['winner']!,
              firstGoalScorerPlayerId: values['scorer']!,
              totalGoals: goals,
              mvpPlayerId: values['mvp']!,
            ),
          ),
          'Prediction submitted.',
        );
        return _controller.actionError == null;
      },
    );
  }

  Future<void> _configureFixture() async {
    final String? matchId = _matchId;
    if (matchId == null) {
      return;
    }
    await showGteFormSheet(
      context,
      title: 'Configure fixture',
      fields: const <GteFormFieldSpec>[
        GteFormFieldSpec(key: 'title', label: 'Title'),
        GteFormFieldSpec(
          key: 'tokenCost',
          label: 'Token cost',
          keyboardType: TextInputType.number,
        ),
        GteFormFieldSpec(
          key: 'promoPool',
          label: 'Promo pool fancoin',
          keyboardType: TextInputType.number,
        ),
      ],
      onSubmit: (Map<String, String> values) async {
        final int? tokenCost = int.tryParse(values['tokenCost'] ?? '');
        final double? promoPool = double.tryParse(values['promoPool'] ?? '');
        if ((values['title'] ?? '').isEmpty ||
            tokenCost == null ||
            promoPool == null) {
          AppFeedback.showError(context, 'Enter valid fixture config values.');
          return false;
        }
        await _run(
          () => _controller.configureFixture(
            matchId,
            FanPredictionFixtureConfigRequest(
              title: values['title'],
              tokenCost: tokenCost,
              promoPoolFancoin: promoPool,
            ),
          ),
          'Fixture configured.',
        );
        return _controller.actionError == null;
      },
    );
  }

  Future<void> _settleFixture() async {
    final String? matchId = _matchId;
    if (matchId == null) {
      return;
    }
    await showGteFormSheet(
      context,
      title: 'Settle fixture',
      fields: const <GteFormFieldSpec>[
        GteFormFieldSpec(key: 'winner', label: 'Winner club id'),
        GteFormFieldSpec(key: 'scorer', label: 'First goal scorer player id'),
        GteFormFieldSpec(
          key: 'goals',
          label: 'Total goals',
          keyboardType: TextInputType.number,
        ),
        GteFormFieldSpec(key: 'mvp', label: 'MVP player id'),
      ],
      onSubmit: (Map<String, String> values) async {
        final int? goals = int.tryParse(values['goals'] ?? '');
        if ((values['winner'] ?? '').isEmpty ||
            (values['scorer'] ?? '').isEmpty ||
            (values['mvp'] ?? '').isEmpty ||
            goals == null) {
          AppFeedback.showError(context, 'Complete all settlement fields.');
          return false;
        }
        await _run(
          () => _controller.settleFixture(
            matchId,
            FanPredictionOutcomeOverrideRequest(
              winnerClubId: values['winner'],
              firstGoalScorerPlayerId: values['scorer'],
              totalGoals: goals,
              mvpPlayerId: values['mvp'],
              disburseRewards: true,
            ),
          ),
          'Fixture settled.',
        );
        return _controller.actionError == null;
      },
    );
  }
}

class _LeaderboardCard extends StatelessWidget {
  const _LeaderboardCard({
    required this.title,
    required this.entries,
  });

  final String title;
  final List<Map<String, Object?>> entries;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          if (entries.isEmpty)
            const Text('No entries yet.')
          else
            ...entries.take(5).map(
                  (Map<String, Object?> entry) => Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text(
                      '${entry['display_name'] ?? entry['user_id'] ?? entry['club_id'] ?? 'Entry'} • ${entry['points'] ?? entry['score'] ?? 0}',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ),
                ),
        ],
      ),
    );
  }
}
