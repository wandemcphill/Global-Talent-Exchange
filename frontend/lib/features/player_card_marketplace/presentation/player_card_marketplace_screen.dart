import 'package:flutter/material.dart';

import '../../../core/app_feedback.dart';
import '../../../data/gte_api_repository.dart';
import '../../../services/avatar_mapper.dart';
import '../../../widgets/gte_formatters.dart';
import '../../../widgets/gte_metric_chip.dart';
import '../../../widgets/gte_shell_theme.dart';
import '../../../widgets/gte_state_panel.dart';
import '../../../widgets/gte_surface_panel.dart';
import '../../../widgets/gtex_branding.dart';
import '../../../widgets/football_player_card.dart';
import '../../../widgets/player_card_avatar.dart';
import '../data/player_card_marketplace_models.dart';
import 'player_card_marketplace_controller.dart';

class PlayerCardMarketplaceScreen extends StatefulWidget {
  const PlayerCardMarketplaceScreen({
    super.key,
    required this.baseUrl,
    required this.backendMode,
    this.controller,
    this.accessToken,
    this.currentUserId,
    this.onOpenLogin,
    this.onOpenPlayer,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final PlayerCardMarketplaceController? controller;
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
  late final bool _ownsController;
  late final TabController _tabController;
  late final TextEditingController _searchController;
  late final TextEditingController _negotiationIdController;

  bool get _hasAuth => widget.accessToken?.trim().isNotEmpty == true;

  @override
  void initState() {
    super.initState();
    _ownsController = widget.controller == null;
    _controller =
        widget.controller ??
        PlayerCardMarketplaceController.standard(
          baseUrl: widget.baseUrl,
          backendMode: widget.backendMode,
          accessToken: widget.accessToken,
        );
    _tabController = TabController(length: 5, vsync: this);
    _searchController = TextEditingController();
    _negotiationIdController = TextEditingController();
    _reload();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _searchController.dispose();
    _negotiationIdController.dispose();
    if (_ownsController) {
      _controller.dispose();
    }
    super.dispose();
  }

  @override
  void didUpdateWidget(covariant PlayerCardMarketplaceScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_ownsController &&
        (oldWidget.baseUrl != widget.baseUrl ||
            oldWidget.backendMode != widget.backendMode ||
            oldWidget.accessToken != widget.accessToken)) {
      _controller.dispose();
      _controller = PlayerCardMarketplaceController.standard(
        baseUrl: widget.baseUrl,
        backendMode: widget.backendMode,
        accessToken: widget.accessToken,
      );
      _reload();
      return;
    }
    if (oldWidget.currentUserId != widget.currentUserId ||
        oldWidget.accessToken != widget.accessToken) {
      _reload();
    }
  }

  Future<void> _reload() async {
    await Future.wait<void>(<Future<void>>[
      _controller.loadMarketplace(
        query: PlayerCardMarketplaceQuery(
          search: _searchController.text.trim(),
        ),
      ),
      _controller.loadSupport(
        playersQuery: PlayerCardPlayersQuery(
          search: _searchController.text.trim(),
        ),
        includeAuthed: _hasAuth,
      ),
    ]);
  }

  PlayerCardMarketplaceListing? _openSaleForPlayer(String playerId) {
    for (final PlayerCardMarketplaceListing listing
        in _controller.marketplaceSales.items) {
      if (listing.playerId == playerId &&
          listing.status.toLowerCase() == 'open') {
        return listing;
      }
    }
    return null;
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
              title: const Text('Transfer desk'),
              actions: <Widget>[
                IconButton(onPressed: _reload, icon: const Icon(Icons.refresh)),
              ],
            ),
            body: RefreshIndicator(
              onRefresh: _reload,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
                children: <Widget>[
                  GtexHeroBanner(
                    eyebrow: 'PLAYER UNIVERSE',
                    title: 'Trade live player cards and move squad capital.',
                    description:
                        'This desk keeps live sales, loans, squad inventory, and move execution in one football trading surface instead of scattering the action.',
                    accent: const Color(0xFF91C9FF),
                    chips: <Widget>[
                      GteMetricChip(
                        label: 'Sale board',
                        value: _controller.marketplaceSales.total.toString(),
                      ),
                      GteMetricChip(
                        label: 'Loan board',
                        value: _controller.marketplaceLoans.total.toString(),
                      ),
                      GteMetricChip(
                        label: 'Scouted',
                        value: _controller.players.length.toString(),
                      ),
                      GteMetricChip(
                        label: 'Squad',
                        value: _controller.inventory.length.toString(),
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
                        label: const Text('Refresh desk'),
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
                            labelText: 'Scout the board',
                            hintText: 'player, club, position, nationality',
                          ),
                          onSubmitted: (_) => _reload(),
                        ),
                        const SizedBox(height: 12),
                        FilledButton.tonalIcon(
                          onPressed: _reload,
                          icon: const Icon(Icons.search),
                          label: const Text('Scout'),
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
                        Tab(text: 'Transfer Market'),
                        Tab(text: 'Loan Market'),
                        Tab(text: 'Scout Players'),
                        Tab(text: 'Squad'),
                        Tab(text: 'My Listings'),
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
                        _buildPlayersTab(context),
                        _buildInventoryTab(context),
                        _buildMyListingsTab(context),
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
        title: 'Transfer desk unavailable',
        message: _controller.marketplaceError!,
        actionLabel: 'Retry',
        onAction: _reload,
        icon: Icons.storefront_outlined,
      );
    }
    if (_controller.isLoadingMarketplace && items.isEmpty) {
      return const GteStatePanel(
        title: 'Loading transfer desk',
        message: 'Players, prices, and availability are loading.',
        icon: Icons.storefront_outlined,
        isLoading: true,
      );
    }
    if (items.isEmpty) {
      return const GteStatePanel(
        title: 'No players listed right now',
        message: 'Try a new search or check back when the next listings drop.',
        icon: Icons.search_off_outlined,
      );
    }
    return Column(
      children: items
          .map((PlayerCardMarketplaceListing item) {
            final bool isOwner =
                widget.currentUserId == item.listingOwnerUserId;
            return Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _MarketplaceListingTile(
                listing: item,
                onPrimary:
                    isOwner
                        ? () => _controller.cancelSaleListing(item.listingId)
                        : !_hasAuth
                        ? widget.onOpenLogin
                        : () => _showBuySaleDialog(context, item),
                primaryLabel: isOwner ? 'Remove Listing' : 'Buy Now',
                onSecondary: () => widget.onOpenPlayer?.call(item.playerId),
                secondaryLabel: 'View Player',
              ),
            );
          })
          .toList(growable: false),
    );
  }

  Widget _buildLoansTab(BuildContext context) {
    final List<PlayerCardMarketplaceListing> items =
        _controller.marketplaceLoans.items;
    if (_controller.marketplaceError != null && items.isEmpty) {
      return GteStatePanel(
        title: 'Loan Market unavailable',
        message: _controller.marketplaceError!,
        actionLabel: 'Retry',
        onAction: _reload,
        icon: Icons.swap_horiz_outlined,
      );
    }
    if (_controller.isLoadingMarketplace && items.isEmpty) {
      return const GteStatePanel(
        title: 'Loading Loan Market',
        message: 'Loan listings and available slots are loading.',
        icon: Icons.swap_horiz_outlined,
        isLoading: true,
      );
    }
    if (items.isEmpty) {
      return const GteStatePanel(
        title: 'No loan listings right now',
        message: 'List a squad player for loan or scout the market again.',
        icon: Icons.search_off_outlined,
      );
    }
    return Column(
      children: items
          .map((PlayerCardMarketplaceListing item) {
            final bool isOwner =
                widget.currentUserId == item.listingOwnerUserId;
            return Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _MarketplaceListingTile(
                listing: item,
                onPrimary:
                    isOwner
                        ? () => _controller.cancelLoanListing(item.listingId)
                        : !_hasAuth
                        ? widget.onOpenLogin
                        : () => _showLoanNegotiationDialog(context, item),
                primaryLabel: isOwner ? 'Remove Listing' : 'Make Bid',
                onSecondary: () => widget.onOpenPlayer?.call(item.playerId),
                secondaryLabel: 'View Player',
              ),
            );
          })
          .toList(growable: false),
    );
  }

  Widget _buildPlayersTab(BuildContext context) {
    final List<PlayerCardPlayerSummary> players = _controller.players;
    if (_controller.supportError != null && players.isEmpty) {
      return GteStatePanel(
        title: 'Player scouting unavailable',
        message: _controller.supportError!,
        actionLabel: 'Retry',
        onAction: _reload,
        icon: Icons.manage_search_outlined,
      );
    }
    if (_controller.isLoadingSupport && players.isEmpty) {
      return const GteStatePanel(
        title: 'Scouting players',
        message: 'Real players and regens are loading.',
        icon: Icons.manage_search_outlined,
        isLoading: true,
      );
    }
    if (players.isEmpty) {
      return const GteStatePanel(
        title: 'No players found',
        message: 'Try another player, club, or position search.',
        icon: Icons.search_off_outlined,
      );
    }
    return Column(
      children: players
          .map((PlayerCardPlayerSummary player) {
            final PlayerCardMarketplaceListing? sale = _openSaleForPlayer(
              player.playerId,
            );
            return Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: FootballPlayerCard(
                playerName: player.playerName,
                avatar: player.avatar,
                imageUrl: player.imageUrl,
                tierLabel:
                    player.cardSupplyTotal > 0
                        ? '${player.cardSupplyTotal} cards'
                        : 'Tradable player',
                position: player.position,
                clubName: player.currentClubName,
                nationalityCode: player.nationalityCode,
                valueLabel:
                    player.latestValueCredits == null
                        ? null
                        : gteFormatCredits(player.latestValueCredits!),
                attributes: <String>[
                  if (player.cardSupplyTotal > 0) 'Cards issued',
                  if (player.currentClubName != null) 'Club profile',
                ],
                actions: <Widget>[
                  if (sale != null)
                    FilledButton(
                      onPressed:
                          !_hasAuth
                              ? widget.onOpenLogin
                              : () => _showBuySaleDialog(context, sale),
                      child: const Text('Buy Now'),
                    ),
                  FilledButton.tonal(
                    onPressed: () => widget.onOpenPlayer?.call(player.playerId),
                    child: const Text('View Player'),
                  ),
                ],
              ),
            );
          })
          .toList(growable: false),
    );
  }

  Widget _buildInventoryTab(BuildContext context) {
    if (!_hasAuth) {
      return GteStatePanel(
        title: 'Sign in required',
        message: 'Sign in to list players from your own squad.',
        actionLabel: widget.onOpenLogin == null ? null : 'Sign in',
        onAction: widget.onOpenLogin,
        icon: Icons.lock_outline,
      );
    }
    if (_controller.isLoadingSupport && _controller.inventory.isEmpty) {
      return const GteStatePanel(
        title: 'Loading squad',
        message: 'Your squad cards and available quantities are loading.',
        icon: Icons.inventory_2_outlined,
        isLoading: true,
      );
    }
    if (_controller.inventory.isEmpty) {
      return const GteStatePanel(
        title: 'No tradable players in your squad yet',
        message: 'Sign players or win cards to start listing them.',
        icon: Icons.inventory_2_outlined,
      );
    }
    return Column(
      children: _controller.inventory
          .map((PlayerCardHolding holding) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _HoldingTile(
                holding: holding,
                onSale: () => _showCreateSaleDialog(context, holding),
                onLoan: () => _showCreateLoanDialog(context, holding),
              ),
            );
          })
          .toList(growable: false),
    );
  }

  Widget _buildMyListingsTab(BuildContext context) {
    if (!_hasAuth) {
      return GteStatePanel(
        title: 'Sign in required',
        message: 'Sign in to manage your Transfer Market listings.',
        actionLabel: widget.onOpenLogin == null ? null : 'Sign in',
        onAction: widget.onOpenLogin,
        icon: Icons.lock_outline,
      );
    }
    if (_controller.myListings.isEmpty) {
      return const GteStatePanel(
        title: 'No listed players',
        message: 'Use List for Transfer from your squad to open a listing.',
        icon: Icons.assignment_outlined,
      );
    }
    return Column(
      children: _controller.myListings
          .map(
            (PlayerCardListing listing) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: FootballPlayerCard(
                playerName: listing.playerName,
                avatar: listing.avatar,
                imageUrl: listing.imageUrl,
                tierLabel: listing.tierName,
                position: listing.tierCode,
                valueLabel: gteFormatCredits(listing.pricePerCardCredits),
                attributes: <String>[
                  '${listing.quantity} listed',
                  listing.status.toUpperCase(),
                ],
                actions: <Widget>[
                  FilledButton.tonal(
                    onPressed:
                        () => _controller.cancelSaleListing(listing.listingId),
                    child: const Text('Remove Listing'),
                  ),
                ],
              ),
            ),
          )
          .toList(growable: false),
    );
  }

  // ignore: unused_element
  Widget _buildDeskTab(BuildContext context) {
    if (!_hasAuth) {
      return GteStatePanel(
        title: 'Sign in required',
        message: 'Sign in to view your listings and live loan deals.',
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
              Text(
                'My listings',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 12),
              if (_controller.myListings.isEmpty)
                const Text('No live listings yet.')
              else
                ..._controller.myListings.map(
                  (PlayerCardListing listing) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: PlayerCardAvatar(
                      avatar: AvatarMapper.fromListing(listing),
                      imageUrl: listing.imageUrl,
                      size: 42,
                    ),
                    title: Text(listing.playerName),
                    subtitle: Text(
                      '${listing.quantity} cards | ${gteFormatCredits(listing.pricePerCardCredits)}',
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
              Text(
                'Loan contracts',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 12),
              if (_controller.loanContracts.items.isEmpty)
                const Text('No live loan deals yet.')
              else
                ..._controller.loanContracts.items.map(
                  (PlayerCardMarketplaceLoanContract contract) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: PlayerCardAvatar(
                      avatar: AvatarMapper.fromMarketplaceLoanContract(
                        contract,
                      ),
                      imageUrl: contract.imageUrl,
                      size: 42,
                    ),
                    title: Text(contract.playerName),
                    subtitle: Text(
                      '${contract.contractStatus.toUpperCase()} | ${gteFormatCredits(contract.effectiveLoanFeeCredits)} | due ${gteFormatDateTime(contract.dueAt)}',
                    ),
                    trailing: Wrap(
                      spacing: 8,
                      children: <Widget>[
                        FilledButton.tonal(
                          onPressed:
                              () => _controller.settleLoanContract(
                                contract.loanContractId,
                              ),
                          child: const Text('Settle'),
                        ),
                        OutlinedButton(
                          onPressed:
                              () => _controller.returnLoanContract(
                                contract.loanContractId,
                              ),
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

  // ignore: unused_element
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
          label: const Text('Add to watchlist'),
        ),
        const SizedBox(height: 16),
        if (_controller.watchlist.isEmpty)
          const GteStatePanel(
            title: 'Watchlist is empty',
            message: 'Add a player or card id and track it here.',
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
                  subtitle: Text(item.notes ?? 'No notes yet'),
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
    final TextEditingController quantityController = TextEditingController(
      text: '1',
    );
    await _showSimpleSheet(
      context,
      title: 'List Player for Transfer',
      fields: <Widget>[
        TextField(
          controller: priceController,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(labelText: 'Buy Now price'),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: quantityController,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Quantity'),
        ),
      ],
      submitLabel: 'List for Transfer',
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
    final TextEditingController slotsController = TextEditingController(
      text: '1',
    );
    final TextEditingController durationController = TextEditingController(
      text: '7',
    );
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

  // ignore: unused_element
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
            requestedPlayerCardId:
                requestedCardController.text.trim().isEmpty
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
    final TextEditingController quantityController = TextEditingController(
      text: '1',
    );
    await _showSimpleSheet(
      context,
      title: 'Buy Now',
      fields: <Widget>[
        Text(
          '${listing.playerName} - ${gteFormatCredits(listing.salePriceCredits ?? 0)}',
        ),
        const SizedBox(height: 12),
        TextField(
          controller: quantityController,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Quantity'),
        ),
      ],
      submitLabel: 'Buy Now',
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
    final TextEditingController feeController = TextEditingController(
      text: listing.loanFeeCredits == null ? '' : '${listing.loanFeeCredits}',
    );
    final TextEditingController durationController = TextEditingController(
      text: '${listing.loanDurationDays ?? 7}',
    );
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
    final TextEditingController durationController = TextEditingController(
      text: '7',
    );
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
    if (_controller.actionError == null && context.mounted) {
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
            playerCardId:
                cardController.text.trim().isEmpty
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
                  if (success && context.mounted) {
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
    if (submitted == true && context.mounted) {
      AppFeedback.showSuccess(context, '$submitLabel complete.');
    }
  }
}

class _ExecutionSummaryPanel extends StatelessWidget {
  const _ExecutionSummaryPanel({required this.controller});

  final PlayerCardMarketplaceController controller;

  @override
  Widget build(BuildContext context) {
    final PlayerCardMarketplaceSaleExecution? sale =
        controller.latestSaleExecution;
    if (sale == null) {
      return const GteSurfacePanel(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: Icon(Icons.insights_outlined),
          title: Text('Latest transfer'),
          subtitle: Text('Completed Buy Now deals show up here.'),
        ),
      );
    }
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Latest transfer',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          Text(
            'Signed player for ${gteFormatCredits(sale.grossCredits)}. Seller received ${gteFormatCredits(sale.sellerNetCredits)} after fees.',
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
    final avatar = AvatarMapper.fromMarketplaceListing(listing);
    final String priceLabel =
        listing.salePriceCredits != null
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
              PlayerCardAvatar(avatar: avatar, imageUrl: listing.imageUrl),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      listing.playerName,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${listing.tierName} | ${listing.clubName ?? 'Unknown club'} | ${listing.position ?? 'n/a'}',
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
              if (listing.averageRating != null)
                GteMetricChip(
                  label: 'Rating',
                  value: listing.averageRating!.round().toString(),
                ),
              if (listing.position != null)
                GteMetricChip(label: 'Position', value: listing.position!),
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
  });

  final PlayerCardHolding holding;
  final VoidCallback onSale;
  final VoidCallback onLoan;

  @override
  Widget build(BuildContext context) {
    final avatar = AvatarMapper.fromHolding(holding);
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              PlayerCardAvatar(
                avatar: avatar,
                size: 52,
                imageUrl: holding.imageUrl,
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      holding.playerName,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      '${holding.tierName} | ${holding.quantityAvailable}/${holding.quantityTotal} available',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.tonal(
                onPressed: onSale,
                child: const Text('List for Transfer'),
              ),
              OutlinedButton(
                onPressed: onLoan,
                child: const Text('List for Loan'),
              ),
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
          Text(
            'Loan negotiation actions',
            style: Theme.of(context).textTheme.titleLarge,
          ),
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
                onPressed: onCounter,
                child: const Text('Counter'),
              ),
              FilledButton(onPressed: onAccept, child: const Text('Accept')),
            ],
          ),
        ],
      ),
    );
  }
}
