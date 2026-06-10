import 'package:flutter/material.dart';

import '../../core/app_feedback.dart';
import '../../core/constants/app_spacing.dart';
import '../../data/community_api.dart';
import '../../data/gte_api_repository.dart';
import '../../models/community_models.dart';
import '../../shared/widgets/section_heading.dart';
import '../../widgets/creator_club_follow_panel.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import '../community/presentation/community_canonical_surface.dart';

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
    this.api,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final bool isAuthenticated;
  final String? currentClubId;
  final String? currentClubName;
  final VoidCallback? onOpenLogin;
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

  void _showSuccessMessage(String message) {
    AppFeedback.showSuccess(context, message);
  }

  void _showErrorMessage(String message) {
    AppFeedback.showError(context, message);
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
      await _api.addWatchlist(
        competitionKey: draft.competitionKey,
        competitionTitle: draft.competitionTitle,
        competitionType: draft.competitionType,
      );
      if (!mounted) {
        return;
      }
      await _load();
      _showSuccessMessage(
        'Added ${draft.competitionTitle} to your community watchlist.',
      );
    } catch (error) {
      if (!mounted) {
        return;
      }
      _showErrorMessage(AppFeedback.messageFor(error));
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
      await _load();
      _showSuccessMessage(
        'Removed ${item.competitionTitle} from your watchlist.',
      );
    } catch (error) {
      if (!mounted) {
        return;
      }
      _showErrorMessage(AppFeedback.messageFor(error));
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
      await _load();
      _showSuccessMessage('Opened live thread "${draft.title}".');
      await _openLiveThread(thread);
    } catch (error) {
      if (!mounted) {
        return;
      }
      _showErrorMessage(AppFeedback.messageFor(error));
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
      await _load();
      _showSuccessMessage('Opened direct thread "${draft.subjectLabel}".');
      await _openPrivateThread(thread);
    } catch (error) {
      if (!mounted) {
        return;
      }
      _showErrorMessage(AppFeedback.messageFor(error));
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

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(spacingMD),
        children: <Widget>[
          SectionHeading(
            title: 'Community',
            subtitle:
                _hasAuthenticatedCommunityAccess
                    ? 'Watchlists, live threads, direct messages, and creator-club follows are wired to live community endpoints.'
                    : 'Public live threads stay visible here. Sign in to manage follows, watchlists, and direct messages.',
          ),
          CommunityCanonicalSurface(
            isAuthenticated: widget.isAuthenticated,
            hasLiveToken: _hasAuthenticatedCommunityAccess,
            isLoading: _isLoading,
            isMutating: _isMutating,
            digest: _digest,
            watchlist: _watchlist,
            liveThreads: _liveThreads,
            privateThreads: _privateThreads,
            currentClubId: widget.currentClubId,
            currentClubName: widget.currentClubName,
            loadError: _loadError,
          ),
          const SizedBox(height: spacingSM),
          if ((widget.currentClubId?.trim().isNotEmpty ?? false)) ...<Widget>[
            CreatorClubFollowPanel(
              api: widget.api,
              baseUrl: widget.baseUrl,
              backendMode: widget.backendMode,
              clubId: widget.currentClubId!,
              clubName: widget.currentClubName,
              accessToken: widget.accessToken,
              isAuthenticated: _hasAuthenticatedCommunityAccess,
              onOpenLogin: widget.onOpenLogin,
            ),
            const SizedBox(height: spacingSM),
          ],
          if (!_hasAuthenticatedCommunityAccess) ...<Widget>[
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
            const SizedBox(height: spacingSM),
          ],
          if (_digest != null) ...<Widget>[
            _DigestSummary(digest: _digest!),
            const SizedBox(height: spacingSM),
          ],
          if (_loadError != null) ...<Widget>[
            GteStatePanel(
              title: 'Community sync degraded',
              message: _loadError!,
              icon: Icons.sync_problem_outlined,
              actionLabel: 'Retry',
              onAction: _load,
            ),
            const SizedBox(height: spacingSM),
          ],
          _CommunitySection(
            title: 'Competition watchlist',
            subtitle:
                'Pin community competitions and keep their live launches in view.',
            action:
                _hasAuthenticatedCommunityAccess
                    ? FilledButton.tonal(
                      onPressed: _isMutating ? null : _addWatchlist,
                      child: const Text('Add competition'),
                    )
                    : null,
            child:
                _hasAuthenticatedCommunityAccess
                    ? _buildWatchlistBody()
                    : _buildReadOnlyBody(
                      'Sign in to add or remove watchlist entries.',
                    ),
          ),
          const SizedBox(height: spacingSM),
          _CommunitySection(
            title: 'Live threads',
            subtitle:
                'Open real-time matchday and competition discussion lanes.',
            action:
                _hasAuthenticatedCommunityAccess
                    ? FilledButton.tonal(
                      onPressed: _isMutating ? null : _createLiveThread,
                      child: const Text('Start thread'),
                    )
                    : widget.onOpenLogin == null
                    ? null
                    : FilledButton.tonal(
                      onPressed: widget.onOpenLogin,
                      child: const Text('Sign in'),
                    ),
            child: _buildLiveThreadsBody(),
          ),
          const SizedBox(height: spacingSM),
          _CommunitySection(
            title: 'Direct messages',
            subtitle:
                'Open private creator-community threads with real participants.',
            action:
                _hasAuthenticatedCommunityAccess
                    ? FilledButton.tonal(
                      onPressed: _isMutating ? null : _createPrivateThread,
                      child: const Text('New DM'),
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
      ),
    );
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
                    '${item.competitionType} lane - ${item.competitionKey}',
                detail:
                    'Stories ${item.notifyOnStory ? 'on' : 'off'} - Launches ${item.notifyOnLaunch ? 'on' : 'off'} - Updated ${gteFormatDateTime(item.updatedAt)}',
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
                    '${thread.threadKey} - ${thread.status.toUpperCase()}${thread.pinned ? ' - PINNED' : ''}',
                detail:
                    'Competition ${thread.competitionKey ?? 'general'} - Last message ${gteFormatDateTime(thread.lastMessageAt)}',
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
                    '${thread.participants.length} participants - ${thread.status.toUpperCase()}',
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
                '${widget.thread.threadKey} - ${widget.thread.status.toUpperCase()}',
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
              '${message.visibility} - ${message.likeCount} likes - ${gteFormatDateTime(message.createdAt)}',
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
                '${widget.thread.participants.length} participants - ${widget.thread.status.toUpperCase()}',
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
