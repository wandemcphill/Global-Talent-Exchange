import 'gtex_regen_wire_models.dart';

/// Why a regen has no dossier.
///
/// The regen world lists prospects from three sources, and only one of them is
/// backed by a `RegenProfile`. Saying which is the difference between "we have
/// nothing to show you" and "this regen genuinely has no recorded lineage".
enum GtexRegenDossierAbsence {
  /// The backend has no `RegenProfile` for this player id. National-pool seed
  /// rows are the common case: they are generated depth, not tracked careers.
  notPublished,

  /// The request failed. Distinct from [notPublished] because it is transient
  /// and a retry is the right affordance.
  loadFailed,
}

/// A regen's full record: who they descend from, how good they might become,
/// what has actually happened to them, and what they are worth.
///
/// Assembled from `GET /regen-universe/players/{id}` plus, when the regen has
/// a profile id, `GET /regens/{regen_id}/lineage`. Everything is either a real
/// backend value or explicitly absent - see the Phase 4 contract, §P5/§P6.
class GtexRegenDossier {
  const GtexRegenDossier({
    required this.playerId,
    required this.showcase,
    this.lineageChain = const <RegenLineageChainNode>[],
    this.lineageChainUnavailable = false,
    this.lifecycle,
  });

  final String playerId;
  final RegenPlayerShowcase showcase;

  /// The multi-generation chain from `/regens/{id}/lineage`. Empty when this
  /// regen starts its own line, or when [lineageChainUnavailable] is set.
  final List<RegenLineageChainNode> lineageChain;

  /// True when the chain request failed, so the UI can distinguish "no
  /// ancestors" from "we could not read the ancestors".
  final bool lineageChainUnavailable;

  /// The ownership state: contract phase, free agency, transfer listing, what
  /// the regen is agitating for, and the offer market around them. Null when
  /// the backend publishes no lifecycle row for this player - which is a real
  /// answer, not a failure.
  final RegenLifecycleState? lifecycle;

  RegenProfileDetail get profile => showcase.profile;

  String get displayName => profile.displayName;

  /// The declared parent relationship, when the backend recorded one.
  RegenLineageDescriptor? get lineage => profile.lineage;

  /// The parent's canonical player id when the parent is a real player row,
  /// so the UI can offer navigation into Player Detail. Null means the parent
  /// is a celebrity/external reference or there is no parent at all - the
  /// relationship is stated but not navigable.
  String? get parentPlayerId => profile.lineage?.parentPlayerId;

  bool get hasLineage => profile.lineage != null || lineageChain.isNotEmpty;

  /// How far the regen still has to climb, using the backend's own current
  /// and potential values. Null when either side is unknown - the UI shows
  /// "potential not rated" rather than a zero headroom.
  int? get growthHeadroom {
    final int? potential = profile.potential ?? profile.potentialRange?.maximum;
    final int? current = profile.currentRating ?? profile.currentGsi;
    if (potential == null || current == null) {
      return null;
    }
    return potential - current;
  }

  /// The scouted potential band, e.g. "78-91". Null when the backend supplied
  /// neither a band nor a point potential.
  String? get potentialBandLabel {
    final RegenAbilityRange? band = profile.potentialRange;
    if (band != null) {
      return band.label;
    }
    final int? potential = profile.potential;
    return potential == null ? null : '$potential';
  }

  /// The current ability band, e.g. "64-70".
  String? get currentBandLabel {
    final RegenAbilityRange? band = profile.currentAbilityRange;
    if (band != null) {
      return band.label;
    }
    final int? current = profile.currentRating;
    return current == null ? null : '$current';
  }

  /// How confident the scouting is in that band. The backend supplies this as
  /// a word ("low", "medium", "high"); it is shown as-is because it qualifies
  /// every other potential number on the screen.
  String get scoutConfidenceLabel => profile.scoutConfidence;

  /// Development events, newest first.
  List<RegenStoryEvent> get developmentTimeline {
    final List<RegenStoryEvent> events = List<RegenStoryEvent>.of(
      showcase.timeline,
    );
    events.sort(
      (RegenStoryEvent a, RegenStoryEvent b) =>
          b.occurredAt.compareTo(a.occurredAt),
    );
    return List<RegenStoryEvent>.unmodifiable(events);
  }

  bool get hasDevelopmentTimeline => showcase.timeline.isNotEmpty;

  List<RegenPlayerAchievement> get achievements => showcase.achievements;

  RegenLegacySnapshot? get legacy => showcase.legacy;

  RegenValueBreakdown? get value => showcase.latestValue;

  RegenPersonality? get personality => profile.personality;

  /// The offer market around this regen, when one is published.
  RegenOfferMarket? get offerMarket => lifecycle?.offerMarket;

  /// True when the backend has told us anything about this regen's ownership
  /// situation. When false the UI says so rather than drawing an empty board.
  bool get hasLifecycle => lifecycle != null;

  RegenOrigin? get origin => profile.origin;

  /// A one-line lineage label for the regen card, e.g. "Son of Okoye".
  /// Null when the backend recorded no lineage, so the card simply omits it.
  String? get lineageLabel {
    final RegenLineageDescriptor? descriptor = profile.lineage;
    if (descriptor == null) {
      return null;
    }
    final String relationship = _humanise(descriptor.relationshipType);
    return '$relationship of ${descriptor.relatedLegendRefId}';
  }

  /// "Generation 3" when the chain places this regen, otherwise null.
  String? get generationLabel {
    if (lineageChain.length <= 1) {
      return null;
    }
    return 'Generation ${lineageChain.length}';
  }

  static String _humanise(String value) {
    final String trimmed = value.trim().replaceAll('_', ' ');
    if (trimmed.isEmpty) {
      return 'Descendant';
    }
    return trimmed[0].toUpperCase() + trimmed.substring(1);
  }
}

/// The dossier request outcome: loaded, or absent for a stated reason.
///
/// Modelled as one object rather than a nullable dossier plus a nullable error
/// so a caller cannot render a "missing" state without saying why it is
/// missing.
class GtexRegenDossierResult {
  const GtexRegenDossierResult.loaded(GtexRegenDossier this.dossier)
    : absence = null,
      message = null;

  const GtexRegenDossierResult.absent({
    required GtexRegenDossierAbsence this.absence,
    required String this.message,
  }) : dossier = null;

  final GtexRegenDossier? dossier;
  final GtexRegenDossierAbsence? absence;
  final String? message;

  bool get isLoaded => dossier != null;
}
