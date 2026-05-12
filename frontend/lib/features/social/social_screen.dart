import 'package:flutter/material.dart';

import '../../core/app_feedback.dart';
import '../../core/constants/app_spacing.dart';
import '../../data/community_api.dart';
import '../../data/gte_api_repository.dart';
import '../../models/community_models.dart';
import '../../widgets/creator_club_follow_panel.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import '../../ui_gtex/ui_gtex.dart';
import '../engagement_redesign/engagement_widgets.dart';
import '../matchday_economy_redesign/matchday_economy_widgets.dart';

class CommunityScreen extends StatefulWidget {
  const CommunityScreen({
    super.key,
    required this.baseUrl,
    required this.backendMode,
    this.accessToken,
    this.isAuthenticated = false,
    this.currentClubId,
    this.currentClubName,
    this.onOpenLogin,
    this.onOpenFanWars,
    this.api,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final bool isAuthenticated;
  final String? currentClubId;
  final String? currentClubName;
  final VoidCallback? onOpenLogin;
  final VoidCallback? onOpenFanWars;
  final CommunityApi? api;

  @override
  State<CommunityScreen> createState() => _CommunityScreenState();
}

class _CommunityScreenState extends State<CommunityScreen> {
  late CommunityApi _api;
  CommunityDigest? _digest;
  List<CommunityWatchlistItem> _watchlist = const <CommunityWatchlistItem>[];
  List<LiveThread> _liveThreads = const <LiveThread>[];
  List<PrivateMessageThread> _privateThreads = const <PrivateMessageThread>[];
  _CommunityModule _selectedModule = _CommunityModule.liveThreads;
  bool _isLoading = false;
  bool _isMutating = false;
  String? _loadError;

  bool get _hasAuthenticatedCommunityAccess =>
      widget.isAuthenticated &&
      (widget.api != null || !(widget.accessToken?.trim().isEmpty ?? true));

  @override
  void initState() {
    super.initState();
    _api = _buildApi();
    _load();
  }

  @override
  void didUpdateWidget(covariant CommunityScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.api != widget.api ||
        oldWidget.baseUrl != widget.baseUrl ||
        oldWidget.backendMode != widget.backendMode ||
        oldWidget.accessToken != widget.accessToken ||
        oldWidget.isAuthenticated != widget.isAuthenticated) {
      _api = _buildApi();
      _load();
    }
  }

  CommunityApi _buildApi() {
    return widget.api ??
        CommunityApi.standard(
          baseUrl: widget.baseUrl,
          accessToken: widget.accessToken,
          mode: widget.backendMode,
        );
  }

  Future<void> _load() async {
    if (_isLoading) {
      return;
    }
    setState(() {
      _isLoading = true;
      _loadError = null;
    });
    try {
      final List<LiveThread> liveThreads = await _api.listLiveThreads();
      CommunityDigest? digest;
      List<CommunityWatchlistItem> watchlist = const <CommunityWatchlistItem>[];
      List<PrivateMessageThread> privateThreads =
          const <PrivateMessageThread>[];
      if (_hasAuthenticatedCommunityAccess) {
        final List<Object> authedPayload = await Future.wait<Object>(
          <Future<Object>>[
            _api.fetchDigest(),
            _api.listWatchlist(),
            _api.listPrivateThreads(),
          ],
        );
        digest = authedPayload[0] as CommunityDigest;
        watchlist = authedPayload[1] as List<CommunityWatchlistItem>;
        privateThreads = authedPayload[2] as List<PrivateMessageThread>;
      }
      if (!mounted) {
        return;
      }
      setState(() {
        _digest = digest;
        _watchlist = watchlist;
        _liveThreads = liveThreads;
        _privateThreads = privateThreads;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _loadError = AppFeedback.messageFor(error);
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  CommunityDigest _copyDigest({
    int? watchlistCount,
    int? liveThreadCount,
    int? privateThreadCount,
  }) {
    final CommunityDigest baseline =
        _digest ??
        CommunityDigest(
          watchlistCount: _watchlist.length,
          liveThreadCount: _liveThreads.length,
          privateThreadCount: _privateThreads.length,
          unreadHintCount: 0,
        );
    return CommunityDigest(
      watchlistCount: watchlistCount ?? baseline.watchlistCount,
      liveThreadCount: liveThreadCount ?? baseline.liveThreadCount,
      privateThreadCount: privateThreadCount ?? baseline.privateThreadCount,
      unreadHintCount: baseline.unreadHintCount,
    );
  }

  Future<void> _addWatchlist() async {
    final _WatchlistDraft? draft = await _showWatchlistDialog();
    if (draft == null) {
      return;
    }
    setState(() {
      _isMutating = true;
    });
    try {
      final CommunityWatchlistItem item = await _api.addWatchlist(
        competitionKey: draft.competitionKey,
        competitionTitle: draft.competitionTitle,
        competitionType: draft.competitionType,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _watchlist = <CommunityWatchlistItem>[item, ..._watchlist];
        _digest = _copyDigest(watchlistCount: _watchlist.length);
      });
      AppFeedback.showSuccess(
        context,
        'Added ${draft.competitionTitle} to your community watchlist.',
      );
    } catch (error) {
      if (!mounted) {
        return;
      }
      AppFeedback.showError(context, AppFeedback.messageFor(error));
    } finally {
      if (mounted) {
        setState(() {
          _isMutating = false;
        });
      }
    }
  }

  Future<void> _removeWatchlist(CommunityWatchlistItem item) async {
    setState(() {
      _isMutating = true;
    });
    try {
      await _api.removeWatchlist(item.competitionKey);
      if (!mounted) {
        return;
      }
      setState(() {
        _watchlist = _watchlist
            .where(
              (CommunityWatchlistItem existing) =>
                  existing.competitionKey != item.competitionKey,
            )
            .toList(growable: false);
        _digest = _copyDigest(watchlistCount: _watchlist.length);
      });
      AppFeedback.showSuccess(
        context,
        'Removed ${item.competitionTitle} from your watchlist.',
      );
    } catch (error) {
      if (!mounted) {
        return;
      }
      AppFeedback.showError(context, AppFeedback.messageFor(error));
    } finally {
      if (mounted) {
        setState(() {
          _isMutating = false;
        });
      }
    }
  }

  Future<void> _createLiveThread() async {
    final _LiveThreadDraft? draft = await _showLiveThreadDialog();
    if (draft == null) {
      return;
    }
    setState(() {
      _isMutating = true;
    });
    try {
      final LiveThread thread = await _api.createLiveThread(
        threadKey: draft.threadKey,
        title: draft.title,
        competitionKey: draft.competitionKey,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _liveThreads = <LiveThread>[thread, ..._liveThreads];
        _digest = _copyDigest(liveThreadCount: _liveThreads.length);
      });
      AppFeedback.showSuccess(context, 'Opened live thread "${draft.title}".');
      await _openLiveThread(thread);
    } catch (error) {
      if (!mounted) {
        return;
      }
      AppFeedback.showError(context, AppFeedback.messageFor(error));
    } finally {
      if (mounted) {
        setState(() {
          _isMutating = false;
        });
      }
    }
  }

  Future<void> _createPrivateThread() async {
    final _PrivateThreadDraft? draft = await _showPrivateThreadDialog();
    if (draft == null) {
      return;
    }
    setState(() {
      _isMutating = true;
    });
    try {
      final PrivateMessageThread thread = await _api.createPrivateThread(
        participantUserIds: draft.participantUserIds,
        initialMessage: draft.initialMessage,
        subject: draft.subject,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _privateThreads = <PrivateMessageThread>[thread, ..._privateThreads];
        _digest = _copyDigest(privateThreadCount: _privateThreads.length);
      });
      AppFeedback.showSuccess(
        context,
        'Opened direct thread "${draft.subjectLabel}".',
      );
      await _openPrivateThread(thread);
    } catch (error) {
      if (!mounted) {
        return;
      }
      AppFeedback.showError(context, AppFeedback.messageFor(error));
    } finally {
      if (mounted) {
        setState(() {
          _isMutating = false;
        });
      }
    }
  }

  Future<void> _openLiveThread(LiveThread thread) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder:
          (BuildContext context) => _LiveThreadSheet(
            api: _api,
            thread: thread,
            canPost: _hasAuthenticatedCommunityAccess,
            onOpenLogin: widget.onOpenLogin,
          ),
    );
  }

  Future<void> _openPrivateThread(PrivateMessageThread thread) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder:
          (BuildContext context) => _PrivateThreadSheet(
            api: _api,
            thread: thread,
            canPost: _hasAuthenticatedCommunityAccess,
            onOpenLogin: widget.onOpenLogin,
          ),
    );
  }

  Future<_WatchlistDraft?> _showWatchlistDialog() async {
    final BuildContext pageContext = context;
    final TextEditingController keyController = TextEditingController();
    final TextEditingController titleController = TextEditingController();
    final TextEditingController typeController = TextEditingController(
      text: 'creator',
    );
    final _WatchlistDraft? result = await showDialog<_WatchlistDraft>(
      context: context,
      builder:
          (BuildContext context) => AlertDialog(
            title: const Text('Add watchlist entry'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  TextField(
                    controller: keyController,
                    decoration: const InputDecoration(
                      labelText: 'Competition key',
                      hintText: 'creator-cup-night',
                    ),
                  ),
                  const SizedBox(height: spacingSM),
                  TextField(
                    controller: titleController,
                    decoration: const InputDecoration(
                      labelText: 'Competition title',
                      hintText: 'Creator Cup Night',
                    ),
                  ),
                  const SizedBox(height: spacingSM),
                  TextField(
                    controller: typeController,
                    decoration: const InputDecoration(
                      labelText: 'Competition type',
                    ),
                  ),
                ],
              ),
            ),
            actions: <Widget>[
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Cancel'),
              ),
              FilledButton(
                onPressed: () {
                  final String competitionKey = keyController.text.trim();
                  final String competitionTitle = titleController.text.trim();
                  final String competitionType = typeController.text.trim();
                  if (competitionKey.isEmpty || competitionTitle.isEmpty) {
                    AppFeedback.showError(
                      pageContext,
                      'Competition key and title are required.',
                    );
                    return;
                  }
                  Navigator.of(context).pop(
                    _WatchlistDraft(
                      competitionKey: competitionKey,
                      competitionTitle: competitionTitle,
                      competitionType:
                          competitionType.isEmpty ? 'general' : competitionType,
                    ),
                  );
                },
                child: const Text('Add'),
              ),
            ],
          ),
    );
    return result;
  }

  Future<_LiveThreadDraft?> _showLiveThreadDialog() async {
    final BuildContext pageContext = context;
    final TextEditingController keyController = TextEditingController();
    final TextEditingController titleController = TextEditingController();
    final TextEditingController competitionKeyController =
        TextEditingController();
    final _LiveThreadDraft? result = await showDialog<_LiveThreadDraft>(
      context: context,
      builder:
          (BuildContext context) => AlertDialog(
            title: const Text('Open live thread'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  TextField(
                    controller: keyController,
                    decoration: const InputDecoration(
                      labelText: 'Thread key',
                      hintText: 'matchday-derby',
                    ),
                  ),
                  const SizedBox(height: spacingSM),
                  TextField(
                    controller: titleController,
                    decoration: const InputDecoration(
                      labelText: 'Thread title',
                      hintText: 'Matchday derby watch party',
                    ),
                  ),
                  const SizedBox(height: spacingSM),
                  TextField(
                    controller: competitionKeyController,
                    decoration: const InputDecoration(
                      labelText: 'Competition key (optional)',
                    ),
                  ),
                ],
              ),
            ),
            actions: <Widget>[
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Cancel'),
              ),
              FilledButton(
                onPressed: () {
                  final String threadKey = keyController.text.trim();
                  final String title = titleController.text.trim();
                  final String competitionKey =
                      competitionKeyController.text.trim();
                  if (threadKey.isEmpty || title.isEmpty) {
                    AppFeedback.showError(
                      pageContext,
                      'Thread key and title are required.',
                    );
                    return;
                  }
                  Navigator.of(context).pop(
                    _LiveThreadDraft(
                      threadKey: threadKey,
                      title: title,
                      competitionKey:
                          competitionKey.isEmpty ? null : competitionKey,
                    ),
                  );
                },
                child: const Text('Open thread'),
              ),
            ],
          ),
    );
    return result;
  }

  Future<_PrivateThreadDraft?> _showPrivateThreadDialog() async {
    final BuildContext pageContext = context;
    final TextEditingController participantController = TextEditingController();
    final TextEditingController subjectController = TextEditingController();
    final TextEditingController messageController = TextEditingController();
    final _PrivateThreadDraft? result = await showDialog<_PrivateThreadDraft>(
      context: context,
      builder:
          (BuildContext context) => AlertDialog(
            title: const Text('Open direct thread'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  TextField(
                    controller: participantController,
                    decoration: const InputDecoration(
                      labelText: 'Participant user IDs',
                      hintText: 'user-2, user-7',
                    ),
                  ),
                  const SizedBox(height: spacingSM),
                  TextField(
                    controller: subjectController,
                    decoration: const InputDecoration(
                      labelText: 'Subject',
                      hintText: 'Transfer room collab',
                    ),
                  ),
                  const SizedBox(height: spacingSM),
                  TextField(
                    controller: messageController,
                    minLines: 3,
                    maxLines: 5,
                    decoration: const InputDecoration(
                      labelText: 'Initial message',
                    ),
                  ),
                ],
              ),
            ),
            actions: <Widget>[
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Cancel'),
              ),
              FilledButton(
                onPressed: () {
                  final List<String> participants = participantController.text
                      .split(',')
                      .map((String item) => item.trim())
                      .where((String item) => item.isNotEmpty)
                      .toList(growable: false);
                  final String subject = subjectController.text.trim();
                  final String initialMessage = messageController.text.trim();
                  if (participants.isEmpty || initialMessage.isEmpty) {
                    AppFeedback.showError(
                      pageContext,
                      'Participants and an initial message are required.',
                    );
                    return;
                  }
                  Navigator.of(context).pop(
                    _PrivateThreadDraft(
                      participantUserIds: participants,
                      subject: subject,
                      initialMessage: initialMessage,
                    ),
                  );
                },
                child: const Text('Open DM'),
              ),
            ],
          ),
    );
    return result;
  }

  @override
  Widget build(BuildContext context) {
    final bool hasData =
        _digest != null ||
        _watchlist.isNotEmpty ||
        _liveThreads.isNotEmpty ||
        _privateThreads.isNotEmpty;
    if (_isLoading && !hasData) {
      return const Center(
        child: GteStatePanel(
          title: 'Loading community',
          message:
              'Syncing watchlists, live discussion threads, and private creator conversations.',
          icon: Icons.forum_outlined,
          isLoading: true,
        ),
      );
    }
    if (_loadError != null && !hasData) {
      return Center(
        child: GteStatePanel(
          title: 'Community unavailable',
          message: _loadError!,
          icon: Icons.error_outline,
          actionLabel: 'Retry',
          onAction: _load,
        ),
      );
    }

    return GtexMasterDetailScaffold(
      title: 'GTEX Social',
      subtitle:
          _hasAuthenticatedCommunityAccess
              ? 'Live community threads, watchlists, follows, and direct messages from GTEX APIs.'
              : 'Public live threads stay visible. Sign in to manage follows, watchlists, and direct messages.',
      accent: GtexColors.mint,
      mobileLeftTitle: 'Social lanes',
      leftPanelWidth: 330,
      rightPanelWidth: 310,
      actions: <Widget>[
        GtexActionButton(
          label: _isLoading ? 'Syncing' : 'Refresh',
          icon: Icons.refresh_outlined,
          onPressed: _isLoading ? null : _load,
          accent: GtexColors.mint,
          secondary: true,
        ),
        if (!_hasAuthenticatedCommunityAccess && widget.onOpenLogin != null)
          GtexActionButton(
            label: 'Sign in',
            icon: Icons.login_outlined,
            onPressed: widget.onOpenLogin,
            accent: GtexColors.mint,
          ),
      ],
      leftPanel: _CommunityLeftPanel(
        selected: _selectedModule,
        digest: _digest,
        isAuthenticated: _hasAuthenticatedCommunityAccess,
        liveThreadCount: _liveThreads.length,
        watchlistCount: _watchlist.length,
        privateThreadCount: _privateThreads.length,
        hasClubFollow: widget.currentClubId?.trim().isNotEmpty ?? false,
        onOpenFanWars: widget.onOpenFanWars,
        onSelected:
            (_CommunityModule module) =>
                setState(() => _selectedModule = module),
      ),
      detail: _buildSelectedCommunityDetail(),
      rightPanel: _CommunityRightPanel(
        digest: _digest,
        isAuthenticated: _hasAuthenticatedCommunityAccess,
        isMutating: _isMutating,
        hasCurrentClub: widget.currentClubId?.trim().isNotEmpty ?? false,
        loadError: _loadError,
        onRefresh: _load,
        onSignIn: widget.onOpenLogin,
        onAddWatchlist: _addWatchlist,
        onCreateLiveThread: _createLiveThread,
        onCreatePrivateThread: _createPrivateThread,
        onOpenWatchlist:
            () => setState(() => _selectedModule = _CommunityModule.watchlist),
        onOpenLiveThreads:
            () =>
                setState(() => _selectedModule = _CommunityModule.liveThreads),
        onOpenPrivateThreads:
            () => setState(
              () => _selectedModule = _CommunityModule.privateMessages,
            ),
        onOpenClubFollow:
            () => setState(() => _selectedModule = _CommunityModule.clubFollow),
        onOpenFanWars: widget.onOpenFanWars,
      ),
    );
  }

  Widget _buildSelectedCommunityDetail() {
    switch (_selectedModule) {
      case _CommunityModule.liveThreads:
        return _CommunityDetailScroll(
          children: <Widget>[
            _CommunitySection(
              title: 'Live threads',
              subtitle:
                  'Open real-time matchday and competition discussion lanes.',
              action:
                  _hasAuthenticatedCommunityAccess
                      ? GtexActionButton(
                        label: 'Start thread',
                        icon: Icons.add_comment_outlined,
                        onPressed: _isMutating ? null : _createLiveThread,
                        accent: GtexColors.mint,
                        secondary: true,
                      )
                      : widget.onOpenLogin == null
                      ? null
                      : GtexActionButton(
                        label: 'Sign in',
                        icon: Icons.login_outlined,
                        onPressed: widget.onOpenLogin,
                        accent: GtexColors.mint,
                      ),
              child: _buildLiveThreadsBody(),
            ),
          ],
        );
      case _CommunityModule.watchlist:
        return _CommunityDetailScroll(
          children: <Widget>[
            _CommunitySection(
              title: 'Competition watchlist',
              subtitle:
                  'Pin community competitions and keep their live launches in view.',
              action:
                  _hasAuthenticatedCommunityAccess
                      ? GtexActionButton(
                        label: 'Add competition',
                        icon: Icons.playlist_add_outlined,
                        onPressed: _isMutating ? null : _addWatchlist,
                        accent: GtexColors.mint,
                        secondary: true,
                      )
                      : null,
              child:
                  _hasAuthenticatedCommunityAccess
                      ? _buildWatchlistBody()
                      : _buildReadOnlyBody(
                        'Sign in to add or remove watchlist entries.',
                      ),
            ),
          ],
        );
      case _CommunityModule.privateMessages:
        return _CommunityDetailScroll(
          children: <Widget>[
            _CommunitySection(
              title: 'Direct messages',
              subtitle:
                  'Open private creator-community threads with real participants.',
              action:
                  _hasAuthenticatedCommunityAccess
                      ? GtexActionButton(
                        label: 'New DM',
                        icon: Icons.mark_chat_unread_outlined,
                        onPressed: _isMutating ? null : _createPrivateThread,
                        accent: GtexColors.mint,
                        secondary: true,
                      )
                      : null,
              child:
                  _hasAuthenticatedCommunityAccess
                      ? _buildPrivateMessagesBody()
                      : _buildReadOnlyBody(
                        'Sign in to open direct threads and reply to private messages.',
                      ),
            ),
          ],
        );
      case _CommunityModule.clubFollow:
        return _CommunityDetailScroll(
          children: <Widget>[
            if ((widget.currentClubId?.trim().isNotEmpty ?? false))
              CreatorClubFollowPanel(
                api: widget.api,
                baseUrl: widget.baseUrl,
                backendMode: widget.backendMode,
                clubId: widget.currentClubId!,
                clubName: widget.currentClubName,
                accessToken: widget.accessToken,
                isAuthenticated: _hasAuthenticatedCommunityAccess,
                onOpenLogin: widget.onOpenLogin,
              )
            else
              const GtexEmptyState(
                title: 'No active club context',
                message:
                    'Create or select a club to manage follows and community club actions.',
                icon: Icons.shield_outlined,
                accent: GtexColors.mint,
              ),
          ],
        );
      case _CommunityModule.overview:
        return _CommunityDetailScroll(
          children: <Widget>[
            GtexMatchdayEconomyPanel(
              baseUrl: widget.baseUrl,
              backendMode: widget.backendMode,
              accessToken: widget.accessToken,
            ),
            if (!_hasAuthenticatedCommunityAccess)
              GteStatePanel(
                eyebrow: 'COMMUNITY ACCESS',
                title: 'Sign in to manage community actions',
                message:
                    'Watchlist edits, direct messages, and creator-club follow mutations require a signed-in session with a live access token.',
                icon: Icons.lock_outline,
                accentColor: GteShellTheme.accentCommunity,
                actionLabel: widget.onOpenLogin == null ? null : 'Sign in',
                onAction: widget.onOpenLogin,
              ),
            if (_digest != null) _DigestSummary(digest: _digest!),
            if (_loadError != null)
              GteStatePanel(
                title: 'Community sync degraded',
                message: _loadError!,
                icon: Icons.sync_problem_outlined,
                actionLabel: 'Retry',
                onAction: _load,
              ),
          ],
        );
    }
  }

  Widget _buildWatchlistBody() {
    if (_watchlist.isEmpty) {
      return _buildReadOnlyBody(
        'No competitions are followed yet. Add one to expose the live watchlist mutation.',
      );
    }
    return Column(
      children: _watchlist
          .map(
            (CommunityWatchlistItem item) => Padding(
              padding: const EdgeInsets.only(bottom: spacingSM),
              child: _ActionRowCard(
                title: item.competitionTitle,
                subtitle:
                    '${item.competitionType} lane · ${item.competitionKey}',
                detail:
                    'Stories ${item.notifyOnStory ? 'on' : 'off'} · Launches ${item.notifyOnLaunch ? 'on' : 'off'} · Updated ${gteFormatDateTime(item.updatedAt)}',
                action: OutlinedButton(
                  onPressed: _isMutating ? null : () => _removeWatchlist(item),
                  child: const Text('Remove'),
                ),
              ),
            ),
          )
          .toList(growable: false),
    );
  }

  Widget _buildLiveThreadsBody() {
    if (_liveThreads.isEmpty) {
      return _buildReadOnlyBody(
        'No public live threads are open yet. Start one to expose the live thread creation endpoint.',
      );
    }
    return Column(
      children: _liveThreads
          .map(
            (LiveThread thread) => Padding(
              padding: const EdgeInsets.only(bottom: spacingSM),
              child: _ActionRowCard(
                title: thread.title,
                subtitle:
                    '${thread.threadKey} · ${thread.status.toUpperCase()}${thread.pinned ? ' · PINNED' : ''}',
                detail:
                    'Competition ${thread.competitionKey ?? 'general'} · Last message ${gteFormatDateTime(thread.lastMessageAt)}',
                action: FilledButton.tonal(
                  onPressed: () => _openLiveThread(thread),
                  child: const Text('Open'),
                ),
              ),
            ),
          )
          .toList(growable: false),
    );
  }

  Widget _buildPrivateMessagesBody() {
    if (_privateThreads.isEmpty) {
      return _buildReadOnlyBody(
        'No private threads are open yet. Start one to expose the direct-message mutation path.',
      );
    }
    return Column(
      children: _privateThreads
          .map(
            (PrivateMessageThread thread) => Padding(
              padding: const EdgeInsets.only(bottom: spacingSM),
              child: _ActionRowCard(
                title:
                    thread.subject.trim().isEmpty
                        ? thread.threadKey
                        : thread.subject,
                subtitle:
                    '${thread.participants.length} participants · ${thread.status.toUpperCase()}',
                detail:
                    'Last message ${gteFormatDateTime(thread.lastMessageAt)}',
                action: FilledButton.tonal(
                  onPressed: () => _openPrivateThread(thread),
                  child: const Text('Open'),
                ),
              ),
            ),
          )
          .toList(growable: false),
    );
  }

  Widget _buildReadOnlyBody(String message) {
    return Text(message, style: Theme.of(context).textTheme.bodyMedium);
  }
}

class _DigestSummary extends StatelessWidget {
  const _DigestSummary({required this.digest});

  final CommunityDigest digest;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor: GteShellTheme.accentCommunity,
      child: Wrap(
        spacing: spacingSM,
        runSpacing: spacingSM,
        children: <Widget>[
          _DigestChip(label: 'Watchlist', value: '${digest.watchlistCount}'),
          _DigestChip(
            label: 'Live threads',
            value: '${digest.liveThreadCount}',
          ),
          _DigestChip(
            label: 'Direct threads',
            value: '${digest.privateThreadCount}',
          ),
          _DigestChip(
            label: 'Unread hints',
            value: '${digest.unreadHintCount}',
          ),
        ],
      ),
    );
  }
}

enum _CommunityModule {
  overview,
  liveThreads,
  watchlist,
  privateMessages,
  clubFollow,
}

extension _CommunityModuleX on _CommunityModule {
  String get label {
    switch (this) {
      case _CommunityModule.overview:
        return 'Overview';
      case _CommunityModule.liveThreads:
        return 'Live threads';
      case _CommunityModule.watchlist:
        return 'Watchlist';
      case _CommunityModule.privateMessages:
        return 'Direct messages';
      case _CommunityModule.clubFollow:
        return 'Club follow';
    }
  }

  String get subtitle {
    switch (this) {
      case _CommunityModule.overview:
        return 'Digest and access state';
      case _CommunityModule.liveThreads:
        return 'Matchday discussion lanes';
      case _CommunityModule.watchlist:
        return 'Pinned competitions';
      case _CommunityModule.privateMessages:
        return 'Creator and support DMs';
      case _CommunityModule.clubFollow:
        return 'Current club community';
    }
  }

  IconData get icon {
    switch (this) {
      case _CommunityModule.overview:
        return Icons.space_dashboard_outlined;
      case _CommunityModule.liveThreads:
        return Icons.forum_outlined;
      case _CommunityModule.watchlist:
        return Icons.playlist_add_check_outlined;
      case _CommunityModule.privateMessages:
        return Icons.mark_chat_unread_outlined;
      case _CommunityModule.clubFollow:
        return Icons.shield_outlined;
    }
  }
}

class _CommunityLeftPanel extends StatelessWidget {
  const _CommunityLeftPanel({
    required this.selected,
    required this.digest,
    required this.isAuthenticated,
    required this.liveThreadCount,
    required this.watchlistCount,
    required this.privateThreadCount,
    required this.hasClubFollow,
    required this.onOpenFanWars,
    required this.onSelected,
  });

  final _CommunityModule selected;
  final CommunityDigest? digest;
  final bool isAuthenticated;
  final int liveThreadCount;
  final int watchlistCount;
  final int privateThreadCount;
  final bool hasClubFollow;
  final VoidCallback? onOpenFanWars;
  final ValueChanged<_CommunityModule> onSelected;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        GtexPanel(
          accent: GtexColors.mint,
          title: 'Social command',
          subtitle:
              isAuthenticated
                  ? 'Live community access'
                  : 'Public read-only mode',
          child: Wrap(
            spacing: GtexSpacing.xs,
            runSpacing: GtexSpacing.xs,
            children: <Widget>[
              GtexStatusChip(
                label: isAuthenticated ? 'SIGNED IN' : 'GUEST',
                color: isAuthenticated ? GtexColors.mint : GtexColors.gold,
                icon:
                    isAuthenticated
                        ? Icons.verified_user_outlined
                        : Icons.visibility_outlined,
              ),
              GtexStatusChip(
                label: '${digest?.unreadHintCount ?? 0} UNREAD HINTS',
                color: GtexColors.cyan,
                icon: Icons.notifications_active_outlined,
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        for (final _CommunityModule module in _CommunityModule.values)
          if (module != _CommunityModule.clubFollow || hasClubFollow)
            GtexSectionListTile(
              title: module.label,
              subtitle: '${module.subtitle} - ${_countFor(module)}',
              icon: module.icon,
              accent: GtexColors.mint,
              isSelected: selected == module,
              onTap: () => onSelected(module),
            ),
        if (onOpenFanWars != null) ...<Widget>[
          const SizedBox(height: GtexSpacing.sm),
          GtexSectionListTile(
            title: 'Fan wars',
            subtitle: 'Leaderboards and Nations Cup rivalries',
            icon: Icons.military_tech_outlined,
            accent: GtexColors.gold,
            isSelected: false,
            onTap: onOpenFanWars!,
            trailing: const Icon(
              Icons.open_in_new_outlined,
              color: GtexColors.gold,
              size: 18,
            ),
          ),
        ],
      ],
    );
  }

  String _countFor(_CommunityModule module) {
    switch (module) {
      case _CommunityModule.liveThreads:
        return '$liveThreadCount live';
      case _CommunityModule.watchlist:
        return '$watchlistCount pinned';
      case _CommunityModule.privateMessages:
        return '$privateThreadCount threads';
      case _CommunityModule.clubFollow:
        return 'club context';
      case _CommunityModule.overview:
        return '${digest?.watchlistCount ?? watchlistCount} watchlist';
    }
  }
}

class _CommunityRightPanel extends StatelessWidget {
  const _CommunityRightPanel({
    required this.digest,
    required this.isAuthenticated,
    required this.isMutating,
    required this.hasCurrentClub,
    required this.loadError,
    required this.onRefresh,
    required this.onSignIn,
    required this.onAddWatchlist,
    required this.onCreateLiveThread,
    required this.onCreatePrivateThread,
    required this.onOpenWatchlist,
    required this.onOpenLiveThreads,
    required this.onOpenPrivateThreads,
    required this.onOpenClubFollow,
    required this.onOpenFanWars,
  });

  final CommunityDigest? digest;
  final bool isAuthenticated;
  final bool isMutating;
  final bool hasCurrentClub;
  final String? loadError;
  final VoidCallback onRefresh;
  final VoidCallback? onSignIn;
  final VoidCallback onAddWatchlist;
  final VoidCallback onCreateLiveThread;
  final VoidCallback onCreatePrivateThread;
  final VoidCallback onOpenWatchlist;
  final VoidCallback onOpenLiveThreads;
  final VoidCallback onOpenPrivateThreads;
  final VoidCallback onOpenClubFollow;
  final VoidCallback? onOpenFanWars;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        GtexPanel(
          title: 'Social pulse',
          subtitle: 'Live API summary',
          accent: GtexColors.mint,
          child: Column(
            children: <Widget>[
              _MetricLine(
                label: 'Watchlist',
                value: '${digest?.watchlistCount ?? 0}',
              ),
              _MetricLine(
                label: 'Live threads',
                value: '${digest?.liveThreadCount ?? 0}',
              ),
              _MetricLine(
                label: 'Direct threads',
                value: '${digest?.privateThreadCount ?? 0}',
              ),
              _MetricLine(
                label: 'Unread hints',
                value: '${digest?.unreadHintCount ?? 0}',
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Quick actions',
          subtitle:
              isAuthenticated
                  ? 'Create live social work'
                  : 'Sign in to unlock mutations',
          accent: GtexColors.mint,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              if (isAuthenticated) ...<Widget>[
                GtexActionButton(
                  label: 'Start live thread',
                  icon: Icons.add_comment_outlined,
                  onPressed: isMutating ? null : onCreateLiveThread,
                  accent: GtexColors.mint,
                ),
                const SizedBox(height: GtexSpacing.sm),
                GtexActionButton(
                  label: 'Add watchlist',
                  icon: Icons.playlist_add_outlined,
                  onPressed: isMutating ? null : onAddWatchlist,
                  accent: GtexColors.mint,
                  secondary: true,
                ),
                const SizedBox(height: GtexSpacing.sm),
                GtexActionButton(
                  label: 'New direct message',
                  icon: Icons.mark_chat_unread_outlined,
                  onPressed: isMutating ? null : onCreatePrivateThread,
                  accent: GtexColors.mint,
                  secondary: true,
                ),
              ] else
                GtexActionButton(
                  label: 'Sign in',
                  icon: Icons.login_outlined,
                  onPressed: onSignIn,
                  accent: GtexColors.mint,
                ),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                label: 'Refresh',
                icon: Icons.refresh_outlined,
                onPressed: onRefresh,
                accent: GtexColors.cyan,
                secondary: true,
              ),
            ],
          ),
        ),
        if (loadError != null) ...<Widget>[
          const SizedBox(height: GtexSpacing.md),
          GtexPanel(
            title: 'Sync degraded',
            subtitle: loadError,
            accent: GtexColors.red,
            child: GtexActionButton(
              label: 'Retry',
              icon: Icons.sync_problem_outlined,
              onPressed: onRefresh,
              accent: GtexColors.red,
              secondary: true,
            ),
          ),
        ],
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Jump to',
          subtitle: 'Move without losing live state',
          accent: GtexColors.cyan,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              GtexActionButton(
                label: 'Live threads',
                icon: Icons.forum_outlined,
                onPressed: onOpenLiveThreads,
                accent: GtexColors.mint,
                secondary: true,
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                label: 'Watchlist',
                icon: Icons.playlist_add_check_outlined,
                onPressed: onOpenWatchlist,
                accent: GtexColors.mint,
                secondary: true,
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                label: 'Direct messages',
                icon: Icons.mark_chat_unread_outlined,
                onPressed: onOpenPrivateThreads,
                accent: GtexColors.mint,
                secondary: true,
              ),
              if (hasCurrentClub) ...<Widget>[
                const SizedBox(height: GtexSpacing.sm),
                GtexActionButton(
                  label: 'Club follow',
                  icon: Icons.shield_outlined,
                  onPressed: onOpenClubFollow,
                  accent: GtexColors.mint,
                  secondary: true,
                ),
              ],
              if (onOpenFanWars != null) ...<Widget>[
                const SizedBox(height: GtexSpacing.sm),
                GtexActionButton(
                  label: 'Fan wars',
                  icon: Icons.military_tech_outlined,
                  onPressed: onOpenFanWars,
                  accent: GtexColors.gold,
                  secondary: true,
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

class _CommunityDetailScroll extends StatelessWidget {
  const _CommunityDetailScroll({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.lg),
      children: children
          .expand((Widget child) sync* {
            yield child;
            yield const SizedBox(height: GtexSpacing.md);
          })
          .toList(growable: false),
    );
  }
}

class _MetricLine extends StatelessWidget {
  const _MetricLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Text(
              label,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: GtexColors.textMuted),
            ),
          ),
          Text(
            value,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
              color: GtexColors.text,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

class _DigestChip extends StatelessWidget {
  const _DigestChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: GteShellTheme.accentCommunity.withValues(alpha: 0.12),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.labelMedium),
          const SizedBox(height: 4),
          Text(value, style: Theme.of(context).textTheme.titleLarge),
        ],
      ),
    );
  }
}

class _CommunitySection extends StatelessWidget {
  const _CommunitySection({
    required this.title,
    required this.subtitle,
    required this.child,
    this.action,
  });

  final String title;
  final String subtitle;
  final Widget child;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor: GteShellTheme.accentCommunity,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(title, style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 6),
                    Text(
                      subtitle,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              if (action != null) ...<Widget>[
                const SizedBox(width: spacingSM),
                action!,
              ],
            ],
          ),
          const SizedBox(height: spacingMD),
          child,
        ],
      ),
    );
  }
}

class _ActionRowCard extends StatelessWidget {
  const _ActionRowCard({
    required this.title,
    required this.subtitle,
    required this.detail,
    required this.action,
  });

  final String title;
  final String subtitle;
  final String detail;
  final Widget action;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: GteShellTheme.accentCommunity.withValues(alpha: 0.18),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(title, style: Theme.of(context).textTheme.titleSmall),
                    const SizedBox(height: 4),
                    Text(
                      subtitle,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: spacingSM),
              action,
            ],
          ),
          const SizedBox(height: 10),
          Text(detail, style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}

class _LiveThreadSheet extends StatefulWidget {
  const _LiveThreadSheet({
    required this.api,
    required this.thread,
    required this.canPost,
    this.onOpenLogin,
  });

  final CommunityApi api;
  final LiveThread thread;
  final bool canPost;
  final VoidCallback? onOpenLogin;

  @override
  State<_LiveThreadSheet> createState() => _LiveThreadSheetState();
}

class _LiveThreadSheetState extends State<_LiveThreadSheet> {
  final TextEditingController _messageController = TextEditingController();
  List<LiveThreadMessage> _messages = const <LiveThreadMessage>[];
  bool _isLoading = true;
  bool _isSending = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _messageController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final List<LiveThreadMessage> messages = await widget.api
          .listLiveThreadMessages(widget.thread.id);
      if (!mounted) {
        return;
      }
      setState(() {
        _messages = messages;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = AppFeedback.messageFor(error);
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _sendMessage() async {
    final String body = _messageController.text.trim();
    if (body.isEmpty || _isSending) {
      return;
    }
    setState(() {
      _isSending = true;
    });
    try {
      final LiveThreadMessage message = await widget.api.postLiveThreadMessage(
        threadId: widget.thread.id,
        body: body,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _messages = <LiveThreadMessage>[..._messages, message];
        _messageController.clear();
      });
      AppFeedback.showSuccess(context, 'Posted to ${widget.thread.title}.');
    } catch (error) {
      if (!mounted) {
        return;
      }
      AppFeedback.showError(context, AppFeedback.messageFor(error));
    } finally {
      if (mounted) {
        setState(() {
          _isSending = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Padding(
        padding: EdgeInsets.only(
          left: spacingMD,
          right: spacingMD,
          top: spacingMD,
          bottom: MediaQuery.of(context).viewInsets.bottom + spacingMD,
        ),
        child: SizedBox(
          height: 520,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                widget.thread.title,
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 6),
              Text(
                '${widget.thread.threadKey} · ${widget.thread.status.toUpperCase()}',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: spacingMD),
              Expanded(child: _buildBody()),
              const SizedBox(height: spacingSM),
              if (widget.canPost)
                Row(
                  children: <Widget>[
                    Expanded(
                      child: TextField(
                        controller: _messageController,
                        minLines: 1,
                        maxLines: 3,
                        decoration: const InputDecoration(
                          labelText: 'Reply to thread',
                        ),
                      ),
                    ),
                    const SizedBox(width: spacingSM),
                    FilledButton(
                      onPressed: _isSending ? null : _sendMessage,
                      child: Text(_isSending ? 'Posting...' : 'Send'),
                    ),
                  ],
                )
              else
                GteStatePanel(
                  title: 'Sign in to reply',
                  message:
                      'Public thread reads stay open here, but message posting requires a live signed-in session.',
                  icon: Icons.lock_outline,
                  actionLabel: widget.onOpenLogin == null ? null : 'Sign in',
                  onAction: widget.onOpenLogin,
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return GteStatePanel(
        title: 'Thread unavailable',
        message: _error!,
        icon: Icons.error_outline,
        actionLabel: 'Retry',
        onAction: _load,
      );
    }
    if (_messages.isEmpty) {
      return const Center(
        child: Text('No messages yet. Be the first to open the conversation.'),
      );
    }
    return ListView.separated(
      itemCount: _messages.length,
      separatorBuilder: (_, _) => const SizedBox(height: spacingSM),
      itemBuilder: (BuildContext context, int index) {
        final LiveThreadMessage message = _messages[index];
        return _MessageCard(
          title: message.authorUserId,
          body: message.body,
          footer:
              '${message.visibility} · ${message.likeCount} likes · ${gteFormatDateTime(message.createdAt)}',
        );
      },
    );
  }
}

class _PrivateThreadSheet extends StatefulWidget {
  const _PrivateThreadSheet({
    required this.api,
    required this.thread,
    required this.canPost,
    this.onOpenLogin,
  });

  final CommunityApi api;
  final PrivateMessageThread thread;
  final bool canPost;
  final VoidCallback? onOpenLogin;

  @override
  State<_PrivateThreadSheet> createState() => _PrivateThreadSheetState();
}

class _PrivateThreadSheetState extends State<_PrivateThreadSheet> {
  final TextEditingController _messageController = TextEditingController();
  List<PrivateMessage> _messages = const <PrivateMessage>[];
  bool _isLoading = true;
  bool _isSending = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _messageController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final List<PrivateMessage> messages = await widget.api
          .listPrivateMessages(widget.thread.id);
      if (!mounted) {
        return;
      }
      setState(() {
        _messages = messages;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = AppFeedback.messageFor(error);
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _sendMessage() async {
    final String body = _messageController.text.trim();
    if (body.isEmpty || _isSending) {
      return;
    }
    setState(() {
      _isSending = true;
    });
    try {
      final PrivateMessage message = await widget.api.postPrivateMessage(
        threadId: widget.thread.id,
        body: body,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _messages = <PrivateMessage>[..._messages, message];
        _messageController.clear();
      });
      AppFeedback.showSuccess(
        context,
        'Posted in ${widget.thread.subject.trim().isEmpty ? widget.thread.threadKey : widget.thread.subject}.',
      );
    } catch (error) {
      if (!mounted) {
        return;
      }
      AppFeedback.showError(context, AppFeedback.messageFor(error));
    } finally {
      if (mounted) {
        setState(() {
          _isSending = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final String threadLabel =
        widget.thread.subject.trim().isEmpty
            ? widget.thread.threadKey
            : widget.thread.subject;
    return SafeArea(
      top: false,
      child: Padding(
        padding: EdgeInsets.only(
          left: spacingMD,
          right: spacingMD,
          top: spacingMD,
          bottom: MediaQuery.of(context).viewInsets.bottom + spacingMD,
        ),
        child: SizedBox(
          height: 520,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(threadLabel, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 6),
              Text(
                '${widget.thread.participants.length} participants · ${widget.thread.status.toUpperCase()}',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: spacingMD),
              Expanded(child: _buildBody()),
              const SizedBox(height: spacingSM),
              if (widget.canPost)
                Row(
                  children: <Widget>[
                    Expanded(
                      child: TextField(
                        controller: _messageController,
                        minLines: 1,
                        maxLines: 3,
                        decoration: const InputDecoration(
                          labelText: 'Reply in thread',
                        ),
                      ),
                    ),
                    const SizedBox(width: spacingSM),
                    FilledButton(
                      onPressed: _isSending ? null : _sendMessage,
                      child: Text(_isSending ? 'Sending...' : 'Send'),
                    ),
                  ],
                )
              else
                GteStatePanel(
                  title: 'Sign in to reply',
                  message:
                      'Private thread replies require a live signed-in session with community access.',
                  icon: Icons.lock_outline,
                  actionLabel: widget.onOpenLogin == null ? null : 'Sign in',
                  onAction: widget.onOpenLogin,
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return GteStatePanel(
        title: 'Direct thread unavailable',
        message: _error!,
        icon: Icons.error_outline,
        actionLabel: 'Retry',
        onAction: _load,
      );
    }
    if (_messages.isEmpty) {
      return const Center(child: Text('No direct messages yet.'));
    }
    return ListView.separated(
      itemCount: _messages.length,
      separatorBuilder: (_, _) => const SizedBox(height: spacingSM),
      itemBuilder: (BuildContext context, int index) {
        final PrivateMessage message = _messages[index];
        return _MessageCard(
          title: message.senderUserId,
          body: message.body,
          footer: gteFormatDateTime(message.createdAt),
        );
      },
    );
  }
}

class _MessageCard extends StatelessWidget {
  const _MessageCard({
    required this.title,
    required this.body,
    required this.footer,
  });

  final String title;
  final String body;
  final String footer;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: GteShellTheme.accentCommunity.withValues(alpha: 0.08),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 6),
          Text(body, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 8),
          Text(footer, style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}

class _WatchlistDraft {
  const _WatchlistDraft({
    required this.competitionKey,
    required this.competitionTitle,
    required this.competitionType,
  });

  final String competitionKey;
  final String competitionTitle;
  final String competitionType;
}

class _LiveThreadDraft {
  const _LiveThreadDraft({
    required this.threadKey,
    required this.title,
    required this.competitionKey,
  });

  final String threadKey;
  final String title;
  final String? competitionKey;
}

class _PrivateThreadDraft {
  const _PrivateThreadDraft({
    required this.participantUserIds,
    required this.subject,
    required this.initialMessage,
  });

  final List<String> participantUserIds;
  final String subject;
  final String initialMessage;

  String get subjectLabel => subject.trim().isEmpty ? 'Direct thread' : subject;
}
