import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/gte_authed_api.dart';
import '../../features/competitions/live_competitions_provider.dart';
import '../../features/shared/data/gte_feature_support.dart';
import '../../shared/models/auth_session.dart';
import '../../shared/providers/auth_provider.dart';

class WorldAggregateData {
  const WorldAggregateData({
    required this.risingStars,
    required this.scoutingFeed,
    required this.seasons,
    required this.awards,
    required this.hallOfFame,
    required this.federations,
    required this.tracking,
    required this.competitions,
    required this.federationJoinReason,
  });

  final List<JsonMap> risingStars;
  final List<JsonMap> scoutingFeed;
  final List<JsonMap> seasons;
  final List<JsonMap> awards;
  final List<JsonMap> hallOfFame;
  final List<JsonMap> federations;
  final JsonMap tracking;
  final CompetitionHubData competitions;
  final String federationJoinReason;
}

final FutureProvider<WorldAggregateData>
worldAggregateProvider = FutureProvider<WorldAggregateData>((Ref ref) async {
  final GteAuthedApi api = ref.watch(authedApiProvider);
  final CompetitionHubData competitions = await ref.watch(
    competitionHubProvider.future,
  );
  final List<dynamic> risingStarsPayload = await api.getList(
    '/regen-universe/rising-stars',
    auth: false,
  );
  final List<dynamic> scoutingPayload = await api.getList(
    '/regen-universe/scouting-feed',
    auth: false,
  );
  final List<dynamic> seasonsPayload = await api.getList(
    '/regen-universe/seasons',
    auth: false,
  );
  final List<dynamic> awardsPayload = await api.getList(
    '/regen-universe/awards',
    auth: false,
  );
  final JsonMap hallOfFamePayload = await api.getMap(
    '/regen-universe/hall-of-fame',
    auth: false,
  );
  final List<dynamic> federationsPayload = await api.getList(
    '/federations',
    auth: false,
  );
  final JsonMap trackingPayload = await api.getMap(
    '/regen-universe/tracking',
    auth: false,
  );
  final ClubContext? clubContext = ref.watch(clubContextProvider);
  return WorldAggregateData(
    risingStars: risingStarsPayload
        .map((dynamic item) => jsonMap(item, label: 'rising star'))
        .toList(growable: false),
    scoutingFeed: scoutingPayload
        .map((dynamic item) => jsonMap(item, label: 'scouting item'))
        .toList(growable: false),
    seasons: seasonsPayload
        .map((dynamic item) => jsonMap(item, label: 'season'))
        .toList(growable: false),
    awards: awardsPayload
        .map((dynamic item) => jsonMap(item, label: 'award'))
        .toList(growable: false),
    hallOfFame: jsonMapList(
      hallOfFamePayload['entries'] ?? hallOfFamePayload['players'],
      label: 'hall of fame entries',
    ),
    federations: federationsPayload
        .map((dynamic item) => jsonMap(item, label: 'federation'))
        .toList(growable: false),
    tracking: trackingPayload,
    competitions: competitions,
    federationJoinReason:
        clubContext == null
            ? 'Federation membership is blocked: this session has no verified club context.'
            : 'Federation membership creation requires a live club-backed action flow and remains disabled from the summary tab.',
  );
});
