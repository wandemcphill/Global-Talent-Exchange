import 'package:flutter/foundation.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/regen_universe_api.dart';
import 'package:gte_frontend/models/regen_universe_models.dart';

class _RegenControllerLoadResult<T> {
  const _RegenControllerLoadResult({this.value, this.error});

  final T? value;
  final Object? error;
}

Future<_RegenControllerLoadResult<T>> _safeRegenControllerLoad<T>(
  Future<T> future,
) async {
  try {
    return _RegenControllerLoadResult<T>(value: await future);
  } catch (error) {
    return _RegenControllerLoadResult<T>(error: error);
  }
}

const RegenGenerationTracking _emptyRegenControllerTracking =
    RegenGenerationTracking(
      totalSeededPlayers: 0,
      seedTypes: <RegenGenerationTrackingEntry>[],
      rarityBreakdown: <RegenGenerationTrackingEntry>[],
      countryDistribution: <RegenGenerationTrackingEntry>[],
      globalPeakRating: 0,
      trackedAchievements: <String>[],
    );

class RegenUniverseController extends ChangeNotifier {
  RegenUniverseController({required RegenUniverseApi api}) : _api = api;

  factory RegenUniverseController.standard({
    required String baseUrl,
    GteBackendMode backendMode = GteBackendMode.live,
  }) {
    return RegenUniverseController(
      api: RegenUniverseApi.standard(baseUrl: baseUrl, mode: backendMode),
    );
  }

  final RegenUniverseApi _api;
  Future<void>? _loadFuture;

  DateTime? syncedAt;
  bool isLoading = false;
  String? errorMessage;
  List<RegenRisingStar> risingStars = const <RegenRisingStar>[];
  List<RegenScoutingFeedItem> scoutingFeed = const <RegenScoutingFeedItem>[];
  List<NationalRegenSeed> nationalRegens = const <NationalRegenSeed>[];
  RegenGenerationTracking? tracking;

  bool get hasData =>
      risingStars.isNotEmpty ||
      scoutingFeed.isNotEmpty ||
      nationalRegens.isNotEmpty ||
      tracking != null;

  Future<void> ensureLoaded() async {
    if (isLoading || hasData) {
      return;
    }
    await load();
  }

  Future<void> load() {
    if (_loadFuture != null) {
      return _loadFuture!;
    }
    isLoading = true;
    errorMessage = null;
    notifyListeners();
    final Future<void> task = () async {
      try {
        final List<Object?> payload =
            await Future.wait<Object?>(<Future<Object?>>[
              _safeRegenControllerLoad<List<RegenRisingStar>>(
                _api.listRisingStars(),
              ),
              _safeRegenControllerLoad<List<RegenScoutingFeedItem>>(
                _api.listScoutingFeed(),
              ),
              _safeRegenControllerLoad<List<NationalRegenSeed>>(
                _api.listNationalRegens(),
              ),
              _safeRegenControllerLoad<RegenGenerationTracking>(
                _api.fetchTracking(),
              ),
            ]);
        final _RegenControllerLoadResult<List<RegenRisingStar>>
        risingStarsResult =
            payload[0] as _RegenControllerLoadResult<List<RegenRisingStar>>;
        final _RegenControllerLoadResult<List<RegenScoutingFeedItem>>
        scoutingFeedResult =
            payload[1]
                as _RegenControllerLoadResult<List<RegenScoutingFeedItem>>;
        final _RegenControllerLoadResult<List<NationalRegenSeed>>
        nationalRegensResult =
            payload[2] as _RegenControllerLoadResult<List<NationalRegenSeed>>;
        final _RegenControllerLoadResult<RegenGenerationTracking>
        trackingResult =
            payload[3] as _RegenControllerLoadResult<RegenGenerationTracking>;
        final bool hasAnyData =
            risingStarsResult.value != null ||
            scoutingFeedResult.value != null ||
            nationalRegensResult.value != null ||
            trackingResult.value != null;
        if (!hasAnyData) {
          throw trackingResult.error ??
              risingStarsResult.error ??
              scoutingFeedResult.error ??
              nationalRegensResult.error ??
              StateError('Unable to load the regen universe.');
        }
        risingStars = risingStarsResult.value ?? const <RegenRisingStar>[];
        scoutingFeed =
            scoutingFeedResult.value ?? const <RegenScoutingFeedItem>[];
        nationalRegens =
            nationalRegensResult.value ?? const <NationalRegenSeed>[];
        tracking = trackingResult.value ?? _emptyRegenControllerTracking;
        syncedAt = DateTime.now().toUtc();
      } catch (error) {
        errorMessage = AppFeedback.messageFor(
          error,
          fallback: 'Unable to load the regen universe.',
        );
      } finally {
        isLoading = false;
        _loadFuture = null;
        notifyListeners();
      }
    }();
    _loadFuture = task;
    return task;
  }

  Future<void> refresh() => load();
}
