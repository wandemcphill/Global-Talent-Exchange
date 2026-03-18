import 'package:flutter/foundation.dart';

import '../../../core/app_feedback.dart';
import '../../../data/gte_api_repository.dart';
import '../data/player_card_marketplace_models.dart';
import '../data/player_card_marketplace_repository.dart';

class PlayerCardMarketplaceController extends ChangeNotifier {
  PlayerCardMarketplaceController({
    required PlayerCardMarketplaceRepository repository,
  }) : _repository = repository;

  factory PlayerCardMarketplaceController.standard({
    required String baseUrl,
    required GteBackendMode backendMode,
    required String? accessToken,
  }) {
    return PlayerCardMarketplaceController(
      repository: PlayerCardMarketplaceApiRepository.standard(
        baseUrl: baseUrl,
        mode: backendMode,
        accessToken: accessToken,
      ),
    );
  }

  final PlayerCardMarketplaceRepository _repository;
  final GteRequestGate _marketplaceGate = GteRequestGate();
  final GteRequestGate _supportGate = GteRequestGate();
  final GteRequestGate _playerGate = GteRequestGate();
  final GteRequestGate _contractsGate = GteRequestGate();

  PlayerCardMarketplaceQuery currentMarketplaceQuery =
      const PlayerCardMarketplaceQuery();
  PlayerCardPlayersQuery currentPlayersQuery = const PlayerCardPlayersQuery();
  PlayerCardListingsQuery currentListingsQuery =
      const PlayerCardListingsQuery();
  PlayerCardLoanSupportQuery currentLoanSupportQuery =
      const PlayerCardLoanSupportQuery();
  PlayerCardLoanContractsQuery currentLoanContractsQuery =
      const PlayerCardLoanContractsQuery();

  List<PlayerCardPlayerSummary> players = const <PlayerCardPlayerSummary>[];
  PlayerCardPlayerDetail? playerDetail;
  List<PlayerCardHolding> inventory = const <PlayerCardHolding>[];
  List<PlayerCardListing> listings = const <PlayerCardListing>[];
  List<PlayerCardListing> myListings = const <PlayerCardListing>[];
  List<PlayerCardLoanSupportListing> loanSupportListings =
      const <PlayerCardLoanSupportListing>[];
  List<PlayerCardWatchlistItem> watchlist = const <PlayerCardWatchlistItem>[];
  PlayerCardMarketplaceSearchResult marketplace =
      const PlayerCardMarketplaceSearchResult.empty();
  PlayerCardMarketplaceSearchResult marketplaceSales =
      const PlayerCardMarketplaceSearchResult.empty();
  PlayerCardMarketplaceSearchResult marketplaceLoans =
      const PlayerCardMarketplaceSearchResult.empty();
  PlayerCardMarketplaceSearchResult marketplaceSwaps =
      const PlayerCardMarketplaceSearchResult.empty();
  PlayerCardMarketplaceLoanContractList loanContracts =
      const PlayerCardMarketplaceLoanContractList.empty();

  PlayerCardMarketplaceSaleExecution? latestSaleExecution;
  PlayerCardMarketplaceLoanNegotiation? latestLoanNegotiation;
  PlayerCardMarketplaceLoanContract? latestLoanContract;
  PlayerCardMarketplaceSwapExecution? latestSwapExecution;

  bool isLoadingMarketplace = false;
  bool isLoadingSupport = false;
  bool isLoadingPlayer = false;
  bool isLoadingLoanContracts = false;
  bool isCreatingSaleListing = false;
  bool isCancelingSaleListing = false;
  bool isBuyingSaleListing = false;
  bool isCreatingLoanListing = false;
  bool isCancelingLoanListing = false;
  bool isCreatingLoanNegotiation = false;
  bool isCounteringLoanNegotiation = false;
  bool isAcceptingLoanNegotiation = false;
  bool isSettlingLoanContract = false;
  bool isReturningLoanContract = false;
  bool isCreatingSwapListing = false;
  bool isCancelingSwapListing = false;
  bool isExecutingSwapListing = false;
  bool isAddingWatchlist = false;
  bool isRemovingWatchlist = false;

  String? marketplaceError;
  String? supportError;
  String? playerError;
  String? loanContractsError;
  String? actionError;

  Future<void> loadMarketplace({
    PlayerCardMarketplaceQuery query = const PlayerCardMarketplaceQuery(),
  }) async {
    final int requestId = _marketplaceGate.begin();
    currentMarketplaceQuery = query;
    marketplaceError = null;
    isLoadingMarketplace = true;
    notifyListeners();

    try {
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
        _repository.searchMarketplace(query),
        _repository.listMarketplaceSales(query),
        _repository.listMarketplaceLoans(query),
        _repository.listMarketplaceSwaps(query),
      ]);
      if (!_marketplaceGate.isActive(requestId)) {
        return;
      }
      marketplace = payload[0] as PlayerCardMarketplaceSearchResult;
      marketplaceSales = payload[1] as PlayerCardMarketplaceSearchResult;
      marketplaceLoans = payload[2] as PlayerCardMarketplaceSearchResult;
      marketplaceSwaps = payload[3] as PlayerCardMarketplaceSearchResult;
    } catch (error) {
      if (_marketplaceGate.isActive(requestId)) {
        marketplaceError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_marketplaceGate.isActive(requestId)) {
        isLoadingMarketplace = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadSupport({
    PlayerCardPlayersQuery playersQuery = const PlayerCardPlayersQuery(),
    PlayerCardListingsQuery listingsQuery = const PlayerCardListingsQuery(),
    PlayerCardLoanSupportQuery loanSupportQuery =
        const PlayerCardLoanSupportQuery(),
    bool includeAuthed = false,
  }) async {
    final int requestId = _supportGate.begin();
    currentPlayersQuery = playersQuery;
    currentListingsQuery = listingsQuery;
    currentLoanSupportQuery = loanSupportQuery;
    supportError = null;
    isLoadingSupport = true;
    notifyListeners();

    try {
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
        _repository.listPlayers(playersQuery),
        _repository.listListings(listingsQuery),
        _repository.listLoanSupportListings(loanSupportQuery),
        if (includeAuthed) _repository.listInventory(),
        if (includeAuthed) _repository.listMyListings(),
        if (includeAuthed) _repository.listWatchlist(),
      ]);
      if (!_supportGate.isActive(requestId)) {
        return;
      }
      players = payload[0] as List<PlayerCardPlayerSummary>;
      listings = payload[1] as List<PlayerCardListing>;
      loanSupportListings = payload[2] as List<PlayerCardLoanSupportListing>;
      if (includeAuthed) {
        inventory = payload[3] as List<PlayerCardHolding>;
        myListings = payload[4] as List<PlayerCardListing>;
        watchlist = payload[5] as List<PlayerCardWatchlistItem>;
      }
    } catch (error) {
      if (_supportGate.isActive(requestId)) {
        supportError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_supportGate.isActive(requestId)) {
        isLoadingSupport = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadPlayer(String playerId) async {
    final int requestId = _playerGate.begin();
    playerError = null;
    isLoadingPlayer = true;
    notifyListeners();

    try {
      final PlayerCardPlayerDetail detail =
          await _repository.fetchPlayerDetail(playerId);
      if (!_playerGate.isActive(requestId)) {
        return;
      }
      playerDetail = detail;
    } catch (error) {
      if (_playerGate.isActive(requestId)) {
        playerError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_playerGate.isActive(requestId)) {
        isLoadingPlayer = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadLoanContracts({
    PlayerCardLoanContractsQuery query = const PlayerCardLoanContractsQuery(),
  }) async {
    final int requestId = _contractsGate.begin();
    currentLoanContractsQuery = query;
    loanContractsError = null;
    isLoadingLoanContracts = true;
    notifyListeners();

    try {
      final PlayerCardMarketplaceLoanContractList result =
          await _repository.listLoanContracts(query);
      if (!_contractsGate.isActive(requestId)) {
        return;
      }
      loanContracts = result;
    } catch (error) {
      if (_contractsGate.isActive(requestId)) {
        loanContractsError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_contractsGate.isActive(requestId)) {
        isLoadingLoanContracts = false;
        notifyListeners();
      }
    }
  }

  Future<void> createSaleListing(
    PlayerCardMarketplaceSaleListingCreateRequest request,
  ) async {
    if (isCreatingSaleListing) {
      return;
    }
    isCreatingSaleListing = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.createSaleListing(request);
      await Future.wait<void>(<Future<void>>[
        loadMarketplace(query: currentMarketplaceQuery),
        loadSupport(
          playersQuery: currentPlayersQuery,
          listingsQuery: currentListingsQuery,
          loanSupportQuery: currentLoanSupportQuery,
          includeAuthed: true,
        ),
      ]);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isCreatingSaleListing = false;
      notifyListeners();
    }
  }

  Future<void> cancelSaleListing(String listingId) async {
    if (isCancelingSaleListing) {
      return;
    }
    isCancelingSaleListing = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.cancelSaleListing(listingId);
      await Future.wait<void>(<Future<void>>[
        loadMarketplace(query: currentMarketplaceQuery),
        loadSupport(
          playersQuery: currentPlayersQuery,
          listingsQuery: currentListingsQuery,
          loanSupportQuery: currentLoanSupportQuery,
          includeAuthed: true,
        ),
      ]);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isCancelingSaleListing = false;
      notifyListeners();
    }
  }

  Future<void> buySaleListing(
    String listingId,
    PlayerCardMarketplaceSalePurchaseRequest request,
  ) async {
    if (isBuyingSaleListing) {
      return;
    }
    isBuyingSaleListing = true;
    actionError = null;
    notifyListeners();
    try {
      latestSaleExecution =
          await _repository.buySaleListing(listingId, request);
      await Future.wait<void>(<Future<void>>[
        loadMarketplace(query: currentMarketplaceQuery),
        loadSupport(
          playersQuery: currentPlayersQuery,
          listingsQuery: currentListingsQuery,
          loanSupportQuery: currentLoanSupportQuery,
          includeAuthed: true,
        ),
      ]);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isBuyingSaleListing = false;
      notifyListeners();
    }
  }

  Future<void> createLoanListing(
    PlayerCardMarketplaceLoanListingCreateRequest request,
  ) async {
    if (isCreatingLoanListing) {
      return;
    }
    isCreatingLoanListing = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.createLoanListing(request);
      await Future.wait<void>(<Future<void>>[
        loadMarketplace(query: currentMarketplaceQuery),
        loadSupport(
          playersQuery: currentPlayersQuery,
          listingsQuery: currentListingsQuery,
          loanSupportQuery: currentLoanSupportQuery,
          includeAuthed: true,
        ),
      ]);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isCreatingLoanListing = false;
      notifyListeners();
    }
  }

  Future<void> cancelLoanListing(String listingId) async {
    if (isCancelingLoanListing) {
      return;
    }
    isCancelingLoanListing = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.cancelLoanListing(listingId);
      await Future.wait<void>(<Future<void>>[
        loadMarketplace(query: currentMarketplaceQuery),
        loadSupport(
          playersQuery: currentPlayersQuery,
          listingsQuery: currentListingsQuery,
          loanSupportQuery: currentLoanSupportQuery,
          includeAuthed: true,
        ),
      ]);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isCancelingLoanListing = false;
      notifyListeners();
    }
  }

  Future<void> createLoanNegotiation(
    String listingId,
    PlayerCardMarketplaceLoanNegotiationCreateRequest request,
  ) async {
    if (isCreatingLoanNegotiation) {
      return;
    }
    isCreatingLoanNegotiation = true;
    actionError = null;
    notifyListeners();
    try {
      latestLoanNegotiation =
          await _repository.createLoanNegotiation(listingId, request);
      await Future.wait<void>(<Future<void>>[
        loadMarketplace(query: currentMarketplaceQuery),
        loadLoanContracts(query: currentLoanContractsQuery),
      ]);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isCreatingLoanNegotiation = false;
      notifyListeners();
    }
  }

  Future<void> counterLoanNegotiation(
    String negotiationId,
    PlayerCardMarketplaceLoanNegotiationCreateRequest request,
  ) async {
    if (isCounteringLoanNegotiation) {
      return;
    }
    isCounteringLoanNegotiation = true;
    actionError = null;
    notifyListeners();
    try {
      latestLoanNegotiation =
          await _repository.counterLoanNegotiation(negotiationId, request);
      await Future.wait<void>(<Future<void>>[
        loadMarketplace(query: currentMarketplaceQuery),
        loadLoanContracts(query: currentLoanContractsQuery),
      ]);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isCounteringLoanNegotiation = false;
      notifyListeners();
    }
  }

  Future<void> acceptLoanNegotiation(String negotiationId) async {
    if (isAcceptingLoanNegotiation) {
      return;
    }
    isAcceptingLoanNegotiation = true;
    actionError = null;
    notifyListeners();
    try {
      latestLoanContract =
          await _repository.acceptLoanNegotiation(negotiationId);
      await Future.wait<void>(<Future<void>>[
        loadMarketplace(query: currentMarketplaceQuery),
        loadLoanContracts(query: currentLoanContractsQuery),
      ]);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isAcceptingLoanNegotiation = false;
      notifyListeners();
    }
  }

  Future<void> settleLoanContract(String contractId) async {
    if (isSettlingLoanContract) {
      return;
    }
    isSettlingLoanContract = true;
    actionError = null;
    notifyListeners();
    try {
      latestLoanContract = await _repository.settleLoanContract(contractId);
      await Future.wait<void>(<Future<void>>[
        loadMarketplace(query: currentMarketplaceQuery),
        loadLoanContracts(query: currentLoanContractsQuery),
      ]);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isSettlingLoanContract = false;
      notifyListeners();
    }
  }

  Future<void> returnLoanContract(String contractId) async {
    if (isReturningLoanContract) {
      return;
    }
    isReturningLoanContract = true;
    actionError = null;
    notifyListeners();
    try {
      latestLoanContract = await _repository.returnLoanContract(contractId);
      await Future.wait<void>(<Future<void>>[
        loadMarketplace(query: currentMarketplaceQuery),
        loadLoanContracts(query: currentLoanContractsQuery),
      ]);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isReturningLoanContract = false;
      notifyListeners();
    }
  }

  Future<void> createSwapListing(
    PlayerCardMarketplaceSwapListingCreateRequest request,
  ) async {
    if (isCreatingSwapListing) {
      return;
    }
    isCreatingSwapListing = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.createSwapListing(request);
      await Future.wait<void>(<Future<void>>[
        loadMarketplace(query: currentMarketplaceQuery),
        loadSupport(
          playersQuery: currentPlayersQuery,
          listingsQuery: currentListingsQuery,
          loanSupportQuery: currentLoanSupportQuery,
          includeAuthed: true,
        ),
      ]);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isCreatingSwapListing = false;
      notifyListeners();
    }
  }

  Future<void> cancelSwapListing(String listingId) async {
    if (isCancelingSwapListing) {
      return;
    }
    isCancelingSwapListing = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.cancelSwapListing(listingId);
      await loadMarketplace(query: currentMarketplaceQuery);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isCancelingSwapListing = false;
      notifyListeners();
    }
  }

  Future<void> executeSwapListing(
    String listingId,
    PlayerCardMarketplaceSwapExecuteRequest request,
  ) async {
    if (isExecutingSwapListing) {
      return;
    }
    isExecutingSwapListing = true;
    actionError = null;
    notifyListeners();
    try {
      latestSwapExecution =
          await _repository.executeSwapListing(listingId, request);
      await Future.wait<void>(<Future<void>>[
        loadMarketplace(query: currentMarketplaceQuery),
        loadSupport(
          playersQuery: currentPlayersQuery,
          listingsQuery: currentListingsQuery,
          loanSupportQuery: currentLoanSupportQuery,
          includeAuthed: true,
        ),
      ]);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isExecutingSwapListing = false;
      notifyListeners();
    }
  }

  Future<void> addWatchlist(PlayerCardWatchlistCreateRequest request) async {
    if (isAddingWatchlist) {
      return;
    }
    isAddingWatchlist = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.addWatchlist(request);
      await loadSupport(
        playersQuery: currentPlayersQuery,
        listingsQuery: currentListingsQuery,
        loanSupportQuery: currentLoanSupportQuery,
        includeAuthed: true,
      );
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isAddingWatchlist = false;
      notifyListeners();
    }
  }

  Future<void> removeWatchlist(String watchlistId) async {
    if (isRemovingWatchlist) {
      return;
    }
    isRemovingWatchlist = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.removeWatchlist(watchlistId);
      await loadSupport(
        playersQuery: currentPlayersQuery,
        listingsQuery: currentListingsQuery,
        loanSupportQuery: currentLoanSupportQuery,
        includeAuthed: true,
      );
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isRemovingWatchlist = false;
      notifyListeners();
    }
  }
}
