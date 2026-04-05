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
  final bool authenticated = ref.watch(isAuthenticatedProvider);
  final CompetitionHubData competitions = await ref.watch(
    competitionHubProvider.future,
  );
  final JsonMap risingStarsPayload = await api.getMap(
    '/regen-universe/rising-stars',
    auth: false,
  );
  final JsonMap scoutingPayload = await api.getMap(
    '/regen-universe/scouting-feed',
    auth: false,
  );
  final JsonMap seasonsPayload = await api.getMap(
    '/regen-universe/seasons',
    auth: false,
  );
  final JsonMap awardsPayload = await api.getMap(
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
    risingStars: jsonMapList(
      risingStarsPayload['entries'],
      label: 'rising stars',
    ),
    scoutingFeed: jsonMapList(
      scoutingPayload['items'],
      label: 'scouting items',
    ),
    seasons: jsonMapList(seasonsPayload['items'], label: 'season'),
    awards: jsonMapList(awardsPayload['items'], label: 'award'),
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
            ? (authenticated
                ? 'Club context is still syncing for this session. Retry once bootstrap completes.'
                : 'Sign in to unlock club-backed federation actions.')
            : 'Federation membership creation requires a live club-backed action flow and remains disabled from the summary tab.',
  );
});
