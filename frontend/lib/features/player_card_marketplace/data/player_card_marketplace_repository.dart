import '../../../data/gte_api_repository.dart';
import '../../../data/gte_authed_api.dart';
import '../../shared/data/gte_feature_support.dart';
import 'player_card_marketplace_models.dart';

abstract class PlayerCardMarketplaceRepository {
  Future<List<PlayerCardPlayerSummary>> listPlayers(
      PlayerCardPlayersQuery query);

  Future<PlayerCardPlayerDetail> fetchPlayerDetail(String playerId);

  Future<List<PlayerCardHolding>> listInventory();

  Future<List<PlayerCardListing>> listListings(PlayerCardListingsQuery query);

  Future<List<PlayerCardListing>> listMyListings();

  Future<List<PlayerCardLoanSupportListing>> listLoanSupportListings(
    PlayerCardLoanSupportQuery query,
  );

  Future<PlayerCardMarketplaceSearchResult> searchMarketplace(
    PlayerCardMarketplaceQuery query,
  );

  Future<PlayerCardMarketplaceSearchResult> listMarketplaceSales(
    PlayerCardMarketplaceQuery query,
  );

  Future<PlayerCardMarketplaceSearchResult> listMarketplaceLoans(
    PlayerCardMarketplaceQuery query,
  );

  Future<PlayerCardMarketplaceSearchResult> listMarketplaceSwaps(
    PlayerCardMarketplaceQuery query,
  );

  Future<PlayerCardMarketplaceListing> createSaleListing(
    PlayerCardMarketplaceSaleListingCreateRequest request,
  );

  Future<PlayerCardMarketplaceListing> cancelSaleListing(String listingId);

  Future<PlayerCardMarketplaceSaleExecution> buySaleListing(
    String listingId,
    PlayerCardMarketplaceSalePurchaseRequest request,
  );

  Future<PlayerCardMarketplaceLoanListing> createLoanListing(
    PlayerCardMarketplaceLoanListingCreateRequest request,
  );

  Future<PlayerCardMarketplaceLoanListing> cancelLoanListing(String listingId);

  Future<PlayerCardMarketplaceLoanNegotiation> createLoanNegotiation(
    String listingId,
    PlayerCardMarketplaceLoanNegotiationCreateRequest request,
  );

  Future<PlayerCardMarketplaceLoanNegotiation> counterLoanNegotiation(
    String negotiationId,
    PlayerCardMarketplaceLoanNegotiationCreateRequest request,
  );

  Future<PlayerCardMarketplaceLoanContract> acceptLoanNegotiation(
    String negotiationId,
  );

  Future<PlayerCardMarketplaceLoanContractList> listLoanContracts(
    PlayerCardLoanContractsQuery query,
  );

  Future<PlayerCardMarketplaceLoanContract> settleLoanContract(
    String contractId,
  );

  Future<PlayerCardMarketplaceLoanContract> returnLoanContract(
    String contractId,
  );

  Future<PlayerCardMarketplaceSwapListing> createSwapListing(
    PlayerCardMarketplaceSwapListingCreateRequest request,
  );

  Future<PlayerCardMarketplaceSwapListing> cancelSwapListing(String listingId);

  Future<PlayerCardMarketplaceSwapExecution> executeSwapListing(
    String listingId,
    PlayerCardMarketplaceSwapExecuteRequest request,
  );

  Future<List<PlayerCardWatchlistItem>> listWatchlist();

  Future<PlayerCardWatchlistItem> addWatchlist(
    PlayerCardWatchlistCreateRequest request,
  );

  Future<void> removeWatchlist(String watchlistId);
}

class PlayerCardMarketplaceApiRepository
    implements PlayerCardMarketplaceRepository {
  PlayerCardMarketplaceApiRepository({
    required GteAuthedApi client,
  }) : _client = client;

  factory PlayerCardMarketplaceApiRepository.standard({
    required String baseUrl,
    required GteBackendMode mode,
    required String? accessToken,
  }) {
    return PlayerCardMarketplaceApiRepository(
      client: createFeatureApi(
        baseUrl: baseUrl,
        mode: mode,
        accessToken: accessToken,
      ),
    );
  }

  final GteAuthedApi _client;

  @override
  Future<List<PlayerCardPlayerSummary>> listPlayers(
    PlayerCardPlayersQuery query,
  ) async {
    return parseList(
      await _client.getList(
        '/player-cards/players',
        query: query.toQuery(),
        auth: false,
      ),
      PlayerCardPlayerSummary.fromJson,
      label: 'player card players',
    );
  }

  @override
  Future<PlayerCardPlayerDetail> fetchPlayerDetail(String playerId) async {
    return PlayerCardPlayerDetail.fromJson(
      await _client.getMap('/player-cards/players/$playerId', auth: false),
    );
  }

  @override
  Future<List<PlayerCardHolding>> listInventory() async {
    return parseList(
      await _client.getList('/player-cards/inventory'),
      PlayerCardHolding.fromJson,
      label: 'player card inventory',
    );
  }

  @override
  Future<List<PlayerCardListing>> listListings(
    PlayerCardListingsQuery query,
  ) async {
    return parseList(
      await _client.getList(
        '/player-cards/listings',
        query: query.toQuery(),
        auth: false,
      ),
      PlayerCardListing.fromJson,
      label: 'player card listings',
    );
  }

  @override
  Future<List<PlayerCardListing>> listMyListings() async {
    return parseList(
      await _client.getList('/player-cards/listings/mine'),
      PlayerCardListing.fromJson,
      label: 'my player card listings',
    );
  }

  @override
  Future<List<PlayerCardLoanSupportListing>> listLoanSupportListings(
    PlayerCardLoanSupportQuery query,
  ) async {
    return parseList(
      await _client.getList(
        '/player-cards/loans',
        query: query.toQuery(),
        auth: false,
      ),
      PlayerCardLoanSupportListing.fromJson,
      label: 'player card loan listings',
    );
  }

  @override
  Future<PlayerCardMarketplaceSearchResult> searchMarketplace(
    PlayerCardMarketplaceQuery query,
  ) async {
    return PlayerCardMarketplaceSearchResult.fromJson(
      await _client.getMap(
        '/player-cards/marketplace/listings',
        query: query.toQuery(),
        auth: false,
      ),
    );
  }

  @override
  Future<PlayerCardMarketplaceSearchResult> listMarketplaceSales(
    PlayerCardMarketplaceQuery query,
  ) async {
    return PlayerCardMarketplaceSearchResult.fromJson(
      await _client.getMap(
        '/player-cards/marketplace/sales',
        query: query.toQuery(forceListingType: 'sale'),
        auth: false,
      ),
    );
  }

  @override
  Future<PlayerCardMarketplaceSearchResult> listMarketplaceLoans(
    PlayerCardMarketplaceQuery query,
  ) async {
    return PlayerCardMarketplaceSearchResult.fromJson(
      await _client.getMap(
        '/player-cards/marketplace/loans',
        query: query.toQuery(forceListingType: 'loan'),
        auth: false,
      ),
    );
  }

  @override
  Future<PlayerCardMarketplaceSearchResult> listMarketplaceSwaps(
    PlayerCardMarketplaceQuery query,
  ) async {
    return PlayerCardMarketplaceSearchResult.fromJson(
      await _client.getMap(
        '/player-cards/marketplace/swaps',
        query: query.toQuery(forceListingType: 'swap'),
        auth: false,
      ),
    );
  }

  @override
  Future<PlayerCardMarketplaceListing> createSaleListing(
    PlayerCardMarketplaceSaleListingCreateRequest request,
  ) async {
    return PlayerCardMarketplaceListing.fromJson(
      await _client.request(
        'POST',
        '/player-cards/marketplace/sales',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<PlayerCardMarketplaceListing> cancelSaleListing(
      String listingId) async {
    return PlayerCardMarketplaceListing.fromJson(
      await _client.request(
        'POST',
        '/player-cards/marketplace/sales/$listingId/cancel',
      ),
    );
  }

  @override
  Future<PlayerCardMarketplaceSaleExecution> buySaleListing(
    String listingId,
    PlayerCardMarketplaceSalePurchaseRequest request,
  ) async {
    return PlayerCardMarketplaceSaleExecution.fromJson(
      await _client.request(
        'POST',
        '/player-cards/marketplace/sales/$listingId/buy',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<PlayerCardMarketplaceLoanListing> createLoanListing(
    PlayerCardMarketplaceLoanListingCreateRequest request,
  ) async {
    return PlayerCardMarketplaceLoanListing.fromJson(
      await _client.request(
        'POST',
        '/player-cards/marketplace/loans',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<PlayerCardMarketplaceLoanListing> cancelLoanListing(
    String listingId,
  ) async {
    return PlayerCardMarketplaceLoanListing.fromJson(
      await _client.request(
        'POST',
        '/player-cards/marketplace/loans/$listingId/cancel',
      ),
    );
  }

  @override
  Future<PlayerCardMarketplaceLoanNegotiation> createLoanNegotiation(
    String listingId,
    PlayerCardMarketplaceLoanNegotiationCreateRequest request,
  ) async {
    return PlayerCardMarketplaceLoanNegotiation.fromJson(
      await _client.request(
        'POST',
        '/player-cards/marketplace/loans/$listingId/negotiations',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<PlayerCardMarketplaceLoanNegotiation> counterLoanNegotiation(
    String negotiationId,
    PlayerCardMarketplaceLoanNegotiationCreateRequest request,
  ) async {
    return PlayerCardMarketplaceLoanNegotiation.fromJson(
      await _client.request(
        'POST',
        '/player-cards/marketplace/loans/negotiations/$negotiationId/counter',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<PlayerCardMarketplaceLoanContract> acceptLoanNegotiation(
    String negotiationId,
  ) async {
    return PlayerCardMarketplaceLoanContract.fromJson(
      await _client.request(
        'POST',
        '/player-cards/marketplace/loans/negotiations/$negotiationId/accept',
      ),
    );
  }

  @override
  Future<PlayerCardMarketplaceLoanContractList> listLoanContracts(
    PlayerCardLoanContractsQuery query,
  ) async {
    return PlayerCardMarketplaceLoanContractList.fromJson(
      await _client.getMap(
        '/player-cards/marketplace/loans/contracts',
        query: query.toQuery(),
      ),
    );
  }

  @override
  Future<PlayerCardMarketplaceLoanContract> settleLoanContract(
    String contractId,
  ) async {
    return PlayerCardMarketplaceLoanContract.fromJson(
      await _client.request(
        'POST',
        '/player-cards/marketplace/loans/contracts/$contractId/settle',
      ),
    );
  }

  @override
  Future<PlayerCardMarketplaceLoanContract> returnLoanContract(
    String contractId,
  ) async {
    return PlayerCardMarketplaceLoanContract.fromJson(
      await _client.request(
        'POST',
        '/player-cards/marketplace/loans/contracts/$contractId/return',
      ),
    );
  }

  @override
  Future<PlayerCardMarketplaceSwapListing> createSwapListing(
    PlayerCardMarketplaceSwapListingCreateRequest request,
  ) async {
    return PlayerCardMarketplaceSwapListing.fromJson(
      await _client.request(
        'POST',
        '/player-cards/marketplace/swaps',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<PlayerCardMarketplaceSwapListing> cancelSwapListing(
    String listingId,
  ) async {
    return PlayerCardMarketplaceSwapListing.fromJson(
      await _client.request(
        'POST',
        '/player-cards/marketplace/swaps/$listingId/cancel',
      ),
    );
  }

  @override
  Future<PlayerCardMarketplaceSwapExecution> executeSwapListing(
    String listingId,
    PlayerCardMarketplaceSwapExecuteRequest request,
  ) async {
    return PlayerCardMarketplaceSwapExecution.fromJson(
      await _client.request(
        'POST',
        '/player-cards/marketplace/swaps/$listingId/execute',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<List<PlayerCardWatchlistItem>> listWatchlist() async {
    return parseList(
      await _client.getList('/player-cards/watchlist'),
      PlayerCardWatchlistItem.fromJson,
      label: 'player card watchlist',
    );
  }

  @override
  Future<PlayerCardWatchlistItem> addWatchlist(
    PlayerCardWatchlistCreateRequest request,
  ) async {
    return PlayerCardWatchlistItem.fromJson(
      await _client.request(
        'POST',
        '/player-cards/watchlist',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<void> removeWatchlist(String watchlistId) async {
    await _client.request(
      'DELETE',
      '/player-cards/watchlist/$watchlistId',
    );
  }
}
