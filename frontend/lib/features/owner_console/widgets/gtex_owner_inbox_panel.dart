import 'package:flutter/material.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/owner_console/data/owner_console_api.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

/// Unified Owner Inbox & Attention surface (Master Plan Document H2 & Phase E1).
///
/// Renders server-supplied attention counts, status/category filters, and inbox
/// items using canonical [GtexAttentionCard], [GtexStatusChip.fromBackendStatus],
/// and [GtexConfirmSheet] with double-tap protection, idempotency keys, and
/// graceful `409` (already decided) recovery.
class GtexOwnerInboxPanel extends StatefulWidget {
  const GtexOwnerInboxPanel({
    super.key,
    required this.api,
    this.clubId,
    this.saveContextId,
    this.initialStatus = 'open',
    this.initialCategory = 'all',
    this.initialUnreadOnly = false,
    this.initialFeed,
    this.onItemUpdated,
    this.onNavigateRoute,
  });

  final GtexOwnerInboxDataSource api;
  final String? clubId;
  final String? saveContextId;
  final String initialStatus;
  final String initialCategory;
  final bool initialUnreadOnly;
  final GtexOwnerInboxFeed? initialFeed;
  final ValueChanged<OwnerInboxEntry>? onItemUpdated;
  final ValueChanged<String>? onNavigateRoute;

  static const List<(String, String)> statusFilters = <(String, String)>[
    ('open', 'Open'),
    ('resolved', 'Resolved'),
    ('archived', 'Archived'),
  ];

  static const List<(String, String)> categoryFilters = <(String, String)>[
    ('all', 'All'),
    ('requests', 'Requests'),
    ('deadlines', 'Deadlines'),
    ('staff_recommendations', 'Staff'),
    ('player_issues', 'Player Issues'),
    ('scouting_reports', 'Scouting'),
    ('negotiations', 'Negotiations'),
    ('scheduling', 'Scheduling'),
  ];

  @override
  State<GtexOwnerInboxPanel> createState() => _GtexOwnerInboxPanelState();
}

class _GtexOwnerInboxPanelState extends State<GtexOwnerInboxPanel> {
  late String _selectedStatus;
  late String _selectedCategory;
  late bool _unreadOnly;

  GtexOwnerInboxFeed? _feed;
  bool _loading = false;
  String? _errorMessage;
  String? _conflictMessage;

  final Set<String> _inFlightItemIds = <String>{};
  final Map<String, OwnerInboxEntry> _sessionResolvedOverlay =
      <String, OwnerInboxEntry>{};

  @override
  void initState() {
    super.initState();
    _selectedStatus = widget.initialStatus;
    _selectedCategory = widget.initialCategory;
    _unreadOnly = widget.initialUnreadOnly;
    if (widget.initialFeed != null) {
      _feed = widget.initialFeed;
    } else {
      _loadInbox();
    }
  }

  @override
  void didUpdateWidget(covariant GtexOwnerInboxPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.clubId != widget.clubId ||
        oldWidget.saveContextId != widget.saveContextId) {
      _sessionResolvedOverlay.clear();
      _loadInbox();
    }
  }

  Future<void> _loadInbox({bool preserveOverlay = false}) async {
    if (!preserveOverlay) {
      _conflictMessage = null;
    }
    setState(() {
      _loading = true;
      _errorMessage = null;
    });
    try {
      final GtexOwnerInboxFeed feed = await widget.api.fetchInbox(
        status: _selectedStatus,
        category: _selectedCategory,
        clubId: widget.clubId,
        saveContextId: widget.saveContextId,
        unreadOnly: _unreadOnly,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _feed = feed;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _loading = false;
        _errorMessage = _cleanError(error);
      });
    }
  }

  Future<void> _selectStatus(String status) async {
    if (_selectedStatus == status) {
      return;
    }
    setState(() {
      _selectedStatus = status;
      _sessionResolvedOverlay.clear();
      _conflictMessage = null;
    });
    await _loadInbox();
  }

  Future<void> _selectCategory(String category) async {
    if (_selectedCategory == category) {
      return;
    }
    setState(() {
      _selectedCategory = category;
      _conflictMessage = null;
    });
    await _loadInbox(preserveOverlay: true);
  }

  Future<void> _toggleUnreadOnly() async {
    setState(() {
      _unreadOnly = !_unreadOnly;
    });
    await _loadInbox(preserveOverlay: true);
  }

  Future<void> _markItemRead(OwnerInboxEntry item) async {
    if (_inFlightItemIds.contains(item.id) || item.isRead) {
      return;
    }
    setState(() {
      _inFlightItemIds.add(item.id);
      _errorMessage = null;
    });
    try {
      final OwnerInboxEntry updated = await widget.api.markInboxItemRead(
        item.id,
      );
      widget.onItemUpdated?.call(updated);
      if (_sessionResolvedOverlay.containsKey(item.id)) {
        _sessionResolvedOverlay[item.id] = updated;
      }
      await _loadInbox(preserveOverlay: true);
    } catch (error) {
      if (mounted) {
        setState(() {
          _errorMessage = _cleanError(error);
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _inFlightItemIds.remove(item.id);
        });
      } else {
        _inFlightItemIds.remove(item.id);
      }
    }
  }

  Future<void> _archiveItem(OwnerInboxEntry item) async {
    if (_inFlightItemIds.contains(item.id)) {
      return;
    }
    setState(() {
      _inFlightItemIds.add(item.id);
      _errorMessage = null;
    });
    try {
      final OwnerInboxEntry archived = await widget.api.archiveInboxItem(
        item.id,
      );
      _sessionResolvedOverlay.remove(item.id);
      widget.onItemUpdated?.call(archived);
      await _loadInbox(preserveOverlay: true);
    } catch (error) {
      if (mounted) {
        setState(() {
          _errorMessage = _cleanError(error);
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _inFlightItemIds.remove(item.id);
        });
      } else {
        _inFlightItemIds.remove(item.id);
      }
    }
  }

  Future<void> _promptDecision(
    OwnerInboxEntry item,
    OwnerDecisionAction action,
  ) async {
    if (_inFlightItemIds.contains(item.id) || item.isResolved) {
      return;
    }
    final GtexConfirmFinancialDetails? financialDetails =
        _buildFinancialDetails(item, action);
    final String idempotencyKey = 'inbox-decide-${item.id}-${action.key}';

    await GtexConfirmSheet.show(
      context,
      title: 'Confirm ${action.label}',
      summary: item.what ?? item.why ?? item.title,
      confirmLabel: action.label,
      variant:
          financialDetails != null
              ? GtexConfirmVariant.financial
              : GtexConfirmVariant.standard,
      financialDetails: financialDetails,
      idempotencyKey: idempotencyKey,
      onConfirm: (String resolvedKey) async {
        await _executeDecision(
          item,
          action,
          idempotencyKey: resolvedKey,
        );
      },
    );
  }

  Future<void> _executeDecision(
    OwnerInboxEntry item,
    OwnerDecisionAction action, {
    required String idempotencyKey,
  }) async {
    if (_inFlightItemIds.contains(item.id)) {
      return;
    }
    _inFlightItemIds.add(item.id);
    try {
      final OwnerInboxEntry decided = await widget.api.decideInboxItem(
        item.id,
        action: action.key,
        idempotencyKey: idempotencyKey,
      );
      _sessionResolvedOverlay[item.id] = decided;
      widget.onItemUpdated?.call(decided);
      await _loadInbox(preserveOverlay: true);
    } catch (error) {
      if (_isConflictError(error)) {
        await _recoverFromAlreadyDecided(item);
        return;
      }
      rethrow;
    } finally {
      _inFlightItemIds.remove(item.id);
    }
  }

  bool _isConflictError(Object error) {
    if (error is GteApiException && error.statusCode == 409) {
      return true;
    }
    final String text = error.toString().toLowerCase();
    return text.contains('409') ||
        text.contains('already_resolved') ||
        text.contains('already decided') ||
        text.contains('already resolved');
  }

  Future<void> _recoverFromAlreadyDecided(OwnerInboxEntry staleItem) async {
    OwnerInboxEntry? refreshedItem;
    GtexOwnerInboxFeed? latestFeed;
    try {
      latestFeed = await widget.api.fetchInbox(
        status: _selectedStatus,
        category: _selectedCategory,
        clubId: widget.clubId,
        saveContextId: widget.saveContextId,
        unreadOnly: _unreadOnly,
      );
      for (final OwnerInboxEntry entry in latestFeed.items) {
        if (entry.id == staleItem.id) {
          refreshedItem = entry;
          break;
        }
      }
      if (refreshedItem == null || !refreshedItem.isResolved) {
        final GtexOwnerInboxFeed resolvedFeed = await widget.api.fetchInbox(
          status: 'resolved',
          category: 'all',
          clubId: widget.clubId,
          saveContextId: widget.saveContextId,
        );
        for (final OwnerInboxEntry entry in resolvedFeed.items) {
          if (entry.id == staleItem.id) {
            refreshedItem = entry;
            break;
          }
        }
      }
    } catch (_) {
      // Fallback to local resolved representation if refresh fails.
    }

    final OwnerInboxEntry resolvedItem =
        refreshedItem ??
        staleItem.copyWith(
          status: 'resolved',
          isRead: true,
          outcome:
              staleItem.outcome ?? 'Decision was already resolved on server.',
        );
    _sessionResolvedOverlay[staleItem.id] = resolvedItem;
    widget.onItemUpdated?.call(resolvedItem);

    if (!mounted) {
      return;
    }
    setState(() {
      if (latestFeed != null) {
        _feed = latestFeed;
      }
      _loading = false;
      _conflictMessage =
          'This item was already decided. Refreshed to its resolved state.';
    });
  }

  GtexConfirmFinancialDetails? _buildFinancialDetails(
    OwnerInboxEntry item,
    OwnerDecisionAction action,
  ) {
    final Object? rawAmount =
        item.payload['cost'] ??
        item.payload['bid'] ??
        item.payload['budget'] ??
        item.payload['gross'];
    if (rawAmount == null) {
      return null;
    }
    final num? parsed =
        rawAmount is num ? rawAmount : num.tryParse('$rawAmount');
    if (parsed == null || parsed <= 0) {
      return null;
    }
    return GtexConfirmFinancialDetails(
      amountLabel: parsed.toStringAsFixed(parsed % 1 == 0 ? 0 : 2),
      currencyCode: 'GTX',
      idempotencyKey: 'inbox-decide-${item.id}-${action.key}',
    );
  }

  List<OwnerInboxEntry> _visibleItems() {
    final List<OwnerInboxEntry> serverItems =
        _feed?.items ?? const <OwnerInboxEntry>[];
    final bool showingArchived =
        _selectedStatus == 'archived' || _selectedCategory == 'archive';

    final List<OwnerInboxEntry> merged = <OwnerInboxEntry>[];
    final Set<String> seenIds = <String>{};

    for (final OwnerInboxEntry item in serverItems) {
      final OwnerInboxEntry effective =
          _sessionResolvedOverlay[item.id] ?? item;
      if (showingArchived) {
        if (!effective.isArchived) {
          continue;
        }
      } else {
        if (effective.isArchived) {
          continue;
        }
        if (_selectedStatus == 'open' &&
            !effective.isOpen &&
            !_sessionResolvedOverlay.containsKey(effective.id)) {
          continue;
        }
        if (_selectedStatus == 'resolved' && !effective.isResolved) {
          continue;
        }
      }
      if (_unreadOnly && effective.isRead) {
        continue;
      }
      merged.add(effective);
      seenIds.add(effective.id);
    }

    if (!showingArchived) {
      for (final OwnerInboxEntry overlayItem
          in _sessionResolvedOverlay.values) {
        if (seenIds.contains(overlayItem.id) || overlayItem.isArchived) {
          continue;
        }
        if (_selectedCategory != 'all' &&
            overlayItem.category != _selectedCategory) {
          continue;
        }
        if (_unreadOnly && overlayItem.isRead) {
          continue;
        }
        merged.add(overlayItem);
      }
    }

    return merged;
  }

  String _cleanError(Object error) {
    final String raw = error.toString().trim();
    if (raw.isEmpty) {
      return 'Unable to load owner inbox.';
    }
    return raw.split('\n').first.replaceFirst(RegExp(r'^Exception:\s*'), '');
  }

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    final GtexOwnerInboxCounts counts =
        _feed?.counts ?? const GtexOwnerInboxCounts();
    final List<OwnerInboxEntry> items = _visibleItems();

    return Container(
      key: const Key('gtex-owner-inbox-panel'),
      padding: const EdgeInsets.all(GtexSpacing.md),
      decoration: BoxDecoration(
        color: navy.bgBase,
        borderRadius: BorderRadius.circular(GtexRadius.card),
        border: Border.all(color: navy.lineSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          _InboxHeader(
            counts: counts,
            loading: _loading,
            onRefresh: () => _loadInbox(preserveOverlay: true),
          ),
          const SizedBox(height: GtexSpacing.sm),
          _StatusFilterRow(
            selectedStatus: _selectedStatus,
            counts: counts,
            unreadOnly: _unreadOnly,
            onSelectStatus: _selectStatus,
            onToggleUnreadOnly: _toggleUnreadOnly,
          ),
          const SizedBox(height: GtexSpacing.xs),
          _CategoryFilterRow(
            selectedCategory: _selectedCategory,
            counts: counts,
            onSelectCategory: _selectCategory,
          ),
          if (_conflictMessage != null) ...<Widget>[
            const SizedBox(height: GtexSpacing.sm),
            Container(
              key: const Key('gtex-owner-inbox-conflict-banner'),
              padding: const EdgeInsets.all(GtexSpacing.sm),
              decoration: BoxDecoration(
                color: navy.info.withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(GtexRadius.chip),
                border: Border.all(color: navy.info),
              ),
              child: Row(
                children: <Widget>[
                  Icon(Icons.sync_problem_rounded, size: 18, color: navy.info),
                  const SizedBox(width: GtexSpacing.xs),
                  Expanded(
                    child: Text(
                      _conflictMessage!,
                      style: GtexTypography.bodyS(color: navy.textPrimary),
                    ),
                  ),
                ],
              ),
            ),
          ],
          if (_errorMessage != null) ...<Widget>[
            const SizedBox(height: GtexSpacing.sm),
            GtexErrorBanner(
              key: const Key('gtex-owner-inbox-error-banner'),
              message: _errorMessage!,
              onRetry: () => _loadInbox(preserveOverlay: true),
            ),
          ],
          const SizedBox(height: GtexSpacing.sm),
          if (_loading && _feed == null)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: GtexSpacing.md),
              child: GtexSkeleton.box(height: 140),
            )
          else if (items.isEmpty)
            Container(
              key: const Key('gtex-owner-inbox-empty-state'),
              padding: const EdgeInsets.all(GtexSpacing.lg),
              decoration: BoxDecoration(
                color: navy.bgRaised,
                borderRadius: BorderRadius.circular(GtexRadius.card),
                border: Border.all(color: navy.lineSubtle),
              ),
              child: Column(
                children: <Widget>[
                  Icon(
                    Icons.inbox_outlined,
                    size: 28,
                    color: navy.textSecondary,
                  ),
                  const SizedBox(height: GtexSpacing.xs),
                  Text(
                    _selectedStatus == 'archived'
                        ? 'No archived inbox items'
                        : 'Inbox is clear for this filter',
                    style: GtexTypography.titleS(color: navy.textPrimary),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'New board decisions, staff recommendations, and deadlines appear here.',
                    textAlign: TextAlign.center,
                    style: GtexTypography.bodyS(color: navy.textSecondary),
                  ),
                ],
              ),
            )
          else
            Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                for (final OwnerInboxEntry item in items) ...<Widget>[
                  _OwnerInboxItemTile(
                    key: Key('gtex-owner-inbox-item-${item.id}'),
                    item: item,
                    busy: _inFlightItemIds.contains(item.id),
                    onMarkRead: () => _markItemRead(item),
                    onArchive: () => _archiveItem(item),
                    onDecide:
                        (OwnerDecisionAction action) =>
                            _promptDecision(item, action),
                  ),
                  const SizedBox(height: GtexSpacing.sm),
                ],
              ],
            ),
        ],
      ),
    );
  }
}

class _InboxHeader extends StatelessWidget {
  const _InboxHeader({
    required this.counts,
    required this.loading,
    required this.onRefresh,
  });

  final GtexOwnerInboxCounts counts;
  final bool loading;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    final String badgeSummary =
        counts.deadlines > 0
            ? '${counts.open} Open · ${counts.unread} Unread · ${counts.deadlines} Deadlines'
            : '${counts.open} Open · ${counts.unread} Unread';

    return Wrap(
      alignment: WrapAlignment.spaceBetween,
      crossAxisAlignment: WrapCrossAlignment.center,
      spacing: GtexSpacing.sm,
      runSpacing: GtexSpacing.xs,
      children: <Widget>[
        Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(Icons.mark_email_unread_outlined, color: navy.gold500, size: 20),
            const SizedBox(width: GtexSpacing.xs),
            Text(
              'Owner Inbox & Attention',
              style: GtexTypography.titleM(color: navy.textPrimary),
            ),
          ],
        ),
        Wrap(
          spacing: GtexSpacing.xs,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: <Widget>[
            Container(
              key: const Key('gtex-owner-inbox-counts-badge'),
              padding: const EdgeInsets.symmetric(
                horizontal: GtexSpacing.sm,
                vertical: 6,
              ),
              decoration: BoxDecoration(
                color: navy.bgRaised,
                borderRadius: BorderRadius.circular(GtexRadius.pill),
                border: Border.all(
                  color: counts.open > 0 ? navy.gold500 : navy.lineSubtle,
                ),
              ),
              child: Text(
                badgeSummary,
                style: GtexTypography.numericS(
                  color: counts.open > 0 ? navy.gold300 : navy.textSecondary,
                ),
              ),
            ),
            IconButton(
              key: const Key('gtex-owner-inbox-refresh-button'),
              tooltip: 'Refresh inbox',
              onPressed: loading ? null : onRefresh,
              icon: Icon(
                Icons.refresh_rounded,
                size: 18,
                color: navy.textSecondary,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _StatusFilterRow extends StatelessWidget {
  const _StatusFilterRow({
    required this.selectedStatus,
    required this.counts,
    required this.unreadOnly,
    required this.onSelectStatus,
    required this.onToggleUnreadOnly,
  });

  final String selectedStatus;
  final GtexOwnerInboxCounts counts;
  final bool unreadOnly;
  final ValueChanged<String> onSelectStatus;
  final VoidCallback onToggleUnreadOnly;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    return Wrap(
      spacing: GtexSpacing.xs,
      runSpacing: GtexSpacing.xs,
      children: <Widget>[
        for (final (String key, String label)
            in GtexOwnerInboxPanel.statusFilters)
          ChoiceChip(
            key: Key('gtex-owner-inbox-status-$key'),
            label: Text(
              switch (key) {
                'open' => '$label (${counts.open})',
                'archived' => '$label (${counts.archive})',
                _ => label,
              },
            ),
            selected: selectedStatus == key,
            onSelected: (_) => onSelectStatus(key),
            selectedColor: navy.gold500.withValues(alpha: 0.2),
            backgroundColor: navy.bgRaised,
            labelStyle: GtexTypography.label(
              color:
                  selectedStatus == key ? navy.gold300 : navy.textSecondary,
            ),
            side: BorderSide(
              color: selectedStatus == key ? navy.gold500 : navy.lineSubtle,
            ),
          ),
        FilterChip(
          key: const Key('gtex-owner-inbox-unread-toggle'),
          label: Text('Unread only (${counts.unread})'),
          selected: unreadOnly,
          onSelected: (_) => onToggleUnreadOnly(),
          selectedColor: navy.info.withValues(alpha: 0.2),
          backgroundColor: navy.bgRaised,
          labelStyle: GtexTypography.label(
            color: unreadOnly ? navy.info : navy.textSecondary,
          ),
          side: BorderSide(
            color: unreadOnly ? navy.info : navy.lineSubtle,
          ),
        ),
      ],
    );
  }
}

class _CategoryFilterRow extends StatelessWidget {
  const _CategoryFilterRow({
    required this.selectedCategory,
    required this.counts,
    required this.onSelectCategory,
  });

  final String selectedCategory;
  final GtexOwnerInboxCounts counts;
  final ValueChanged<String> onSelectCategory;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: <Widget>[
          for (final (String key, String label)
              in GtexOwnerInboxPanel.categoryFilters) ...<Widget>[
            ChoiceChip(
              key: Key('gtex-owner-inbox-category-$key'),
              label: Text(
                '$label (${counts.countForCategory(key)})',
              ),
              selected: selectedCategory == key,
              onSelected: (_) => onSelectCategory(key),
              selectedColor: navy.bgOverlay,
              backgroundColor: navy.bgInset,
              labelStyle: GtexTypography.bodyS(
                color:
                    selectedCategory == key
                        ? navy.textPrimary
                        : navy.textSecondary,
              ),
              side: BorderSide(
                color:
                    selectedCategory == key ? navy.lineStrong : navy.lineSubtle,
              ),
            ),
            const SizedBox(width: GtexSpacing.xs),
          ],
        ],
      ),
    );
  }
}

class _OwnerInboxItemTile extends StatelessWidget {
  const _OwnerInboxItemTile({
    super.key,
    required this.item,
    required this.busy,
    required this.onMarkRead,
    required this.onArchive,
    required this.onDecide,
  });

  final OwnerInboxEntry item;
  final bool busy;
  final VoidCallback onMarkRead;
  final VoidCallback onArchive;
  final ValueChanged<OwnerDecisionAction> onDecide;

  GtexAttentionVariant _resolveVariant() {
    return switch (item.category) {
      'deadlines' => GtexAttentionVariant.deadline,
      'player_issues' => GtexAttentionVariant.alert,
      'staff_recommendations' =>
        item.isDecision
            ? GtexAttentionVariant.approval
            : GtexAttentionVariant.info,
      _ =>
        item.isDecision
            ? GtexAttentionVariant.decision
            : GtexAttentionVariant.info,
    };
  }

  GtexAttentionState _resolveState(DateTime now) {
    if (item.isResolved) {
      return GtexAttentionState.resolved;
    }
    final DateTime? due = item.respondBy ?? item.deadlineAt;
    if (due != null) {
      final Duration remaining = due.difference(now);
      if (remaining <= Duration.zero) {
        return GtexAttentionState.overdue;
      }
      if (remaining <= const Duration(hours: 6)) {
        return GtexAttentionState.dueSoon;
      }
    }
    if (item.isRead) {
      return GtexAttentionState.dueSoon;
    }
    return GtexAttentionState.unread;
  }

  String? _resolveDueLabel(DateTime now) {
    if (item.isResolved) {
      return 'Resolved';
    }
    final DateTime? due = item.respondBy ?? item.deadlineAt;
    if (due != null) {
      final Duration remaining = due.difference(now);
      if (remaining <= Duration.zero) {
        return 'Overdue';
      }
      if (remaining.inDays > 0) {
        return 'Due ${remaining.inDays}d';
      }
      if (remaining.inHours > 0) {
        return 'Due ${remaining.inHours}h';
      }
      return 'Due ${remaining.inMinutes.clamp(1, 59)}m';
    }
    return item.isRead ? 'Read' : 'Unread';
  }

  String _backendStatusToken() {
    if (item.isResolved) {
      return 'accepted';
    }
    if (item.isArchived) {
      return 'archived';
    }
    return item.status ?? 'open';
  }

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    final DateTime now = DateTime.now().toUtc();
    final OwnerDecisionAction? primaryAction =
        item.actions.isEmpty
            ? null
            : item.actions.firstWhere(
              (OwnerDecisionAction a) => a.isPrimary,
              orElse: () => item.actions.first,
            );

    return Container(
      padding: const EdgeInsets.all(GtexSpacing.sm),
      decoration: BoxDecoration(
        color: navy.bgRaised,
        borderRadius: BorderRadius.circular(GtexRadius.card),
        border: Border.all(color: navy.lineSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          GtexAttentionCard(
            key: Key('gtex-owner-inbox-attention-${item.id}'),
            title: item.title,
            subtitle: item.what ?? item.why ?? item.body ?? '',
            variant: _resolveVariant(),
            state: _resolveState(now),
            dueLabel: _resolveDueLabel(now),
            whoActsNextLabel:
                item.isResolved
                    ? 'RESOLVED'
                    : (item.isDecision ? 'OWNER ACTS NEXT' : 'BOARD BRIEFING'),
            primaryActionLabel: primaryAction?.label ?? 'Review',
            onPrimaryAction:
                !item.isResolved && !item.isArchived && primaryAction != null
                    ? () => onDecide(primaryAction)
                    : null,
            onTap: !item.isRead ? onMarkRead : null,
          ),
          const SizedBox(height: GtexSpacing.xs),
          Wrap(
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: GtexSpacing.xs,
            runSpacing: GtexSpacing.xs,
            children: <Widget>[
              Wrap(
                spacing: GtexSpacing.xs,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: <Widget>[
                  GtexStatusChip.fromBackendStatus(
                    _backendStatusToken(),
                    key: Key('gtex-owner-inbox-status-chip-${item.id}'),
                    context:
                        item.isDecision
                            ? GtexStatusContext.decisionRequired
                            : GtexStatusContext.general,
                    compact: true,
                  ),
                  Container(
                    key: Key('gtex-owner-inbox-read-state-${item.id}'),
                    padding: const EdgeInsets.symmetric(
                      horizontal: GtexSpacing.xs,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: navy.bgInset,
                      borderRadius: BorderRadius.circular(GtexRadius.pill),
                      border: Border.all(color: navy.lineSubtle),
                    ),
                    child: Text(
                      item.isRead ? 'Read' : 'Unread',
                      style: GtexTypography.bodyS(
                        color:
                            item.isRead ? navy.textSecondary : navy.gold300,
                      ),
                    ),
                  ),
                  if ((item.sender ?? '').isNotEmpty)
                    Text(
                      'From ${item.sender}',
                      style: GtexTypography.bodyS(color: navy.textSecondary),
                    ),
                ],
              ),
              Wrap(
                spacing: GtexSpacing.xs,
                runSpacing: GtexSpacing.xs,
                children: <Widget>[
                  if (!item.isRead)
                    TextButton.icon(
                      key: Key('gtex-owner-inbox-read-${item.id}'),
                      onPressed: busy ? null : onMarkRead,
                      icon: Icon(
                        Icons.done_rounded,
                        size: 16,
                        color: navy.info,
                      ),
                      label: Text(
                        'Mark read',
                        style: GtexTypography.label(color: navy.info),
                      ),
                    ),
                  if (!item.isResolved && !item.isArchived)
                    for (final OwnerDecisionAction action in item.actions)
                      ElevatedButton(
                        key: Key(
                          'gtex-owner-inbox-decide-${item.id}-${action.key}',
                        ),
                        onPressed: busy ? null : () => onDecide(action),
                        style: ElevatedButton.styleFrom(
                          backgroundColor:
                              action.isPrimary ? navy.gold500 : navy.bgOverlay,
                          foregroundColor:
                              action.isPrimary
                                  ? navy.textInverse
                                  : navy.textPrimary,
                        ),
                        child: Text(action.label),
                      ),
                  if (!item.isArchived)
                    OutlinedButton.icon(
                      key: Key('gtex-owner-inbox-archive-${item.id}'),
                      onPressed: busy ? null : onArchive,
                      style: OutlinedButton.styleFrom(
                        foregroundColor: navy.textSecondary,
                        side: BorderSide(color: navy.lineSubtle),
                      ),
                      icon: Icon(
                        Icons.archive_outlined,
                        size: 16,
                        color: navy.textSecondary,
                      ),
                      label: const Text('Archive'),
                    ),
                ],
              ),
            ],
          ),
          if (item.isResolved && (item.outcome ?? '').trim().isNotEmpty) ...<Widget>[
            const SizedBox(height: GtexSpacing.xs),
            Container(
              key: Key('gtex-owner-inbox-outcome-${item.id}'),
              padding: const EdgeInsets.all(GtexSpacing.sm),
              decoration: BoxDecoration(
                color: navy.success.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(GtexRadius.chip),
                border: Border.all(color: navy.success.withValues(alpha: 0.5)),
              ),
              child: Row(
                children: <Widget>[
                  Icon(
                    Icons.check_circle_outline_rounded,
                    size: 16,
                    color: navy.success,
                  ),
                  const SizedBox(width: GtexSpacing.xs),
                  Expanded(
                    child: Text(
                      item.outcome!.trim(),
                      style: GtexTypography.bodyS(color: navy.textPrimary),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}
