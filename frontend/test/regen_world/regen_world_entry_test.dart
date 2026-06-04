import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/regen_world/regen_world.dart';
import 'package:gte_frontend/models/regen_creation_models.dart';
import 'package:gte_frontend/models/regen_universe_models.dart';
import 'package:gte_frontend/shared/providers/regen_provider.dart';

void main() {
  test('maps backend regen facts without filling unpublished truth', () {
    final List<RegenWorldEntry> entries = buildRegenWorldEntries(
      _hubData(
        nationalRegens: <NationalRegenSeed>[
          const NationalRegenSeed(
            id: 'kwame',
            seedKey: 'seed:gh:kwame',
            displayName: 'Kwame Jr.',
            age: 17,
            countryCode: 'GH',
            countryName: 'Ghana',
            seedType: 'national_seed',
            primaryPosition: 'CAM',
            generationIndex: 2,
            currentRating: 72,
            potentialRating: 82,
            growthCurve: 0.76,
            personalitySeed: <String, Object?>{
              'traits': <String>['Ghost Goal', 'Dribbler'],
              'lineage': <String>['Kwame Sr.', 'Kwame Jr.'],
            },
            rarityTier: 'rare',
            metadata: <String, Object?>{
              'projected_value_coin': 1800000,
              'dna': <String, Object?>{'PAC': 84, 'SHO': 78},
            },
          ),
        ],
      ),
    );

    expect(entries, hasLength(1));
    final RegenWorldEntry entry = entries.single;
    expect(entry.name, 'Kwame Jr.');
    expect(entry.generationDisplay, 'GEN-2');
    expect(entry.projectedValueLabel, 'GTC 1.8M');
    expect(entry.traits, contains('Ghost Goal'));
    expect(entry.lineage, containsAll(<String>['Kwame Sr.', 'Kwame Jr.']));
    expect(entry.dnaProfile?.valueFor('PAC'), 84);
    expect(entry.dnaProfile?.valueFor('PAS'), isNull);
    expect(entry.hasMarketAccessTruth, isTrue);
    expect(entry.marketAccessDisplay, 'National pool only');
    expect(entry.truthState, RegenWorldTruthState.degraded);
    expect(entry.missingFields, contains('origin story'));
    expect(entry.missingFields.join(' '), contains('DNA PAS/DRI/DEF/PHY'));
  });

  test(
    'marks records blocked when core backend identity fields are absent',
    () {
      final List<RegenWorldEntry> entries = buildRegenWorldEntries(
        _hubData(
          risingStars: const <RegenRisingStar>[
            RegenRisingStar(
              playerId: 'blocked-1',
              player: RegenUniversePlayer(
                id: 'blocked-1',
                name: 'Backend Pending Prospect',
                age: 18,
                nationality: '',
                nationalityCode: null,
                position: '',
                potential: 0,
                currentRating: 0,
                growthCurve: 0.1,
                sourceType: 'generated',
              ),
              momentumLabel: 'Pending sync',
              storySnippet: null,
              badges: <String>[],
              marketValueCoin: null,
            ),
          ],
        ),
      );

      final RegenWorldEntry entry = entries.single;
      expect(entry.truthState, RegenWorldTruthState.blocked);
      expect(
        entry.blockingMissingFields,
        containsAll(<String>[
          'position',
          'potential',
          'current rating',
          'nationality',
        ]),
      );
      expect(entry.positionDisplay, 'Position not published');
      expect(entry.nationalityDisplay, 'Nationality not published');
    },
  );

  test('does not treat origin labels as backend origin stories', () {
    final List<RegenWorldEntry> entries = buildRegenWorldEntries(
      _hubData(
        risingStars: const <RegenRisingStar>[
          RegenRisingStar(
            playerId: 'origin-label-only',
            player: RegenUniversePlayer(
              id: 'origin-label-only',
              name: 'Origin Label Only',
              age: 18,
              nationality: 'Ghana',
              nationalityCode: 'GH',
              position: 'CAM',
              potential: 84,
              currentRating: 69,
              growthCurve: 0.7,
              sourceType: 'generated',
            ),
            momentumLabel: 'Awaiting backend story',
            storySnippet: null,
            badges: <String>[],
            marketValueCoin: 900000,
            details: RegenWorldDetails(
              key: 'origin-label-only',
              name: 'Origin Label Only',
              nationality: 'Ghana',
              nationalityCode: 'GH',
              position: 'CAM',
              age: 18,
              currentRating: 69,
              potentialRating: 84,
              generationLabel: 'GEN-2',
              originLabel: 'Accra Academy',
              projectedValueCoin: 900000,
              rarityLabel: 'rare',
              lineage: <String>['Accra Line'],
              traits: <String>['Tempo Carrier'],
              dna: <String, double>{
                'PAC': 82,
                'SHO': 71,
                'PAS': 75,
                'DRI': 83,
                'DEF': 44,
                'PHY': 70,
              },
            ),
          ),
        ],
      ),
    );

    final RegenWorldEntry entry = entries.single;
    expect(entry.originDisplay, 'Origin: Accra Academy');
    expect(entry.missingFields, contains('origin story'));
    expect(entry.truthState, RegenWorldTruthState.degraded);
  });

  test('propagates parsed backend market access into Regen World entries', () {
    final RegenUniversePlayer player = RegenUniversePlayer.fromJson(
      const <String, Object?>{
        'id': 'market-1',
        'name': 'Market Linked Prospect',
        'age': 18,
        'nationality': 'Nigeria',
        'nationality_code': 'NG',
        'position': 'CM',
        'potential': 86,
        'current_rating': 72,
        'growth_curve': 0.72,
        'source_type': 'generated',
        'club_id': 'club-1',
        'market_access': <String, Object?>{
          'market_eligible': true,
          'share_market_eligible': true,
          'tradable': true,
          'buyable': true,
          'transferable': false,
          'card_mint_eligible': false,
          'buy_cta_allowed': false,
        },
      },
    );
    final List<RegenWorldEntry> entries = buildRegenWorldEntries(
      _hubData(
        risingStars: <RegenRisingStar>[
          RegenRisingStar(
            playerId: 'market-1',
            player: player,
            momentumLabel: 'Backend market payload',
            storySnippet: null,
            badges: const <String>['Scouting Pulse'],
            marketValueCoin: 1400000,
            details: const RegenWorldDetails(
              key: 'market-1',
              name: 'Market Linked Prospect',
              nationality: 'Nigeria',
              nationalityCode: 'NG',
              position: 'CM',
              age: 18,
              currentRating: 72,
              potentialRating: 86,
              generationLabel: 'GEN-2',
              originStory: 'Built through a live academy progression feed.',
              projectedValueCoin: 1400000,
              rarityLabel: 'rare',
              lineage: <String>['Academy Line', 'Market Linked Prospect'],
              traits: <String>['Tempo Setter'],
              dna: <String, double>{
                'PAC': 76,
                'SHO': 68,
                'PAS': 84,
                'DRI': 80,
                'DEF': 64,
                'PHY': 73,
              },
            ),
          ),
        ],
      ),
    );

    final RegenWorldEntry entry = entries.single;
    expect(entry.hasMarketAccessTruth, isTrue);
    expect(entry.marketAccess?.buyCtaAllowed, isFalse);
    expect(entry.marketAccess?.transferable, isFalse);
    expect(entry.marketAccessDisplay, 'Dossier access published');
    expect(entry.canViewDossier, isTrue);
    expect(entry.canViewTimeline, isTrue);
    expect(entry.canUseWatchlist, isTrue);
    expect(entry.marketAccessSummary, contains('buy CTAs remain hidden'));
    expect(entry.missingFields, isNot(contains('market access')));
    expect(entry.truthState, RegenWorldTruthState.complete);
  });

  test('maps generated requested sons from backend creation truth', () {
    final DateTime generatedAt = DateTime.utc(2026, 5, 30, 12);
    final List<RegenWorldEntry> entries = buildRegenWorldEntries(
      _hubData(
        creationOrders: <RegenCreationOrder>[
          RegenCreationOrder(
            id: 'order-ayo',
            userId: 'owner-1',
            requestType: 'son',
            amountCoin: 50,
            currency: 'GTC',
            paymentMethod: 'wallet',
            status: 'generated',
            generatedPlayerId: 'player-ayo',
            generatedRegenProfileId: 'regen-ayo',
            createdAt: generatedAt,
            updatedAt: generatedAt,
            generatedAt: generatedAt,
            generatedPlayer: const RegenCreationGeneratedPlayer(
              playerId: 'player-ayo',
              regenProfileId: 'regen-ayo',
              fullName: 'Ayo Adeyemi',
              age: 16,
              position: 'ST',
              countryCode: 'NG',
              countryName: 'Nigeria',
              currentRating: 68,
              potentialRating: 88,
              generationNumber: 2,
              generationLabel: 'GEN-2',
              traits: <String>[
                'line breaker',
                'press resistant',
                'late runner',
              ],
              lineage: <String>['Samuel Adeyemi', 'Ayo Adeyemi'],
              dnaProfile: RegenDnaProfile(
                ratings: <String, int>{
                  'PAC': 86,
                  'SHO': 74,
                  'PAS': 70,
                  'DRI': 81,
                  'DEF': 39,
                  'PHY': 76,
                },
              ),
              originStory: 'Born from a Lagos academy bloodline.',
              projectedValueCoin: 2500000,
              rarityTier: 'rare',
            ),
          ),
        ],
      ),
    );

    expect(entries, hasLength(1));
    final RegenWorldEntry entry = entries.single;
    expect(entry.name, 'Ayo Adeyemi');
    expect(entry.generationDisplay, 'GEN-2');
    expect(entry.projectedValueLabel, 'GTC 2.5M');
    expect(entry.traits, containsAll(<String>['line breaker', 'late runner']));
    expect(
      entry.lineage,
      containsAll(<String>['Samuel Adeyemi', 'Ayo Adeyemi']),
    );
    expect(entry.dnaProfile?.valueFor('PAC'), 86);
    expect(entry.dnaProfile?.valueFor('PHY'), 76);
    expect(
      entry.badges,
      containsAll(<String>['Requested Son', 'Bloodline Regen']),
    );
    expect(entry.hasMarketAccessTruth, isFalse);
    expect(entry.missingFields, contains('market access'));
    expect(entry.truthState, RegenWorldTruthState.degraded);
  });
}

RegenUniverseHubData _hubData({
  List<RegenRisingStar> risingStars = const <RegenRisingStar>[],
  List<NationalRegenSeed> nationalRegens = const <NationalRegenSeed>[],
  List<RegenCreationOrder> creationOrders = const <RegenCreationOrder>[],
}) {
  return RegenUniverseHubData(
    risingStars: risingStars,
    awards: const <RegenAwardResult>[],
    nationalRegens: nationalRegens,
    scoutingFeed: const <RegenScoutingFeedItem>[],
    bloodlines: const <RegenBloodlineChain>[],
    tracking: const RegenGenerationTracking(
      totalSeededPlayers: 0,
      seedTypes: <RegenGenerationTrackingEntry>[],
      rarityBreakdown: <RegenGenerationTrackingEntry>[],
      countryDistribution: <RegenGenerationTrackingEntry>[],
      globalPeakRating: 0,
      trackedAchievements: <String>[],
    ),
    creationOrders: creationOrders,
  );
}
