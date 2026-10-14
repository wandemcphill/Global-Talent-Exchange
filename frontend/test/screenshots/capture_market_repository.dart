import 'package:gte_frontend/features/player_card_marketplace/data/player_card_marketplace_models.dart';
import 'package:gte_frontend/features/player_card_marketplace/data/player_card_marketplace_repository.dart';

class CaptureMarketplaceRepository
    implements PlayerCardMarketplaceRepository {
  CaptureMarketplaceRepository({
    PlayerCardMarketplaceSearchResult? marketSales,
    PlayerCardMarketplaceSearchResult? marketLoans,
    List<PlayerCardPlayerSummary>? players,
    List<PlayerCardHolding>? inventory,
    List<PlayerCardListing>? listings,
    List<PlayerCardListing>? myListings,
    List<PlayerCardWatchlistItem>? watchlist,
    this.inventoryError,
  }) : _marketSales =
           marketSales ?? const PlayerCardMarketplaceSearchResult.empty(),
       _marketLoans =
           marketLoans ?? const PlayerCardMarketplaceSearchResult.empty(),
       _players = players ?? const <PlayerCardPlayerSummary>[],
       _inventory = inventory ?? const <PlayerCardHolding>[],
       _listings = listings ?? const <PlayerCardListing>[],
       _myListings = myListings ?? const <PlayerCardListing>[],
       _watchlist = watchlist ?? const <PlayerCardWatchlistItem>[];

  final PlayerCardMarketplaceSearchResult _marketSales;
  final PlayerCardMarketplaceSearchResult _marketLoans;
  final List<PlayerCardPlayerSummary> _players;
  final List<PlayerCardHolding> _inventory;
  final List<PlayerCardListing> _listings;
  final List<PlayerCardListing> _myListings;
  final List<PlayerCardWatchlistItem> _watchlist;
  final Object? inventoryError;

  @override
  Future<PlayerCardWatchlistItem> addWatchlist(
    PlayerCardWatchlistCreateRequest request,
  ) async {
    return PlayerCardWatchlistItem.fromJson(<String, Object?>{
      'id': 'watch-1',
      'player_id': request.playerId,
      'player_card_id': request.playerCardId,
      'notes': request.notes,
    });
  }

  @override
  Future<PlayerCardMarketplaceLoanContract> acceptLoanNegotiation(
    String negotiationId,
  ) async {
    throw UnimplementedError();
  }

  @override
  Future<PlayerCardMarketplaceSaleExecution> buySaleListing(
    String listingId,
    PlayerCardMarketplaceSalePurchaseRequest request,
  ) async {
    return PlayerCardMarketplaceSaleExecution.fromJson(<String, Object?>{
      'sale_id': 'sale-1',
      'listing_id': listingId,
      'player_card_id': 'card-1',
      'seller_user_id': 'seller-1',
      'buyer_user_id': 'user-1',
      'quantity': request.quantity,
      'price_per_card_credits': 84,
      'gross_credits': 84 * request.quantity,
      'fee_credits': 4,
      'seller_net_credits': 80 * request.quantity,
      'status': 'completed',
    });
  }

  @override
  Future<PlayerCardMarketplaceListing> cancelSaleListing(
    String listingId,
  ) async {
    return PlayerCardMarketplaceListing.fromJson(<String, Object?>{
      'listing_id': listingId,
      'listing_type': 'sale',
      'player_card_id': 'card-3',
      'player_id': 'player-3',
      'player_name': 'William Saliba',
      'listing_owner_user_id': 'user-1',
      'status': 'cancelled',
      'availability': 'available',
      'is_negotiable': false,
      'asset_origin': 'real_player',
      'is_regen_newgen': false,
      'is_creator_linked': false,
      'available_quantity': 1,
      'sale_price_credits': 96,
      'tier_code': 'CB',
      'tier_name': 'First Team',
      'rarity_rank': 4,
      'edition_code': 'launch',
      'club_name': 'Arsenal',
      'position': 'CB',
    });
  }

  @override
  Future<PlayerCardMarketplaceLoanListing> cancelLoanListing(
    String listingId,
  ) async {
    throw UnimplementedError();
  }

  @override
  Future<PlayerCardMarketplaceSwapListing> cancelSwapListing(
    String listingId,
  ) async {
    throw UnimplementedError();
  }

  @override
  Future<PlayerCardMarketplaceLoanNegotiation> counterLoanNegotiation(
    String negotiationId,
    PlayerCardMarketplaceLoanNegotiationCreateRequest request,
  ) async {
    throw UnimplementedError();
  }

  @override
  Future<PlayerCardMarketplaceLoanListing> createLoanListing(
    PlayerCardMarketplaceLoanListingCreateRequest request,
  ) async {
    throw UnimplementedError();
  }

  @override
  Future<PlayerCardMarketplaceLoanNegotiation> createLoanNegotiation(
    String listingId,
    PlayerCardMarketplaceLoanNegotiationCreateRequest request,
  ) async {
    throw UnimplementedError();
  }

  @override
  Future<PlayerCardMarketplaceListing> createSaleListing(
    PlayerCardMarketplaceSaleListingCreateRequest request,
  ) async {
    return PlayerCardMarketplaceListing.fromJson(<String, Object?>{
      'listing_id': 'created-sale-1',
      'listing_type': 'sale',
      'player_card_id': request.playerCardId,
      'player_id': 'player-2',
      'player_name': 'Bukayo Saka',
      'listing_owner_user_id': 'user-1',
      'status': 'open',
      'availability': 'available',
      'is_negotiable': request.isNegotiable,
      'asset_origin': 'real_player',
      'is_regen_newgen': false,
      'is_creator_linked': false,
      'available_quantity': request.quantity,
      'sale_price_credits': request.pricePerCardCredits,
      'tier_code': 'RW',
      'tier_name': 'First Team',
      'rarity_rank': 4,
      'edition_code': 'launch',
      'club_name': 'Arsenal',
      'position': 'RW',
    });
  }

  @override
  Future<PlayerCardMarketplaceSwapListing> createSwapListing(
    PlayerCardMarketplaceSwapListingCreateRequest request,
  ) async {
    throw UnimplementedError();
  }

  @override
  Future<PlayerCardPlayerDetail> fetchPlayerDetail(String playerId) async {
    return PlayerCardPlayerDetail.fromJson(<String, Object?>{
      'player_id': playerId,
      'player_name': 'Fixture Player',
      'cards': const <Object?>[],
      'effects': const <Object?>[],
      'form_buffs': const <Object?>[],
      'real_world_flags': const <Object?>[],
      'real_world_form_modifiers': const <Object?>[],
      'demand_signals': const <Object?>[],
      'recommendation_priority_delta': 0,
      'market_buzz_score': 0,
    });
  }

  @override
  Future<List<PlayerCardHolding>> listInventory() async {
    if (inventoryError != null) {
      throw inventoryError!;
    }
    return _inventory;
  }

  @override
  Future<List<PlayerCardListing>> listListings(
    PlayerCardListingsQuery query,
  ) async => _listings;

  @override
  Future<PlayerCardMarketplaceLoanContractList> listLoanContracts(
    PlayerCardLoanContractsQuery query,
  ) async => const PlayerCardMarketplaceLoanContractList.empty();

  @override
  Future<PlayerCardMarketplaceSearchResult> listMarketplaceLoans(
    PlayerCardMarketplaceQuery query,
  ) async => _marketLoans;

  @override
  Future<PlayerCardMarketplaceSearchResult> listMarketplaceSales(
    PlayerCardMarketplaceQuery query,
  ) async => _marketSales;

  @override
  Future<PlayerCardMarketplaceSearchResult> listMarketplaceSwaps(
    PlayerCardMarketplaceQuery query,
  ) async => const PlayerCardMarketplaceSearchResult.empty();

  @override
  Future<List<PlayerCardListing>> listMyListings() async => _myListings;

  @override
  Future<List<PlayerCardPlayerSummary>> listPlayers(
    PlayerCardPlayersQuery query,
  ) async => _players;

  @override
  Future<List<PlayerCardLoanSupportListing>> listLoanSupportListings(
    PlayerCardLoanSupportQuery query,
  ) async => const <PlayerCardLoanSupportListing>[];

  @override
  Future<List<PlayerCardWatchlistItem>> listWatchlist() async => _watchlist;

  @override
  Future<List<PlayerCardPack>> listPacks() async => const <PlayerCardPack>[];

  @override
  Future<PlayerCardPackOpening> openPack(String packKey) async {
    return PlayerCardPackOpening.fromJson(<String, Object?>{
      'opening_id': 'opening-1',
      'pack_key': packKey,
      'status': 'opened',
      'price_credits': 0,
      'opened_cards': const <Object?>[],
    });
  }

  @override
  Future<PlayerCardCollectibleActionResult> burnCard(
    PlayerCardBurnRequest request,
  ) async {
    return PlayerCardCollectibleActionResult.fromJson(<String, Object?>{
      'burn_event_id': 'burn-${request.playerCardId}',
      'status': 'completed',
    });
  }

  @override
  Future<PlayerCardCollectibleActionResult> upgradeCards(
    PlayerCardUpgradeRequest request,
  ) async {
    return PlayerCardCollectibleActionResult.fromJson(<String, Object?>{
      'upgrade_event_id': 'upgrade-${request.targetTierCode}',
      'status': 'completed',
    });
  }

  @override
  Future<void> removeWatchlist(String watchlistId) async {}

  @override
  Future<PlayerCardMarketplaceSearchResult> searchMarketplace(
    PlayerCardMarketplaceQuery query,
  ) async => _marketSales;

  @override
  Future<PlayerCardMarketplaceLoanContract> settleLoanContract(
    String contractId,
  ) async {
    throw UnimplementedError();
  }

  @override
  Future<PlayerCardMarketplaceSwapExecution> executeSwapListing(
    String listingId,
    PlayerCardMarketplaceSwapExecuteRequest request,
  ) async {
    throw UnimplementedError();
  }

  @override
  Future<PlayerCardMarketplaceLoanContract> returnLoanContract(
    String contractId,
  ) async {
    throw UnimplementedError();
  }
}
