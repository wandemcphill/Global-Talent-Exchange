import 'package:flutter/material.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/shared/data/gte_feature_support.dart';
import 'package:gte_frontend/features/shared/presentation/gte_feature_forms.dart';
import 'package:gte_frontend/features/transfer_center/live_transfer_center_provider.dart';
import 'package:gte_frontend/features/transfer_center/presentation/gtex_transfers_hub_panel.dart';
import 'package:gte_frontend/ui_gtex/components/gtex_status_chip.dart';
import 'package:gte_frontend/ui_gtex/components/gtex_status_presenter.dart';
import 'package:gte_frontend/ui_gtex/theme/gtex_colors.dart';
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
    this.activeClubId,
    this.initialTab = 'windows',
    this.onOpenLogin,
    this.onOpenPlayer,
    this.onOpenFinancialMarket,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final String? currentUserRole;
  final String? activeClubId;
  final String initialTab;
  final VoidCallback? onOpenLogin;
  final ValueChanged<String>? onOpenPlayer;
  final VoidCallback? onOpenFinancialMarket;

  @override
  State<TransferNewsCalendarScreen> createState() =>
      _TransferNewsCalendarScreenState();
}

class _TransferNewsCalendarScreenState
    extends State<TransferNewsCalendarScreen> {
  late TransferNewsCalendarController _controller;
  late GteAuthedApi _api;
  late TransferCenterApi _transferCenterApi;
  late GtexTransferHubSegment _selectedSegment;

  List<TransferCenterListingRecord> _listings =
      const <TransferCenterListingRecord>[];
  List<TransferHubOfferRecord> _offers = const <TransferHubOfferRecord>[];
  List<TransferNegotiationRecord> _negotiations =
      const <TransferNegotiationRecord>[];
  List<TransferShortlistEntryRecord> _shortlist =
      const <TransferShortlistEntryRecord>[];
  List<_TransferWindowRecord> _windows = const <_TransferWindowRecord>[];
  List<_TransferBidRecord> _bids = const <_TransferBidRecord>[];
  String? _selectedWindowId;
  String? _windowsError;
  String? _bidsError;
  bool _isLoadingWindows = false;
  bool _isLoadingBids = false;

  bool get _isAuthenticated =>
      widget.accessToken != null && widget.accessToken!.trim().isNotEmpty;
  bool get _isAdmin => <String>{
    'admin',
    'super_admin',
  }.contains((widget.currentUserRole ?? '').trim().toLowerCase());

  @override
  void initState() {
    super.initState();
    _selectedSegment = GtexTransferHubSegment.fromSlug(widget.initialTab);
    _hydrateClients();
    _load();
  }

  @override
  void didUpdateWidget(covariant TransferNewsCalendarScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.baseUrl != widget.baseUrl ||
        oldWidget.backendMode != widget.backendMode ||
        oldWidget.accessToken != widget.accessToken ||
        oldWidget.currentUserRole != widget.currentUserRole ||
        oldWidget.activeClubId != widget.activeClubId) {
      _controller.dispose();
      _hydrateClients();
      _load();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _hydrateClients() {
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
    _transferCenterApi = TransferCenterApi(client: _api);
  }

  Future<void> _load() async {
    await _controller.loadCalendar();
    if (_isAdmin) {
      await _controller.loadAdminEvents();
    }
    await Future.wait<void>(<Future<void>>[
      _loadWindows(),
      _loadTransferHubData(),
    ]);
  }

  Future<void> _loadTransferHubData() async {
    try {
      final List<TransferCenterListingRecord> listings =
          await _transferCenterApi.listListings(status: 'open');
      if (mounted) {
        setState(() {
          _listings = listings;
        });
      }
    } catch (_) {
      // Preserve last known listings when unconfigured in test/offline mode.
    }

    if (!_isAuthenticated) {
      return;
    }

    try {
      final List<TransferHubOfferRecord> offers = await _transferCenterApi
          .listOffers(clubId: widget.activeClubId);
      if (mounted) {
        setState(() {
          _offers = offers;
        });
      }
    } catch (_) {
      // Non-fatal in guest/limited test environments.
    }
  }

  Future<void> _loadWindows() async {
    setState(() {
      _isLoadingWindows = true;
      _windowsError = null;
    });
    try {
      final List<dynamic> payload = await _api.getList(
        '/api/transfers/windows',
        auth: false,
      );
      _windows = payload
          .map(_TransferWindowRecord.fromJson)
          .toList(growable: false);
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
    final ScaffoldMessengerState messenger = ScaffoldMessenger.of(context);
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
            context,
            'Enter player, buying club, and amount.',
          );
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
          messenger.showSnackBar(
            const SnackBar(content: Text('Transfer bid created.')),
          );
          return true;
        } catch (error) {
          messenger.showSnackBar(
            SnackBar(content: Text(AppFeedback.messageFor(error))),
          );
          return false;
        }
      },
    );
  }

  Future<void> _acceptBid(_TransferBidRecord bid) async {
    final String? windowId = _selectedWindowId;
    if (windowId == null || bid.isTerminal) {
      return;
    }
    final ScaffoldMessengerState messenger = ScaffoldMessenger.of(context);
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
      messenger.showSnackBar(
        const SnackBar(content: Text('Transfer bid accepted.')),
      );
    } catch (error) {
      messenger.showSnackBar(
        SnackBar(content: Text(AppFeedback.messageFor(error))),
      );
    }
  }

  Future<void> _rejectBid(_TransferBidRecord bid) async {
    final String? windowId = _selectedWindowId;
    if (windowId == null || bid.isTerminal) {
      return;
    }
    final ScaffoldMessengerState messenger = ScaffoldMessenger.of(context);
    try {
      await _api.request(
        'POST',
        '/api/transfers/windows/$windowId/bids/${bid.id}/reject',
        body: const <String, Object?>{'reason': 'frontend_review'},
      );
      await _loadBids(windowId);
      messenger.showSnackBar(
        const SnackBar(content: Text('Transfer bid rejected.')),
      );
    } catch (error) {
      messenger.showSnackBar(
        SnackBar(content: Text(AppFeedback.messageFor(error))),
      );
    }
  }

  Future<void> _acceptHubOffer(TransferHubOfferRecord offer) async {
    final ScaffoldMessengerState messenger = ScaffoldMessenger.of(context);
    try {
      await _transferCenterApi.acceptOffer(offer.id);
      await _loadTransferHubData();
      messenger.showSnackBar(
        const SnackBar(content: Text('Transfer offer accepted.')),
      );
    } catch (error) {
      messenger.showSnackBar(
        SnackBar(content: Text(AppFeedback.messageFor(error))),
      );
    }
  }

  Future<void> _rejectHubOffer(TransferHubOfferRecord offer) async {
    final ScaffoldMessengerState messenger = ScaffoldMessenger.of(context);
    try {
      await _transferCenterApi.rejectOffer(offer.id);
      await _loadTransferHubData();
      messenger.showSnackBar(
        const SnackBar(content: Text('Transfer offer rejected.')),
      );
    } catch (error) {
      messenger.showSnackBar(
        SnackBar(content: Text(AppFeedback.messageFor(error))),
      );
    }
  }

  Future<void> _cancelHubOffer(TransferHubOfferRecord offer) async {
    final ScaffoldMessengerState messenger = ScaffoldMessenger.of(context);
    try {
      await _transferCenterApi.cancelOffer(offer.id);
      await _loadTransferHubData();
      messenger.showSnackBar(
        const SnackBar(content: Text('Transfer offer cancelled.')),
      );
    } catch (error) {
      messenger.showSnackBar(
        SnackBar(content: Text(AppFeedback.messageFor(error))),
      );
    }
  }

  Future<void> _counterHubOffer(TransferHubOfferRecord offer) async {
    final ScaffoldMessengerState messenger = ScaffoldMessenger.of(context);
    await showGteFormSheet(
      context,
      title: 'Counter transfer offer #${offer.id}',
      fields: const <GteFormFieldSpec>[
        GteFormFieldSpec(
          key: 'amount',
          label: 'Counter cash amount',
          keyboardType: TextInputType.number,
        ),
        GteFormFieldSpec(key: 'message', label: 'Message'),
      ],
      onSubmit: (Map<String, String> values) async {
        final double? amount = double.tryParse(values['amount'] ?? '');
        if (amount == null || amount < 0) {
          AppFeedback.showError(context, 'Enter a valid counter amount.');
          return false;
        }
        try {
          await _transferCenterApi.counterOffer(
            offer.id,
            cashAmount: amount,
            message: values['message'],
          );
          await _loadTransferHubData();
          messenger.showSnackBar(
            const SnackBar(content: Text('Counter-offer sent.')),
          );
          return true;
        } catch (error) {
          messenger.showSnackBar(
            SnackBar(content: Text(AppFeedback.messageFor(error))),
          );
          return false;
        }
      },
    );
  }

  Future<void> _shortlistListing(TransferCenterListingRecord listing) async {
    final ScaffoldMessengerState messenger = ScaffoldMessenger.of(context);
    final String clubId = (widget.activeClubId ?? '').trim();
    if (clubId.isNotEmpty && _isAuthenticated) {
      try {
        await _transferCenterApi.addToWatchlist(
          clubId: clubId,
          playerId: listing.playerId,
          listingId: listing.id,
        );
      } catch (_) {
        // Fall through to local shortlist sync if offline.
      }
    }
    if (mounted) {
      setState(() {
        _shortlist = <TransferShortlistEntryRecord>[
          ..._shortlist.where(
            (TransferShortlistEntryRecord item) =>
                item.playerId != listing.playerId,
          ),
          TransferShortlistEntryRecord(
            id: 'shortlist-${listing.id}',
            clubId: clubId.isEmpty ? 'active-club' : clubId,
            playerId: listing.playerId,
            playerName: listing.playerName,
            source: 'transfer_center',
            discoveryScore: 84,
            listingId: listing.id,
            estimatedFeeCredits: listing.basePrice,
          ),
        ];
      });
      messenger.showSnackBar(
        SnackBar(content: Text('${listing.playerName} added to shortlist.')),
      );
    }
  }

  Future<void> _createSeason() async {
    final ScaffoldMessengerState messenger = ScaffoldMessenger.of(context);
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
          messenger.showSnackBar(
            SnackBar(content: Text(_controller.actionError!)),
          );
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
          title: const Text('Sporting Transfers / Calendar'),
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
                  GtexTransfersHubPanel(
                    selectedSegment: _selectedSegment,
                    onSelectSegment:
                        (GtexTransferHubSegment segment) =>
                            setState(() => _selectedSegment = segment),
                    activeClubId: widget.activeClubId,
                    listings: _listings,
                    offers: _offers,
                    negotiations: _negotiations,
                    shortlist: _shortlist,
                    onAcceptOffer: _acceptHubOffer,
                    onRejectOffer: _rejectHubOffer,
                    onCounterOffer: _counterHubOffer,
                    onCancelOffer: _cancelHubOffer,
                    onShortlistListing: _shortlistListing,
                    onOpenPlayer: widget.onOpenPlayer,
                    onOpenFinancialMarket: widget.onOpenFinancialMarket,
                  ),
                  const SizedBox(height: 18),
                  GteSurfacePanel(
                    accentColor: GtexNavyColors.info,
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
                              value: _selectedSegment.label.toUpperCase(),
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
                                onPressed:
                                    _selectedWindowId == null
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
                    child:
                        _windows.isEmpty
                            ? const Text('No transfer windows available.')
                            : Column(
                              children: _windows
                                  .map(
                                    (_TransferWindowRecord item) => Padding(
                                      padding: const EdgeInsets.only(
                                        bottom: 10,
                                      ),
                                      child: GteSurfacePanel(
                                        accentColor:
                                            _selectedWindowId == item.id
                                                ? GtexNavyColors.info
                                                : null,
                                        onTap: () => _loadBids(item.id),
                                        child: Row(
                                          children: <Widget>[
                                            Expanded(
                                              child: Text(
                                                '${item.label}\n${item.status} • ${item.territoryCode} • ${item.opensOn} to ${item.closesOn}',
                                                style:
                                                    Theme.of(
                                                      context,
                                                    ).textTheme.bodyMedium,
                                              ),
                                            ),
                                            GtexStatusChip.fromBackendStatus(
                                              item.status,
                                              context:
                                                  GtexStatusContext.transfer,
                                              compact: true,
                                            ),
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
                    title: 'Transfer bids',
                    loading: _isLoadingBids,
                    error: _bidsError,
                    child:
                        _bids.isEmpty
                            ? const Text(
                              'No bids loaded for the selected window.',
                            )
                            : Column(
                              children: _bids
                                  .map(
                                    (_TransferBidRecord item) => Padding(
                                      padding: const EdgeInsets.only(
                                        bottom: 10,
                                      ),
                                      child: GteSurfacePanel(
                                        child: Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: <Widget>[
                                            Row(
                                              children: <Widget>[
                                                Expanded(
                                                  child: Text(
                                                    '${item.playerId} • ${item.status} • ${item.bidAmount}',
                                                    style:
                                                        Theme.of(
                                                          context,
                                                        ).textTheme.bodyMedium,
                                                  ),
                                                ),
                                                GtexStatusChip.fromBackendStatus(
                                                  item.status,
                                                  context:
                                                      GtexStatusContext.offer,
                                                  compact: true,
                                                ),
                                              ],
                                            ),
                                            if (_isAuthenticated) ...<Widget>[
                                              const SizedBox(height: 10),
                                              Wrap(
                                                spacing: 10,
                                                runSpacing: 10,
                                                children: <Widget>[
                                                  FilledButton.tonal(
                                                    onPressed:
                                                        item.isTerminal
                                                            ? null
                                                            : () => _acceptBid(
                                                              item,
                                                            ),
                                                    child: const Text('Accept'),
                                                  ),
                                                  FilledButton.tonal(
                                                    onPressed:
                                                        item.isTerminal
                                                            ? null
                                                            : () => _rejectBid(
                                                              item,
                                                            ),
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
                    child:
                        _controller.calendarEvents.isEmpty
                            ? const Text('No calendar events available.')
                            : Column(
                              children: _controller.calendarEvents
                                  .take(6)
                                  .map(
                                    (CalendarEventViewModel item) => Padding(
                                      padding: const EdgeInsets.only(bottom: 8),
                                      child: Text(
                                        '${item.title} • ${item.status} • ${item.family}',
                                        style:
                                            Theme.of(
                                              context,
                                            ).textTheme.bodyMedium,
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

  bool get isTerminal =>
      GtexStatusPresenter.present(
        status,
        context: GtexStatusContext.offer,
      ).isTerminal;

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
