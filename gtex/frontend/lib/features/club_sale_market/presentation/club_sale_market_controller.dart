import 'package:flutter/foundation.dart';

import '../../../core/app_feedback.dart';
import '../../../data/gte_api_repository.dart';
import '../data/club_sale_market_models.dart';
import '../data/club_sale_market_repository.dart';

class ClubSaleMarketController extends ChangeNotifier {
  ClubSaleMarketController({
    required ClubSaleMarketRepository repository,
  }) : _repository = repository;

  factory ClubSaleMarketController.standard({
    required String baseUrl,
    required GteBackendMode backendMode,
    required String? accessToken,
  }) {
    return ClubSaleMarketController(
      repository: ClubSaleMarketApiRepository.standard(
        baseUrl: baseUrl,
        mode: backendMode,
        accessToken: accessToken,
      ),
    );
  }

  final ClubSaleMarketRepository _repository;
  final GteRequestGate _publicGate = GteRequestGate();
  final GteRequestGate _publicListingsGate = GteRequestGate();
  final GteRequestGate _ownerGate = GteRequestGate();
  final GteRequestGate _historyGate = GteRequestGate();

  String? currentClubId;
  ClubSaleValuation? valuation;
  ClubSaleListing? publicListing;
  ClubSaleListingCollection publicListings =
      const ClubSaleListingCollection.empty();
  ClubSaleListingCollection myListings =
      const ClubSaleListingCollection.empty();
  ClubSaleInquiryCollection clubInquiries =
      const ClubSaleInquiryCollection.empty();
  ClubSaleOfferCollection clubOffers = const ClubSaleOfferCollection.empty();
  ClubSaleOfferCollection myOffers = const ClubSaleOfferCollection.empty();
  ClubSaleHistory? history;
  ClubSaleTransferExecution? latestTransfer;

  bool isLoadingPublicSnapshot = false;
  bool isLoadingPublicListings = false;
  bool isLoadingOwnerWorkspace = false;
  bool isLoadingHistory = false;
  bool isCreatingListing = false;
  bool isUpdatingListing = false;
  bool isCancellingListing = false;
  bool isSubmittingInquiry = false;
  bool isRespondingInquiry = false;
  bool isSubmittingOffer = false;
  bool isCounteringOffer = false;
  bool isAcceptingOffer = false;
  bool isRejectingOffer = false;
  bool isExecutingTransfer = false;

  String? publicError;
  String? listingsError;
  String? ownerError;
  String? historyError;
  String? actionError;
  bool isHistoryVisibilityRestricted = false;

  bool get hasPublicSnapshot => valuation != null || publicListing != null;

  Future<void> _reloadMyOffersSilently() async {
    try {
      myOffers = await _repository.listMyOffers();
    } catch (_) {
      // Buyer-facing refresh should not override a successful action.
    }
  }

  Future<void> loadPublicSnapshot(String clubId) async {
    final int requestId = _publicGate.begin();
    currentClubId = clubId;
    publicError = null;
    isLoadingPublicSnapshot = true;
    notifyListeners();

    try {
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
        _repository.fetchValuation(clubId),
        _repository.fetchPublicListing(clubId),
      ]);
      if (!_publicGate.isActive(requestId)) {
        return;
      }
      valuation = payload[0] as ClubSaleValuation;
      publicListing = payload[1] as ClubSaleListing?;
    } catch (error) {
      if (_publicGate.isActive(requestId)) {
        publicError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_publicGate.isActive(requestId)) {
        isLoadingPublicSnapshot = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadPublicListings({
    ClubSaleListingsQuery query = const ClubSaleListingsQuery(),
  }) async {
    final int requestId = _publicListingsGate.begin();
    listingsError = null;
    isLoadingPublicListings = true;
    notifyListeners();

    try {
      final ClubSaleListingCollection collection =
          await _repository.listPublicListings(query);
      if (!_publicListingsGate.isActive(requestId)) {
        return;
      }
      publicListings = collection;
    } catch (error) {
      if (_publicListingsGate.isActive(requestId)) {
        listingsError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_publicListingsGate.isActive(requestId)) {
        isLoadingPublicListings = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadOwnerWorkspace(String clubId) async {
    final int requestId = _ownerGate.begin();
    currentClubId = clubId;
    ownerError = null;
    isLoadingOwnerWorkspace = true;
    notifyListeners();

    try {
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
        _repository.listMyListings(),
        _repository.listInquiries(clubId),
        _repository.listOffers(clubId),
        _repository.listMyOffers(),
      ]);
      if (!_ownerGate.isActive(requestId)) {
        return;
      }
      myListings = payload[0] as ClubSaleListingCollection;
      clubInquiries = payload[1] as ClubSaleInquiryCollection;
      clubOffers = payload[2] as ClubSaleOfferCollection;
      myOffers = payload[3] as ClubSaleOfferCollection;
    } catch (error) {
      if (_ownerGate.isActive(requestId)) {
        ownerError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_ownerGate.isActive(requestId)) {
        isLoadingOwnerWorkspace = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadHistory(
    String clubId, {
    ClubSaleHistoryQuery query = const ClubSaleHistoryQuery(),
  }) async {
    final int requestId = _historyGate.begin();
    currentClubId = clubId;
    historyError = null;
    isHistoryVisibilityRestricted = false;
    isLoadingHistory = true;
    notifyListeners();

    try {
      final ClubSaleHistory nextHistory =
          await _repository.fetchHistory(clubId, query);
      if (!_historyGate.isActive(requestId)) {
        return;
      }
      history = nextHistory;
      latestTransfer =
          nextHistory.transfers.isEmpty ? null : nextHistory.transfers.first;
    } catch (error) {
      if (_historyGate.isActive(requestId)) {
        history = null;
        latestTransfer = null;
        if (error is GteApiException &&
            (error.type == GteApiErrorType.unauthorized ||
                error.statusCode == 403)) {
          isHistoryVisibilityRestricted = true;
          historyError = null;
        } else {
          historyError = AppFeedback.messageFor(error);
        }
      }
    } finally {
      if (_historyGate.isActive(requestId)) {
        isLoadingHistory = false;
        notifyListeners();
      }
    }
  }

  Future<void> createListing(
    String clubId,
    ClubSaleListingUpsertRequest request,
  ) async {
    if (isCreatingListing) {
      return;
    }
    isCreatingListing = true;
    actionError = null;
    notifyListeners();
    try {
      publicListing = await _repository.createListing(clubId, request);
      await Future.wait<void>(<Future<void>>[
        loadPublicSnapshot(clubId),
        loadOwnerWorkspace(clubId),
      ]);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isCreatingListing = false;
      notifyListeners();
    }
  }

  Future<void> updateListing(
    String clubId,
    ClubSaleListingUpsertRequest request,
  ) async {
    if (isUpdatingListing) {
      return;
    }
    isUpdatingListing = true;
    actionError = null;
    notifyListeners();
    try {
      publicListing = await _repository.updateListing(clubId, request);
      await Future.wait<void>(<Future<void>>[
        loadPublicSnapshot(clubId),
        loadOwnerWorkspace(clubId),
      ]);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isUpdatingListing = false;
      notifyListeners();
    }
  }

  Future<void> cancelListing(
    String clubId,
    ClubSaleListingCancelRequest request,
  ) async {
    if (isCancellingListing) {
      return;
    }
    isCancellingListing = true;
    actionError = null;
    notifyListeners();
    try {
      publicListing = await _repository.cancelListing(clubId, request);
      await Future.wait<void>(<Future<void>>[
        loadPublicSnapshot(clubId),
        loadOwnerWorkspace(clubId),
      ]);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isCancellingListing = false;
      notifyListeners();
    }
  }

  Future<void> submitInquiry(
    String clubId,
    ClubSaleInquiryCreateRequest request,
  ) async {
    if (isSubmittingInquiry) {
      return;
    }
    isSubmittingInquiry = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.createInquiry(clubId, request);
      await Future.wait<void>(<Future<void>>[
        loadPublicSnapshot(clubId),
        loadHistory(clubId),
      ]);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isSubmittingInquiry = false;
      notifyListeners();
    }
  }

  Future<void> respondInquiry(
    String clubId,
    String inquiryId,
    ClubSaleInquiryRespondRequest request,
  ) async {
    if (isRespondingInquiry) {
      return;
    }
    isRespondingInquiry = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.respondInquiry(clubId, inquiryId, request);
      await loadOwnerWorkspace(clubId);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isRespondingInquiry = false;
      notifyListeners();
    }
  }

  Future<void> submitOffer(
    String clubId,
    ClubSaleOfferCreateRequest request,
  ) async {
    if (isSubmittingOffer) {
      return;
    }
    isSubmittingOffer = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.createOffer(clubId, request);
      await Future.wait<void>(<Future<void>>[
        loadPublicSnapshot(clubId),
        loadHistory(clubId),
        _reloadMyOffersSilently(),
      ]);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isSubmittingOffer = false;
      notifyListeners();
    }
  }

  Future<void> counterOffer(
    String clubId,
    String offerId,
    ClubSaleOfferCounterRequest request,
  ) async {
    if (isCounteringOffer) {
      return;
    }
    isCounteringOffer = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.counterOffer(clubId, offerId, request);
      await loadOwnerWorkspace(clubId);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isCounteringOffer = false;
      notifyListeners();
    }
  }

  Future<void> acceptOffer(
    String clubId,
    String offerId,
    ClubSaleOfferRespondRequest request,
  ) async {
    if (isAcceptingOffer) {
      return;
    }
    isAcceptingOffer = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.acceptOffer(clubId, offerId, request);
      await loadOwnerWorkspace(clubId);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isAcceptingOffer = false;
      notifyListeners();
    }
  }

  Future<void> rejectOffer(
    String clubId,
    String offerId,
    ClubSaleOfferRespondRequest request,
  ) async {
    if (isRejectingOffer) {
      return;
    }
    isRejectingOffer = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.rejectOffer(clubId, offerId, request);
      await loadOwnerWorkspace(clubId);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isRejectingOffer = false;
      notifyListeners();
    }
  }

  Future<void> executeTransfer(
    String clubId,
    ClubSaleTransferExecuteRequest request,
  ) async {
    if (isExecutingTransfer) {
      return;
    }
    isExecutingTransfer = true;
    actionError = null;
    notifyListeners();
    try {
      latestTransfer = await _repository.executeTransfer(clubId, request);
      await Future.wait<void>(<Future<void>>[
        loadPublicSnapshot(clubId),
        loadOwnerWorkspace(clubId),
        loadHistory(clubId),
      ]);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isExecutingTransfer = false;
      notifyListeners();
    }
  }
}
