import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/player_card_marketplace/data/player_card_marketplace_models.dart';
import 'package:gte_frontend/features/player_card_marketplace/data/player_card_marketplace_repository.dart';
import 'package:gte_frontend/features/player_card_marketplace/presentation/player_card_marketplace_controller.dart';
import 'package:gte_frontend/features/player_card_marketplace/presentation/player_card_marketplace_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('transfer market shows launch actions for signed-in managers', (
    WidgetTester tester,
  ) async {
    _setLargeViewport(tester);
    final PlayerCardMarketplaceController controller =
        PlayerCardMarketplaceController(
          repository: _FakePlayerCardMarketplaceRepository(
            marketSales: PlayerCardMarketplaceSearchResult.fromJson(
              <String, Object?>{
                'total': 1,
                'limit': 20,
                'offset': 0,
                'items': <Object?>[
                  <String, Object?>{
                    'listing_id': 'listing-sale-1',
                    'listing_type': 'sale',
                    'player_card_id': 'card-1',
                    'player_id': 'player-1',
                    'player_name': 'Victor Osimhen',
                    'listing_owner_user_id': 'seller-1',
                    'status': 'open',
                    'availability': 'available',
                    'is_negotiable': true,
                    'asset_origin': 'real_player',
                    'is_regen_newgen': false,
                    'is_creator_linked': false,
                    'available_quantity': 2,
                    'sale_price_credits': 84,
                    'average_rating': 86,
                    'tier_code': 'ST',
                    'tier_name': 'Elite Striker',
                    'rarity_rank': 5,
                    'edition_code': 'launch',
                    'club_name': 'Galatasaray',
                    'position': 'ST',
                    'image_url': 'https://example.test/players/osimhen.png',
                  },
                ],
              },
            ),
            marketLoans: PlayerCardMarketplaceSearchResult.fromJson(
              <String, Object?>{
                'total': 1,
                'limit': 20,
                'offset': 0,
                'items': <Object?>[
                  <String, Object?>{
                    'loan_listing_id': 'loan-listing-1',
                    'player_card_id': 'card-loan-1',
                    'player_id': 'player-loan-1',
                    'player_name': 'Amina Okoro',
                    'owner_user_id': 'seller-2',
                    'status': 'open',
                    'is_negotiable': true,
                    'total_slots': 1,
                    'available_slots': 1,
                    'loan_fee_credits': 18,
                    'duration_days': 7,
                    'tier_code': 'CM',
                    'tier_name': 'Regen Prospect',
                    'edition_code': 'launch',
                    'position': 'CM',
                    'portraitUrl': '/generated-media/regen.png',
                  },
                ],
              },
            ),
            inventory: <PlayerCardHolding>[
              PlayerCardHolding.fromJson(<String, Object?>{
                'holding_id': 'holding-1',
                'player_card_id': 'card-2',
                'player_id': 'player-2',
                'player_name': 'Bukayo Saka',
                'tier_code': 'RW',
                'tier_name': 'First Team',
                'edition_code': 'launch',
                'quantity_total': 2,
                'quantity_reserved': 0,
                'quantity_available': 2,
                'image_url': 'https://example.test/players/saka.png',
              }),
            ],
            myListings: <PlayerCardListing>[
              PlayerCardListing.fromJson(<String, Object?>{
                'listing_id': 'my-listing-1',
                'player_card_id': 'card-3',
                'player_id': 'player-3',
                'player_name': 'William Saliba',
                'tier_code': 'CB',
                'tier_name': 'First Team',
                'edition_code': 'launch',
                'seller_user_id': 'user-1',
                'quantity': 1,
                'price_per_card_credits': 96,
                'status': 'open',
                'image_url': 'https://example.test/players/saliba.png',
              }),
            ],
          ),
        );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: PlayerCardMarketplaceScreen(
          baseUrl: 'https://example.test',
          backendMode: GteBackendMode.fixture,
          accessToken: 'token-1',
          currentUserId: 'user-1',
          controller: controller,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Transfer desk'), findsWidgets);
    expect(
      find.text('Trade live player cards and move squad capital.'),
      findsOneWidget,
    );
    expect(find.text('Victor Osimhen'), findsOneWidget);
    expect(find.widgetWithText(OutlinedButton, 'View Player'), findsOneWidget);
    expect(find.text('Buy Now'), findsOneWidget);
    expect(find.text('Refresh desk'), findsOneWidget);
    expect(find.text('Loan contracts'), findsNothing);
    expect(find.text('Watchlist is empty'), findsNothing);

    await tester.tap(find.text('Loan Market'));
    await tester.pumpAndSettle();
    expect(find.text('Amina Okoro'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Make Bid'), findsOneWidget);

    await tester.tap(find.text('Squad'));
    await tester.pumpAndSettle();
    expect(find.text('Bukayo Saka'), findsOneWidget);
    expect(find.text('List for Transfer'), findsOneWidget);
    expect(find.text('List for Loan'), findsOneWidget);

    await tester.tap(find.text('My Listings'));
    await tester.pumpAndSettle();
    expect(find.text('William Saliba'), findsOneWidget);
    expect(find.text('Remove Listing'), findsOneWidget);
  });

  testWidgets(
    'transfer market still renders public listings when authed support calls fail',
    (WidgetTester tester) async {
      _setLargeViewport(tester);
      final PlayerCardMarketplaceController controller =
          PlayerCardMarketplaceController(
            repository: _FakePlayerCardMarketplaceRepository(
              inventoryError: StateError('Inventory timed out.'),
              marketSales: PlayerCardMarketplaceSearchResult.fromJson(
                <String, Object?>{
                  'total': 1,
                  'limit': 20,
                  'offset': 0,
                  'items': <Object?>[
                    <String, Object?>{
                      'listing_id': 'listing-sale-3',
                      'listing_type': 'sale',
                      'player_card_id': 'card-6',
                      'player_id': 'player-6',
                      'player_name': 'Victor Boniface',
                      'listing_owner_user_id': 'seller-8',
                      'status': 'open',
                      'availability': 'available',
                      'is_negotiable': true,
                      'asset_origin': 'real_player',
                      'is_regen_newgen': false,
                      'is_creator_linked': false,
                      'available_quantity': 1,
                      'sale_price_credits': 72,
                      'average_rating': 82,
                      'tier_code': 'ST',
                      'tier_name': 'First Team',
                      'rarity_rank': 4,
                      'edition_code': 'launch',
                      'club_name': 'Leverkusen',
                      'position': 'ST',
                    },
                  ],
                },
              ),
            ),
          );

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: PlayerCardMarketplaceScreen(
            baseUrl: 'https://example.test',
            backendMode: GteBackendMode.fixture,
            accessToken: 'token-1',
            currentUserId: 'user-1',
            controller: controller,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Victor Boniface'), findsOneWidget);
      expect(find.text('Buy Now'), findsOneWidget);
      expect(find.textContaining('Inventory timed out'), findsNothing);
    },
  );

  testWidgets(
    'transfer market preview keeps sign-in gates on squad and listing tabs',
    (WidgetTester tester) async {
      _setLargeViewport(tester);
      bool openedLogin = false;
      final PlayerCardMarketplaceController controller =
          PlayerCardMarketplaceController(
            repository: _FakePlayerCardMarketplaceRepository(
              marketSales: PlayerCardMarketplaceSearchResult.fromJson(
                <String, Object?>{
                  'total': 1,
                  'limit': 20,
                  'offset': 0,
                  'items': <Object?>[
                    <String, Object?>{
                      'listing_id': 'listing-sale-2',
                      'listing_type': 'sale',
                      'player_card_id': 'card-4',
                      'player_id': 'player-4',
                      'player_name': 'Jude Bellingham',
                      'listing_owner_user_id': 'seller-2',
                      'status': 'open',
                      'availability': 'available',
                      'is_negotiable': false,
                      'asset_origin': 'real_player',
                      'is_regen_newgen': false,
                      'is_creator_linked': false,
                      'available_quantity': 1,
                      'sale_price_credits': 110,
                      'average_rating': 90,
                      'tier_code': 'CM',
                      'tier_name': 'Galactico',
                      'rarity_rank': 5,
                      'edition_code': 'launch',
                      'club_name': 'Real Madrid',
                      'position': 'CM',
                    },
                  ],
                },
              ),
            ),
          );

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: PlayerCardMarketplaceScreen(
            baseUrl: 'https://example.test',
            backendMode: GteBackendMode.fixture,
            controller: controller,
            onOpenLogin: () {
              openedLogin = true;
            },
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Jude Bellingham'), findsOneWidget);
      expect(find.widgetWithText(FilledButton, 'Sign in'), findsOneWidget);

      await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
      await tester.pumpAndSettle();
      expect(openedLogin, isTrue);

      await tester.tap(find.text('Squad'));
      await tester.pumpAndSettle();
      expect(find.text('Sign in required'), findsOneWidget);
      expect(
        find.text('Sign in to list players from your own squad.'),
        findsOneWidget,
      );

      await tester.tap(find.text('My Listings'));
      await tester.pumpAndSettle();
      expect(
        find.text('Sign in to manage your Transfer Market listings.'),
        findsOneWidget,
      );
    },
  );
}

class _FakePlayerCardMarketplaceRepository
    implements PlayerCardMarketplaceRepository {
  _FakePlayerCardMarketplaceRepository({
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

void _setLargeViewport(WidgetTester tester) {
  tester.view.physicalSize = const Size(1400, 2000);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}
