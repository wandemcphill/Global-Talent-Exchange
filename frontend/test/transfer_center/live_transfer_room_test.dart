import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/features/club_redesign/models/gtex_club_redesign_models.dart';
import 'package:gte_frontend/features/shared/data/gte_feature_support.dart';
import 'package:gte_frontend/features/transfer_center/live_transfer_center_provider.dart';
import 'package:gte_frontend/features/transfer_center/presentation/gtex_live_transfer_room.dart';

class _RecordingTransferApi extends TransferCenterApi {
  _RecordingTransferApi()
    : super(
        client: GteAuthedApi(
          config: const GteRepositoryConfig(baseUrl: 'http://127.0.0.1'),
          transport: GteHttpTransport(),
          mode: GteBackendMode.live,
        ),
      );

  String? listedPlayerId;
  double? listedPrice;

  @override
  Future<List<TransferCenterListingRecord>> listListings({
    String? status,
    String? playerId,
    String? query,
    int? minGsi,
    int? maxGsi,
    bool publicBoard = false,
    String? clubId,
  }) async {
    return const <TransferCenterListingRecord>[];
  }

  @override
  Future<JsonMap> createListing({
    required String playerId,
    required String sellingClubId,
    required double basePrice,
    required DateTime expiresAt,
    String visibility = 'public',
    double? salaryAmount,
    double? contractYears,
  }) async {
    listedPlayerId = playerId;
    listedPrice = basePrice;
    return <String, Object?>{'id': 'listing-1'};
  }
}

void main() {
  testWidgets('list for sale posts the chosen squad player', (WidgetTester tester) async {
    final _RecordingTransferApi api = _RecordingTransferApi();
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: GtexLiveTransferRoom(
            clubId: 'club-alpha',
            squad: const <GtexClubMember>[
              GtexClubMember(
                id: 'player-kane',
                name: 'Harry Kane',
                position: 'ST',
                nationality: 'ENG',
                valueCredits: 1000,
                rating: 91,
              ),
            ],
            baseUrl: 'http://127.0.0.1',
            backendMode: GteBackendMode.live,
            api: api,
          ),
        ),
      ),
    );
    await tester.pump();

    await tester.tap(find.byKey(const Key('gtex-list-for-sale')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('gtex-list-player-price')), '2500');
    await tester.tap(find.byKey(const Key('gtex-list-player-submit')));
    await tester.pumpAndSettle();

    expect(api.listedPlayerId, 'player-kane');
    expect(api.listedPrice, 2500);
  });
}
