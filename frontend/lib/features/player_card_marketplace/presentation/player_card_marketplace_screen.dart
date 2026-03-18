import 'package:flutter/material.dart';

import '../../../core/app_feedback.dart';
import '../../../data/gte_api_repository.dart';
import '../../../widgets/gte_formatters.dart';
import '../../../widgets/gte_metric_chip.dart';
import '../../../widgets/gte_shell_theme.dart';
import '../../../widgets/gte_state_panel.dart';
import '../../../widgets/gte_surface_panel.dart';
import '../../../widgets/gtex_branding.dart';
import '../data/player_card_marketplace_models.dart';
import 'player_card_marketplace_controller.dart';

class PlayerCardMarketplaceScreen extends StatefulWidget {
  const PlayerCardMarketplaceScreen({
    super.key,
    required this.baseUrl,
    required this.backendMode,
    this.accessToken,
    this.currentUserId,
    this.onOpenLogin,
    this.onOpenPlayer,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final String? currentUserId;
  final VoidCallback? onOpenLogin;
  final ValueChanged<String>? onOpenPlayer;

  @override
  State<PlayerCardMarketplaceScreen> createState() =>
      _PlayerCardMarketplaceScreenState();
}

class _PlayerCardMarketplaceScreenState
    extends State<PlayerCardMarketplaceScreen>
    with SingleTickerProviderStateMixin {
  late final PlayerCardMarketplaceController _controller;
  late final TabController _tabController;
  late final TextEditingController _searchController;
  late final TextEditingController _negotiationIdController;

  bool get _hasAuth => widget.accessToken?.trim().isNotEmpty == true;

  @override
  void initState() {
    super.initState();
    _controller = PlayerCardMarketplaceController.standard(
      baseUrl: widget.baseUrl,
      backendMode: widget.backendMode,
      accessToken: widget.accessToken,
    );
    _tabController = TabController(length: 6, vsync: this);
    _searchController = TextEditingController();
    _negotiationIdController = TextEditingController();
    _reload();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _searchController.dispose();
    _negotiationIdController.dispose();
    _controller.dispose();
    super.dispose();
  }

  Future<void> _reload() async {
    await Future.wait<void>(<Future<void>>[
      _controller.loadMarketplace(
        query:
            PlayerCardMarketplaceQuery(search: _searchController.text.trim()),
      ),
      _controller.loadSupport(
        playersQuery:
            PlayerCardPlayersQuery(search: _searchController.text.trim()),
        includeAuthed: _hasAuth,
      ),
      if (_hasAuth) _controller.loadLoanContracts(),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (BuildContext context, Widget? child) {
        return Container(
          decoration: gteBackdropDecoration(),
          child: Scaffold(
            backgroundColor: Colors.transparent,
            appBar: AppBar(
              title: const Text('Player-card marketplace'),
              actions: <Widget>[
                IconButton(
                  onPressed: _reload,
                  icon: const Icon(Icons.refresh),
                ),
              ],
            ),
            body: RefreshIndicator(
              onRefresh: _reload,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
                children: <Widget>[
                  GtexHeroBanner(
                    eyebrow: 'PLAYER-CARD MARKETPLACE',
                    title:
                        'Sales, loans, swaps, inventory, contracts, and watchlists live on one trading surface.',
                    description:
                        'This screen is wired to the canonical card marketplace endpoints, so pricing, fees, loan terms, and swap execution all come straight from the backend.',
                    accent: const Color(0xFF91C9FF),
                    chips: <Widget>[
                      GteMetricChip(
                        label: 'Sales',
                        value: _controller.marketplaceSales.total.toString(),
                      ),
                      GteMetricChip(
                        label: 'Loans',
                        value: _controller.marketplaceLoans.total.toString(),
                      ),
                      GteMetricChip(
                        label: 'Swaps',
                        value: _controller.marketplaceSwaps.total.toString(),
                      ),
                      GteMetricChip(
                        label: 'Session',
                        value: _hasAuth ? 'LIVE' : 'PREVIEW',
                        positive: _hasAuth,
                      ),
                    ],
                    actions: <Widget>[
                      FilledButton.tonalIcon(
                        onPressed: _reload,
                        icon: const Icon(Icons.refresh),
                        label: const Text('Refresh market'),
                      ),
                      if (!_hasAuth && widget.onOpenLogin != null)
                        FilledButton.icon(
                          onPressed: widget.onOpenLogin,
                          icon: const Icon(Icons.login),
                          label: const Text('Sign in'),
                        ),
                    ],
                    sidePanel: Column(
                      children: <Widget>[
                        TextField(
                          controller: _searchController,
                          decoration: const InputDecoration(
                            labelText: 'Search player cards',
                            hintText: 'player, club, position',
                          ),
                          onSubmitted: (_) => _reload(),
                        ),
                        const SizedBox(height: 12),
                        FilledButton.tonalIcon(
                          onPressed: _reload,
                          icon: const Icon(Icons.search),
                          label: const Text('Apply search'),
                        ),
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
                  const SizedBox(height: 18),
                  _ExecutionSummaryPanel(controller: _controller),
                  const SizedBox(height: 18),
                  GteSurfacePanel(
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    child: TabBar(
                      controller: _tabController,
                      isScrollable: true,
                      tabs: const <Tab>[
                        Tab(text: 'Sales'),
                        Tab(text: 'Loans'),
                        Tab(text: 'Swaps'),
                        Tab(text: 'Inventory'),
                        Tab(text: 'My desk'),
                        Tab(text: 'Watchlist'),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    height: 900,
                    child: TabBarView(
                      controller: _tabController,
                      children: <Widget>[
                        _buildSalesTab(context),
                        _buildLoansTab(context),
                        _buildSwapsTab(context),
                        _buildInventoryTab(context),
                        _buildDeskTab(context),
                        _buildWatchlistTab(context),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildSalesTab(BuildContext context) {
    final List<PlayerCardMarketplaceListing> items =
        _controller.marketplaceSales.items;
    if (_controller.marketplaceError != null && items.isEmpty) {
      return GteStatePanel(
        title: 'Sales unavailable',
        message: _controller.marketplaceError!,
        actionLabel: 'Retry',
        onAction: _reload,
        icon: Icons.storefront_outlined,
      );
    }
    if (_controller.isLoadingMarketplace && items.isEmpty) {
      return const GteStatePanel(
        title: 'Loading sales',
        message: 'Sale listings, pricing, and card availability are loading.',
        icon: Icons.storefront_outlined,
        isLoading: true,
      );
    }
    if (items.isEmpty) {
      return const GteStatePanel(
        title: 'No sale listings found',
        message: 'This sale book is currently empty for the active search.',
        icon: Icons.search_off_outlined,
      );
    }
    return Column(
      children: items.map((PlayerCardMarketplaceListing item) {
        final bool isOwner = widget.currentUserId == item.listingOwnerUserId;
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: _MarketplaceListingTile(
            listing: item,
            onPrimary: isOwner
                ? () => _controller.cancelSaleListing(item.listingId)
                : !_hasAuth
                    ? widget.onOpenLogin
                    : () => _showBuySaleDialog(context, item),
            primaryLabel: isOwner ? 'Cancel sale' : 'Buy sale',
            onSecondary: () => widget.onOpenPlayer?.call(item.playerId),
            secondaryLabel: 'Player',
          ),
        );
      }).toList(growable: false),
    );
  }

  Widget _buildLoansTab(BuildContext context) {
    final List<PlayerCardMarketplaceListing> items =
        _controller.marketplaceLoans.items;
    if (_controller.isLoadingMarketplace && items.isEmpty) {
      return const GteStatePanel(
        title: 'Loading loans',
        message: 'Loan listings and flexible borrowing terms are loading.',
        icon: Icons.handshake_outlined,
        isLoading: true,
      );
    }
    if (items.isEmpty) {
      return const GteStatePanel(
        title: 'No loan listings found',
        message: 'The current loan book is empty for this search.',
        icon: Icons.search_off_outlined,
      );
    }
    return Column(
      children: items.map((PlayerCardMarketplaceListing item) {
        final bool isOwner = widget.currentUserId == item.listingOwnerUserId;
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: _MarketplaceListingTile(
            listing: item,
            onPrimary: isOwner
                ? () => _controller.cancelLoanListing(item.listingId)
                : !_hasAuth
                    ? widget.onOpenLogin
                    : () => _showLoanNegotiationDialog(context, item),
            primaryLabel: isOwner ? 'Cancel loan' : 'Negotiate',
            onSecondary: () => widget.onOpenPlayer?.call(item.playerId),
            secondaryLabel: 'Player',
          ),
        );
      }).toList(growable: false),
    );
  }

  Widget _buildSwapsTab(BuildContext context) {
    final List<PlayerCardMarketplaceListing> items =
        _controller.marketplaceSwaps.items;
    if (_controller.isLoadingMarketplace && items.isEmpty) {
      return const GteStatePanel(
        title: 'Loading swaps',
        message: 'Swap listings and requested card targets are loading.',
        icon: Icons.swap_horiz_outlined,
        isLoading: true,
      );
    }
    if (items.isEmpty) {
      return const GteStatePanel(
        title: 'No swap listings found',
        message: 'No swap opportunities match the active search.',
        icon: Icons.search_off_outlined,
      );
    }
    return Column(
      children: items.map((PlayerCardMarketplaceListing item) {
        final bool isOwner = widget.currentUserId == item.listingOwnerUserId;
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: _MarketplaceListingTile(
            listing: item,
            onPrimary: isOwner
                ? () => _controller.cancelSwapListing(item.listingId)
                : !_hasAuth
                    ? widget.onOpenLogin
                    : () => _showExecuteSwapDialog(context, item),
            primaryLabel: isOwner ? 'Cancel swap' : 'Execute swap',
            onSecondary: () => widget.onOpenPlayer?.call(item.playerId),
            secondaryLabel: 'Player',
          ),
        );
      }).toList(growable: false),
    );
  }

  Widget _buildInventoryTab(BuildContext context) {
    if (!_hasAuth) {
      return GteStatePanel(
        title: 'Sign in required',
        message:
            'Inventory actions are only available for authenticated owners.',
        actionLabel: widget.onOpenLogin == null ? null : 'Sign in',
        onAction: widget.onOpenLogin,
        icon: Icons.lock_outline,
      );
    }
    if (_controller.isLoadingSupport && _controller.inventory.isEmpty) {
      return const GteStatePanel(
        title: 'Loading inventory',
        message: 'Your card inventory and available quantities are loading.',
        icon: Icons.inventory_2_outlined,
        isLoading: true,
      );
    }
    if (_controller.inventory.isEmpty) {
      return const GteStatePanel(
        title: 'No card inventory yet',
        message: 'Acquire or buy player cards to start creating listings.',
        icon: Icons.inventory_2_outlined,
      );
    }
    return Column(
      children: _controller.inventory.map((PlayerCardHolding holding) {
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: _HoldingTile(
            holding: holding,
            onSale: () => _showCreateSaleDialog(context, holding),
            onLoan: () => _showCreateLoanDialog(context, holding),
            onSwap: () => _showCreateSwapDialog(context, holding),
          ),
        );
      }).toList(growable: false),
    );
  }

  Widget _buildDeskTab(BuildContext context) {
    if (!_hasAuth) {
      return GteStatePanel(
        title: 'Sign in required',
        message:
            'My listings and loan contracts need an authenticated session.',
        actionLabel: widget.onOpenLogin == null ? null : 'Sign in',
        onAction: widget.onOpenLogin,
        icon: Icons.lock_outline,
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        _NegotiationActionPanel(
          controller: _negotiationIdController,
          onCounter: () => _showCounterNegotiationDialog(context),
          onAccept: () => _acceptNegotiationById(context),
        ),
        const SizedBox(height: 16),
        GteSurfacePanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('My listings',
                  style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 12),
              if (_controller.myListings.isEmpty)
                const Text('No personal listings are open right now.')
              else
                ..._controller.myListings.map(
                  (PlayerCardListing listing) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(listing.playerName),
                    subtitle: Text(
                      '${listing.quantity} cards â€¢ ${gteFormatCredits(listing.pricePerCardCredits)}',
                    ),
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        GteSurfacePanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Loan contracts',
                  style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 12),
              if (_controller.loanContracts.items.isEmpty)
                const Text('No active marketplace loan contracts yet.')
              else
                ..._controller.loanContracts.items.map(
                  (PlayerCardMarketplaceLoanContract contract) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(contract.playerName),
                    subtitle: Text(
                      '${contract.contractStatus.toUpperCase()} â€¢ ${gteFormatCredits(contract.effectiveLoanFeeCredits)} â€¢ due ${gteFormatDateTime(contract.dueAt)}',
                    ),
                    trailing: Wrap(
                      spacing: 8,
                      children: <Widget>[
                        FilledButton.tonal(
                          onPressed: () => _controller
                              .settleLoanContract(contract.loanContractId),
                          child: const Text('Settle'),
                        ),
                        OutlinedButton(
                          onPressed: () => _controller
                              .returnLoanContract(contract.loanContractId),
                          child: const Text('Return'),
                        ),
                      ],
                    ),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildWatchlistTab(BuildContext context) {
    if (!_hasAuth) {
      return GteStatePanel(
        title: 'Sign in required',
        message: 'Watchlists are tied to your account.',
        actionLabel: widget.onOpenLogin == null ? null : 'Sign in',
        onAction: widget.onOpenLogin,
        icon: Icons.lock_outline,
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        FilledButton.tonalIcon(
          onPressed: () => _showAddWatchlistDialog(context),
          icon: const Icon(Icons.playlist_add_outlined),
          label: const Text('Add watchlist item'),
        ),
        const SizedBox(height: 16),
        if (_controller.watchlist.isEmpty)
          const GteStatePanel(
            title: 'Watchlist is empty',
            message: 'Add a player or card id to track it from one place.',
            icon: Icons.visibility_outlined,
          )
        else
          ..._controller.watchlist.map(
            (PlayerCardWatchlistItem item) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: GteSurfacePanel(
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(item.playerCardId ?? item.playerId),
                  subtitle: Text(item.notes ?? 'No notes'),
                  trailing: OutlinedButton(
                    onPressed: () => _controller.removeWatchlist(item.id),
                    child: const Text('Remove'),
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }

  Future<void> _showCreateSaleDialog(
    BuildContext context,
    PlayerCardHolding holding,
  ) async {
    final TextEditingController priceController = TextEditingController();
    final TextEditingController quantityController =
        TextEditingController(text: '1');
    await _showSimpleSheet(
      context,
      title: 'Create sale listing',
      fields: <Widget>[
        TextField(
          controller: priceController,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(labelText: 'Price per card'),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: quantityController,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Quantity'),
        ),
      ],
      submitLabel: 'Create sale',
      onSubmit: () async {
        final double? price = double.tryParse(priceController.text.trim());
        final int? quantity = int.tryParse(quantityController.text.trim());
        if (price == null || quantity == null || price <= 0 || quantity <= 0) {
          AppFeedback.showError(context, 'Enter a valid price and quantity.');
          return false;
        }
        await _controller.createSaleListing(
          PlayerCardMarketplaceSaleListingCreateRequest(
            playerCardId: holding.playerCardId,
            quantity: quantity,
            pricePerCardCredits: price,
          ),
        );
        return _controller.actionError == null;
      },
    );
    priceController.dispose();
    quantityController.dispose();
  }

  Future<void> _showCreateLoanDialog(
    BuildContext context,
    PlayerCardHolding holding,
  ) async {
    final TextEditingController feeController = TextEditingController();
    final TextEditingController slotsController =
        TextEditingController(text: '1');
    final TextEditingController durationController =
        TextEditingController(text: '7');
    await _showSimpleSheet(
      context,
      title: 'Create loan listing',
      fields: <Widget>[
        TextField(
          controller: feeController,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(labelText: 'Loan fee'),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: slotsController,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Total slots'),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: durationController,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Duration (days)'),
        ),
      ],
      submitLabel: 'Create loan',
      onSubmit: () async {
        final double? fee = double.tryParse(feeController.text.trim());
        final int? slots = int.tryParse(slotsController.text.trim());
        final int? duration = int.tryParse(durationController.text.trim());
        if (fee == null || slots == null || duration == null) {
          AppFeedback.showError(context, 'Enter valid loan terms.');
          return false;
        }
        await _controller.createLoanListing(
          PlayerCardMarketplaceLoanListingCreateRequest(
            playerCardId: holding.playerCardId,
            totalSlots: slots,
            durationDays: duration,
            loanFeeCredits: fee,
          ),
        );
        return _controller.actionError == null;
      },
    );
    feeController.dispose();
    slotsController.dispose();
    durationController.dispose();
  }

  Future<void> _showCreateSwapDialog(
    BuildContext context,
    PlayerCardHolding holding,
  ) async {
    final TextEditingController requestedCardController =
        TextEditingController();
    await _showSimpleSheet(
      context,
      title: 'Create swap listing',
      fields: <Widget>[
        TextField(
          controller: requestedCardController,
          decoration: const InputDecoration(
            labelText: 'Requested player card id',
          ),
        ),
      ],
      submitLabel: 'Create swap',
      onSubmit: () async {
        await _controller.createSwapListing(
          PlayerCardMarketplaceSwapListingCreateRequest(
            playerCardId: holding.playerCardId,
            requestedPlayerCardId: requestedCardController.text.trim().isEmpty
                ? null
                : requestedCardController.text.trim(),
          ),
        );
        return _controller.actionError == null;
      },
    );
    requestedCardController.dispose();
  }

  Future<void> _showBuySaleDialog(
    BuildContext context,
    PlayerCardMarketplaceListing listing,
  ) async {
    final TextEditingController quantityController =
        TextEditingController(text: '1');
    await _showSimpleSheet(
      context,
      title: 'Buy sale listing',
      fields: <Widget>[
        Text(
          '${listing.playerName} â€¢ ${gteFormatCredits(listing.salePriceCredits ?? 0)} per card',
        ),
        const SizedBox(height: 12),
        TextField(
          controller: quantityController,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Quantity'),
        ),
      ],
      submitLabel: 'Buy sale',
      onSubmit: () async {
        final int? quantity = int.tryParse(quantityController.text.trim());
        if (quantity == null || quantity <= 0) {
          AppFeedback.showError(context, 'Enter a valid quantity.');
          return false;
        }
        await _controller.buySaleListing(
          listing.listingId,
          PlayerCardMarketplaceSalePurchaseRequest(quantity: quantity),
        );
        return _controller.actionError == null;
      },
    );
    quantityController.dispose();
  }

  Future<void> _showLoanNegotiationDialog(
    BuildContext context,
    PlayerCardMarketplaceListing listing,
  ) async {
    final TextEditingController feeController = TextEditingController();
    final TextEditingController durationController =
        TextEditingController(text: '${listing.loanDurationDays ?? 7}');
    final TextEditingController noteController = TextEditingController();
    await _showSimpleSheet(
      context,
      title: 'Start loan negotiation',
      fields: <Widget>[
        TextField(
          controller: feeController,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(labelText: 'Proposed fee'),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: durationController,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Proposed duration'),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: noteController,
          maxLines: 3,
          decoration: const InputDecoration(labelText: 'Note'),
        ),
      ],
      submitLabel: 'Send negotiation',
      onSubmit: () async {
        final double? fee = double.tryParse(feeController.text.trim());
        final int? duration = int.tryParse(durationController.text.trim());
        if (fee == null || duration == null) {
          AppFeedback.showError(context, 'Enter valid negotiation terms.');
          return false;
        }
        await _controller.createLoanNegotiation(
          listing.listingId,
          PlayerCardMarketplaceLoanNegotiationCreateRequest(
            proposedFeeCredits: fee,
            proposedDurationDays: duration,
            note: noteController.text.trim(),
          ),
        );
        return _controller.actionError == null;
      },
    );
    feeController.dispose();
    durationController.dispose();
    noteController.dispose();
  }

  Future<void> _showCounterNegotiationDialog(BuildContext context) async {
    final String negotiationId = _negotiationIdController.text.trim();
    if (negotiationId.isEmpty) {
      AppFeedback.showError(context, 'Enter a negotiation id first.');
      return;
    }
    final TextEditingController feeController = TextEditingController();
    final TextEditingController durationController =
        TextEditingController(text: '7');
    final TextEditingController noteController = TextEditingController();
    await _showSimpleSheet(
      context,
      title: 'Counter negotiation',
      fields: <Widget>[
        TextField(
          controller: feeController,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(labelText: 'Counter fee'),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: durationController,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Counter duration'),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: noteController,
          maxLines: 3,
          decoration: const InputDecoration(labelText: 'Counter note'),
        ),
      ],
      submitLabel: 'Send counter',
      onSubmit: () async {
        final double? fee = double.tryParse(feeController.text.trim());
        final int? duration = int.tryParse(durationController.text.trim());
        if (fee == null || duration == null) {
          AppFeedback.showError(context, 'Enter valid counter terms.');
          return false;
        }
        await _controller.counterLoanNegotiation(
          negotiationId,
          PlayerCardMarketplaceLoanNegotiationCreateRequest(
            proposedFeeCredits: fee,
            proposedDurationDays: duration,
            note: noteController.text.trim(),
          ),
        );
        return _controller.actionError == null;
      },
    );
    feeController.dispose();
    durationController.dispose();
    noteController.dispose();
  }

  Future<void> _acceptNegotiationById(BuildContext context) async {
    final String negotiationId = _negotiationIdController.text.trim();
    if (negotiationId.isEmpty) {
      AppFeedback.showError(context, 'Enter a negotiation id first.');
      return;
    }
    await _controller.acceptLoanNegotiation(negotiationId);
    if (_controller.actionError == null && mounted) {
      AppFeedback.showSuccess(context, 'Negotiation accepted.');
    }
  }

  Future<void> _showExecuteSwapDialog(
    BuildContext context,
    PlayerCardMarketplaceListing listing,
  ) async {
    final TextEditingController counterpartyController =
        TextEditingController();
    await _showSimpleSheet(
      context,
      title: 'Execute swap',
      fields: <Widget>[
        TextField(
          controller: counterpartyController,
          decoration: const InputDecoration(
            labelText: 'Counterparty player card id',
          ),
        ),
      ],
      submitLabel: 'Execute swap',
      onSubmit: () async {
        if (counterpartyController.text.trim().isEmpty) {
          AppFeedback.showError(
            context,
            'Enter the counterparty player card id.',
          );
          return false;
        }
        await _controller.executeSwapListing(
          listing.listingId,
          PlayerCardMarketplaceSwapExecuteRequest(
            counterpartyPlayerCardId: counterpartyController.text.trim(),
          ),
        );
        return _controller.actionError == null;
      },
    );
    counterpartyController.dispose();
  }

  Future<void> _showAddWatchlistDialog(BuildContext context) async {
    final TextEditingController playerController = TextEditingController();
    final TextEditingController cardController = TextEditingController();
    final TextEditingController noteController = TextEditingController();
    await _showSimpleSheet(
      context,
      title: 'Add watchlist item',
      fields: <Widget>[
        TextField(
          controller: playerController,
          decoration: const InputDecoration(labelText: 'Player id'),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: cardController,
          decoration: const InputDecoration(
            labelText: 'Player card id (optional)',
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: noteController,
          maxLines: 3,
          decoration: const InputDecoration(labelText: 'Notes'),
        ),
      ],
      submitLabel: 'Add watchlist item',
      onSubmit: () async {
        if (playerController.text.trim().isEmpty) {
          AppFeedback.showError(context, 'Enter a player id.');
          return false;
        }
        await _controller.addWatchlist(
          PlayerCardWatchlistCreateRequest(
            playerId: playerController.text.trim(),
            playerCardId: cardController.text.trim().isEmpty
                ? null
                : cardController.text.trim(),
            notes: noteController.text.trim(),
          ),
        );
        return _controller.actionError == null;
      },
    );
    playerController.dispose();
    cardController.dispose();
    noteController.dispose();
  }

  Future<void> _showSimpleSheet(
    BuildContext context, {
    required String title,
    required List<Widget> fields,
    required String submitLabel,
    required Future<bool> Function() onSubmit,
  }) async {
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
              ...fields,
              const SizedBox(height: 16),
              FilledButton(
                onPressed: () async {
                  final bool success = await onSubmit();
                  if (success && mounted) {
                    Navigator.of(context).pop(true);
                  }
                },
                child: Text(submitLabel),
              ),
            ],
          ),
        );
      },
    );
    if (submitted == true && mounted) {
      AppFeedback.showSuccess(context, '$submitLabel complete.');
    }
  }
}

class _ExecutionSummaryPanel extends StatelessWidget {
  const _ExecutionSummaryPanel({
    required this.controller,
  });

  final PlayerCardMarketplaceController controller;

  @override
  Widget build(BuildContext context) {
    final PlayerCardMarketplaceSaleExecution? sale =
        controller.latestSaleExecution;
    final PlayerCardMarketplaceLoanContract? contract =
        controller.latestLoanContract;
    final PlayerCardMarketplaceSwapExecution? swap =
        controller.latestSwapExecution;
    if (sale == null && contract == null && swap == null) {
      return const GteSurfacePanel(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: Icon(Icons.insights_outlined),
          title: Text('Latest execution summary'),
          subtitle:
              Text('Completed sale, loan, and swap actions will appear here.'),
        ),
      );
    }
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Latest execution summary',
              style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          if (sale != null)
            Text(
              'Sale: ${gteFormatCredits(sale.grossCredits)} gross â€¢ fee ${gteFormatCredits(sale.feeCredits)} â€¢ seller net ${gteFormatCredits(sale.sellerNetCredits)}',
            ),
          if (contract != null)
            Text(
              'Loan: ${contract.contractStatus.toUpperCase()} â€¢ lender net ${gteFormatCredits(contract.lenderNetCredits)} â€¢ fee ${gteFormatCredits(contract.platformFeeCredits)}',
            ),
          if (swap != null)
            Text(
              'Swap: ${swap.status.toUpperCase()} â€¢ owner card ${swap.ownerPlayerCardId} for ${swap.counterpartyPlayerCardId}',
            ),
        ],
      ),
    );
  }
}

class _MarketplaceListingTile extends StatelessWidget {
  const _MarketplaceListingTile({
    required this.listing,
    required this.onPrimary,
    required this.primaryLabel,
    required this.onSecondary,
    required this.secondaryLabel,
  });

  final PlayerCardMarketplaceListing listing;
  final VoidCallback? onPrimary;
  final String primaryLabel;
  final VoidCallback? onSecondary;
  final String secondaryLabel;

  @override
  Widget build(BuildContext context) {
    final String priceLabel = listing.salePriceCredits != null
        ? gteFormatCredits(listing.salePriceCredits!)
        : listing.loanFeeCredits != null
            ? gteFormatCredits(listing.loanFeeCredits!)
            : 'Negotiated';
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
                    Text(listing.playerName,
                        style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 4),
                    Text(
                      '${listing.tierName} â€¢ ${listing.clubName ?? 'Unknown club'} â€¢ ${listing.position ?? 'n/a'}',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              GteMetricChip(
                label: listing.listingType.toUpperCase(),
                value: listing.status.toUpperCase(),
                positive: listing.status.toLowerCase() == 'open',
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              GteMetricChip(label: 'Price', value: priceLabel),
              if (listing.availableQuantity != null)
                GteMetricChip(
                  label: 'Available',
                  value: listing.availableQuantity.toString(),
                ),
              if (listing.loanDurationDays != null)
                GteMetricChip(
                  label: 'Duration',
                  value: '${listing.loanDurationDays}d',
                ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.tonal(
                onPressed: onPrimary,
                child: Text(primaryLabel),
              ),
              OutlinedButton(
                onPressed: onSecondary,
                child: Text(secondaryLabel),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _HoldingTile extends StatelessWidget {
  const _HoldingTile({
    required this.holding,
    required this.onSale,
    required this.onLoan,
    required this.onSwap,
  });

  final PlayerCardHolding holding;
  final VoidCallback onSale;
  final VoidCallback onLoan;
  final VoidCallback onSwap;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(holding.playerName,
              style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 6),
          Text(
            '${holding.tierName} â€¢ ${holding.quantityAvailable}/${holding.quantityTotal} available',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.tonal(
                  onPressed: onSale, child: const Text('Create sale')),
              FilledButton.tonal(
                  onPressed: onLoan, child: const Text('Create loan')),
              OutlinedButton(
                  onPressed: onSwap, child: const Text('Create swap')),
            ],
          ),
        ],
      ),
    );
  }
}

class _NegotiationActionPanel extends StatelessWidget {
  const _NegotiationActionPanel({
    required this.controller,
    required this.onCounter,
    required this.onAccept,
  });

  final TextEditingController controller;
  final VoidCallback onCounter;
  final VoidCallback onAccept;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Loan negotiation actions',
              style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(
            'The backend exposes direct negotiation action endpoints but no negotiation feed yet, so this adapter lets you continue a known negotiation by id.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 12),
          TextField(
            controller: controller,
            decoration: const InputDecoration(labelText: 'Negotiation id'),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.tonal(
                  onPressed: onCounter, child: const Text('Counter')),
              FilledButton(onPressed: onAccept, child: const Text('Accept')),
            ],
          ),
        ],
      ),
    );
  }
}

