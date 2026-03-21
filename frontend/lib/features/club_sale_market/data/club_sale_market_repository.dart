import '../../../data/gte_api_repository.dart';
import '../../../data/gte_authed_api.dart';
import '../../shared/data/gte_feature_support.dart';
import 'club_sale_market_models.dart';

part 'club_sale_market_fixture_repository.dart';

abstract class ClubSaleMarketRepository {
  Future<ClubSaleValuation> fetchValuation(String clubId);

  Future<ClubSaleListingCollection> listPublicListings(
      ClubSaleListingsQuery query);

  Future<ClubSaleListing?> fetchPublicListing(String clubId);

  Future<ClubSaleListing> createListing(
    String clubId,
    ClubSaleListingUpsertRequest request,
  );

  Future<ClubSaleListing> updateListing(
    String clubId,
    ClubSaleListingUpsertRequest request,
  );

  Future<ClubSaleListing> cancelListing(
    String clubId,
    ClubSaleListingCancelRequest request,
  );

  Future<ClubSaleListingCollection> listMyListings();

  Future<ClubSaleInquiry> createInquiry(
    String clubId,
    ClubSaleInquiryCreateRequest request,
  );

  Future<ClubSaleInquiryCollection> listInquiries(String clubId);

  Future<ClubSaleInquiry> respondInquiry(
    String clubId,
    String inquiryId,
    ClubSaleInquiryRespondRequest request,
  );

  Future<ClubSaleOffer> createOffer(
    String clubId,
    ClubSaleOfferCreateRequest request,
  );

  Future<ClubSaleOfferCollection> listOffers(String clubId);

  Future<ClubSaleOfferCollection> listMyOffers();

  Future<ClubSaleOffer> counterOffer(
    String clubId,
    String offerId,
    ClubSaleOfferCounterRequest request,
  );

  Future<ClubSaleOffer> acceptOffer(
    String clubId,
    String offerId,
    ClubSaleOfferRespondRequest request,
  );

  Future<ClubSaleOffer> rejectOffer(
    String clubId,
    String offerId,
    ClubSaleOfferRespondRequest request,
  );

  Future<ClubSaleTransferExecution> executeTransfer(
    String clubId,
    ClubSaleTransferExecuteRequest request,
  );

  Future<ClubSaleHistory> fetchHistory(
    String clubId,
    ClubSaleHistoryQuery query,
  );
}

class ClubSaleMarketApiRepository implements ClubSaleMarketRepository {
  ClubSaleMarketApiRepository({
    required GteAuthedApi client,
    ClubSaleMarketRepository? fixtures,
  })  : _client = client,
        _fixtures = fixtures ?? ClubSaleMarketFixtureRepository();

  factory ClubSaleMarketApiRepository.standard({
    required String baseUrl,
    required GteBackendMode mode,
    required String? accessToken,
  }) {
    return ClubSaleMarketApiRepository(
      client: createFeatureApi(
        baseUrl: baseUrl,
        mode: mode,
        accessToken: accessToken,
      ),
    );
  }

  final GteAuthedApi _client;
  final ClubSaleMarketRepository _fixtures;

  @override
  Future<ClubSaleValuation> fetchValuation(String clubId) {
    return _withFallback<ClubSaleValuation>(
      () async => ClubSaleValuation.fromJson(
        await _client.getMap('/api/clubs/$clubId/valuation', auth: false),
      ),
      () => _fixtures.fetchValuation(clubId),
    );
  }

  @override
  Future<ClubSaleListingCollection> listPublicListings(
    ClubSaleListingsQuery query,
  ) {
    return _withFallback<ClubSaleListingCollection>(
      () async => ClubSaleListingCollection.fromJson(
        await _client.getMap(
          '/api/clubs/sale-market/listings',
          query: query.toQuery(),
          auth: false,
        ),
      ),
      () => _fixtures.listPublicListings(query),
    );
  }

  @override
  Future<ClubSaleListing?> fetchPublicListing(String clubId) {
    return _withFallback<ClubSaleListing?>(
      () async {
        try {
          return ClubSaleListing.fromJson(
            await _client.getMap('/api/clubs/$clubId/sale-market', auth: false),
          );
        } on GteApiException catch (error) {
          if (error.type == GteApiErrorType.notFound) {
            return null;
          }
          rethrow;
        }
      },
      () => _fixtures.fetchPublicListing(clubId),
    );
  }

  @override
  Future<ClubSaleListing> createListing(
    String clubId,
    ClubSaleListingUpsertRequest request,
  ) {
    return _withFallback<ClubSaleListing>(
      () async => ClubSaleListing.fromJson(
        await _client.request(
          'POST',
          '/api/clubs/$clubId/sale-market/listing',
          body: request.toJson(),
        ),
      ),
      () => _fixtures.createListing(clubId, request),
    );
  }

  @override
  Future<ClubSaleListing> updateListing(
    String clubId,
    ClubSaleListingUpsertRequest request,
  ) {
    return _withFallback<ClubSaleListing>(
      () async => ClubSaleListing.fromJson(
        await _client.request(
          'PUT',
          '/api/clubs/$clubId/sale-market/listing',
          body: request.toJson(),
        ),
      ),
      () => _fixtures.updateListing(clubId, request),
    );
  }

  @override
  Future<ClubSaleListing> cancelListing(
    String clubId,
    ClubSaleListingCancelRequest request,
  ) {
    return _withFallback<ClubSaleListing>(
      () async => ClubSaleListing.fromJson(
        await _client.request(
          'POST',
          '/api/clubs/$clubId/sale-market/listing/cancel',
          body: request.toJson(),
        ),
      ),
      () => _fixtures.cancelListing(clubId, request),
    );
  }

  @override
  Future<ClubSaleListingCollection> listMyListings() {
    return _withFallback<ClubSaleListingCollection>(
      () async => ClubSaleListingCollection.fromJson(
        await _client.getMap('/api/me/clubs/sale-market/listings'),
      ),
      _fixtures.listMyListings,
    );
  }

  @override
  Future<ClubSaleInquiry> createInquiry(
    String clubId,
    ClubSaleInquiryCreateRequest request,
  ) {
    return _withFallback<ClubSaleInquiry>(
      () async => ClubSaleInquiry.fromJson(
        await _client.request(
          'POST',
          '/api/clubs/$clubId/sale-market/inquiries',
          body: request.toJson(),
        ),
      ),
      () => _fixtures.createInquiry(clubId, request),
    );
  }

  @override
  Future<ClubSaleInquiryCollection> listInquiries(String clubId) {
    return _withFallback<ClubSaleInquiryCollection>(
      () async => ClubSaleInquiryCollection.fromJson(
        await _client.getMap('/api/clubs/$clubId/sale-market/inquiries'),
      ),
      () => _fixtures.listInquiries(clubId),
    );
  }

  @override
  Future<ClubSaleInquiry> respondInquiry(
    String clubId,
    String inquiryId,
    ClubSaleInquiryRespondRequest request,
  ) {
    return _withFallback<ClubSaleInquiry>(
      () async => ClubSaleInquiry.fromJson(
        await _client.request(
          'POST',
          '/api/clubs/$clubId/sale-market/inquiries/$inquiryId/respond',
          body: request.toJson(),
        ),
      ),
      () => _fixtures.respondInquiry(clubId, inquiryId, request),
    );
  }

  @override
  Future<ClubSaleOffer> createOffer(
    String clubId,
    ClubSaleOfferCreateRequest request,
  ) {
    return _withFallback<ClubSaleOffer>(
      () async => ClubSaleOffer.fromJson(
        await _client.request(
          'POST',
          '/api/clubs/$clubId/sale-market/offers',
          body: request.toJson(),
        ),
      ),
      () => _fixtures.createOffer(clubId, request),
    );
  }

  @override
  Future<ClubSaleOfferCollection> listOffers(String clubId) {
    return _withFallback<ClubSaleOfferCollection>(
      () async => ClubSaleOfferCollection.fromJson(
        await _client.getMap('/api/clubs/$clubId/sale-market/offers'),
      ),
      () => _fixtures.listOffers(clubId),
    );
  }

  @override
  Future<ClubSaleOfferCollection> listMyOffers() {
    return _withFallback<ClubSaleOfferCollection>(
      () async => ClubSaleOfferCollection.fromJson(
        await _client.getMap('/api/me/clubs/sale-market/offers'),
      ),
      _fixtures.listMyOffers,
    );
  }

  @override
  Future<ClubSaleOffer> counterOffer(
    String clubId,
    String offerId,
    ClubSaleOfferCounterRequest request,
  ) {
    return _withFallback<ClubSaleOffer>(
      () async => ClubSaleOffer.fromJson(
        await _client.request(
          'POST',
          '/api/clubs/$clubId/sale-market/offers/$offerId/counter',
          body: request.toJson(),
        ),
      ),
      () => _fixtures.counterOffer(clubId, offerId, request),
    );
  }

  @override
  Future<ClubSaleOffer> acceptOffer(
    String clubId,
    String offerId,
    ClubSaleOfferRespondRequest request,
  ) {
    return _withFallback<ClubSaleOffer>(
      () async => ClubSaleOffer.fromJson(
        await _client.request(
          'POST',
          '/api/clubs/$clubId/sale-market/offers/$offerId/accept',
          body: request.toJson(),
        ),
      ),
      () => _fixtures.acceptOffer(clubId, offerId, request),
    );
  }

  @override
  Future<ClubSaleOffer> rejectOffer(
    String clubId,
    String offerId,
    ClubSaleOfferRespondRequest request,
  ) {
    return _withFallback<ClubSaleOffer>(
      () async => ClubSaleOffer.fromJson(
        await _client.request(
          'POST',
          '/api/clubs/$clubId/sale-market/offers/$offerId/reject',
          body: request.toJson(),
        ),
      ),
      () => _fixtures.rejectOffer(clubId, offerId, request),
    );
  }

  @override
  Future<ClubSaleTransferExecution> executeTransfer(
    String clubId,
    ClubSaleTransferExecuteRequest request,
  ) {
    return _withFallback<ClubSaleTransferExecution>(
      () async => ClubSaleTransferExecution.fromJson(
        await _client.request(
          'POST',
          '/api/clubs/$clubId/sale-market/transfer',
          body: request.toJson(),
        ),
      ),
      () => _fixtures.executeTransfer(clubId, request),
    );
  }

  @override
  Future<ClubSaleHistory> fetchHistory(
    String clubId,
    ClubSaleHistoryQuery query,
  ) {
    return _withFallback<ClubSaleHistory>(
      () async => ClubSaleHistory.fromJson(
        await _client.getMap(
          '/api/clubs/$clubId/sale-market/history',
          query: query.toQuery(),
        ),
      ),
      () => _fixtures.fetchHistory(clubId, query),
    );
  }

  Future<T> _withFallback<T>(
    Future<T> Function() live,
    Future<T> Function() fixture,
  ) async {
    if (_client.mode == GteBackendMode.fixture) {
      return fixture();
    }
    try {
      return await live();
    } catch (error) {
      if (_client.mode == GteBackendMode.liveThenFixture &&
          ((error is GteApiException && error.supportsFixtureFallback) ||
              error is! GteApiException)) {
        return fixture();
      }
      rethrow;
    }
  }
}
