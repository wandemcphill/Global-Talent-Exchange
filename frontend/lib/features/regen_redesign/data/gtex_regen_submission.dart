import '../models/gtex_regen_wire_models.dart';
import 'gtex_regen_demo_dossier.dart';
import 'gtex_regen_repository.dart';
import 'gtex_regen_world_api.dart';

/// Canonical live free-agent offer submission bridge.
///
/// Kept outside the legacy repository contract so the existing browse/demo
/// model does not need to invent a second money or contract representation.
extension GtexRegenSubmission on GtexRegenRepository {
  Future<RegenLifecycleState?> submitContractOffer(
    String playerId,
    GtexRegenOfferDraft draft,
  ) async {
    if (!canActOnOwnership) {
      throw StateError('Sign in to submit a regen contract offer.');
    }

    if (this is LiveGtexRegenRepository) {
      final LiveGtexRegenRepository live = this as LiveGtexRegenRepository;
      return GtexRegenWorldApi(
        client: live.universeApi.client,
      ).submitContractOffer(playerId, draft);
    }

    if (this is DemoGtexRegenRepository) {
      return demoRegenLifecycle();
    }

    throw StateError(
      'This regen repository does not expose the canonical offer-submission path.',
    );
  }
}
