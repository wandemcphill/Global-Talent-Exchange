import 'package:flutter/material.dart';

import '../../../core/app_feedback.dart';
import '../../../data/gte_api_repository.dart';
import '../../../widgets/gte_formatters.dart';
import '../../../widgets/gte_metric_chip.dart';
import '../../../widgets/gte_shell_theme.dart';
import '../../../widgets/gte_state_panel.dart';
import '../../../widgets/gte_surface_panel.dart';
import '../../../widgets/gtex_branding.dart';
import '../data/club_sale_market_models.dart';
import 'club_sale_market_controller.dart';

class ClubSaleMarketScreen extends StatefulWidget {
  const ClubSaleMarketScreen({
    super.key,
    this.clubId,
    this.clubName,
    required this.baseUrl,
    required this.backendMode,
    this.accessToken,
    this.currentUserId,
    this.currentClubId,
    this.forceOwnerWorkspace = false,
    this.onOpenLogin,
    this.controller,
  });

  final String? clubId;
  final String? clubName;
  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final String? currentUserId;
  final String? currentClubId;
  final bool forceOwnerWorkspace;
  final VoidCallback? onOpenLogin;
  final ClubSaleMarketController? controller;

  @override
  State<ClubSaleMarketScreen> createState() => _ClubSaleMarketScreenState();
}

class _ClubSaleMarketScreenState extends State<ClubSaleMarketScreen> {
  late final ClubSaleMarketController _controller;
  late final TextEditingController _clubLookupController;
  late final bool _ownsController;

  bool get _hasAuth => widget.accessToken?.trim().isNotEmpty == true;

  @override
  void initState() {
    super.initState();
    _ownsController = widget.controller == null;
    _controller = widget.controller ??
        ClubSaleMarketController.standard(
          baseUrl: widget.baseUrl,
          backendMode: widget.backendMode,
          accessToken: widget.accessToken,
        );
    _clubLookupController = TextEditingController(text: widget.clubId ?? '');
    if (widget.clubId == null) {
      _controller.loadPublicListings();
    } else {
      _loadClub(
        widget.clubId!,
        forceOwnerWorkspace: widget.forceOwnerWorkspace,
      );
    }
  }

  @override
  void dispose() {
    _clubLookupController.dispose();
    if (_ownsController) {
      _controller.dispose();
    }
    super.dispose();
  }

  Future<void> _loadClub(
    String clubId, {
    bool forceOwnerWorkspace = false,
  }) async {
    await Future.wait<void>(<Future<void>>[
      _controller.loadPublicSnapshot(clubId),
      _controller.loadHistory(clubId),
      if (_hasAuth && (forceOwnerWorkspace || _looksLikeOwner(clubId)))
        _controller.loadOwnerWorkspace(clubId),
    ]);
  }

  bool _looksLikeOwner(String clubId) {
    if (widget.currentClubId == clubId) {
      return true;
    }
    final String? currentUserId = widget.currentUserId;
    if (currentUserId != null &&
        _controller.publicListing?.sellerUserId == currentUserId) {
      return true;
    }
    return _controller.myListings.items
        .any((ClubSaleListing item) => item.clubId == clubId);
  }

  bool _isCurrentClubScope(String clubId) => widget.currentClubId == clubId;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (BuildContext context, Widget? child) {
        final String? clubId = widget.clubId;
        return Container(
          decoration: gteBackdropDecoration(),
          child: Scaffold(
            backgroundColor: Colors.transparent,
            appBar: AppBar(
              title: Text(
                clubId == null
                    ? 'Club sale market'
                    : widget.forceOwnerWorkspace
                        ? '${widget.clubName ?? clubId} owner inbox'
                        : '${widget.clubName ?? clubId} sale market',
              ),
              actions: <Widget>[
                IconButton(
                  onPressed: clubId == null
                      ? _controller.loadPublicListings
                      : () => _loadClub(
                            clubId,
                            forceOwnerWorkspace: widget.forceOwnerWorkspace,
                          ),
                  icon: const Icon(Icons.refresh),
                ),
              ],
            ),
            body: clubId == null
                ? _buildBrowseView(context)
                : _buildClubView(context, clubId),
          ),
        );
      },
    );
  }

  Widget _buildBrowseView(BuildContext context) {
    final List<ClubSaleListing> listings = _controller.publicListings.items;
    return RefreshIndicator(
      onRefresh: _controller.loadPublicListings,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
        children: <Widget>[
          GtexHeroBanner(
            eyebrow: 'CLUB SALE MARKET',
            title:
                'Public valuations, asking prices, and live deal posture stay readable.',
            description:
                'Club sales do not invent a second ownership system in the client. This screen only shows the canonical backend valuation, listing posture, and sale history.',
            accent: const Color(0xFFF5C65B),
            chips: <Widget>[
              GteMetricChip(
                label: 'Listings',
                value: listings.length.toString(),
              ),
              GteMetricChip(
                label: 'Session',
                value: _hasAuth ? 'LIVE' : 'PREVIEW',
                positive: _hasAuth,
              ),
            ],
            actions: <Widget>[
              FilledButton.tonalIcon(
                onPressed: _controller.loadPublicListings,
                icon: const Icon(Icons.refresh),
                label: const Text('Refresh market'),
              ),
              if (widget.currentClubId?.isNotEmpty == true)
                FilledButton.icon(
                  onPressed: () => _openClub(context, widget.currentClubId!),
                  icon: const Icon(Icons.shield_outlined),
                  label: const Text('Open my club'),
                ),
            ],
            sidePanel: Column(
              children: <Widget>[
                TextField(
                  controller: _clubLookupController,
                  decoration: const InputDecoration(
                    labelText: 'Open club by id',
                    hintText: 'club-123',
                  ),
                ),
                const SizedBox(height: 12),
                FilledButton.tonalIcon(
                  onPressed: () => _openClub(
                    context,
                    _clubLookupController.text.trim(),
                  ),
                  icon: const Icon(Icons.open_in_new),
                  label: const Text('Open club market'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          if (_controller.listingsError != null && listings.isEmpty)
            GteStatePanel(
              title: 'Club sale market unavailable',
              message: _controller.listingsError!,
              actionLabel: 'Retry',
              onAction: _controller.loadPublicListings,
              icon: Icons.storefront_outlined,
            )
          else if (_controller.isLoadingPublicListings && listings.isEmpty)
            const GteStatePanel(
              title: 'Loading listings',
              message:
                  'Valuations, asking prices, and listing posture are being assembled.',
              icon: Icons.storefront_outlined,
              isLoading: true,
            )
          else if (listings.isEmpty)
            const GteStatePanel(
              title: 'No clubs are listed right now',
              message:
                  'The market stays explicit when there are no active sale listings. Try again later or open a club directly by id.',
              icon: Icons.search_off_outlined,
            )
          else
            ...listings.map(
              (ClubSaleListing listing) => Padding(
                padding: const EdgeInsets.only(bottom: 14),
                child: _ClubSaleListingTile(
                  listing: listing,
                  onOpen: () => _openClub(context, listing.clubId),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildClubView(BuildContext context, String clubId) {
    final ClubSaleValuation? valuation = _controller.valuation;
    final ClubSaleListing? listing = _controller.publicListing;
    final ClubSaleHistory? history = _controller.history;
    final ClubSaleTransferExecution? latestTransfer =
        _controller.latestTransfer;
    final bool ownerView = _hasAuth && _looksLikeOwner(clubId);
    final bool canManageListing = _hasAuth && _isCurrentClubScope(clubId);
    final bool historyVisibilityRestricted =
        _controller.isHistoryVisibilityRestricted;

    if (_controller.publicError != null &&
        valuation == null &&
        listing == null &&
        !_controller.isLoadingPublicSnapshot) {
      return Padding(
        padding: const EdgeInsets.all(20),
        child: GteStatePanel(
          title: 'Club sale market unavailable',
          message: _controller.publicError!,
          actionLabel: 'Retry',
          onAction: () => _loadClub(
            clubId,
            forceOwnerWorkspace: widget.forceOwnerWorkspace,
          ),
          icon: Icons.shield_outlined,
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => _loadClub(
        clubId,
        forceOwnerWorkspace: widget.forceOwnerWorkspace,
      ),
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
        children: <Widget>[
          GteSurfacePanel(
            emphasized: true,
            accentColor: const Color(0xFFF5C65B),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  widget.clubName ??
                      valuation?.clubName ??
                      listing?.clubName ??
                      clubId,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 8),
                Text(
                  'Public view shows canonical valuation and asking price. Transfer settlement stays backend-owned and is only displayed here after execution.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 14),
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: <Widget>[
                    GteMetricChip(
                      label: 'Valuation',
                      value: valuation == null
                          ? '--'
                          : _formatAmount(
                              valuation.systemValuation,
                              valuation.currency,
                            ),
                    ),
                    GteMetricChip(
                      label: 'Asking price',
                      value: listing == null
                          ? 'No listing'
                          : _formatAmount(
                              listing.askingPrice, listing.currency),
                    ),
                    if (listing != null)
                      GteMetricChip(
                        label: 'Status',
                        value: listing.status.toUpperCase(),
                        positive: listing.isActive,
                      ),
                    if (latestTransfer != null)
                      GteMetricChip(
                        label: 'Last sale',
                        value: _formatAmount(
                          latestTransfer.executedSalePrice,
                          latestTransfer.currency,
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: <Widget>[
                    FilledButton.icon(
                      onPressed: listing == null
                          ? null
                          : !_hasAuth
                              ? widget.onOpenLogin
                              : () => _showInquiryDialog(context, clubId),
                      icon: const Icon(Icons.question_answer_outlined),
                      label: const Text('Inquiry'),
                    ),
                    FilledButton.tonalIcon(
                      onPressed: listing == null
                          ? null
                          : !_hasAuth
                              ? widget.onOpenLogin
                              : () => _showOfferDialog(context, clubId),
                      icon: const Icon(Icons.local_offer_outlined),
                      label: const Text('Make offer'),
                    ),
                    if (canManageListing)
                      OutlinedButton.icon(
                        onPressed: () => _showListingEditor(
                          context,
                          clubId,
                          existing: listing,
                        ),
                        icon: Icon(
                          listing == null
                              ? Icons.add_circle_outline
                              : Icons.edit_outlined,
                        ),
                        label: Text(
                          listing == null ? 'Create listing' : 'Update listing',
                        ),
                      ),
                    if (canManageListing && listing != null)
                      OutlinedButton.icon(
                        onPressed: () =>
                            _showCancelListingDialog(context, clubId),
                        icon: const Icon(Icons.cancel_outlined),
                        label: const Text('Cancel listing'),
                      ),
                  ],
                ),
                if (!_hasAuth && widget.onOpenLogin != null) ...<Widget>[
                  const SizedBox(height: 12),
                  Text(
                    'Sign in to send inquiries, submit offers, and open owner inboxes.',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ],
            ),
          ),
          if (_controller.actionError != null) ...<Widget>[
            const SizedBox(height: 16),
            GteSurfacePanel(
              child: Text(
                _controller.actionError!,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ),
          ],
          if (widget.forceOwnerWorkspace && ownerView) ...<Widget>[
            const SizedBox(height: 18),
            _OwnerWorkspaceSection(
              isLoading: _controller.isLoadingOwnerWorkspace,
              error: _controller.ownerError,
              inquiries: _controller.clubInquiries.items,
              offers: _controller.clubOffers.items,
              myOffers: _controller.myOffers.items,
              onRetry: () => _controller.loadOwnerWorkspace(clubId),
              onRespondInquiry: (ClubSaleInquiry inquiry) =>
                  _showInquiryResponseDialog(context, clubId, inquiry),
              onCounterOffer: (ClubSaleOffer offer) =>
                  _showCounterOfferDialog(context, clubId, offer),
              onAcceptOffer: (ClubSaleOffer offer) => _showOfferResponseDialog(
                context,
                title: 'Accept offer',
                submitLabel: 'Accept',
                onSubmit: (String? message) async {
                  await _controller.acceptOffer(
                    clubId,
                    offer.offerId,
                    ClubSaleOfferRespondRequest(message: message),
                  );
                  if (!mounted || _controller.actionError != null) {
                    return;
                  }
                  AppFeedback.showSuccess(context, 'Offer accepted.');
                },
              ),
              onRejectOffer: (ClubSaleOffer offer) => _showOfferResponseDialog(
                context,
                title: 'Reject offer',
                submitLabel: 'Reject',
                onSubmit: (String? message) async {
                  await _controller.rejectOffer(
                    clubId,
                    offer.offerId,
                    ClubSaleOfferRespondRequest(message: message),
                  );
                  if (!mounted || _controller.actionError != null) {
                    return;
                  }
                  AppFeedback.showSuccess(context, 'Offer rejected.');
                },
              ),
              onExecuteTransfer: (ClubSaleOffer offer) =>
                  _showExecuteTransferDialog(context, clubId, offer),
            ),
          ],
          const SizedBox(height: 18),
          _SnapshotSection(
            valuation: valuation,
            listing: listing,
            isLoading: _controller.isLoadingPublicSnapshot,
          ),
          const SizedBox(height: 18),
          _TransferResultSection(
            latestTransfer: latestTransfer,
            visibilityRestricted: historyVisibilityRestricted,
          ),
          const SizedBox(height: 18),
          _HistorySection(
            history: history,
            isLoading: _controller.isLoadingHistory,
            error: _controller.historyError,
            visibilityRestricted: historyVisibilityRestricted,
            onRetry: () => _controller.loadHistory(clubId),
          ),
          if (widget.forceOwnerWorkspace && !ownerView) ...<Widget>[
            const SizedBox(height: 18),
            GteStatePanel(
              title: _hasAuth ? 'Owner access required' : 'Sign in required',
              message: _hasAuth
                  ? 'This route only exposes the owner offer inbox when the signed-in account matches the canonical club owner or sale-listing seller.'
                  : 'Sign in with the club owner account to access the offer inbox, counteroffers, accepts, and rejects.',
              actionLabel:
                  !_hasAuth && widget.onOpenLogin != null ? 'Sign in' : null,
              onAction: !_hasAuth ? widget.onOpenLogin : null,
              icon: _hasAuth
                  ? Icons.admin_panel_settings_outlined
                  : Icons.lock_outline,
              accentColor: GteShellTheme.accentArena,
            ),
          ],
          if (ownerView && !widget.forceOwnerWorkspace) ...<Widget>[
            const SizedBox(height: 18),
            _OwnerWorkspaceSection(
              isLoading: _controller.isLoadingOwnerWorkspace,
              error: _controller.ownerError,
              inquiries: _controller.clubInquiries.items,
              offers: _controller.clubOffers.items,
              myOffers: _controller.myOffers.items,
              onRetry: () => _controller.loadOwnerWorkspace(clubId),
              onRespondInquiry: (ClubSaleInquiry inquiry) =>
                  _showInquiryResponseDialog(context, clubId, inquiry),
              onCounterOffer: (ClubSaleOffer offer) =>
                  _showCounterOfferDialog(context, clubId, offer),
              onAcceptOffer: (ClubSaleOffer offer) => _showOfferResponseDialog(
                context,
                title: 'Accept offer',
                submitLabel: 'Accept',
                onSubmit: (String? message) async {
                  await _controller.acceptOffer(
                    clubId,
                    offer.offerId,
                    ClubSaleOfferRespondRequest(message: message),
                  );
                  if (!mounted || _controller.actionError != null) {
                    return;
                  }
                  AppFeedback.showSuccess(context, 'Offer accepted.');
                },
              ),
              onRejectOffer: (ClubSaleOffer offer) => _showOfferResponseDialog(
                context,
                title: 'Reject offer',
                submitLabel: 'Reject',
                onSubmit: (String? message) async {
                  await _controller.rejectOffer(
                    clubId,
                    offer.offerId,
                    ClubSaleOfferRespondRequest(message: message),
                  );
                  if (!mounted || _controller.actionError != null) {
                    return;
                  }
                  AppFeedback.showSuccess(context, 'Offer rejected.');
                },
              ),
              onExecuteTransfer: (ClubSaleOffer offer) =>
                  _showExecuteTransferDialog(context, clubId, offer),
            ),
          ],
        ],
      ),
    );
  }

  Future<void> _showListingEditor(
    BuildContext context,
    String clubId, {
    ClubSaleListing? existing,
  }) async {
    final TextEditingController priceController = TextEditingController(
      text: existing == null ? '' : existing.askingPrice.toStringAsFixed(2),
    );
    final TextEditingController noteController = TextEditingController(
      text: existing?.note ?? '',
    );
    String visibility =
        existing?.visibility.isEmpty == false ? existing!.visibility : 'public';
    final bool? submitted = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext context) {
        return Padding(
          padding: EdgeInsets.fromLTRB(
            20,
            20,
            20,
            20 + MediaQuery.of(context).viewInsets.bottom,
          ),
          child: StatefulBuilder(
            builder: (BuildContext context,
                void Function(void Function()) setModalState) {
              return Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    existing == null
                        ? 'Create club sale listing'
                        : 'Update club sale listing',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: priceController,
                    keyboardType:
                        const TextInputType.numberWithOptions(decimal: true),
                    decoration:
                        const InputDecoration(labelText: 'Asking price'),
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    value: visibility,
                    items: const <DropdownMenuItem<String>>[
                      DropdownMenuItem<String>(
                        value: 'public',
                        child: Text('Public'),
                      ),
                      DropdownMenuItem<String>(
                        value: 'private',
                        child: Text('Private'),
                      ),
                    ],
                    onChanged: (String? value) {
                      if (value == null) {
                        return;
                      }
                      setModalState(() => visibility = value);
                    },
                    decoration: const InputDecoration(labelText: 'Visibility'),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: noteController,
                    maxLines: 3,
                    decoration: const InputDecoration(labelText: 'Owner note'),
                  ),
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: () async {
                      final double? price =
                          double.tryParse(priceController.text.trim());
                      if (price == null || price <= 0) {
                        AppFeedback.showError(
                          context,
                          'Enter a valid asking price.',
                        );
                        return;
                      }
                      final ClubSaleListingUpsertRequest request =
                          ClubSaleListingUpsertRequest(
                        askingPrice: price,
                        visibility: visibility,
                        note: noteController.text.trim(),
                      );
                      if (existing == null) {
                        await _controller.createListing(clubId, request);
                      } else {
                        await _controller.updateListing(clubId, request);
                      }
                      if (!mounted || _controller.actionError != null) {
                        return;
                      }
                      Navigator.of(context).pop(true);
                    },
                    child: Text(
                      existing == null ? 'Create listing' : 'Save changes',
                    ),
                  ),
                ],
              );
            },
          ),
        );
      },
    );
    priceController.dispose();
    noteController.dispose();
    if (submitted == true && mounted) {
      AppFeedback.showSuccess(
        context,
        existing == null ? 'Listing created.' : 'Listing updated.',
      );
    }
  }

  Future<void> _showCancelListingDialog(
    BuildContext context,
    String clubId,
  ) async {
    final TextEditingController reasonController = TextEditingController();
    final bool? submitted = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext context) {
        return Padding(
          padding: EdgeInsets.fromLTRB(
            20,
            20,
            20,
            20 + MediaQuery.of(context).viewInsets.bottom,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Cancel listing',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: reasonController,
                maxLines: 3,
                decoration: const InputDecoration(labelText: 'Reason'),
              ),
              const SizedBox(height: 16),
              FilledButton.tonal(
                onPressed: () async {
                  await _controller.cancelListing(
                    clubId,
                    ClubSaleListingCancelRequest(
                      reason: reasonController.text.trim(),
                    ),
                  );
                  if (!mounted || _controller.actionError != null) {
                    return;
                  }
                  Navigator.of(context).pop(true);
                },
                child: const Text('Cancel listing'),
              ),
            ],
          ),
        );
      },
    );
    reasonController.dispose();
    if (submitted == true && mounted) {
      AppFeedback.showSuccess(context, 'Listing cancelled.');
    }
  }

  Future<void> _showInquiryDialog(BuildContext context, String clubId) async {
    final TextEditingController messageController = TextEditingController();
    final bool? submitted = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext context) {
        return Padding(
          padding: EdgeInsets.fromLTRB(
            20,
            20,
            20,
            20 + MediaQuery.of(context).viewInsets.bottom,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Send inquiry',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: messageController,
                maxLines: 4,
                decoration: const InputDecoration(
                  labelText: 'What would you like to ask?',
                ),
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: () async {
                  if (messageController.text.trim().isEmpty) {
                    AppFeedback.showError(context, 'Enter an inquiry message.');
                    return;
                  }
                  await _controller.submitInquiry(
                    clubId,
                    ClubSaleInquiryCreateRequest(
                      message: messageController.text.trim(),
                    ),
                  );
                  if (!mounted || _controller.actionError != null) {
                    return;
                  }
                  Navigator.of(context).pop(true);
                },
                child: const Text('Send inquiry'),
              ),
            ],
          ),
        );
      },
    );
    messageController.dispose();
    if (submitted == true && mounted) {
      AppFeedback.showSuccess(context, 'Inquiry sent.');
    }
  }

  Future<void> _showInquiryResponseDialog(
    BuildContext context,
    String clubId,
    ClubSaleInquiry inquiry,
  ) async {
    final TextEditingController responseController = TextEditingController();
    final bool? submitted = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext context) {
        return Padding(
          padding: EdgeInsets.fromLTRB(
            20,
            20,
            20,
            20 + MediaQuery.of(context).viewInsets.bottom,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Respond to inquiry',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 10),
              Text(
                inquiry.message,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: responseController,
                maxLines: 4,
                decoration: const InputDecoration(labelText: 'Response'),
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: () async {
                  if (responseController.text.trim().isEmpty) {
                    AppFeedback.showError(context, 'Enter a response message.');
                    return;
                  }
                  await _controller.respondInquiry(
                    clubId,
                    inquiry.inquiryId,
                    ClubSaleInquiryRespondRequest(
                      responseMessage: responseController.text.trim(),
                    ),
                  );
                  if (!mounted || _controller.actionError != null) {
                    return;
                  }
                  Navigator.of(context).pop(true);
                },
                child: const Text('Send response'),
              ),
            ],
          ),
        );
      },
    );
    responseController.dispose();
    if (submitted == true && mounted) {
      AppFeedback.showSuccess(context, 'Inquiry response sent.');
    }
  }

  Future<void> _showOfferDialog(
    BuildContext context,
    String clubId, {
    ClubSaleOffer? existingOffer,
    String? inquiryId,
  }) async {
    final TextEditingController priceController = TextEditingController(
      text: existingOffer == null
          ? ''
          : existingOffer.offerPrice.toStringAsFixed(2),
    );
    final TextEditingController noteController = TextEditingController(
      text: existingOffer?.message ?? '',
    );
    final TextEditingController expiryController =
        TextEditingController(text: '7');
    final bool? submitted = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext context) {
        return Padding(
          padding: EdgeInsets.fromLTRB(
            20,
            20,
            20,
            20 + MediaQuery.of(context).viewInsets.bottom,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                existingOffer == null ? 'Make an offer' : 'Counter offer',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: priceController,
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(labelText: 'Offer price'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: expiryController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Expires in days'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: noteController,
                maxLines: 3,
                decoration: const InputDecoration(labelText: 'Message'),
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: () async {
                  final double? price =
                      double.tryParse(priceController.text.trim());
                  final int? days = int.tryParse(expiryController.text.trim());
                  if (price == null || price <= 0) {
                    AppFeedback.showError(
                      context,
                      'Enter a valid offer price.',
                    );
                    return;
                  }
                  final DateTime? expiresAt = days == null || days <= 0
                      ? null
                      : DateTime.now().toUtc().add(Duration(days: days));
                  if (existingOffer == null) {
                    await _controller.submitOffer(
                      clubId,
                      ClubSaleOfferCreateRequest(
                        offerPrice: price,
                        inquiryId: inquiryId,
                        message: noteController.text.trim(),
                        expiresAt: expiresAt,
                      ),
                    );
                  } else {
                    await _controller.counterOffer(
                      clubId,
                      existingOffer.offerId,
                      ClubSaleOfferCounterRequest(
                        offerPrice: price,
                        message: noteController.text.trim(),
                        expiresAt: expiresAt,
                      ),
                    );
                  }
                  if (!mounted || _controller.actionError != null) {
                    return;
                  }
                  Navigator.of(context).pop(true);
                },
                child: Text(
                  existingOffer == null ? 'Submit offer' : 'Send counter',
                ),
              ),
            ],
          ),
        );
      },
    );
    priceController.dispose();
    noteController.dispose();
    expiryController.dispose();
    if (submitted == true && mounted) {
      AppFeedback.showSuccess(
        context,
        existingOffer == null ? 'Offer submitted.' : 'Counteroffer submitted.',
      );
    }
  }

  Future<void> _showCounterOfferDialog(
    BuildContext context,
    String clubId,
    ClubSaleOffer offer,
  ) async {
    await _showOfferDialog(
      context,
      clubId,
      existingOffer: offer,
    );
  }

  Future<void> _showOfferResponseDialog(
    BuildContext context, {
    required String title,
    required String submitLabel,
    required Future<void> Function(String? message) onSubmit,
  }) async {
    final TextEditingController messageController = TextEditingController();
    final bool? submitted = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext context) {
        return Padding(
          padding: EdgeInsets.fromLTRB(
            20,
            20,
            20,
            20 + MediaQuery.of(context).viewInsets.bottom,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(title, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 12),
              TextField(
                controller: messageController,
                maxLines: 3,
                decoration: const InputDecoration(labelText: 'Optional note'),
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: () async {
                  await onSubmit(messageController.text.trim());
                  if (!mounted || _controller.actionError != null) {
                    return;
                  }
                  Navigator.of(context).pop(true);
                },
                child: Text(submitLabel),
              ),
            ],
          ),
        );
      },
    );
    messageController.dispose();
    if (submitted == true && mounted) {
      AppFeedback.showSuccess(context, '$submitLabel complete.');
    }
  }

  Future<void> _showExecuteTransferDialog(
    BuildContext context,
    String clubId,
    ClubSaleOffer offer,
  ) async {
    final TextEditingController priceController = TextEditingController(
      text: offer.offerPrice.toStringAsFixed(2),
    );
    final bool? submitted = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext context) {
        return Padding(
          padding: EdgeInsets.fromLTRB(
            20,
            20,
            20,
            20 + MediaQuery.of(context).viewInsets.bottom,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Execute transfer',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 10),
              Text(
                'Enter the executed sale price returned to settlement. The platform fee and seller net are displayed from the backend transfer payload after execution.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: priceController,
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                decoration:
                    const InputDecoration(labelText: 'Executed sale price'),
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: () async {
                  final double? price =
                      double.tryParse(priceController.text.trim());
                  if (price == null || price <= 0) {
                    AppFeedback.showError(
                      context,
                      'Enter a valid executed sale price.',
                    );
                    return;
                  }
                  await _controller.executeTransfer(
                    clubId,
                    ClubSaleTransferExecuteRequest(
                      offerId: offer.offerId,
                      executedSalePrice: price,
                    ),
                  );
                  if (!mounted || _controller.actionError != null) {
                    return;
                  }
                  Navigator.of(context).pop(true);
                },
                child: const Text('Execute transfer'),
              ),
            ],
          ),
        );
      },
    );
    priceController.dispose();
    if (submitted == true && mounted) {
      AppFeedback.showSuccess(context, 'Transfer executed.');
    }
  }

  void _openClub(BuildContext context, String clubId) {
    if (clubId.trim().isEmpty) {
      AppFeedback.showError(context, 'Enter a club id.');
      return;
    }
    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => ClubSaleMarketScreen(
          clubId: clubId.trim(),
          clubName:
              widget.currentClubId == clubId.trim() ? widget.clubName : null,
          baseUrl: widget.baseUrl,
          backendMode: widget.backendMode,
          accessToken: widget.accessToken,
          currentUserId: widget.currentUserId,
          currentClubId: widget.currentClubId,
          onOpenLogin: widget.onOpenLogin,
        ),
      ),
    );
  }

  String _formatAmount(double amount, String currency) {
    return currency.toLowerCase() == 'credits' ||
            currency.toLowerCase() == 'credit'
        ? gteFormatCredits(amount)
        : gteFormatFiat(amount, currency: currency.toUpperCase());
  }
}

class _ClubSaleListingTile extends StatelessWidget {
  const _ClubSaleListingTile({
    required this.listing,
    required this.onOpen,
  });

  final ClubSaleListing listing;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final bool canOpen = listing.clubId.trim().isNotEmpty;
    final String? listingNote = listing.note?.trim();
    return GteSurfacePanel(
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
                      listing.clubName.trim().isNotEmpty
                          ? listing.clubName
                          : _displayClubName(listing.clubId),
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      listingNote?.isNotEmpty == true
                          ? listingNote!
                          : 'Active listing on the canonical club sale market.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              FilledButton.tonal(
                onPressed: canOpen ? onOpen : null,
                child: const Text('Open'),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              GteMetricChip(
                label: 'Valuation',
                value: gteFormatCredits(listing.systemValuation),
              ),
              GteMetricChip(
                label: 'Asking',
                value: gteFormatCredits(listing.askingPrice),
              ),
              GteMetricChip(
                label: 'Updated',
                value: gteFormatRelativeTime(listing.updatedAt),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _displayClubName(String clubId) {
    if (clubId.trim().isEmpty) {
      return 'Unnamed club';
    }
    return clubId.replaceAll(RegExp(r'[-_]+'), ' ').replaceAllMapped(
          RegExp(r'\b[a-z]'),
          (Match match) => match.group(0)!.toUpperCase(),
        );
  }
}

class _SnapshotSection extends StatelessWidget {
  const _SnapshotSection({
    required this.valuation,
    required this.listing,
    required this.isLoading,
  });

  final ClubSaleValuation? valuation;
  final ClubSaleListing? listing;
  final bool isLoading;

  @override
  Widget build(BuildContext context) {
    if (isLoading && valuation == null && listing == null) {
      return const GteStatePanel(
        title: 'Loading snapshot',
        message: 'Valuation, asking price, and listing note are syncing.',
        icon: Icons.timeline_outlined,
        isLoading: true,
      );
    }
    if (valuation == null && listing == null) {
      return const GteStatePanel(
        title: 'No public snapshot yet',
        message:
            'This club has no active public sale listing right now, but the history and owner workspace may still be available.',
        icon: Icons.info_outline,
      );
    }
    final ClubSaleValuationBreakdown? breakdown =
        listing?.valuationBreakdown ?? valuation?.breakdown;
    final String? listingNote = listing?.note?.trim();
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Public sale snapshot',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          if (listing != null)
            Text(
              listingNote?.isNotEmpty == true
                  ? listingNote!
                  : 'This listing is active on the canonical club sale market.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          if (listing != null) const SizedBox(height: 12),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              if (valuation != null)
                GteMetricChip(
                  label: 'System valuation',
                  value: gteFormatCredits(valuation!.systemValuation),
                ),
              if (listing != null)
                GteMetricChip(
                  label: 'Asking price',
                  value: gteFormatCredits(listing!.askingPrice),
                ),
              if (listing != null)
                GteMetricChip(
                  label: 'Visibility',
                  value: listing!.visibility.toUpperCase(),
                ),
            ],
          ),
          if (breakdown != null) ...<Widget>[
            const SizedBox(height: 16),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: <Widget>[
                GteMetricChip(
                  label: 'First team',
                  value: gteFormatCredits(breakdown.firstTeamValue),
                ),
                GteMetricChip(
                  label: 'Reserve',
                  value: gteFormatCredits(breakdown.reserveSquadValue),
                ),
                GteMetricChip(
                  label: 'U19',
                  value: gteFormatCredits(breakdown.u19SquadValue),
                ),
                GteMetricChip(
                  label: 'Academy',
                  value: gteFormatCredits(breakdown.academyValue),
                ),
                GteMetricChip(
                  label: 'Stadium',
                  value: gteFormatCredits(breakdown.stadiumValue),
                ),
                GteMetricChip(
                  label: 'Enhancements',
                  value: gteFormatCredits(breakdown.paidEnhancementsValue),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _TransferResultSection extends StatelessWidget {
  const _TransferResultSection({
    required this.latestTransfer,
    this.visibilityRestricted = false,
  });

  final ClubSaleTransferExecution? latestTransfer;
  final bool visibilityRestricted;

  @override
  Widget build(BuildContext context) {
    if (latestTransfer == null) {
      return GteSurfacePanel(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: Icon(
            visibilityRestricted
                ? Icons.visibility_off_outlined
                : Icons.swap_horiz_outlined,
          ),
          title: Text(
            visibilityRestricted
                ? 'Settlement visibility restricted'
                : 'No completed transfer yet',
          ),
          subtitle: Text(
            visibilityRestricted
                ? 'Executed sale price, platform fee, and seller net appear only when the backend exposes transfer history for this route.'
                : 'Executed sale price, platform fee, and seller net will appear here after settlement.',
          ),
        ),
      );
    }
    return GteSurfacePanel(
      accentColor: const Color(0xFF83D483),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Latest completed transfer',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              GteMetricChip(
                label: 'Sale price',
                value: gteFormatCredits(latestTransfer!.executedSalePrice),
                positive: true,
              ),
              GteMetricChip(
                label: 'Platform fee',
                value: gteFormatCredits(latestTransfer!.platformFeeAmount),
              ),
              GteMetricChip(
                label: 'Seller net',
                value: gteFormatCredits(latestTransfer!.sellerNetAmount),
                positive: true,
              ),
              GteMetricChip(
                label: 'Fee bps',
                value: latestTransfer!.platformFeeBps.toString(),
              ),
            ],
          ),
          if (latestTransfer!.ownershipTransition != null) ...<Widget>[
            const SizedBox(height: 12),
            Text(
              'Shareholders preserved: ${latestTransfer!.ownershipTransition!.shareholderRightsPreserved ? 'yes' : 'no'} | Count preserved: ${latestTransfer!.ownershipTransition!.shareholderCountPreserved}',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ],
      ),
    );
  }
}

class _HistorySection extends StatelessWidget {
  const _HistorySection({
    required this.history,
    required this.isLoading,
    required this.error,
    required this.visibilityRestricted,
    required this.onRetry,
  });

  final ClubSaleHistory? history;
  final bool isLoading;
  final String? error;
  final bool visibilityRestricted;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    if (isLoading && history == null) {
      return const GteStatePanel(
        title: 'Loading history',
        message:
            'Past transfers, ownership continuity, and audit trail are loading.',
        icon: Icons.history_outlined,
        isLoading: true,
      );
    }
    if (visibilityRestricted && history == null) {
      return const GteSurfacePanel(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: Icon(Icons.visibility_off_outlined),
          title: Text('History visibility restricted'),
          subtitle: Text(
            'Ownership continuity and transfer history appear only when the backend contract exposes them for this route.',
          ),
        ),
      );
    }
    if (error != null && history == null) {
      return GteStatePanel(
        title: 'History unavailable',
        message: error!,
        actionLabel: 'Retry',
        onAction: onRetry,
        icon: Icons.history_outlined,
      );
    }
    if (history == null) {
      return const SizedBox.shrink();
    }
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Ownership continuity',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              GteMetricChip(
                label: 'Transfers',
                value: history!.ownershipHistory.transferCount.toString(),
              ),
              GteMetricChip(
                label: 'Shareholders',
                value: history!.ownershipHistory.shareholderCount.toString(),
              ),
              GteMetricChip(
                label: 'Dynasty score',
                value: history!.dynastySnapshot.dynastyScore.toString(),
              ),
              GteMetricChip(
                label: 'Ownership eras',
                value: history!.ownershipHistory.ownershipEras.toString(),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (history!.ownershipHistory.recentTransfers.isEmpty)
            const Text('No completed transfers have been recorded yet.')
          else
            ...history!.ownershipHistory.recentTransfers.take(5).map(
                  (ClubSaleOwnershipHistoryEvent event) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.swap_horiz_outlined),
                    title: Text(gteFormatCredits(event.executedSalePrice)),
                    subtitle: Text(
                      'Seller ${event.sellerUserId} -> Buyer ${event.buyerUserId} | ${gteFormatDateTime(event.createdAt)}',
                    ),
                  ),
                ),
        ],
      ),
    );
  }
}

class _OwnerWorkspaceSection extends StatelessWidget {
  const _OwnerWorkspaceSection({
    required this.isLoading,
    required this.error,
    required this.inquiries,
    required this.offers,
    required this.myOffers,
    required this.onRetry,
    required this.onRespondInquiry,
    required this.onCounterOffer,
    required this.onAcceptOffer,
    required this.onRejectOffer,
    required this.onExecuteTransfer,
  });

  final bool isLoading;
  final String? error;
  final List<ClubSaleInquiry> inquiries;
  final List<ClubSaleOffer> offers;
  final List<ClubSaleOffer> myOffers;
  final VoidCallback onRetry;
  final ValueChanged<ClubSaleInquiry> onRespondInquiry;
  final ValueChanged<ClubSaleOffer> onCounterOffer;
  final ValueChanged<ClubSaleOffer> onAcceptOffer;
  final ValueChanged<ClubSaleOffer> onRejectOffer;
  final ValueChanged<ClubSaleOffer> onExecuteTransfer;

  @override
  Widget build(BuildContext context) {
    if (isLoading && inquiries.isEmpty && offers.isEmpty && myOffers.isEmpty) {
      return const GteStatePanel(
        title: 'Loading owner workspace',
        message: 'Offer inbox, inquiry inbox, and owner actions are loading.',
        icon: Icons.inbox_outlined,
        isLoading: true,
      );
    }
    return GteSurfacePanel(
      accentColor: const Color(0xFF9CC4FF),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  'Owner workspace',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              IconButton(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh),
              ),
            ],
          ),
          if (error != null) ...<Widget>[
            Text(error!, style: Theme.of(context).textTheme.bodyMedium),
            const SizedBox(height: 12),
          ],
          Text('Offer inbox', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          if (offers.isEmpty)
            const Text('No offers yet.')
          else
            ...offers.map(
              (ClubSaleOffer offer) => Card(
                margin: const EdgeInsets.only(bottom: 12),
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        '${gteFormatCredits(offer.offerPrice)} ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¾ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¾ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¾ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¦ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¾ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¦ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ ${offer.status.toUpperCase()}',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        offer.message?.trim().isNotEmpty == true
                            ? offer.message!
                            : 'No buyer message attached.',
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 10,
                        runSpacing: 10,
                        children: <Widget>[
                          FilledButton.tonal(
                            onPressed: () => onCounterOffer(offer),
                            child: const Text('Counter'),
                          ),
                          FilledButton(
                            onPressed: () => onAcceptOffer(offer),
                            child: const Text('Accept'),
                          ),
                          OutlinedButton(
                            onPressed: () => onRejectOffer(offer),
                            child: const Text('Reject'),
                          ),
                          if (offer.status.toLowerCase() == 'accepted')
                            OutlinedButton.icon(
                              onPressed: () => onExecuteTransfer(offer),
                              icon: const Icon(Icons.payments_outlined),
                              label: const Text('Execute transfer'),
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          const SizedBox(height: 16),
          Text('Inquiry inbox', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          if (inquiries.isEmpty)
            const Text('No inquiries yet.')
          else
            ...inquiries.map(
              (ClubSaleInquiry inquiry) => ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(inquiry.message),
                subtitle: Text('Status: ${inquiry.status.toUpperCase()}'),
                trailing: FilledButton.tonal(
                  onPressed: () => onRespondInquiry(inquiry),
                  child: const Text('Respond'),
                ),
              ),
            ),
          if (myOffers.isNotEmpty) ...<Widget>[
            const SizedBox(height: 16),
            Text(
              'My outbound offers',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            ...myOffers.take(3).map(
                  (ClubSaleOffer offer) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.south_east_outlined),
                    title: Text(gteFormatCredits(offer.offerPrice)),
                    subtitle: Text('Status: ${offer.status.toUpperCase()}'),
                  ),
                ),
          ],
        ],
      ),
    );
  }
}
