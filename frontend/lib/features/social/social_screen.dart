import 'dart:math' as math;

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
import 'widgets/gtex_community_pulse_panel.dart';
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
    this.onOpenClub,
    this.onOpenMarket,
    this.onOpenRegens,
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

  /// Existing shell destinations a community signal can route into. Null when
  /// this surface is hosted outside the shell, in which case the matching
  /// action is not rendered rather than rendered dead.
  final VoidCallback? onOpenClub;
  final VoidCallback? onOpenMarket;
  final VoidCallback? onOpenRegens;
  final CommunityApi? api;

  @override
  State<CommunityScreen> createState() => _CommunityScreenState();
}

class _CommunityScreenState extends State<CommunityScreen> {
  late CommunityApi _api;
  CommunityDigest? _digest;
  List<CommunityWatchlistItem> _watchlist = const <CommunityWatchlistItem>[];
  List<LiveThread> _liveThreads = const <LiveThread>[];
  List<DiscussionCategory> _discussionCategories = const <DiscussionCategory>[];
  List<LiveThread> _discussionThreads = const <LiveThread>[];
  List<PrivateMessageThread> _privateThreads = const <PrivateMessageThread>[];
  List<GiftCatalogItem> _giftCatalog = const <GiftCatalogItem>[];
  List<GiftCatalogItem> _awardGiftPacks = const <GiftCatalogItem>[];
  _CommunityModule _selectedModule = _CommunityModule.footballWorld;
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
      final List<Object> publicPayload =
          await Future.wait<Object>(<Future<Object>>[
            _api.listLiveThreads(),
            _api.listDiscussionCategories(),
            _api.listDiscussionThreads(),
            _api.listGiftCatalog(),
            _api.listAwardGiftPacks(),
          ]);
      final List<LiveThread> liveThreads = publicPayload[0] as List<LiveThread>;
      final List<DiscussionCategory> discussionCategories =
          publicPayload[1] as List<DiscussionCategory>;
      final List<LiveThread> discussionThreads =
          publicPayload[2] as List<LiveThread>;
      final List<GiftCatalogItem> giftCatalog =
          publicPayload[3] as List<GiftCatalogItem>;
      final List<GiftCatalogItem> awardGiftPacks =
          publicPayload[4] as List<GiftCatalogItem>;
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
        _discussionCategories = discussionCategories;
        _discussionThreads = discussionThreads;
        _giftCatalog = giftCatalog;
        _awardGiftPacks = awardGiftPacks;
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

  Future<void> _createDiscussionThread() async {
    final _DiscussionThreadDraft? draft = await _showDiscussionThreadDialog();
    if (draft == null) {
      return;
    }
    setState(() {
      _isMutating = true;
    });
    try {
      final LiveThread thread = await _api.createDiscussionThread(
        category: draft.category,
        title: draft.title,
        body: draft.body,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _discussionThreads = <LiveThread>[thread, ..._discussionThreads];
      });
      AppFeedback.showSuccess(context, 'Opened discussion "${draft.title}".');
      await _openDiscussionThread(thread);
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

  Future<void> _openDiscussionThread(LiveThread thread) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder:
          (BuildContext context) => _DiscussionThreadSheet(
            api: _api,
            thread: thread,
            giftCatalog: _giftCatalog,
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

  Future<_DiscussionThreadDraft?> _showDiscussionThreadDialog() async {
    final BuildContext pageContext = context;
    final TextEditingController titleController = TextEditingController();
    final TextEditingController bodyController = TextEditingController();
    String selectedCategory =
        _discussionCategories.isEmpty
            ? 'tactics_room'
            : _discussionCategories.first.code;
    final _DiscussionThreadDraft? result =
        await showDialog<_DiscussionThreadDraft>(
          context: context,
          builder:
              (BuildContext context) => StatefulBuilder(
                builder:
                    (
                      BuildContext context,
                      StateSetter setDialogState,
                    ) => AlertDialog(
                      title: const Text('Open football discussion'),
                      content: SingleChildScrollView(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: <Widget>[
                            DropdownButtonFormField<String>(
                              value: selectedCategory,
                              decoration: const InputDecoration(
                                labelText: 'Category',
                              ),
                              items: (_discussionCategories.isEmpty
                                      ? const <DiscussionCategory>[
                                        DiscussionCategory(
                                          code: 'tactics_room',
                                          label: 'Tactics Room',
                                        ),
                                      ]
                                      : _discussionCategories)
                                  .map(
                                    (DiscussionCategory item) =>
                                        DropdownMenuItem<String>(
                                          value: item.code,
                                          child: Text(item.label),
                                        ),
                                  )
                                  .toList(growable: false),
                              onChanged:
                                  (String? value) => setDialogState(() {
                                    selectedCategory =
                                        value ?? selectedCategory;
                                  }),
                            ),
                            const SizedBox(height: spacingSM),
                            TextField(
                              controller: titleController,
                              decoration: const InputDecoration(
                                labelText: 'Title',
                                hintText: 'Who owns the midfield this week?',
                              ),
                            ),
                            const SizedBox(height: spacingSM),
                            TextField(
                              controller: bodyController,
                              minLines: 4,
                              maxLines: 7,
                              decoration: const InputDecoration(
                                labelText: 'Opening post',
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
                            final String title = titleController.text.trim();
                            final String body = bodyController.text.trim();
                            if (title.isEmpty || body.isEmpty) {
                              AppFeedback.showError(
                                pageContext,
                                'Title and opening post are required.',
                              );
                              return;
                            }
                            Navigator.of(context).pop(
                              _DiscussionThreadDraft(
                                category: selectedCategory,
                                title: title,
                                body: body,
                              ),
                            );
                          },
                          child: const Text('Open discussion'),
                        ),
                      ],
                    ),
              ),
        );
    return result;
  }

  Future<void> _openGiftDrawer({
    String? recipientUserId,
    String? chatThreadId,
    String? discussionThreadId,
    String? discussionReplyId,
  }) async {
    if (!_hasAuthenticatedCommunityAccess) {
      widget.onOpenLogin?.call();
      return;
    }
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder:
          (BuildContext context) => _GiftDrawerSheet(
            api: _api,
            catalog: _giftCatalog,
            recipientUserId: recipientUserId,
            chatThreadId: chatThreadId,
            discussionThreadId: discussionThreadId,
            discussionReplyId: discussionReplyId,
          ),
    );
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
    // The football-world lane has its own sources and its own honest states,
    // so a slow or failing thread/gift sync must not blank it. The legacy
    // whole-screen gates apply only to the lanes they actually feed; the
    // failure itself still surfaces in the right rail and the overview lane.
    final bool gateWholeScreen =
        _selectedModule != _CommunityModule.footballWorld;
    if (gateWholeScreen && _isLoading && !hasData) {
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
    if (gateWholeScreen && _loadError != null && !hasData) {
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
        discussionThreadCount: _discussionThreads.length,
        giftCount: _giftCatalog.length,
        awardGiftCount: _awardGiftPacks.length,
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
        onCreateDiscussionThread: _createDiscussionThread,
        onCreatePrivateThread: _createPrivateThread,
        onOpenGiftDrawer: () => _openGiftDrawer(),
        onOpenWatchlist:
            () => setState(() => _selectedModule = _CommunityModule.watchlist),
        onOpenLiveThreads:
            () =>
                setState(() => _selectedModule = _CommunityModule.liveThreads),
        onOpenDiscussions:
            () =>
                setState(() => _selectedModule = _CommunityModule.discussions),
        onOpenGifts:
            () => setState(() => _selectedModule = _CommunityModule.gifts),
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
      case _CommunityModule.footballWorld:
        return _CommunityDetailScroll(
          children: <Widget>[
            GtexCommunityPulsePanel(
              onOpenLogin: widget.onOpenLogin,
              onOpenClub: widget.onOpenClub,
              onOpenMarket: widget.onOpenMarket,
              onOpenRegens: widget.onOpenRegens,
            ),
          ],
        );
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
      case _CommunityModule.discussions:
        return _CommunityDetailScroll(
          children: <Widget>[
            _CommunitySection(
              title: 'Football discussion threads',
              subtitle:
                  'Open football forum categories for tactics, transfers, national teams, regens, and GTEX competition talk.',
              action:
                  _hasAuthenticatedCommunityAccess
                      ? GtexActionButton(
                        label: 'New discussion',
                        icon: Icons.post_add_outlined,
                        onPressed: _isMutating ? null : _createDiscussionThread,
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
              child: _buildDiscussionsBody(),
            ),
          ],
        );
      case _CommunityModule.gifts:
        return _CommunityDetailScroll(
          children: <Widget>[
            _CommunitySection(
              title: 'Award gifts and fanfare',
              subtitle:
                  "Football-themed gifts use Fan Coin for emotion and status. They never buy competitive club ranking.",
              action:
                  _hasAuthenticatedCommunityAccess
                      ? GtexActionButton(
                        label: 'Send gift',
                        icon: Icons.card_giftcard_outlined,
                        onPressed: _isMutating ? null : () => _openGiftDrawer(),
                        accent: GtexColors.gold,
                        secondary: true,
                      )
                      : widget.onOpenLogin == null
                      ? null
                      : GtexActionButton(
                        label: 'Sign in',
                        icon: Icons.login_outlined,
                        onPressed: widget.onOpenLogin,
                        accent: GtexColors.gold,
                      ),
              child: _buildGiftCatalogueBody(),
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

  Widget _buildDiscussionsBody() {
    if (_discussionThreads.isEmpty) {
      return _buildReadOnlyBody(
        'No football discussions are open yet. Start one from tactics, competitions, transfers, regens, or national-team talk.',
      );
    }
    return Column(
      children: _discussionThreads
          .map(
            (LiveThread thread) => Padding(
              padding: const EdgeInsets.only(bottom: spacingSM),
              child: _ActionRowCard(
                title: thread.title,
                subtitle:
                    '${_categoryLabel(thread.category)} - ${thread.status.toUpperCase()} - trend ${thread.trendScore}',
                detail:
                    '${thread.body.isEmpty ? 'Football discussion' : thread.body} - Last reply ${gteFormatDateTime(thread.lastMessageAt)}',
                action: FilledButton.tonal(
                  onPressed: () => _openDiscussionThread(thread),
                  child: const Text('Open'),
                ),
              ),
            ),
          )
          .toList(growable: false),
    );
  }

  Widget _buildGiftCatalogueBody() {
    final List<GiftCatalogItem> awards =
        _awardGiftPacks.isEmpty
            ? _giftCatalog
                .where((GiftCatalogItem item) => item.isAwardPack)
                .toList(growable: false)
            : _awardGiftPacks;
    if (_giftCatalog.isEmpty && awards.isEmpty) {
      return _buildReadOnlyBody(
        'Gift catalogue is syncing. Awards will appear here once the live gift API responds.',
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Wrap(
          spacing: spacingSM,
          runSpacing: spacingSM,
          children: <Widget>[
            _DigestChip(label: 'Catalogue', value: '${_giftCatalog.length}'),
            _DigestChip(label: 'Award packs', value: '${awards.length}'),
            const _DigestChip(label: 'Ranking impact', value: '0'),
          ],
        ),
        const SizedBox(height: spacingMD),
        ...awards
            .take(8)
            .map(
              (GiftCatalogItem item) => Padding(
                padding: const EdgeInsets.only(bottom: spacingSM),
                child: _ActionRowCard(
                  title:
                      '${item.displayName}${item.code == 'ballon_dor' ? ' - highest pack' : ''}',
                  subtitle:
                      '${item.rarity.toUpperCase()} - ${item.costAmount.toStringAsFixed(item.costAmount.truncateToDouble() == item.costAmount ? 0 : 2)} ${item.currencyLabel}',
                  detail:
                      '${item.animationKey ?? 'gift_fanfare'} - legal ${item.legalStatus}${item.fallbackDisplayName == null ? '' : ' - fallback ${item.fallbackDisplayName}'}',
                  action: FilledButton.tonalIcon(
                    onPressed:
                        _hasAuthenticatedCommunityAccess
                            ? () => _openGiftDrawer()
                            : widget.onOpenLogin,
                    icon: const Icon(Icons.auto_awesome_outlined),
                    label: const Text('Gift'),
                  ),
                ),
              ),
            ),
      ],
    );
  }

  String _categoryLabel(String code) {
    return _discussionCategories
        .firstWhere(
          (DiscussionCategory item) => item.code == code,
          orElse: () => DiscussionCategory(code: code, label: code),
        )
        .label;
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
  footballWorld,
  overview,
  liveThreads,
  discussions,
  gifts,
  watchlist,
  privateMessages,
  clubFollow,
}

extension _CommunityModuleX on _CommunityModule {
  String get label {
    switch (this) {
      case _CommunityModule.footballWorld:
        return 'Football world';
      case _CommunityModule.overview:
        return 'Overview';
      case _CommunityModule.liveThreads:
        return 'Live threads';
      case _CommunityModule.discussions:
        return 'Discussions';
      case _CommunityModule.gifts:
        return 'Award gifts';
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
      case _CommunityModule.footballWorld:
        return 'Live football and owner activity';
      case _CommunityModule.overview:
        return 'Digest and access state';
      case _CommunityModule.liveThreads:
        return 'Matchday discussion lanes';
      case _CommunityModule.discussions:
        return 'Open football forums';
      case _CommunityModule.gifts:
        return 'Fan Coin celebrations';
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
      case _CommunityModule.footballWorld:
        return Icons.public_outlined;
      case _CommunityModule.overview:
        return Icons.space_dashboard_outlined;
      case _CommunityModule.liveThreads:
        return Icons.forum_outlined;
      case _CommunityModule.discussions:
        return Icons.forum_rounded;
      case _CommunityModule.gifts:
        return Icons.card_giftcard_outlined;
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
    required this.discussionThreadCount,
    required this.giftCount,
    required this.awardGiftCount,
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
  final int discussionThreadCount;
  final int giftCount;
  final int awardGiftCount;
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
              // Omitted while the digest is absent rather than claiming zero
              // unread hints - a count the screen has not been given is
              // unknown, not empty.
              if (digest != null)
                GtexStatusChip(
                  label: '${digest!.unreadHintCount} UNREAD HINTS',
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
      case _CommunityModule.footballWorld:
        return 'market, matchday, owners';
      case _CommunityModule.liveThreads:
        return '$liveThreadCount live';
      case _CommunityModule.discussions:
        return '$discussionThreadCount threads';
      case _CommunityModule.gifts:
        return '$awardGiftCount awards / $giftCount gifts';
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
    required this.onCreateDiscussionThread,
    required this.onCreatePrivateThread,
    required this.onOpenGiftDrawer,
    required this.onOpenWatchlist,
    required this.onOpenLiveThreads,
    required this.onOpenDiscussions,
    required this.onOpenGifts,
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
  final VoidCallback onCreateDiscussionThread;
  final VoidCallback onCreatePrivateThread;
  final VoidCallback onOpenGiftDrawer;
  final VoidCallback onOpenWatchlist;
  final VoidCallback onOpenLiveThreads;
  final VoidCallback onOpenDiscussions;
  final VoidCallback onOpenGifts;
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
              // The social pulse reports the digest the API returned. When
              // the digest has not arrived - still loading, its own source
              // failed while other lanes loaded, or the session is a guest
              // the digest is never fetched for - each line reads as unknown.
              // Printing `0` stated four counts about the reader's own
              // community that nothing had measured.
              _MetricLine(
                label: 'Watchlist',
                value: _countLabel(digest?.watchlistCount),
              ),
              _MetricLine(
                label: 'Live threads',
                value: _countLabel(digest?.liveThreadCount),
              ),
              _MetricLine(
                label: 'Direct threads',
                value: _countLabel(digest?.privateThreadCount),
              ),
              _MetricLine(
                label: 'Unread hints',
                value: _countLabel(digest?.unreadHintCount),
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
                const SizedBox(height: GtexSpacing.sm),
                GtexActionButton(
                  label: 'New discussion',
                  icon: Icons.post_add_outlined,
                  onPressed: isMutating ? null : onCreateDiscussionThread,
                  accent: GtexColors.mint,
                  secondary: true,
                ),
                const SizedBox(height: GtexSpacing.sm),
                GtexActionButton(
                  label: 'Send award gift',
                  icon: Icons.card_giftcard_outlined,
                  onPressed: isMutating ? null : onOpenGiftDrawer,
                  accent: GtexColors.gold,
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
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                label: 'Discussions',
                icon: Icons.forum_rounded,
                onPressed: onOpenDiscussions,
                accent: GtexColors.mint,
                secondary: true,
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                label: 'Award gifts',
                icon: Icons.card_giftcard_outlined,
                onPressed: onOpenGifts,
                accent: GtexColors.gold,
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

/// Renders a count the backend supplied, or GTEX's unknown token when it did
/// not. Never substitutes zero for absent.
String _countLabel(int? value) => value == null ? '-' : '$value';

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

class _DiscussionThreadSheet extends StatefulWidget {
  const _DiscussionThreadSheet({
    required this.api,
    required this.thread,
    required this.giftCatalog,
    required this.canPost,
    this.onOpenLogin,
  });

  final CommunityApi api;
  final LiveThread thread;
  final List<GiftCatalogItem> giftCatalog;
  final bool canPost;
  final VoidCallback? onOpenLogin;

  @override
  State<_DiscussionThreadSheet> createState() => _DiscussionThreadSheetState();
}

class _DiscussionThreadSheetState extends State<_DiscussionThreadSheet> {
  final TextEditingController _replyController = TextEditingController();
  List<LiveThreadMessage> _replies = const <LiveThreadMessage>[];
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
    _replyController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final List<LiveThreadMessage> replies = await widget.api
          .listDiscussionReplies(widget.thread.id);
      if (!mounted) {
        return;
      }
      setState(() {
        _replies = replies;
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

  Future<void> _sendReply() async {
    final String body = _replyController.text.trim();
    if (body.isEmpty || _isSending) {
      return;
    }
    setState(() {
      _isSending = true;
    });
    try {
      final LiveThreadMessage reply = await widget.api.postDiscussionReply(
        threadId: widget.thread.id,
        body: body,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _replies = <LiveThreadMessage>[..._replies, reply];
        _replyController.clear();
      });
      AppFeedback.showSuccess(context, 'Reply posted.');
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

  Future<void> _openGiftDrawer({String? replyId}) async {
    if (!widget.canPost) {
      widget.onOpenLogin?.call();
      return;
    }
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder:
          (BuildContext context) => _GiftDrawerSheet(
            api: widget.api,
            catalog: widget.giftCatalog,
            discussionThreadId: widget.thread.id,
            discussionReplyId: replyId,
          ),
    );
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
          height: 620,
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
                        Text(
                          widget.thread.title,
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 6),
                        Text(
                          '${widget.thread.category} - ${widget.thread.visibility} - trend ${widget.thread.trendScore}',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: spacingSM),
                  FilledButton.tonalIcon(
                    onPressed: widget.canPost ? () => _openGiftDrawer() : null,
                    icon: const Icon(Icons.card_giftcard_outlined),
                    label: const Text('Gift'),
                  ),
                ],
              ),
              if (widget.thread.body.trim().isNotEmpty) ...<Widget>[
                const SizedBox(height: spacingSM),
                Text(widget.thread.body),
              ],
              const SizedBox(height: spacingMD),
              Expanded(child: _buildBody()),
              const SizedBox(height: spacingSM),
              if (widget.canPost)
                Row(
                  children: <Widget>[
                    Expanded(
                      child: TextField(
                        controller: _replyController,
                        minLines: 1,
                        maxLines: 4,
                        decoration: const InputDecoration(
                          labelText: 'Reply to discussion',
                        ),
                      ),
                    ),
                    const SizedBox(width: spacingSM),
                    FilledButton(
                      onPressed: _isSending ? null : _sendReply,
                      child: Text(_isSending ? 'Posting...' : 'Reply'),
                    ),
                  ],
                )
              else
                GteStatePanel(
                  title: 'Sign in to join the discussion',
                  message:
                      'Football discussion threads are readable, but posting and gifting require a signed-in session.',
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
        title: 'Discussion unavailable',
        message: _error!,
        icon: Icons.error_outline,
        actionLabel: 'Retry',
        onAction: _load,
      );
    }
    if (_replies.isEmpty) {
      return const Center(
        child: Text('No replies yet. Open the football argument cleanly.'),
      );
    }
    return ListView.separated(
      itemCount: _replies.length,
      separatorBuilder: (_, _) => const SizedBox(height: spacingSM),
      itemBuilder: (BuildContext context, int index) {
        final LiveThreadMessage reply = _replies[index];
        final bool isGift = reply.messageType == 'gift';
        return _MessageCard(
          title: isGift ? 'Gift moment' : reply.authorUserId,
          body: reply.body,
          footer:
              '${reply.moderationStatus} - ${reply.likeCount} likes - ${gteFormatDateTime(reply.createdAt)}',
          trailing:
              widget.canPost
                  ? TextButton.icon(
                    onPressed: () => _openGiftDrawer(replyId: reply.id),
                    icon: const Icon(Icons.card_giftcard_outlined),
                    label: const Text('Gift'),
                  )
                  : null,
          accent: isGift ? GtexColors.gold : GteShellTheme.accentCommunity,
        );
      },
    );
  }
}

class _GiftDrawerSheet extends StatefulWidget {
  const _GiftDrawerSheet({
    required this.api,
    required this.catalog,
    this.recipientUserId,
    this.chatThreadId,
    this.discussionThreadId,
    this.discussionReplyId,
  });

  final CommunityApi api;
  final List<GiftCatalogItem> catalog;
  final String? recipientUserId;
  final String? chatThreadId;
  final String? discussionThreadId;
  final String? discussionReplyId;

  @override
  State<_GiftDrawerSheet> createState() => _GiftDrawerSheetState();
}

class _GiftDrawerSheetState extends State<_GiftDrawerSheet> {
  final TextEditingController _recipientController = TextEditingController();
  final TextEditingController _noteController = TextEditingController();
  GiftCatalogItem? _selectedGift;
  String _filter = 'all';
  bool _confirmPremiumGift = false;
  bool _isSending = false;

  bool get _hasContextTarget =>
      (widget.chatThreadId?.trim().isNotEmpty ?? false) ||
      (widget.discussionThreadId?.trim().isNotEmpty ?? false) ||
      (widget.discussionReplyId?.trim().isNotEmpty ?? false);

  @override
  void initState() {
    super.initState();
    _recipientController.text = widget.recipientUserId ?? '';
    _selectedGift = _bestInitialGift(widget.catalog);
  }

  @override
  void dispose() {
    _recipientController.dispose();
    _noteController.dispose();
    super.dispose();
  }

  GiftCatalogItem? _bestInitialGift(List<GiftCatalogItem> catalog) {
    if (catalog.isEmpty) return null;
    for (final GiftCatalogItem item in catalog) {
      if (item.isAwardPack && !_requiresReview(item)) return item;
    }
    for (final GiftCatalogItem item in catalog) {
      if (!_requiresReview(item)) return item;
    }
    return catalog.first;
  }

  List<GiftCatalogItem> get _visibleGifts {
    final List<GiftCatalogItem> gifts = widget.catalog;
    if (_filter == 'all') return gifts;
    if (_filter == 'award') {
      return gifts.where((GiftCatalogItem gift) => gift.isAwardPack).toList();
    }
    return gifts.where(
      (GiftCatalogItem gift) => gift.rarity.toLowerCase() == _filter,
    ).toList();
  }

  bool _requiresReview(GiftCatalogItem gift) =>
      gift.legalStatus.trim().toLowerCase() == 'requires_review' ||
      gift.legalStatus.trim().toLowerCase() == 'pending_review';

  String _priceLabel(GiftCatalogItem gift) =>
      '${gift.costAmount.toStringAsFixed(gift.costAmount.truncateToDouble() == gift.costAmount ? 0 : 2)} ${gift.currencyLabel}';

  Future<void> _sendGift() async {
    final GiftCatalogItem? gift = _selectedGift;
    if (gift == null || _isSending) return;
    if (_requiresReview(gift)) {
      AppFeedback.showError(context, 'This gift is unavailable while it is under review.');
      return;
    }

    final String recipientUserId = _recipientController.text.trim();
    if (!_hasContextTarget && recipientUserId.isEmpty) {
      AppFeedback.showError(
        context,
        'Enter the recipient’s GTEX user ID or open gifting from a room/thread.',
      );
      return;
    }
    if (gift.costAmount >= 500 && !_confirmPremiumGift) {
      AppFeedback.showError(
        context,
        'Confirm this premium gift spend before sending.',
      );
      return;
    }

    setState(() => _isSending = true);
    try {
      final GiftEvent event = await widget.api.sendGift(
        giftKey: gift.code,
        quantity: 1,
        recipientUserId: recipientUserId.isEmpty ? null : recipientUserId,
        chatThreadId: widget.chatThreadId,
        discussionThreadId: widget.discussionThreadId,
        discussionReplyId: widget.discussionReplyId,
        note: _noteController.text.trim(),
      );
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        barrierDismissible: false,
        barrierColor: Colors.black.withValues(alpha: 0.76),
        builder: (BuildContext context) => _GiftFanfarePreview(
          event: event,
          note: _noteController.text.trim(),
          deliveryContext: _hasContextTarget ? 'Community conversation' : 'GTEX recipient',
        ),
      );
    } catch (error) {
      if (!mounted) return;
      AppFeedback.showError(context, AppFeedback.messageFor(error));
    } finally {
      if (mounted) setState(() => _isSending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final List<GiftCatalogItem> catalog = widget.catalog;
    final List<GiftCatalogItem> visible = _visibleGifts;
    final GiftCatalogItem? selected = _selectedGift;
    final double sheetHeight = math.min(MediaQuery.sizeOf(context).height * 0.88, 800.0).toDouble();
    return SafeArea(
      top: false,
      child: Container(
        height: sheetHeight,
        padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
        decoration: BoxDecoration(
          color: const Color(0xFF080F1B),
          borderRadius: const BorderRadius.vertical(top: Radius.circular(30)),
          border: Border.all(color: GtexColors.gold.withValues(alpha: 0.34)),
          boxShadow: <BoxShadow>[
            BoxShadow(color: GtexColors.gold.withValues(alpha: 0.12), blurRadius: 32),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Center(
              child: Container(
                width: 44,
                height: 4,
                margin: const EdgeInsets.only(top: 10, bottom: 13),
                decoration: BoxDecoration(
                  color: Colors.white24,
                  borderRadius: BorderRadius.circular(99),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 0, 14, 13),
              child: Row(
                children: <Widget>[
                  Container(
                    width: 52,
                    height: 52,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(17),
                      gradient: GtexColors.panelGlow(accent: GtexColors.gold),
                      border: Border.all(color: GtexColors.gold.withValues(alpha: 0.6)),
                    ),
                    child: const Icon(Icons.card_giftcard_rounded, color: GtexColors.gold, size: 28),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        const Text(
                          'THE GTEX GIFT LOUNGE',
                          style: TextStyle(color: Color(0xFFE8C979), fontSize: 9, letterSpacing: 2.0, fontWeight: FontWeight.w900),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Give them a moment to remember',
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.white, fontWeight: FontWeight.w900, height: 1.1),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          _hasContextTarget ? 'Gift attached to this conversation' : 'Send a gift to another GTEX user',
                          style: const TextStyle(color: Color(0xFF9EACC0), fontSize: 11),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    tooltip: 'Close gift lounge',
                    onPressed: _isSending ? null : () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close_rounded, color: Colors.white70),
                  ),
                ],
              ),
            ),
            if (!_hasContextTarget)
              Padding(
                padding: const EdgeInsets.fromLTRB(18, 0, 18, 12),
                child: TextField(
                  key: const Key('social-gift-recipient-id'),
                  controller: _recipientController,
                  style: const TextStyle(color: Colors.white),
                  decoration: InputDecoration(
                    labelText: 'Recipient GTEX user ID',
                    labelStyle: const TextStyle(color: Color(0xFF9EAEC1)),
                    prefixIcon: const Icon(Icons.person_search_rounded, color: GtexColors.gold),
                    filled: true,
                    fillColor: const Color(0xFF111D2D),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(13), borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.08))),
                    enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(13), borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.08))),
                  ),
                ),
              ),
            SizedBox(
              height: 38,
              child: ListView(
                padding: const EdgeInsets.symmetric(horizontal: 18),
                scrollDirection: Axis.horizontal,
                children: <Widget>[
                  for (final String category in <String>['all', 'common', 'rare', 'epic', 'legendary', 'mythic', 'award'])
                    Padding(
                      padding: const EdgeInsets.only(right: 7),
                      child: ChoiceChip(
                        key: Key('social-gift-filter-$category'),
                        label: Text(category == 'all' ? 'All gifts' : category == 'award' ? 'Award packs' : _capitalise(category)),
                        selected: _filter == category,
                        onSelected: (_) => setState(() => _filter = category),
                        showCheckmark: false,
                        selectedColor: GtexColors.gold.withValues(alpha: 0.22),
                        backgroundColor: const Color(0xFF111D2D),
                        side: BorderSide(color: _filter == category ? GtexColors.gold : Colors.white.withValues(alpha: 0.08)),
                        labelStyle: TextStyle(color: _filter == category ? GtexColors.gold : const Color(0xFFB3C0D2), fontSize: 10, fontWeight: FontWeight.w800),
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 10),
            if (catalog.isEmpty)
              const Expanded(
                child: GteStatePanel(
                  title: 'Gift catalogue unavailable',
                  message: 'The gift catalogue has not loaded yet. Try again after the community sync finishes.',
                  icon: Icons.card_giftcard_outlined,
                ),
              )
            else if (visible.isEmpty)
              const Expanded(
                child: Center(
                  child: Text('No gifts in this category yet.', style: TextStyle(color: Color(0xFF9EACC0))),
                ),
              )
            else
              Expanded(
                child: GridView.builder(
                  key: const Key('social-gift-catalog-grid'),
                  padding: const EdgeInsets.fromLTRB(16, 2, 16, 12),
                  itemCount: visible.length,
                  gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                    maxCrossAxisExtent: 235,
                    mainAxisExtent: 151,
                    crossAxisSpacing: 10,
                    mainAxisSpacing: 10,
                  ),
                  itemBuilder: (BuildContext context, int index) {
                    final GiftCatalogItem gift = visible[index];
                    return _CommunityGiftCard(
                      gift: gift,
                      selected: selected?.code == gift.code,
                      onTap: () => setState(() { _selectedGift = gift; _confirmPremiumGift = false; }),
                    );
                  },
                ),
              ),
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 3, 18, 0),
              child: TextField(
                key: const Key('social-gift-note'),
                controller: _noteController,
                minLines: 1,
                maxLines: 1,
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  labelText: 'Add a personal note (optional)',
                  labelStyle: const TextStyle(color: Color(0xFF9EACC0), fontSize: 12),
                  prefixIcon: const Icon(Icons.edit_note_rounded, color: Color(0xFF9EACC0)),
                  filled: true,
                  fillColor: const Color(0xFF111D2D),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(13), borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.07))),
                  enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(13), borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.07))),
                ),
              ),
            ),
            if (selected != null && selected.costAmount >= 500)
              CheckboxListTile(
                key: const Key('social-gift-premium-confirm'),
                contentPadding: const EdgeInsets.symmetric(horizontal: 12),
                dense: true,
                controlAffinity: ListTileControlAffinity.leading,
                activeColor: GtexColors.gold,
                checkColor: const Color(0xFF121212),
                value: _confirmPremiumGift,
                onChanged: (bool? value) => setState(() => _confirmPremiumGift = value ?? false),
                title: const Text('I confirm this premium gift spend', style: TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w700)),
                subtitle: const Text('High-value gift packs require extra confirmation.', style: TextStyle(color: Color(0xFF8999AD), fontSize: 10)),
              ),
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 9, 18, 17),
              child: Row(
                children: <Widget>[
                  if (selected != null) ...<Widget>[
                    _CommunityGiftIcon(gift: selected, size: 46),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(selected.displayName, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 12)),
                          const SizedBox(height: 3),
                          Text(_priceLabel(selected), style: TextStyle(color: _communityGiftColor(selected.rarity), fontWeight: FontWeight.w900, fontSize: 11)),
                        ],
                      ),
                    ),
                  ] else
                    const Expanded(child: Text('Choose a gift to continue', style: TextStyle(color: Color(0xFF9EACC0)))),
                  const SizedBox(width: 8),
                  FilledButton.icon(
                    key: const Key('social-gift-send'),
                    onPressed: _isSending || selected == null || _requiresReview(selected) || (selected.costAmount >= 500 && !_confirmPremiumGift) ? null : _sendGift,
                    style: FilledButton.styleFrom(backgroundColor: GtexColors.gold, foregroundColor: const Color(0xFF11131A), padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 14)),
                    icon: _isSending
                        ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF11131A)))
                        : const Icon(Icons.send_rounded, size: 16),
                    label: Text(_isSending ? 'Sending…' : selected != null && _requiresReview(selected) ? 'Under review' : 'Send gift', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 11)),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CommunityGiftCard extends StatelessWidget {
  const _CommunityGiftCard({
    required this.gift,
    required this.selected,
    required this.onTap,
  });

  final GiftCatalogItem gift;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final Color accent = _communityGiftColor(gift.rarity);
    final bool underReview = gift.legalStatus.trim().toLowerCase() == 'requires_review' ||
        gift.legalStatus.trim().toLowerCase() == 'pending_review';
    return Semantics(
      button: true,
      selected: selected,
      label: '${gift.displayName}, ${gift.costAmount} ${gift.currencyLabel}, ${gift.rarity}',
      child: InkWell(
        key: Key('social-gift-card-${gift.code}'),
        onTap: onTap,
        borderRadius: BorderRadius.circular(17),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 210),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(17),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[
                accent.withValues(alpha: selected ? 0.23 : 0.11),
                const Color(0xFF111B2B),
                const Color(0xFF0B1320),
              ],
            ),
            border: Border.all(color: selected ? accent : accent.withValues(alpha: 0.33), width: selected ? 1.7 : 1),
            boxShadow: selected ? <BoxShadow>[BoxShadow(color: accent.withValues(alpha: 0.14), blurRadius: 16)] : const <BoxShadow>[],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  _CommunityGiftIcon(gift: gift, size: 43),
                  const Spacer(),
                  if (selected) Icon(Icons.check_circle_rounded, color: accent, size: 18),
                ],
              ),
              const Spacer(),
              Text(gift.displayName, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 12)),
              const SizedBox(height: 3),
              Text(gift.rarity.toUpperCase(), style: TextStyle(color: accent, fontSize: 9, fontWeight: FontWeight.w900, letterSpacing: 1.1)),
              const SizedBox(height: 4),
              Row(
                children: <Widget>[
                  Expanded(
                    child: Text(
                      '${gift.costAmount.toStringAsFixed(gift.costAmount.truncateToDouble() == gift.costAmount ? 0 : 2)} ${gift.currencyLabel}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Color(0xFFE7DCBF), fontWeight: FontWeight.w800, fontSize: 10),
                    ),
                  ),
                  if (underReview) const Icon(Icons.lock_clock_rounded, color: Color(0xFFFFC66D), size: 15),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CommunityGiftIcon extends StatelessWidget {
  const _CommunityGiftIcon({required this.gift, this.size = 48});

  final GiftCatalogItem gift;
  final double size;

  @override
  Widget build(BuildContext context) {
    final Color accent = _communityGiftColor(gift.rarity);
    final String key = gift.code.toLowerCase();
    final IconData icon = key.contains('whistle')
        ? Icons.sports
        : key.contains('chant')
        ? Icons.campaign_rounded
        : key.contains('goal') || key.contains('boot')
        ? Icons.sports_soccer_rounded
        : key.contains('legend') || key.contains('award') || key.contains('dor')
        ? Icons.workspace_premium_rounded
        : key.contains('tactic') || key.contains('midfield')
        ? Icons.auto_awesome_motion_rounded
        : key.contains('hands')
        ? Icons.back_hand_rounded
        : Icons.card_giftcard_rounded;
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(size * 0.31),
        gradient: RadialGradient(colors: <Color>[accent.withValues(alpha: 0.25), const Color(0xFF17243A)]),
        border: Border.all(color: accent.withValues(alpha: 0.72)),
      ),
      child: Icon(icon, color: accent, size: size * 0.52),
    );
  }
}

Color _communityGiftColor(String rarity) {
  switch (rarity.trim().toLowerCase()) {
    case 'rare':
      return const Color(0xFF69C7FF);
    case 'epic':
      return const Color(0xFFC29BFF);
    case 'legendary':
      return const Color(0xFFFFC96B);
    case 'mythic':
      return const Color(0xFFFF8EAB);
    default:
      return GtexColors.gold;
  }
}

String _capitalise(String value) =>
    value.isEmpty ? value : '${value[0].toUpperCase()}${value.substring(1)}';

class _GiftFanfarePreview extends StatelessWidget {
  const _GiftFanfarePreview({
    required this.event,
    required this.note,
    required this.deliveryContext,
  });

  final GiftEvent event;
  final String note;
  final String deliveryContext;

  @override
  Widget build(BuildContext context) {
    final Color accent = _communityGiftColor(event.rarity);
    final String animationKey = event.animationKey ??
        (event.animationPayload['animation_key']?.toString() ?? 'gift_fanfare');
    final String receiver = event.recipientUserId.isEmpty
        ? deliveryContext
        : 'GTEX user ${event.recipientUserId}';
    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
      child: TweenAnimationBuilder<double>(
        tween: Tween<double>(begin: 0.82, end: 1),
        duration: const Duration(milliseconds: 430),
        curve: Curves.easeOutBack,
        builder: (BuildContext context, double value, Widget? child) =>
            Transform.scale(scale: value, child: child),
        child: Container(
          padding: const EdgeInsets.all(22),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[Color(0xFF1B2C44), Color(0xFF0C1524), Color(0xFF080F1B)],
            ),
            borderRadius: BorderRadius.circular(27),
            border: Border.all(color: accent.withValues(alpha: 0.78), width: 1.4),
            boxShadow: <BoxShadow>[
              BoxShadow(color: accent.withValues(alpha: 0.20), blurRadius: 36),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              const Text('GTEX COMMUNITY GIFTS', style: TextStyle(color: Color(0xFFE8C979), fontSize: 10, letterSpacing: 2.5, fontWeight: FontWeight.w900)),
              const SizedBox(height: 18),
              Stack(
                alignment: Alignment.center,
                children: <Widget>[
                  TweenAnimationBuilder<double>(
                    tween: Tween<double>(begin: 0.65, end: 1),
                    duration: const Duration(milliseconds: 850),
                    builder: (BuildContext context, double value, Widget? child) =>
                        Transform.scale(scale: value, child: child),
                    child: Container(
                      width: 148,
                      height: 148,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: RadialGradient(colors: <Color>[accent.withValues(alpha: 0.27), accent.withValues(alpha: 0.04), Colors.transparent]),
                        border: Border.all(color: accent.withValues(alpha: 0.33)),
                      ),
                    ),
                  ),
                  _CommunityGiftIcon(gift: GiftCatalogItem(
                    id: event.id,
                    code: event.giftKey,
                    displayName: event.giftDisplayName,
                    costAmount: event.grossAmount,
                    currencyLabel: event.currencyLabel,
                    rarity: event.rarity,
                    tier: 'delivery',
                    isAwardPack: event.rarity == 'legendary' || event.rarity == 'mythic',
                    legalStatus: 'safe',
                    animationKey: event.animationKey,
                  ), size: 105),
                  Positioned(
                    right: 5,
                    bottom: 5,
                    child: Container(
                      width: 34,
                      height: 34,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: const Color(0xFF0D1A2A),
                        border: Border.all(color: const Color(0xFF7DE0AD), width: 1.5),
                      ),
                      child: const Icon(Icons.check_rounded, color: Color(0xFF7DE0AD)),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 19),
              const Text('GIFT SENT SUCCESSFULLY', style: TextStyle(color: Color(0xFF7DE0AD), letterSpacing: 1.8, fontSize: 10, fontWeight: FontWeight.w900)),
              const SizedBox(height: 7),
              Text(
                event.giftDisplayName,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(color: Colors.white, fontWeight: FontWeight.w900),
              ),
              const SizedBox(height: 7),
              Text('Delivered to $receiver', textAlign: TextAlign.center, style: const TextStyle(color: Color(0xFFAFBED1), fontSize: 12)),
              const SizedBox(height: 16),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                decoration: BoxDecoration(color: Colors.black.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(14), border: Border.all(color: accent.withValues(alpha: 0.26))),
                child: Row(
                  children: <Widget>[
                    Icon(Icons.account_balance_wallet_outlined, color: accent, size: 19),
                    const SizedBox(width: 9),
                    const Expanded(child: Text('Confirmed gift total', style: TextStyle(color: Color(0xFFB4C2D5), fontSize: 11))),
                    Text('${event.grossAmount.toStringAsFixed(event.grossAmount.truncateToDouble() == event.grossAmount ? 0 : 2)} ${event.currencyLabel}', style: TextStyle(color: accent, fontWeight: FontWeight.w900, fontSize: 12)),
                  ],
                ),
              ),
              const SizedBox(height: 11),
              if (note.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Text('“$note”', textAlign: TextAlign.center, style: const TextStyle(color: Color(0xFFE1D7BC), fontSize: 12, fontStyle: FontStyle.italic)),
                ),
              Text('Animation: $animationKey · Receipt: ${event.id.isEmpty ? 'recorded by GTEX' : event.id}', textAlign: TextAlign.center, style: const TextStyle(color: Color(0xFF8191A7), fontSize: 10)),
              const SizedBox(height: 18),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  key: const Key('social-gift-delivery-close'),
                  onPressed: () => Navigator.of(context).pop(),
                  style: FilledButton.styleFrom(backgroundColor: accent, foregroundColor: const Color(0xFF10131B), padding: const EdgeInsets.symmetric(vertical: 14), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
                  child: const Text('Return to community', style: TextStyle(fontWeight: FontWeight.w900)),
                ),
              ),
            ],
          ),
        ),
      ),
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
    this.trailing,
    this.accent,
  });

  final String title;
  final String body;
  final String footer;
  final Widget? trailing;
  final Color? accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: (accent ?? GteShellTheme.accentCommunity).withValues(
          alpha: 0.08,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  title,
                  style: Theme.of(context).textTheme.titleSmall,
                ),
              ),
              if (trailing != null) trailing!,
            ],
          ),
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

class _DiscussionThreadDraft {
  const _DiscussionThreadDraft({
    required this.category,
    required this.title,
    required this.body,
  });

  final String category;
  final String title;
  final String body;
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
