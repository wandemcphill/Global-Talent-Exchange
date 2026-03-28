import '../../../data/gte_api_repository.dart';
import '../../../data/gte_authed_api.dart';
import '../../../data/gte_http_transport.dart';
import '../../shared/data/gte_feature_support.dart';
import 'viral_feed_models.dart';

abstract class ViralFeedRepository {
  Future<ViralFeedDeck> fetchDeck({int limit = 10});
}

class ViralFeedApiRepository implements ViralFeedRepository {
  ViralFeedApiRepository({
    required GteAuthedApi client,
    required _ViralFeedFixtures fixtures,
  }) : _client = client,
       _fixtures = fixtures;

  factory ViralFeedApiRepository.standard() {
    return ViralFeedApiRepository(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: _apiBaseUrl, mode: _backendMode),
        transport: GteHttpTransport(),
        mode: _backendMode,
      ),
      fixtures: _ViralFeedFixtures.seed(),
    );
  }

  factory ViralFeedApiRepository.fixture() {
    return ViralFeedApiRepository(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        mode: GteBackendMode.fixture,
      ),
      fixtures: _ViralFeedFixtures.seed(),
    );
  }

  final GteAuthedApi _client;
  final _ViralFeedFixtures _fixtures;

  @override
  Future<ViralFeedDeck> fetchDeck({int limit = 10}) async {
    final List<ViralClip> clips = await _client.withFallback<List<ViralClip>>(
      () async {
        final JsonMap payload = await _client.getMap(
          '/viral/feed',
          query: <String, Object?>{'limit': limit},
          auth: false,
        );
        return parseList(
          payload['clips'],
          ViralClip.fromJson,
          label: 'viral feed clips',
        );
      },
      () async {
        final ViralFeedDeck deck = await _fixtures.deck();
        return deck.clips;
      },
    );
    final Map<String, PunditDebate> debatesByMatch = <String, PunditDebate>{};
    for (final String matchId in clips
        .map((ViralClip clip) => clip.matchId)
        .toSet()
        .take(4)) {
      debatesByMatch[matchId] = await _client.withFallback<PunditDebate>(
        () async => PunditDebate.fromJson(
          await _client.getMap('/pundits/matches/$matchId', auth: false),
        ),
        () async => _fixtures.debate(matchId),
      );
    }
    return ViralFeedDeck(clips: clips, debatesByMatch: debatesByMatch);
  }
}

class _ViralFeedFixtures {
  _ViralFeedFixtures(this._clips, this._debates);

  final List<ViralClip> _clips;
  final Map<String, PunditDebate> _debates;

  static _ViralFeedFixtures seed() {
    const ViralClip first = ViralClip(
      matchId: 'match-lagos-derby',
      highlightId: 'clip-001',
      title: 'Lagos late winner',
      eventType: 'goal',
      minute: 89,
      viralScore: 92,
      rankingScore: 89.4,
      caption: ViralCaption(
        hook: "89' and the whole match flipped 😳🔥",
        caption: 'Ayo Okafor hit the winner and the crowd lost its mind.',
        cta: 'Share to WhatsApp',
        hashtags: <String>['#GTEX', '#LagosDerby', '#LateDrama'],
      ),
      tags: <String>['goal', 'winner', 'comeback'],
      teamName: 'Royal Lagos FC',
      playerName: 'Ayo Okafor',
      scorelineLabel: '2-1',
      shareChannel: 'whatsapp',
    );
    const ViralClip second = ViralClip(
      matchId: 'match-keeper-night',
      highlightId: 'clip-002',
      title: 'Impossible double save',
      eventType: 'double_save',
      minute: 77,
      viralScore: 80,
      rankingScore: 75.2,
      caption: ViralCaption(
        hook: 'How did that NOT go in? 🧤',
        caption: 'One sequence, two saves, zero logic.',
        cta: 'Share to WhatsApp',
        hashtags: <String>['#GTEX', '#Goalkeeper', '#ClipEngine'],
      ),
      tags: <String>['double save', 'chaos'],
      teamName: 'Harbor City',
      playerName: 'Tunde Bale',
      scorelineLabel: '0-0',
      shareChannel: 'whatsapp',
    );
    const ViralClip third = ViralClip(
      matchId: 'match-cup-final',
      highlightId: 'clip-003',
      title: 'Final penalty chaos',
      eventType: 'penalty_scored',
      minute: 118,
      viralScore: 88,
      rankingScore: 81.7,
      caption: ViralCaption(
        hook: 'Cup final nerves in one touch 🏆',
        caption:
            'The pressure was ridiculous and the finish was colder than ice.',
        cta: 'Share to WhatsApp',
        hashtags: <String>['#GTEX', '#CupFinal', '#PenaltyDrama'],
      ),
      tags: <String>['penalty', 'final'],
      teamName: 'Unity Stars',
      playerName: 'Sadiq Bello',
      scorelineLabel: '3-2',
      shareChannel: 'whatsapp',
    );

    return _ViralFeedFixtures(
      const <ViralClip>[first, second, third],
      <String, PunditDebate>{
        'match-lagos-derby': const PunditDebate(
          matchId: 'match-lagos-derby',
          headline: 'Royal Lagos spark post-match chaos',
          hotTakes: <String>[
            'Royal Lagos just broke the game state.',
            'That defending was soft when it mattered.',
          ],
          lines: <PunditDebateLine>[
            PunditDebateLine(
              speaker: 'Tactical Analyst',
              line: 'The late overload on the right side created the winner.',
              emphasis: 'medium',
            ),
            PunditDebateLine(
              speaker: 'Ex-Pro',
              line: 'Forget shape, that was about nerve and hunger.',
              emphasis: 'high',
            ),
            PunditDebateLine(
              speaker: 'Hype Merchant',
              line: 'That clip is going everywhere tonight.',
              emphasis: 'high',
            ),
          ],
        ),
        'match-keeper-night': const PunditDebate(
          matchId: 'match-keeper-night',
          headline: 'Keeper steals the whole show',
          hotTakes: <String>['That save sequence should count double.'],
          lines: <PunditDebateLine>[
            PunditDebateLine(
              speaker: 'Tactical Analyst',
              line:
                  'The shot quality was huge and the goalkeeper still won both actions.',
              emphasis: 'medium',
            ),
            PunditDebateLine(
              speaker: 'Hype Merchant',
              line: 'That was superhero stuff.',
              emphasis: 'high',
            ),
          ],
        ),
        'match-cup-final': const PunditDebate(
          matchId: 'match-cup-final',
          headline: 'Final pressure melts one side',
          hotTakes: <String>['The moment was bigger than the defending.'],
          lines: <PunditDebateLine>[
            PunditDebateLine(
              speaker: 'Ex-Pro',
              line: 'You either live for that pressure or it crushes you.',
              emphasis: 'high',
            ),
            PunditDebateLine(
              speaker: 'Hype Merchant',
              line: 'That finish had trophy-winning energy all over it.',
              emphasis: 'high',
            ),
          ],
        ),
      },
    );
  }

  Future<ViralFeedDeck> deck() async {
    return ViralFeedDeck(
      clips: List<ViralClip>.of(_clips, growable: false),
      debatesByMatch: Map<String, PunditDebate>.from(_debates),
    );
  }

  Future<PunditDebate> debate(String matchId) async {
    return _debates[matchId] ?? _debates.values.first;
  }
}

const String _apiBaseUrl = String.fromEnvironment(
  'GTE_API_BASE_URL',
  defaultValue: 'http://127.0.0.1:8000',
);

const String _rawBackendMode = String.fromEnvironment(
  'GTE_BACKEND_MODE',
  defaultValue: 'livethenfixture',
);

final GteBackendMode _backendMode = _parseBackendMode(_rawBackendMode);

GteBackendMode _parseBackendMode(String rawMode) {
  switch (rawMode.trim().toLowerCase()) {
    case 'fixture':
      return GteBackendMode.fixture;
    case 'live':
      return GteBackendMode.live;
    case 'livethenfixture':
    default:
      return GteBackendMode.liveThenFixture;
  }
}
