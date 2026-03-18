import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/club_sale_market/data/club_sale_market_models.dart';
import 'package:gte_frontend/features/club_sale_market/data/club_sale_market_repository.dart';
import 'package:gte_frontend/features/club_sale_market/presentation/club_sale_market_controller.dart';

void main() {
  test('fixture mode loads owner offers and sale history', () async {
    final ClubSaleMarketController controller =
        ClubSaleMarketController.standard(
      baseUrl: 'http://127.0.0.1:8000',
      backendMode: GteBackendMode.fixture,
      accessToken: 'token-123',
    );

    await controller.loadPublicSnapshot('royal-lagos-fc');
    await controller.loadOwnerWorkspace('royal-lagos-fc');
    await controller.loadHistory('royal-lagos-fc');

    expect(controller.publicError, isNull);
    expect(controller.ownerError, isNull);
    expect(controller.historyError, isNull);
    expect(controller.valuation, isNotNull);
    expect(controller.publicListing, isNotNull);
    expect(controller.clubOffers.items, isNotEmpty);
    expect(controller.clubOffers.items.first.isOpen, isTrue);
    expect(controller.isHistoryVisibilityRestricted, isFalse);
    expect(controller.history?.transfers, isNotEmpty);
  });

  test('unauthorized history keeps the visibility-restricted state', () async {
    final ClubSaleMarketController controller = ClubSaleMarketController(
      repository: _UnauthorizedHistoryRepository(),
    );

    await controller.loadHistory('royal-lagos-fc');

    expect(controller.history, isNull);
    expect(controller.latestTransfer, isNull);
    expect(controller.historyError, isNull);
    expect(controller.isHistoryVisibilityRestricted, isTrue);
  });
}

class _UnauthorizedHistoryRepository implements ClubSaleMarketRepository {
  @override
  Future<ClubSaleOffer> acceptOffer(
    String clubId,
    String offerId,
    ClubSaleOfferRespondRequest request,
  ) {
    throw UnimplementedError();
  }

  @override
  Future<ClubSaleListing> cancelListing(
    String clubId,
    ClubSaleListingCancelRequest request,
  ) {
    throw UnimplementedError();
  }

  @override
  Future<ClubSaleOffer> counterOffer(
    String clubId,
    String offerId,
    ClubSaleOfferCounterRequest request,
  ) {
    throw UnimplementedError();
  }

  @override
  Future<ClubSaleInquiry> createInquiry(
    String clubId,
    ClubSaleInquiryCreateRequest request,
  ) {
    throw UnimplementedError();
  }

  @override
  Future<ClubSaleListing> createListing(
    String clubId,
    ClubSaleListingUpsertRequest request,
  ) {
    throw UnimplementedError();
  }

  @override
  Future<ClubSaleOffer> createOffer(
    String clubId,
    ClubSaleOfferCreateRequest request,
  ) {
    throw UnimplementedError();
  }

  @override
  Future<ClubSaleTransferExecution> executeTransfer(
    String clubId,
    ClubSaleTransferExecuteRequest request,
  ) {
    throw UnimplementedError();
  }

  @override
  Future<ClubSaleHistory> fetchHistory(
    String clubId,
    ClubSaleHistoryQuery query,
  ) {
    throw const GteApiException(
      type: GteApiErrorType.unauthorized,
      message: 'Forbidden.',
      statusCode: 403,
    );
  }

  @override
  Future<ClubSaleListing?> fetchPublicListing(String clubId) {
    throw UnimplementedError();
  }

  @override
  Future<ClubSaleValuation> fetchValuation(String clubId) {
    throw UnimplementedError();
  }

  @override
  Future<ClubSaleInquiryCollection> listInquiries(String clubId) {
    throw UnimplementedError();
  }

  @override
  Future<ClubSaleOfferCollection> listMyOffers() {
    throw UnimplementedError();
  }

  @override
  Future<ClubSaleListingCollection> listMyListings() {
    throw UnimplementedError();
  }

  @override
  Future<ClubSaleOfferCollection> listOffers(String clubId) {
    throw UnimplementedError();
  }

  @override
  Future<ClubSaleListingCollection> listPublicListings(
    ClubSaleListingsQuery query,
  ) {
    throw UnimplementedError();
  }

  @override
  Future<ClubSaleOffer> rejectOffer(
    String clubId,
    String offerId,
    ClubSaleOfferRespondRequest request,
  ) {
    throw UnimplementedError();
  }

  @override
  Future<ClubSaleInquiry> respondInquiry(
    String clubId,
    String inquiryId,
    ClubSaleInquiryRespondRequest request,
  ) {
    throw UnimplementedError();
  }

  @override
  Future<ClubSaleListing> updateListing(
    String clubId,
    ClubSaleListingUpsertRequest request,
  ) {
    throw UnimplementedError();
  }
}
