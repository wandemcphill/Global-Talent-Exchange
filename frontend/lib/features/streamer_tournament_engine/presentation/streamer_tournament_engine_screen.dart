import 'package:flutter/material.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/shared/presentation/gte_feature_forms.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

import '../data/streamer_tournament_engine_models.dart';
import 'streamer_tournament_engine_controller.dart';

class StreamerTournamentEngineScreen extends StatefulWidget {
  const StreamerTournamentEngineScreen({
    super.key,
    required this.baseUrl,
    required this.backendMode,
    this.accessToken,
    this.currentUserId,
    this.currentUserRole,
    this.tournamentId,
    this.onOpenLogin,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final String? currentUserId;
  final String? currentUserRole;
  final String? tournamentId;
  final VoidCallback? onOpenLogin;

  @override
  State<StreamerTournamentEngineScreen> createState() =>
      _StreamerTournamentEngineScreenState();
}

class _StreamerTournamentEngineScreenState
    extends State<StreamerTournamentEngineScreen> {
  late final StreamerTournamentEngineController _controller;

  bool get _isAuthenticated =>
      widget.accessToken != null && widget.accessToken!.trim().isNotEmpty;
  bool get _isAdmin => <String>{'admin', 'super_admin'}
      .contains((widget.currentUserRole ?? '').trim().toLowerCase());

  @override
  void initState() {
    super.initState();
    _controller = StreamerTournamentEngineController.standard(
      baseUrl: widget.baseUrl,
      backendMode: widget.backendMode,
      accessToken: widget.accessToken,
    );
    _load();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  StreamerTournament? get _tournament => _controller.tournament;

  Future<void> _load() async {
    await _controller.loadLists(includeMine: _isAuthenticated);
    if (widget.tournamentId?.trim().isNotEmpty == true) {
      await _controller.loadTournament(widget.tournamentId!.trim());
    }
    if (_isAdmin) {
      await _controller.loadAdmin();
    }
  }

  Future<void> _run(Future<void> Function() action, String success) async {
    await action();
    if (!mounted) {
      return;
    }
    if ((_controller.actionError ?? '').trim().isNotEmpty) {
      AppFeedback.showError(context, _controller.actionError!);
    } else {
      AppFeedback.showSuccess(context, success);
    }
  }

  Future<void> _simpleTournamentForm({
    required String title,
    required Future<void> Function(Map<String, String> values) submit,
    bool includeCapacity = true,
  }) async {
    await showGteFormSheet(
      context,
      title: title,
      fields: <GteFormFieldSpec>[
        const GteFormFieldSpec(key: 'title', label: 'Title'),
        const GteFormFieldSpec(key: 'type', label: 'Tournament type'),
        if (includeCapacity)
          const GteFormFieldSpec(
            key: 'capacity',
            label: 'Max participants',
            keyboardType: TextInputType.number,
          ),
      ],
      onSubmit: (Map<String, String> values) async {
        await submit(values);
        return _controller.actionError == null;
      },
    );
  }

  Future<void> _createTournament() {
    return _simpleTournamentForm(
      title: 'Create tournament',
      submit: (Map<String, String> values) async {
        final int? capacity = int.tryParse(values['capacity'] ?? '');
        if ((values['title'] ?? '').isEmpty ||
            (values['type'] ?? '').isEmpty ||
            capacity == null) {
          AppFeedback.showError(context, 'Enter title, type, and capacity.');
          return;
        }
        await _run(
          () => _controller.createTournament(
            StreamerTournamentCreateRequest(
              title: values['title']!,
              tournamentType: values['type']!,
              maxParticipants: capacity,
            ),
          ),
          'Tournament created.',
        );
      },
    );
  }

  Future<void> _updateTournament() async {
    final StreamerTournament? tournament = _tournament;
    if (tournament == null) {
      return;
    }
    await _simpleTournamentForm(
      title: 'Update tournament',
      submit: (Map<String, String> values) async {
        final int? capacity = int.tryParse(values['capacity'] ?? '');
        await _run(
          () => _controller.updateTournament(
            tournament.id,
            StreamerTournamentUpdateRequest(
              title: values['title'],
              maxParticipants: capacity,
              description: tournament.description,
            ),
          ),
          'Tournament updated.',
        );
      },
    );
  }

  Future<void> _replaceRewardPlan() async {
    final StreamerTournament? tournament = _tournament;
    if (tournament == null) {
      return;
    }
    await _run(
      () => _controller.replaceRewardPlan(
        tournament.id,
        const StreamerTournamentRewardPlanReplaceRequest(
          rewards: <StreamerTournamentRewardInput>[
            StreamerTournamentRewardInput(
              title: 'Winner payout',
              rewardType: 'coin',
              placementStart: 1,
              placementEnd: 1,
              amount: 500,
            ),
          ],
        ),
      ),
      'Reward plan updated.',
    );
  }

  Future<void> _inviteToTournament() async {
    final StreamerTournament? tournament = _tournament;
    if (tournament == null) {
      return;
    }
    await showGteFormSheet(
      context,
      title: 'Create invite',
      fields: const <GteFormFieldSpec>[
        GteFormFieldSpec(key: 'userId', label: 'User id'),
      ],
      onSubmit: (Map<String, String> values) async {
        if ((values['userId'] ?? '').isEmpty) {
          AppFeedback.showError(context, 'Enter a user id.');
          return false;
        }
        await _run(
          () => _controller.createInvite(
            tournament.id,
            StreamerTournamentInviteCreateRequest(userId: values['userId']!),
          ),
          'Invite created.',
        );
        return _controller.actionError == null;
      },
    );
  }

  Future<void> _updatePolicy() async {
    await showGteFormSheet(
      context,
      title: 'Update policy',
      fields: const <GteFormFieldSpec>[
        GteFormFieldSpec(
          key: 'coin',
          label: 'Reward coin approval limit',
          keyboardType: TextInputType.number,
        ),
        GteFormFieldSpec(
          key: 'credit',
          label: 'Reward credit approval limit',
          keyboardType: TextInputType.number,
        ),
        GteFormFieldSpec(
          key: 'invites',
          label: 'Max invites',
          keyboardType: TextInputType.number,
        ),
      ],
      onSubmit: (Map<String, String> values) async {
        final double? coin = double.tryParse(values['coin'] ?? '');
        final double? credit = double.tryParse(values['credit'] ?? '');
        final int? invites = int.tryParse(values['invites'] ?? '');
        if (coin == null || credit == null || invites == null) {
          AppFeedback.showError(context, 'Enter valid policy values.');
          return false;
        }
        await _run(
          () => _controller.upsertPolicy(
            StreamerTournamentPolicyUpsertRequest(
              rewardCoinApprovalLimit: coin,
              rewardCreditApprovalLimit: credit,
              maxInvitesPerTournament: invites,
            ),
          ),
          'Policy updated.',
        );
        return _controller.actionError == null;
      },
    );
  }

  Future<void> _reviewAndSettle({required bool approve}) async {
    final StreamerTournament? tournament = _tournament;
    if (tournament == null) {
      return;
    }
    await _run(
      () => _controller.reviewTournament(
        tournament.id,
        StreamerTournamentReviewRequest(approve: approve),
      ),
      approve ? 'Tournament approved.' : 'Tournament rejected.',
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Streamer tournament engine'),
          actions: <Widget>[
            IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
          ],
        ),
        body: AnimatedBuilder(
          animation: _controller,
          builder: (BuildContext context, Widget? child) {
            final StreamerTournament? tournament = _tournament;
            final List<StreamerTournament> publicItems =
                _controller.publicTournaments.tournaments;
            final List<StreamerTournament> myItems =
                _controller.myTournaments.tournaments;
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
                          'Tournament creation, invites, rewards, review, and settlement are wired to the canonical streamer engine.',
                          style: Theme.of(context).textTheme.bodyLarge,
                        ),
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: <Widget>[
                            GteMetricChip(
                              label: 'Public',
                              value: publicItems.length.toString(),
                            ),
                            GteMetricChip(
                              label: 'Mine',
                              value: myItems.length.toString(),
                            ),
                            GteMetricChip(
                              label: 'Risk',
                              value: _controller.riskSignals.length.toString(),
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 12,
                          runSpacing: 12,
                          children: <Widget>[
                            FilledButton.icon(
                              onPressed: _isAuthenticated
                                  ? _createTournament
                                  : widget.onOpenLogin,
                              icon: Icon(
                                _isAuthenticated ? Icons.add : Icons.login,
                              ),
                              label: Text(
                                _isAuthenticated
                                    ? 'Create tournament'
                                    : 'Sign in to create',
                              ),
                            ),
                            if (tournament != null)
                              FilledButton.tonalIcon(
                                onPressed: _updateTournament,
                                icon: const Icon(Icons.edit_outlined),
                                label: const Text('Update'),
                              ),
                            if (tournament != null)
                              FilledButton.tonalIcon(
                                onPressed: _replaceRewardPlan,
                                icon: const Icon(
                                    Icons.workspace_premium_outlined),
                                label: const Text('Rewards'),
                              ),
                            if (tournament != null && _isAuthenticated)
                              FilledButton.tonalIcon(
                                onPressed: _inviteToTournament,
                                icon: const Icon(Icons.person_add_alt_1),
                                label: const Text('Invite'),
                              ),
                            if (tournament != null && _isAuthenticated)
                              FilledButton.tonalIcon(
                                onPressed: () => _run(
                                  () => _controller.joinTournament(
                                    tournament.id,
                                    const StreamerTournamentJoinRequest(),
                                  ),
                                  'Tournament join submitted.',
                                ),
                                icon: const Icon(Icons.group_add_outlined),
                                label: const Text('Join'),
                              ),
                            if (tournament != null && _isAuthenticated)
                              FilledButton.tonalIcon(
                                onPressed: () => _run(
                                  () => _controller.publishTournament(
                                    tournament.id,
                                    const StreamerTournamentPublishRequest(),
                                  ),
                                  'Tournament published.',
                                ),
                                icon: const Icon(Icons.publish_outlined),
                                label: const Text('Publish'),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  _TournamentSection(
                    title: 'Public tournaments',
                    tournaments: publicItems,
                    selectedId: tournament?.id,
                    onTap: (StreamerTournament item) =>
                        _controller.loadTournament(item.id),
                  ),
                  const SizedBox(height: 18),
                  _TournamentSection(
                    title:
                        _isAuthenticated ? 'My tournaments' : 'Signed-out view',
                    tournaments: myItems,
                    selectedId: tournament?.id,
                    emptyMessage: _isAuthenticated
                        ? 'Create or join a tournament to populate this section.'
                        : 'Sign in to load tournaments tied to your account.',
                    onTap: (StreamerTournament item) =>
                        _controller.loadTournament(item.id),
                  ),
                  const SizedBox(height: 18),
                  if (_controller.isLoadingTournament && tournament == null)
                    const GteStatePanel(
                      title: 'Loading tournament',
                      message:
                          'Entries, rewards, invites, and review state are syncing.',
                      icon: Icons.live_tv_outlined,
                      isLoading: true,
                    )
                  else
                    GteSurfacePanel(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text('Tournament detail',
                              style: Theme.of(context).textTheme.titleLarge),
                          const SizedBox(height: 10),
                          if (tournament == null)
                            const Text('Select a tournament to inspect detail.')
                          else
                            Text(
                              '${tournament.title}\n${tournament.status} • ${tournament.approvalStatus}\nEntries ${tournament.entries.length}/${tournament.maxParticipants}\nInvites ${tournament.invites.length}\nRewards ${tournament.rewards.length}',
                              style: Theme.of(context).textTheme.bodyMedium,
                            ),
                        ],
                      ),
                    ),
                  if (_isAdmin) ...<Widget>[
                    const SizedBox(height: 18),
                    GteSurfacePanel(
                      accentColor: GteShellTheme.accentAdmin,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text('Admin review',
                              style: Theme.of(context).textTheme.titleLarge),
                          const SizedBox(height: 10),
                          Text(
                            _controller.policy == null
                                ? 'Tournament policy is syncing.'
                                : 'Coin cap ${_controller.policy!.rewardCoinApprovalLimit} • credit cap ${_controller.policy!.rewardCreditApprovalLimit} • invite cap ${_controller.policy!.maxInvitesPerTournament}',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                          const SizedBox(height: 12),
                          Wrap(
                            spacing: 12,
                            runSpacing: 12,
                            children: <Widget>[
                              FilledButton.tonalIcon(
                                onPressed: _updatePolicy,
                                icon: const Icon(Icons.policy_outlined),
                                label: const Text('Policy'),
                              ),
                              if (tournament != null)
                                FilledButton.tonalIcon(
                                  onPressed: () =>
                                      _reviewAndSettle(approve: true),
                                  icon: const Icon(Icons.verified_outlined),
                                  label: const Text('Approve'),
                                ),
                              if (tournament != null)
                                FilledButton.tonalIcon(
                                  onPressed: () =>
                                      _reviewAndSettle(approve: false),
                                  icon: const Icon(Icons.block_outlined),
                                  label: const Text('Reject'),
                                ),
                              if (tournament != null)
                                FilledButton.tonalIcon(
                                  onPressed: () => _run(
                                    () => _controller.settleTournament(
                                      tournament.id,
                                      StreamerTournamentSettleRequest(
                                        placements: <StreamerTournamentSettlementPlacement>[
                                          StreamerTournamentSettlementPlacement(
                                            userId: tournament.hostUserId,
                                            placement: 1,
                                          ),
                                        ],
                                      ),
                                    ),
                                    'Tournament settled.',
                                  ),
                                  icon: const Icon(Icons.rule_outlined),
                                  label: const Text('Settle'),
                                ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          Text(
                            _controller.riskSignals.isEmpty
                                ? 'No open risk signals.'
                                : '${_controller.riskSignals.length} risk signals available for review.',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            );
          },
        ),
      ),
    );
  }
}

class _TournamentSection extends StatelessWidget {
  const _TournamentSection({
    required this.title,
    required this.tournaments,
    required this.selectedId,
    required this.onTap,
    this.emptyMessage = 'No tournaments available.',
  });

  final String title;
  final List<StreamerTournament> tournaments;
  final String? selectedId;
  final String emptyMessage;
  final ValueChanged<StreamerTournament> onTap;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          if (tournaments.isEmpty)
            Text(emptyMessage)
          else
            ...tournaments.map(
              (StreamerTournament item) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: GteSurfacePanel(
                  accentColor:
                      selectedId == item.id ? GteShellTheme.accentArena : null,
                  onTap: () => onTap(item),
                  child: Text(
                    '${item.title}\n${item.status} • ${item.approvalStatus} • ${item.entries.length}/${item.maxParticipants}',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
