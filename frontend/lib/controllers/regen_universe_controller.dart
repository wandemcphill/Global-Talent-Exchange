import 'package:flutter/foundation.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/regen_universe_api.dart';
import 'package:gte_frontend/models/regen_universe_models.dart';

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
        final List<Object> payload = await Future.wait<Object>(<Future<Object>>[
          _api.listRisingStars(),
          _api.listScoutingFeed(),
          _api.listNationalRegens(),
          _api.fetchTracking(),
        ]);
        risingStars = payload[0] as List<RegenRisingStar>;
        scoutingFeed = payload[1] as List<RegenScoutingFeedItem>;
        nationalRegens = payload[2] as List<NationalRegenSeed>;
        tracking = payload[3] as RegenGenerationTracking;
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
