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
  bool get _isAdmin => <String>{
    'admin',
    'super_admin',
  }.contains((widget.currentUserRole ?? '').trim().toLowerCase());

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

  Future<void> _load() {
    final List<Future<void>> work = <Future<void>>[
      _controller.loadCompetitionLayer(playerId: widget.currentUserId),
      _controller.loadLists(includeMine: _isAuthenticated),
    ];
    if (widget.tournamentId?.trim().isNotEmpty == true) {
      work.add(_controller.loadTournament(widget.tournamentId!.trim()));
    }
    if (_isAdmin) {
      work.add(_controller.loadAdmin());
    }
    return Future.wait<void>(work);
  }

  Future<void> _run(Future<void> Function() action, String success) async {
    await action();
    if (!mounted) {
      return;
    }
    if ((_controller.actionError ?? '').trim().isNotEmpty) {
      AppFeedback.showError(context, _controller.actionError!);
      return;
    }
    AppFeedback.showSuccess(context, success);
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

  Future<void> _reviewTournament({required bool approve}) async {
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

  Future<void> _settleTournament() async {
    final StreamerTournament? tournament = _tournament;
    if (tournament == null) {
      return;
    }
    await _run(
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
    );
  }

  Map<String, Object?>? _creatorGrowth(StreamerTournament? tournament) {
    final Object? value = tournament?.metadata['creator_growth'];
    if (value is Map) {
      return Map<String, Object?>.from(value);
    }
    return null;
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
            final LeaderboardSeason? season = _controller.currentSeason;
            final LeaderboardBoard? leaderboard = _controller.globalLeaderboard;
            final LeaderboardPlayerRanks? playerRanks =
                _controller.currentPlayerRanks;
            final StreamerTournament? tournament = _tournament;
            final Map<String, Object?>? creatorGrowth = _creatorGrowth(
              tournament,
            );
            final List<LeaderboardSeason> archivedSeasons = _controller
                .seasonHistory
                .seasons
                .where((LeaderboardSeason item) => item.id != season?.id)
                .toList(growable: false);

            return RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
                children: <Widget>[
                  _buildSeasonHero(context, season, leaderboard, playerRanks),
                  const SizedBox(height: 18),
                  _buildSeasonStructure(context, season),
                  const SizedBox(height: 18),
                  _buildLeaderboard(context, leaderboard, playerRanks),
                  const SizedBox(height: 18),
                  _buildSeasonHistory(context, archivedSeasons),
                  const SizedBox(height: 18),
                  _buildTournamentActions(context),
                  const SizedBox(height: 18),
                  _buildTournamentSection(
                    context,
                    title: 'Public tournaments',
                    tournaments: _controller.publicTournaments.tournaments,
                  ),
                  const SizedBox(height: 18),
                  _buildTournamentSection(
                    context,
                    title:
                        _isAuthenticated ? 'My tournaments' : 'Signed-out view',
                    tournaments: _controller.myTournaments.tournaments,
                    emptyMessage:
                        _isAuthenticated
                            ? 'Create or join a tournament to populate this section.'
                            : 'Sign in to load tournaments tied to your account.',
                  ),
                  const SizedBox(height: 18),
                  _buildTournamentDetail(context, tournament, creatorGrowth),
                  if (_isAdmin) ...<Widget>[
                    const SizedBox(height: 18),
                    _buildAdminPanel(context, tournament),
                  ],
                ],
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildSeasonHero(
    BuildContext context,
    LeaderboardSeason? season,
    LeaderboardBoard? leaderboard,
    LeaderboardPlayerRanks? playerRanks,
  ) {
    return GteSurfacePanel(
      accentColor: GteShellTheme.accentArena,
      emphasized: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Season ladder',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Text(
            'Thirty-day competition cycles keep status moving: climb the board, lock in a tier, and cash out season-end rewards before the next reset.',
            style: Theme.of(context).textTheme.bodyLarge,
          ),
          const SizedBox(height: 16),
          if (season == null && _controller.isLoadingCompetition)
            const LinearProgressIndicator(minHeight: 4)
          else
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: <Widget>[
                GteMetricChip(
                  label: 'Days left',
                  value: season?.daysRemaining.toString() ?? '--',
                ),
                GteMetricChip(
                  label: 'Tiers',
                  value: season?.rankTiers.length.toString() ?? '--',
                ),
                GteMetricChip(
                  label: 'Reward slots',
                  value: season?.rewardTiers.length.toString() ?? '--',
                ),
                GteMetricChip(
                  label: 'Leaderboard',
                  value: leaderboard?.entries.length.toString() ?? '--',
                ),
                if (playerRanks != null)
                  GteMetricChip(
                    label: 'My rank',
                    value:
                        playerRanks.globalRank == null
                            ? 'Unranked'
                            : '#${playerRanks.globalRank}',
                  ),
                if (playerRanks != null)
                  GteMetricChip(label: 'My tier', value: playerRanks.tier),
              ],
            ),
          if (season != null) ...<Widget>[
            const SizedBox(height: 14),
            Text(
              '${_formatDateRange(season.startDate, season.endDate)} | ${_sentenceCase(season.status)} season | ${_sentenceCase(season.resetStrategy)} reset',
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: GteShellTheme.textMuted),
            ),
          ],
          if ((_controller.competitionError ?? '')
              .trim()
              .isNotEmpty) ...<Widget>[
            const SizedBox(height: 12),
            Text(
              _controller.competitionError!,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: GteShellTheme.accentWarm),
            ),
          ],
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed:
                _isAuthenticated ? _createTournament : widget.onOpenLogin,
            icon: Icon(_isAuthenticated ? Icons.add : Icons.login),
            label: Text(
              _isAuthenticated ? 'Host a tournament' : 'Sign in to host',
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSeasonStructure(
    BuildContext context,
    LeaderboardSeason? season,
  ) {
    if (season == null) {
      return const GteStatePanel(
        title: 'Season structure loading',
        message: 'Rank tiers and reward entitlements are syncing.',
        icon: Icons.hourglass_top_outlined,
      );
    }

    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Rank tiers and season rewards',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            'Every season converts match outcomes and tournament placements into a visible status economy.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: season.rankTiers
                .map(
                  (LeaderboardRankTier tier) => _tag(
                    context,
                    '${tier.label} ${tier.minRating}+',
                    _tierColor(tier.label),
                  ),
                )
                .toList(growable: false),
          ),
          const SizedBox(height: 16),
          if (season.rewardTiers.isEmpty)
            const Text('Reward tiers are not published yet.')
          else
            ...season.rewardTiers.map(
              (LeaderboardRewardTier tier) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        '#${tier.rankPosition} ${tier.title}',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 10),
                      Wrap(
                        spacing: 10,
                        runSpacing: 10,
                        children: <Widget>[
                          _tag(
                            context,
                            _formatCoins(tier.coins),
                            GteShellTheme.accentCapital,
                          ),
                          _tag(
                            context,
                            '${tier.trophies} trophies',
                            GteShellTheme.accentArena,
                          ),
                          if (tier.visibilityBoost > 0)
                            _tag(
                              context,
                              '+${tier.visibilityBoost} visibility',
                              GteShellTheme.accentWarm,
                            ),
                          if (tier.exclusiveTournamentKey != null)
                            _tag(
                              context,
                              'Exclusive ${tier.exclusiveTournamentKey}',
                              GteShellTheme.accentArena,
                            ),
                          ...tier.badges.map(
                            (String badge) =>
                                _tag(context, badge, GteShellTheme.textMuted),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildLeaderboard(
    BuildContext context,
    LeaderboardBoard? leaderboard,
    LeaderboardPlayerRanks? playerRanks,
  ) {
    final List<LeaderboardEntry> entries =
        leaderboard?.entries.take(12).toList(growable: false) ??
        const <LeaderboardEntry>[];
    final bool showPinned =
        playerRanks != null &&
        entries.every(
          (LeaderboardEntry entry) => entry.playerId != playerRanks.playerId,
        );

    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Global leaderboard',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            'Wins, earnings, win rate, and tournament placements all feed the same competitive loop.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          if (_controller.isLoadingCompetition && entries.isEmpty)
            const GteStatePanel(
              title: 'Loading leaderboard',
              message: 'Top player standings are syncing.',
              icon: Icons.leaderboard_outlined,
              isLoading: true,
            )
          else if (entries.isEmpty)
            const GteStatePanel(
              title: 'No leaderboard entries yet',
              message:
                  'Settle matches or tournaments to start the season race.',
              icon: Icons.emoji_events_outlined,
            )
          else ...<Widget>[
            if (showPinned) ...<Widget>[
              GteSurfacePanel(
                accentColor: GteShellTheme.accentWarm,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Your current position',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: <Widget>[
                        if (playerRanks.globalRank != null)
                          _tag(
                            context,
                            '#${playerRanks.globalRank}',
                            GteShellTheme.accentWarm,
                          ),
                        _tag(
                          context,
                          playerRanks.tier,
                          _tierColor(playerRanks.tier),
                        ),
                        _tag(
                          context,
                          '${playerRanks.rating} rating',
                          GteShellTheme.accentArena,
                        ),
                        _tag(
                          context,
                          _formatPercent(playerRanks.winRate),
                          GteShellTheme.positive,
                        ),
                        _tag(
                          context,
                          _formatCoins(playerRanks.earnings),
                          GteShellTheme.accentCapital,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
            ],
            ...entries.map(
              (LeaderboardEntry entry) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: GteSurfacePanel(
                  accentColor:
                      entry.playerId == widget.currentUserId
                          ? GteShellTheme.accent
                          : null,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Row(
                        children: <Widget>[
                          Expanded(
                            child: Text(
                              '#${entry.rank} ${entry.displayName}',
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                          ),
                          Text(
                            '${entry.rating}',
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        '${entry.tier} | ${entry.wins}-${entry.losses}-${entry.draws} | ${entry.matchesPlayed} matches',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 10),
                      Wrap(
                        spacing: 10,
                        runSpacing: 10,
                        children: <Widget>[
                          _tag(
                            context,
                            _formatPercent(entry.winRate),
                            GteShellTheme.positive,
                          ),
                          _tag(
                            context,
                            _formatCoins(entry.earnings),
                            GteShellTheme.accentCapital,
                          ),
                          _tag(
                            context,
                            '${entry.tournamentTitles} titles',
                            GteShellTheme.accentWarm,
                          ),
                          _tag(
                            context,
                            '${entry.podiumFinishes} podiums',
                            GteShellTheme.accentArena,
                          ),
                          if (entry.bestPlacement != null)
                            _tag(
                              context,
                              'Best #${entry.bestPlacement}',
                              GteShellTheme.textMuted,
                            ),
                          if (entry.visibilityBoost > 0)
                            _tag(
                              context,
                              '+${entry.visibilityBoost} visibility',
                              GteShellTheme.accentWarm,
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildSeasonHistory(
    BuildContext context,
    List<LeaderboardSeason> seasons,
  ) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Season history', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(
            'Archived seasons preserve receipts, so the status race survives beyond a single session.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          if (seasons.isEmpty)
            const GteStatePanel(
              title: 'No archived seasons yet',
              message:
                  'The current cycle is still live. Archive a season to seed the long-term history loop.',
              icon: Icons.history_toggle_off_outlined,
            )
          else
            ...seasons
                .take(4)
                .map(
                  (LeaderboardSeason season) => Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: GteSurfacePanel(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            _formatDateRange(season.startDate, season.endDate),
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            '${season.rewardTiers.length} reward tiers | ${season.rankTiers.length} ranks | ${season.durationDays} day cycle',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
        ],
      ),
    );
  }

  Widget _buildTournamentActions(BuildContext context) {
    final StreamerTournament? tournament = _tournament;
    return GteSurfacePanel(
      accentColor: GteShellTheme.accentArena,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Tournament actions',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            'Creators host tournaments, push fans into competition loops, and turn participation into earnings plus follower growth.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.icon(
                onPressed:
                    _isAuthenticated ? _createTournament : widget.onOpenLogin,
                icon: Icon(_isAuthenticated ? Icons.add : Icons.login),
                label: Text(
                  _isAuthenticated ? 'Create tournament' : 'Sign in to create',
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
                  icon: const Icon(Icons.workspace_premium_outlined),
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
                  onPressed:
                      () => _run(
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
                  onPressed:
                      () => _run(
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
    );
  }

  Widget _buildTournamentSection(
    BuildContext context, {
    required String title,
    required List<StreamerTournament> tournaments,
    String emptyMessage = 'No tournaments available.',
  }) {
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
                      _tournament?.id == item.id
                          ? GteShellTheme.accentArena
                          : null,
                  onTap: () => _controller.loadTournament(item.id),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        item.title,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        '${_sentenceCase(item.status)} | ${_sentenceCase(item.approvalStatus)} | ${item.entries.length}/${item.maxParticipants} entries',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildTournamentDetail(
    BuildContext context,
    StreamerTournament? tournament,
    Map<String, Object?>? creatorGrowth,
  ) {
    if (_controller.isLoadingTournament && tournament == null) {
      return const GteStatePanel(
        title: 'Loading tournament detail',
        message: 'Entries, rewards, and creator growth are syncing.',
        icon: Icons.live_tv_outlined,
        isLoading: true,
      );
    }

    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Tournament detail',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 10),
          if (tournament == null)
            const Text('Select a tournament to inspect detail.')
          else ...<Widget>[
            Text(
              tournament.title,
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              '${_sentenceCase(tournament.status)} | ${_sentenceCase(tournament.approvalStatus)} | ${tournament.entries.length}/${tournament.maxParticipants} entries',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: <Widget>[
                _tag(
                  context,
                  '${tournament.rewards.length} rewards',
                  GteShellTheme.accentCapital,
                ),
                _tag(
                  context,
                  '${tournament.invites.length} invites',
                  GteShellTheme.accentArena,
                ),
                _tag(
                  context,
                  tournament.tournamentType,
                  GteShellTheme.textMuted,
                ),
                if (tournament.requiresAdminApproval)
                  _tag(
                    context,
                    'Admin approval required',
                    GteShellTheme.accentWarm,
                  ),
              ],
            ),
            const SizedBox(height: 16),
            Text(
              'Creator integration',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            if (creatorGrowth == null)
              Text(
                'Settle this tournament to convert participation into creator earnings, follower growth, and visibility boosts.',
                style: Theme.of(context).textTheme.bodyMedium,
              )
            else
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: <Widget>[
                  _tag(
                    context,
                    '${_intFrom(creatorGrowth['participant_count'])} participants',
                    GteShellTheme.accentArena,
                  ),
                  _tag(
                    context,
                    '${_intFrom(creatorGrowth['new_followers'])} new followers',
                    GteShellTheme.positive,
                  ),
                  _tag(
                    context,
                    _formatCoins(_doubleFrom(creatorGrowth['payout_coin'])),
                    GteShellTheme.accentCapital,
                  ),
                  _tag(
                    context,
                    '+${_intFrom(creatorGrowth['visibility_boost'])} visibility',
                    GteShellTheme.accentWarm,
                  ),
                ],
              ),
            if (_controller.latestSettlement != null &&
                _controller.latestSettlement!.tournament.id ==
                    tournament.id) ...<Widget>[
              const SizedBox(height: 16),
              Text(
                '${_controller.latestSettlement!.grants.length} grant records were created in the latest settlement run.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ],
        ],
      ),
    );
  }

  Widget _buildAdminPanel(
    BuildContext context,
    StreamerTournament? tournament,
  ) {
    return GteSurfacePanel(
      accentColor: GteShellTheme.accentAdmin,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Admin review', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          if (_controller.isLoadingAdmin && _controller.policy == null)
            const LinearProgressIndicator(minHeight: 4)
          else
            Text(
              _controller.policy == null
                  ? 'Tournament policy is syncing.'
                  : 'Coin cap ${_controller.policy!.rewardCoinApprovalLimit} | credit cap ${_controller.policy!.rewardCreditApprovalLimit} | invite cap ${_controller.policy!.maxInvitesPerTournament}',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          const SizedBox(height: 14),
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
                  onPressed: () => _reviewTournament(approve: true),
                  icon: const Icon(Icons.verified_outlined),
                  label: const Text('Approve'),
                ),
              if (tournament != null)
                FilledButton.tonalIcon(
                  onPressed: () => _reviewTournament(approve: false),
                  icon: const Icon(Icons.block_outlined),
                  label: const Text('Reject'),
                ),
              if (tournament != null)
                FilledButton.tonalIcon(
                  onPressed: _settleTournament,
                  icon: const Icon(Icons.rule_outlined),
                  label: const Text('Settle'),
                ),
              FilledButton.tonalIcon(
                onPressed:
                    _controller.isRunningSeasonAdminAction
                        ? null
                        : () => _run(
                          _controller.resetSeason,
                          'Season rankings reset.',
                        ),
                icon: const Icon(Icons.restart_alt_outlined),
                label: const Text('Reset season'),
              ),
              FilledButton.tonalIcon(
                onPressed:
                    _controller.isRunningSeasonAdminAction
                        ? null
                        : () => _run(
                          _controller.archiveSeason,
                          'Season archived and rolled forward.',
                        ),
                icon: const Icon(Icons.archive_outlined),
                label: const Text('Archive season'),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Text(
            _controller.riskSignals.isEmpty
                ? 'No open risk signals.'
                : '${_controller.riskSignals.length} risk signals are waiting for review.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          if (_controller.latestSeasonLifecycle != null) ...<Widget>[
            const SizedBox(height: 16),
            GteSurfacePanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Latest season transition',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Ended ${_formatDateRange(_controller.latestSeasonLifecycle!.endedSeason.startDate, _controller.latestSeasonLifecycle!.endedSeason.endDate)}',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  if (_controller.latestSeasonLifecycle!.nextSeason != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Text(
                        'Next ${_formatDateRange(_controller.latestSeasonLifecycle!.nextSeason!.startDate, _controller.latestSeasonLifecycle!.nextSeason!.endDate)}',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ),
                  const SizedBox(height: 8),
                  Text(
                    '${_controller.latestSeasonLifecycle!.rewards.length} reward deliveries were queued in the latest action.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _tag(BuildContext context, String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: color.withValues(alpha: 0.12),
        border: Border.all(color: color.withValues(alpha: 0.28)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(color: color),
      ),
    );
  }
}

Color _tierColor(String tier) {
  switch (tier.trim().toLowerCase()) {
    case 'bronze':
      return const Color(0xFFB87333);
    case 'silver':
      return const Color(0xFFBFC5D2);
    case 'gold':
      return GteShellTheme.accentCapital;
    case 'elite':
      return GteShellTheme.accentArena;
    case 'legend':
      return GteShellTheme.accentWarm;
    default:
      return GteShellTheme.textPrimary;
  }
}

String _formatPercent(double ratio) {
  final double percent = ratio * 100;
  final int decimals = (percent - percent.roundToDouble()).abs() < 0.05 ? 0 : 1;
  return '${percent.toStringAsFixed(decimals)}%';
}

String _formatCoins(double amount) {
  final int decimals =
      (amount - amount.roundToDouble()).abs() < 0.0001
          ? 0
          : amount.abs() >= 100
          ? 1
          : 2;
  return '${amount.toStringAsFixed(decimals)} coins';
}

String _formatDateRange(DateTime? start, DateTime? end) {
  final String startLabel = _formatShortDate(start);
  final String endLabel = _formatShortDate(end);
  if (startLabel.isEmpty && endLabel.isEmpty) {
    return 'Dates pending';
  }
  if (startLabel.isEmpty) {
    return endLabel;
  }
  if (endLabel.isEmpty) {
    return startLabel;
  }
  return '$startLabel to $endLabel';
}

String _formatShortDate(DateTime? value) {
  if (value == null) {
    return '';
  }
  final DateTime local = value.toLocal();
  const List<String> months = <String>[
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ];
  return '${months[local.month - 1]} ${local.day}, ${local.year}';
}

String _sentenceCase(String value) {
  final String trimmed = value.trim();
  if (trimmed.isEmpty) {
    return '';
  }
  return trimmed
      .split('_')
      .map(
        (String part) =>
            part.isEmpty
                ? part
                : '${part[0].toUpperCase()}${part.substring(1).toLowerCase()}',
      )
      .join(' ');
}

int _intFrom(Object? value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  return int.tryParse(value?.toString() ?? '') ?? 0;
}

double _doubleFrom(Object? value) {
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value?.toString() ?? '') ?? 0;
}
