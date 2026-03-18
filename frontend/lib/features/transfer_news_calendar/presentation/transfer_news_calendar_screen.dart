import 'package:flutter/material.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/shared/data/gte_feature_support.dart';
import 'package:gte_frontend/features/shared/presentation/gte_feature_forms.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

import '../data/transfer_news_calendar_models.dart';
import 'transfer_news_calendar_controller.dart';

class TransferNewsCalendarScreen extends StatefulWidget {
  const TransferNewsCalendarScreen({
    super.key,
    required this.baseUrl,
    required this.backendMode,
    this.accessToken,
    this.currentUserRole,
    this.initialTab = 'windows',
    this.onOpenLogin,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final String? currentUserRole;
  final String initialTab;
  final VoidCallback? onOpenLogin;

  @override
  State<TransferNewsCalendarScreen> createState() =>
      _TransferNewsCalendarScreenState();
}

class _TransferNewsCalendarScreenState
    extends State<TransferNewsCalendarScreen> {
  late final TransferNewsCalendarController _controller;
  late final GteAuthedApi _api;

  List<_TransferWindowRecord> _windows = const <_TransferWindowRecord>[];
  List<_TransferBidRecord> _bids = const <_TransferBidRecord>[];
  String? _selectedWindowId;
  String? _windowsError;
  String? _bidsError;
  bool _isLoadingWindows = false;
  bool _isLoadingBids = false;

  bool get _isAuthenticated =>
      widget.accessToken != null && widget.accessToken!.trim().isNotEmpty;
  bool get _isAdmin => <String>{'admin', 'super_admin'}
      .contains((widget.currentUserRole ?? '').trim().toLowerCase());

  @override
  void initState() {
    super.initState();
    _controller = TransferNewsCalendarController.standard(
      baseUrl: widget.baseUrl,
      backendMode: widget.backendMode,
      accessToken: widget.accessToken,
    );
    _api = createFeatureApi(
      baseUrl: widget.baseUrl,
      mode: widget.backendMode,
      accessToken: widget.accessToken,
    );
    _load();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    await _controller.loadCalendar();
    if (_isAdmin) {
      await _controller.loadAdminEvents();
    }
    await _loadWindows();
  }

  Future<void> _loadWindows() async {
    setState(() {
      _isLoadingWindows = true;
      _windowsError = null;
    });
    try {
      final List<dynamic> payload =
          await _api.getList('/api/transfers/windows', auth: false);
      _windows =
          payload.map(_TransferWindowRecord.fromJson).toList(growable: false);
      _selectedWindowId ??= _windows.isEmpty ? null : _windows.first.id;
      if (_selectedWindowId != null) {
        await _loadBids(_selectedWindowId!);
      }
    } catch (error) {
      _windowsError = AppFeedback.messageFor(error);
    } finally {
      if (mounted) {
        setState(() => _isLoadingWindows = false);
      }
    }
  }

  Future<void> _loadBids(String windowId) async {
    setState(() {
      _selectedWindowId = windowId;
      _isLoadingBids = true;
      _bidsError = null;
    });
    try {
      final List<dynamic> payload = await _api.getList(
        '/api/transfers/windows/$windowId/bids',
        auth: false,
      );
      _bids = payload.map(_TransferBidRecord.fromJson).toList(growable: false);
    } catch (error) {
      _bidsError = AppFeedback.messageFor(error);
    } finally {
      if (mounted) {
        setState(() => _isLoadingBids = false);
      }
    }
  }

  Future<void> _createBid() async {
    final String? windowId = _selectedWindowId;
    if (windowId == null) {
      return;
    }
    await showGteFormSheet(
      context,
      title: 'Create transfer bid',
      fields: const <GteFormFieldSpec>[
        GteFormFieldSpec(key: 'playerId', label: 'Player id'),
        GteFormFieldSpec(key: 'buyingClubId', label: 'Buying club id'),
        GteFormFieldSpec(key: 'sellingClubId', label: 'Selling club id'),
        GteFormFieldSpec(
          key: 'amount',
          label: 'Bid amount',
          keyboardType: TextInputType.number,
        ),
      ],
      onSubmit: (Map<String, String> values) async {
        final double? amount = double.tryParse(values['amount'] ?? '');
        if ((values['playerId'] ?? '').isEmpty ||
            (values['buyingClubId'] ?? '').isEmpty ||
            amount == null) {
          AppFeedback.showError(
              context, 'Enter player, buying club, and amount.');
          return false;
        }
        try {
          await _api.request(
            'POST',
            '/api/transfers/windows/$windowId/bids',
            body: <String, Object?>{
              'player_id': values['playerId'],
              'buying_club_id': values['buyingClubId'],
              'selling_club_id': values['sellingClubId'],
              'bid_amount': amount,
            },
          );
          await _loadBids(windowId);
          if (mounted) {
            AppFeedback.showSuccess(context, 'Transfer bid created.');
          }
          return true;
        } catch (error) {
          AppFeedback.showError(context, AppFeedback.messageFor(error));
          return false;
        }
      },
    );
  }

  Future<void> _acceptBid(_TransferBidRecord bid) async {
    final String? windowId = _selectedWindowId;
    if (windowId == null) {
      return;
    }
    try {
      await _api.request(
        'POST',
        '/api/transfers/windows/$windowId/bids/${bid.id}/accept',
        body: <String, Object?>{
          'contract_ends_on':
              DateTime.now().add(const Duration(days: 365)).toIso8601String(),
        },
      );
      await _loadBids(windowId);
      if (mounted) {
        AppFeedback.showSuccess(context, 'Transfer bid accepted.');
      }
    } catch (error) {
      AppFeedback.showError(context, AppFeedback.messageFor(error));
    }
  }

  Future<void> _rejectBid(_TransferBidRecord bid) async {
    final String? windowId = _selectedWindowId;
    if (windowId == null) {
      return;
    }
    try {
      await _api.request(
        'POST',
        '/api/transfers/windows/$windowId/bids/${bid.id}/reject',
        body: const <String, Object?>{'reason': 'frontend_review'},
      );
      await _loadBids(windowId);
      if (mounted) {
        AppFeedback.showSuccess(context, 'Transfer bid rejected.');
      }
    } catch (error) {
      AppFeedback.showError(context, AppFeedback.messageFor(error));
    }
  }

  Future<void> _createSeason() async {
    await showGteFormSheet(
      context,
      title: 'Create calendar season',
      fields: const <GteFormFieldSpec>[
        GteFormFieldSpec(key: 'key', label: 'Season key'),
        GteFormFieldSpec(key: 'title', label: 'Title'),
      ],
      onSubmit: (Map<String, String> values) async {
        if ((values['key'] ?? '').isEmpty || (values['title'] ?? '').isEmpty) {
          AppFeedback.showError(context, 'Enter season key and title.');
          return false;
        }
        await _controller.createSeason(
          CalendarSeasonCreateRequest(
            seasonKey: values['key']!,
            title: values['title']!,
            startsOn: DateTime.now(),
            endsOn: DateTime.now().add(const Duration(days: 90)),
          ),
        );
        if ((_controller.actionError ?? '').isNotEmpty) {
          AppFeedback.showError(context, _controller.actionError!);
          return false;
        }
        await _controller.loadCalendar();
        return true;
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Transfer center / calendar'),
          actions: <Widget>[
            IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
          ],
        ),
        body: AnimatedBuilder(
          animation: _controller,
          builder: (BuildContext context, Widget? child) {
            return RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
                children: <Widget>[
                  GteSurfacePanel(
                    accentColor: const Color(0xFF8ED8FF),
                    emphasized: true,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Transfer windows, bid actions, and the competition calendar are wired to the canonical lifecycle and calendar services.',
                          style: Theme.of(context).textTheme.bodyLarge,
                        ),
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: <Widget>[
                            GteMetricChip(
                              label: 'Tab',
                              value: widget.initialTab.toUpperCase(),
                            ),
                            GteMetricChip(
                              label: 'Windows',
                              value: _windows.length.toString(),
                            ),
                            GteMetricChip(
                              label: 'Calendar events',
                              value:
                                  _controller.calendarEvents.length.toString(),
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 12,
                          runSpacing: 12,
                          children: <Widget>[
                            if (_isAuthenticated)
                              FilledButton.tonalIcon(
                                onPressed: _selectedWindowId == null
                                    ? null
                                    : _createBid,
                                icon: const Icon(Icons.gavel_outlined),
                                label: const Text('Create bid'),
                              )
                            else if (widget.onOpenLogin != null)
                              FilledButton.icon(
                                onPressed: widget.onOpenLogin,
                                icon: const Icon(Icons.login),
                                label: const Text('Sign in for bids'),
                              ),
                            if (_isAdmin)
                              FilledButton.tonalIcon(
                                onPressed: _createSeason,
                                icon: const Icon(Icons.calendar_today_outlined),
                                label: const Text('Create season'),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  _TransferListCard(
                    title: 'Transfer windows',
                    loading: _isLoadingWindows,
                    error: _windowsError,
                    child: _windows.isEmpty
                        ? const Text('No transfer windows available.')
                        : Column(
                            children: _windows
                                .map(
                                  (_TransferWindowRecord item) => Padding(
                                    padding: const EdgeInsets.only(bottom: 10),
                                    child: GteSurfacePanel(
                                      accentColor: _selectedWindowId == item.id
                                          ? const Color(0xFF8ED8FF)
                                          : null,
                                      onTap: () => _loadBids(item.id),
                                      child: Text(
                                        '${item.label}\n${item.status} • ${item.territoryCode} • ${item.opensOn} to ${item.closesOn}',
                                        style: Theme.of(context)
                                            .textTheme
                                            .bodyMedium,
                                      ),
                                    ),
                                  ),
                                )
                                .toList(growable: false),
                          ),
                  ),
                  const SizedBox(height: 18),
                  _TransferListCard(
                    title: 'Transfer bids',
                    loading: _isLoadingBids,
                    error: _bidsError,
                    child: _bids.isEmpty
                        ? const Text('No bids loaded for the selected window.')
                        : Column(
                            children: _bids
                                .map(
                                  (_TransferBidRecord item) => Padding(
                                    padding: const EdgeInsets.only(bottom: 10),
                                    child: GteSurfacePanel(
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: <Widget>[
                                          Text(
                                            '${item.playerId} • ${item.status} • ${item.bidAmount}',
                                            style: Theme.of(context)
                                                .textTheme
                                                .bodyMedium,
                                          ),
                                          if (_isAuthenticated) ...<Widget>[
                                            const SizedBox(height: 10),
                                            Wrap(
                                              spacing: 10,
                                              runSpacing: 10,
                                              children: <Widget>[
                                                FilledButton.tonal(
                                                  onPressed: () =>
                                                      _acceptBid(item),
                                                  child: const Text('Accept'),
                                                ),
                                                FilledButton.tonal(
                                                  onPressed: () =>
                                                      _rejectBid(item),
                                                  child: const Text('Reject'),
                                                ),
                                              ],
                                            ),
                                          ],
                                        ],
                                      ),
                                    ),
                                  ),
                                )
                                .toList(growable: false),
                          ),
                  ),
                  const SizedBox(height: 18),
                  _TransferListCard(
                    title: 'Calendar events',
                    loading: _controller.isLoadingCalendar,
                    error: _controller.calendarError,
                    child: _controller.calendarEvents.isEmpty
                        ? const Text('No calendar events available.')
                        : Column(
                            children: _controller.calendarEvents
                                .take(6)
                                .map(
                                  (CalendarEventViewModel item) => Padding(
                                    padding: const EdgeInsets.only(bottom: 8),
                                    child: Text(
                                      '${item.title} • ${item.status} • ${item.family}',
                                      style: Theme.of(context)
                                          .textTheme
                                          .bodyMedium,
                                    ),
                                  ),
                                )
                                .toList(growable: false),
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
}

class _TransferListCard extends StatelessWidget {
  const _TransferListCard({
    required this.title,
    required this.loading,
    required this.error,
    required this.child,
  });

  final String title;
  final bool loading;
  final String? error;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          if (loading)
            const GteStatePanel(
              title: 'Loading',
              message: 'Transfer-center data is syncing.',
              icon: Icons.hourglass_bottom_outlined,
              isLoading: true,
            )
          else if (error != null)
            GteStatePanel(
              title: 'Unavailable',
              message: error!,
              icon: Icons.error_outline,
            )
          else
            child,
        ],
      ),
    );
  }
}

class _TransferWindowRecord {
  const _TransferWindowRecord({
    required this.id,
    required this.territoryCode,
    required this.label,
    required this.status,
    required this.opensOn,
    required this.closesOn,
  });

  final String id;
  final String territoryCode;
  final String label;
  final String status;
  final String opensOn;
  final String closesOn;

  factory _TransferWindowRecord.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'transfer window');
    return _TransferWindowRecord(
      id: stringValue(json['id']),
      territoryCode: stringValue(json['territory_code']),
      label: stringValue(json['label']),
      status: stringValue(json['status']),
      opensOn: stringValue(json['opens_on']),
      closesOn: stringValue(json['closes_on']),
    );
  }
}

class _TransferBidRecord {
  const _TransferBidRecord({
    required this.id,
    required this.playerId,
    required this.status,
    required this.bidAmount,
  });

  final String id;
  final String playerId;
  final String status;
  final String bidAmount;

  factory _TransferBidRecord.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'transfer bid');
    return _TransferBidRecord(
      id: stringValue(json['id']),
      playerId: stringValue(json['player_id']),
      status: stringValue(json['status']),
      bidAmount: stringValue(json['bid_amount']),
    );
  }
}
