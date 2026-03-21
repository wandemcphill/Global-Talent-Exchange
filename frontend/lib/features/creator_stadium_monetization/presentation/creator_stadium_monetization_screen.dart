import 'package:flutter/material.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/shared/presentation/gte_feature_forms.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

import '../data/creator_stadium_monetization_models.dart';
import 'creator_stadium_monetization_controller.dart';

class CreatorStadiumMonetizationScreen extends StatefulWidget {
  const CreatorStadiumMonetizationScreen({
    super.key,
    required this.baseUrl,
    required this.backendMode,
    this.accessToken,
    this.currentClubId,
    this.currentUserRole,
    this.clubId,
    this.clubName,
    this.seasonId,
    this.matchId,
    this.adminOnly = false,
    this.onOpenLogin,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final String? currentClubId;
  final String? currentUserRole;
  final String? clubId;
  final String? clubName;
  final String? seasonId;
  final String? matchId;
  final bool adminOnly;
  final VoidCallback? onOpenLogin;

  @override
  State<CreatorStadiumMonetizationScreen> createState() =>
      _CreatorStadiumMonetizationScreenState();
}

class _CreatorStadiumMonetizationScreenState
    extends State<CreatorStadiumMonetizationScreen> {
  late final CreatorStadiumMonetizationController _controller;

  bool get _isAuthenticated =>
      widget.accessToken != null && widget.accessToken!.trim().isNotEmpty;

  bool get _isAdmin => <String>{'admin', 'super_admin'}
      .contains((widget.currentUserRole ?? '').trim().toLowerCase());

  bool get _hasClubScope => widget.clubId?.trim().isNotEmpty == true;
  bool get _hasSeasonScope => widget.seasonId?.trim().isNotEmpty == true;
  bool get _hasResolvedClubScope => _hasClubScope && _hasSeasonScope;
  bool get _hasMatchScope => widget.matchId?.trim().isNotEmpty == true;

  @override
  void initState() {
    super.initState();
    _controller = CreatorStadiumMonetizationController.standard(
      baseUrl: widget.baseUrl,
      backendMode: widget.backendMode,
      accessToken: widget.accessToken,
    );
    _load();
  }

  Future<void> _load() async {
    if (widget.adminOnly && !_isAdmin) {
      return;
    }
    if (!widget.adminOnly) {
      await _controller.loadModes();
    }
    if (_hasResolvedClubScope) {
      await _controller.loadClubStadium(
        widget.clubId!,
        widget.seasonId!,
      );
    }
    if (_hasMatchScope) {
      await _controller.loadMatch(
        widget.matchId!,
        analyticsClubId: widget.currentClubId,
        includeAdminAnalytics: _isAdmin,
      );
    }
    if (_isAdmin || widget.adminOnly) {
      await _controller.loadAdmin();
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
    if (widget.adminOnly && !_isAuthenticated) {
      return Container(
        decoration: gteBackdropDecoration(),
        child: Scaffold(
          backgroundColor: Colors.transparent,
          appBar: AppBar(title: const Text('Creator Stadium Control')),
          body: Padding(
            padding: const EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Sign in required',
              message:
                  'Creator stadium controls require an authenticated admin session.',
              actionLabel: widget.onOpenLogin == null ? null : 'Sign in',
              onAction: widget.onOpenLogin,
              icon: Icons.lock_outline,
            ),
          ),
        ),
      );
    }
    if (widget.adminOnly && !_isAdmin) {
      return Container(
        decoration: gteBackdropDecoration(),
        child: Scaffold(
          backgroundColor: Colors.transparent,
          appBar: AppBar(title: const Text('Creator Stadium Control')),
          body: const Padding(
            padding: EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Admin permission required',
              message:
                  'Creator stadium controls are only exposed to admin roles.',
              icon: Icons.admin_panel_settings_outlined,
            ),
          ),
        ),
      );
    }

    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: Text(widget.adminOnly
              ? 'Creator Stadium Control'
              : 'Creator Stadium'),
          actions: <Widget>[
            IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
          ],
        ),
        body: AnimatedBuilder(
          animation: _controller,
          builder: (BuildContext context, Widget? child) {
            final CreatorStadiumMonetization? clubStadium =
                _controller.clubStadium;
            final CreatorMatchAccess? matchAccess = _controller.matchAccess;
            final CreatorStadiumControl? control = _controller.adminControl;
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
                          widget.clubName ?? 'Creator Stadium',
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Run tickets, match access, placements, gifts, and stadium settings from one club-day view.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: <Widget>[
                            GteMetricChip(
                              label: 'Modes',
                              value:
                                  _controller.broadcastModes.length.toString(),
                            ),
                            GteMetricChip(
                              label: 'Passes',
                              value: _controller.seasonPasses.length.toString(),
                            ),
                            if (matchAccess != null)
                              GteMetricChip(
                                label: 'Access',
                                value: matchAccess.hasAccess
                                    ? 'Granted'
                                    : 'Locked',
                                positive: matchAccess.hasAccess,
                              ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 12,
                          runSpacing: 12,
                          children: <Widget>[
                            if (!_isAuthenticated)
                              FilledButton.icon(
                                onPressed: widget.onOpenLogin,
                                icon: const Icon(Icons.login),
                                label: const Text('Sign in'),
                              ),
                            if (_isAuthenticated && _hasResolvedClubScope)
                              FilledButton.tonalIcon(
                                onPressed: _updateClubConfig,
                                icon: const Icon(Icons.settings_outlined),
                                label: const Text('Edit setup'),
                              ),
                            if (_isAuthenticated && _hasMatchScope)
                              FilledButton.tonalIcon(
                                onPressed: _purchaseTicket,
                                icon: const Icon(
                                    Icons.confirmation_number_outlined),
                                label: const Text('Buy ticket'),
                              ),
                            if (_isAuthenticated && _hasMatchScope)
                              FilledButton.tonalIcon(
                                onPressed: _createPlacement,
                                icon: const Icon(Icons.view_carousel_outlined),
                                label: const Text('Add sponsor slot'),
                              ),
                            if (_isAuthenticated && _hasMatchScope)
                              FilledButton.tonalIcon(
                                onPressed: _sendGift,
                                icon: const Icon(Icons.card_giftcard_outlined),
                                label: const Text('Send gift'),
                              ),
                            if (_isAdmin || widget.adminOnly)
                              FilledButton.tonalIcon(
                                onPressed: _updateControl,
                                icon: const Icon(
                                    Icons.admin_panel_settings_outlined),
                                label: const Text('Control'),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  if (!widget.adminOnly && !_hasClubScope && !_hasMatchScope)
                    const GteStatePanel(
                      title: 'Pick a creator club or live match',
                      message:
                          'Open this from a creator club or match to load stadium data.',
                      icon: Icons.stadium_outlined,
                    ),
                  if (_hasClubScope && !_hasSeasonScope)
                    const GteStatePanel(
                      title: 'Creator season required',
                      message:
                          'Stadium data needs an active creator season for this club.',
                      icon: Icons.event_busy_outlined,
                    ),
                  if (_hasClubScope && !_hasSeasonScope)
                    const SizedBox(height: 18),
                  if (_hasResolvedClubScope)
                    GteSurfacePanel(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text('Stadium setup',
                              style: Theme.of(context).textTheme.titleLarge),
                          const SizedBox(height: 10),
                          if (_controller.isLoadingClubStadium &&
                              clubStadium == null)
                            const GteStatePanel(
                              title: 'Loading stadium setup',
                              message:
                                  'Ticket pricing and stadium profile are syncing.',
                              icon: Icons.stadium_outlined,
                              isLoading: true,
                            )
                          else if (_controller.clubError != null &&
                              clubStadium == null)
                            GteStatePanel(
                              title: 'Club stadium unavailable',
                              message: _controller.clubError!,
                              icon: Icons.error_outline,
                            )
                          else if (clubStadium != null)
                            Text(
                              'Season: ${clubStadium.seasonId}\nStadium level: ${clubStadium.stadium.level}\nCapacity: ${clubStadium.stadium.capacity}\nAd slots: ${clubStadium.control.maxInStadiumAdSlots}',
                              style: Theme.of(context).textTheme.bodyMedium,
                            ),
                        ],
                      ),
                    ),
                  if (_hasResolvedClubScope) const SizedBox(height: 18),
                  if (_hasMatchScope)
                    GteSurfacePanel(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text('Matchday access',
                              style: Theme.of(context).textTheme.titleLarge),
                          const SizedBox(height: 10),
                          if (_controller.isLoadingMatch && matchAccess == null)
                            const GteStatePanel(
                              title: 'Loading matchday access',
                              message:
                                  'Broadcast access, placements, and analytics are syncing.',
                              icon: Icons.live_tv_outlined,
                              isLoading: true,
                            )
                          else if (_controller.matchError != null &&
                              matchAccess == null)
                            GteStatePanel(
                              title: 'Matchday access unavailable',
                              message: _controller.matchError!,
                              icon: Icons.error_outline,
                            )
                          else if (matchAccess != null)
                            Text(
                              'Mode: ${matchAccess.modeName}\nDuration: ${matchAccess.durationMinutes} mins\nPrice: ${matchAccess.priceCoin}\nPlacements: ${_controller.placements.length}',
                              style: Theme.of(context).textTheme.bodyMedium,
                            ),
                        ],
                      ),
                    ),
                  if (_hasMatchScope) const SizedBox(height: 18),
                  if (_isAdmin || widget.adminOnly)
                    GteSurfacePanel(
                      accentColor: GteShellTheme.accentAdmin,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text('Admin control',
                              style: Theme.of(context).textTheme.titleLarge),
                          const SizedBox(height: 10),
                          if (_controller.isLoadingAdmin && control == null)
                            const GteStatePanel(
                              title: 'Loading control',
                              message: 'Ticket and placement caps are syncing.',
                              icon: Icons.admin_panel_settings_outlined,
                              isLoading: true,
                            )
                          else if (_controller.adminError != null &&
                              control == null)
                            GteStatePanel(
                              title: 'Control unavailable',
                              message: _controller.adminError!,
                              icon: Icons.error_outline,
                            )
                          else if (control != null)
                            Text(
                              'Max matchday ticket: ${control.maxMatchdayTicketPriceCoin}\nMax VIP ticket: ${control.maxVipTicketPriceCoin}\nMax placement: ${control.maxPlacementPriceCoin}\nAd placements enabled: ${control.adPlacementEnabled}',
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

  Future<void> _updateClubConfig() async {
    final String? clubId = widget.clubId;
    if (clubId == null) {
      return;
    }
    await showGteFormSheet(
      context,
      title: 'Update club stadium',
      fields: const <GteFormFieldSpec>[
        GteFormFieldSpec(key: 'matchday', label: 'Matchday ticket price'),
        GteFormFieldSpec(key: 'season', label: 'Season pass price'),
        GteFormFieldSpec(key: 'vip', label: 'VIP ticket price'),
      ],
      onSubmit: (Map<String, String> values) async {
        final double? matchday = double.tryParse(values['matchday'] ?? '');
        final double? season = double.tryParse(values['season'] ?? '');
        final double? vip = double.tryParse(values['vip'] ?? '');
        if (matchday == null || season == null || vip == null) {
          AppFeedback.showError(context, 'Enter valid pricing values.');
          return false;
        }
        await _run(
          () => _controller.updateClubStadium(
            clubId,
            CreatorStadiumConfigUpdateRequest(
              seasonId: widget.seasonId!,
              matchdayTicketPriceCoin: matchday,
              seasonPassPriceCoin: season,
              vipTicketPriceCoin: vip,
            ),
          ),
          'Club stadium updated.',
        );
        return _controller.actionError == null;
      },
    );
  }

  Future<void> _purchaseTicket() async {
    final String? matchId = widget.matchId;
    if (matchId == null) {
      return;
    }
    await _run(
      () => _controller.purchaseTicket(
        matchId,
        const CreatorStadiumTicketPurchaseRequest(ticketType: 'standard'),
      ),
      'Ticket purchase submitted.',
    );
  }

  Future<void> _createPlacement() async {
    final String? matchId = widget.matchId;
    if (matchId == null) {
      return;
    }
    await showGteFormSheet(
      context,
      title: 'Create placement',
      fields: const <GteFormFieldSpec>[
        GteFormFieldSpec(key: 'slot', label: 'Slot key'),
        GteFormFieldSpec(key: 'sponsor', label: 'Sponsor name'),
        GteFormFieldSpec(key: 'price', label: 'Price'),
      ],
      onSubmit: (Map<String, String> values) async {
        final double? price = double.tryParse(values['price'] ?? '');
        if ((values['slot'] ?? '').isEmpty ||
            (values['sponsor'] ?? '').isEmpty ||
            price == null) {
          AppFeedback.showError(context, 'Enter slot, sponsor, and price.');
          return false;
        }
        await _run(
          () => _controller.createPlacement(
            matchId,
            CreatorStadiumPlacementCreateRequest(
              placementType: 'banner',
              slotKey: values['slot']!,
              sponsorName: values['sponsor']!,
              priceCoin: price,
            ),
          ),
          'Placement created.',
        );
        return _controller.actionError == null;
      },
    );
  }

  Future<void> _sendGift() async {
    final String? matchId = widget.matchId;
    final String? clubId = widget.clubId ?? widget.currentClubId;
    if (matchId == null || clubId == null) {
      AppFeedback.showError(
        context,
        'Gifting needs a real match id and club id.',
      );
      return;
    }
    await _run(
      () => _controller.sendGift(
        matchId,
        CreatorMatchGiftRequest(
          clubId: clubId,
          amountCoin: 100,
          giftLabel: 'Matchday push',
        ),
      ),
      'Gift submitted.',
    );
  }

  Future<void> _updateControl() async {
    await showGteFormSheet(
      context,
      title: 'Update control',
      fields: const <GteFormFieldSpec>[
        GteFormFieldSpec(key: 'matchday', label: 'Max matchday ticket'),
        GteFormFieldSpec(key: 'vip', label: 'Max VIP ticket'),
        GteFormFieldSpec(key: 'placement', label: 'Max placement price'),
      ],
      onSubmit: (Map<String, String> values) async {
        final double? matchday = double.tryParse(values['matchday'] ?? '');
        final double? vip = double.tryParse(values['vip'] ?? '');
        final double? placement = double.tryParse(values['placement'] ?? '');
        if (matchday == null || vip == null || placement == null) {
          AppFeedback.showError(context, 'Enter valid control values.');
          return false;
        }
        await _run(
          () => _controller.updateStadiumControl(
            CreatorStadiumControlUpdateRequest(
              maxMatchdayTicketPriceCoin: matchday,
              maxSeasonPassPriceCoin: matchday,
              maxVipTicketPriceCoin: vip,
              maxStadiumLevel: 5,
              vipSeatRatioBps: 1000,
              maxInStadiumAdSlots: 8,
              maxSponsorBannerSlots: 8,
              adPlacementEnabled: true,
              ticketSalesEnabled: true,
              maxPlacementPriceCoin: placement,
            ),
          ),
          'Control updated.',
        );
        return _controller.actionError == null;
      },
    );
  }
}
