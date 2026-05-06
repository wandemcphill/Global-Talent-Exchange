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

  Future<_SupportLoadResult<T>> _captureSupport<T>(Future<T> future) async {
    try {
      return _SupportLoadResult<T>(value: await future);
    } catch (error) {
      return _SupportLoadResult<T>(error: AppFeedback.messageFor(error));
    }
  }

  Future<void> loadMarketplace({
    PlayerCardMarketplaceQuery query = const PlayerCardMarketplaceQuery(),
  }) async {
    final int requestId = _marketplaceGate.begin();
    currentMarketplaceQuery = query;
    marketplaceError = null;
    isLoadingMarketplace = true;
    notifyListeners();

    try {
      final List<PlayerCardMarketplaceSearchResult> result = await Future.wait<
        PlayerCardMarketplaceSearchResult
      >(<Future<PlayerCardMarketplaceSearchResult>>[
        _repository.listMarketplaceSales(query),
        _repository.listMarketplaceLoans(query),
      ]);
      if (!_marketplaceGate.isActive(requestId)) {
        return;
      }
      marketplace = result[0];
      marketplaceSales = result[0];
      marketplaceLoans = result[1];
      marketplaceSwaps = const PlayerCardMarketplaceSearchResult.empty();
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
      final Future<_SupportLoadResult<List<PlayerCardPlayerSummary>>>
      playersFuture = _captureSupport<List<PlayerCardPlayerSummary>>(
        _repository.listPlayers(playersQuery),
      );
      final Future<_SupportLoadResult<List<PlayerCardListing>>> listingsFuture =
          _captureSupport<List<PlayerCardListing>>(
            _repository.listListings(listingsQuery),
          );
      final Future<_SupportLoadResult<List<PlayerCardHolding>>>?
      inventoryFuture =
          includeAuthed
              ? _captureSupport<List<PlayerCardHolding>>(
                _repository.listInventory(),
              )
              : null;
      final Future<_SupportLoadResult<List<PlayerCardListing>>>?
      myListingsFuture =
          includeAuthed
              ? _captureSupport<List<PlayerCardListing>>(
                _repository.listMyListings(),
              )
              : null;
      final Future<_SupportLoadResult<List<PlayerCardWatchlistItem>>>?
      watchlistFuture =
          includeAuthed
              ? _captureSupport<List<PlayerCardWatchlistItem>>(
                _repository.listWatchlist(),
              )
              : null;

      final _SupportLoadResult<List<PlayerCardPlayerSummary>> playersResult =
          await playersFuture;
      final _SupportLoadResult<List<PlayerCardListing>> listingsResult =
          await listingsFuture;
      final _SupportLoadResult<List<PlayerCardHolding>>? inventoryResult =
          inventoryFuture == null ? null : await inventoryFuture;
      final _SupportLoadResult<List<PlayerCardListing>>? myListingsResult =
          myListingsFuture == null ? null : await myListingsFuture;
      final _SupportLoadResult<List<PlayerCardWatchlistItem>>? watchlistResult =
          watchlistFuture == null ? null : await watchlistFuture;

      if (!_supportGate.isActive(requestId)) {
        return;
      }

      final List<String> failures = <String>[
        if (playersResult.error != null) playersResult.error!,
        if (listingsResult.error != null) listingsResult.error!,
        if (inventoryResult?.error != null) inventoryResult!.error!,
        if (myListingsResult?.error != null) myListingsResult!.error!,
        if (watchlistResult?.error != null) watchlistResult!.error!,
      ];
      final bool hasCoreSuccess =
          playersResult.value != null || listingsResult.value != null;

      if (playersResult.value != null) {
        players = playersResult.value!;
      }
      if (listingsResult.value != null) {
        listings = listingsResult.value!;
      }
      loanSupportListings = const <PlayerCardLoanSupportListing>[];
      if (includeAuthed) {
        inventory = inventoryResult?.value ?? const <PlayerCardHolding>[];
        myListings = myListingsResult?.value ?? const <PlayerCardListing>[];
        watchlist = watchlistResult?.value ?? const <PlayerCardWatchlistItem>[];
      } else {
        inventory = const <PlayerCardHolding>[];
        myListings = const <PlayerCardListing>[];
        watchlist = const <PlayerCardWatchlistItem>[];
      }

      supportError = hasCoreSuccess || failures.isEmpty ? null : failures.first;
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
      final PlayerCardPlayerDetail detail = await _repository.fetchPlayerDetail(
        playerId,
      );
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
      final PlayerCardMarketplaceLoanContractList result = await _repository
          .listLoanContracts(query);
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
      latestSaleExecution = await _repository.buySaleListing(
        listingId,
        request,
      );
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
      latestLoanNegotiation = await _repository.createLoanNegotiation(
        listingId,
        request,
      );
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
      latestLoanNegotiation = await _repository.counterLoanNegotiation(
        negotiationId,
        request,
      );
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
      latestLoanContract = await _repository.acceptLoanNegotiation(
        negotiationId,
      );
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
      latestSwapExecution = await _repository.executeSwapListing(
        listingId,
        request,
      );
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

class _SupportLoadResult<T> {
  const _SupportLoadResult({this.value, this.error});

  final T? value;
  final String? error;
}
