import 'dart:math';
import 'gtex_audio_context.dart';
import 'gtex_track_metadata.dart';

class GtexSoundtrackCatalogue {
  GtexSoundtrackCatalogue({List<GtexTrackMetadata>? initialCatalogue})
      : _tracks = List<GtexTrackMetadata>.from(
          initialCatalogue ?? defaultStarterCatalogue,
        );

  final List<GtexTrackMetadata> _tracks;

  List<GtexTrackMetadata> get allTracks => List<GtexTrackMetadata>.unmodifiable(_tracks);

  static const GtexTrackMetadata defaultBundledTrack = GtexTrackMetadata(
    id: 'gtex-stadium-ambient',
    title: 'GTEX Stadium Atmosphere (Official Theme)',
    artist: 'GTEX Sound Design Team',
    album: 'GTEX Football OS',
    genre: 'Stadium Ambience',
    bpm: 110,
    durationSeconds: 120,
    contexts: <GtexAudioContext>[
      GtexAudioContext.home,
      GtexAudioContext.club,
      GtexAudioContext.market,
      GtexAudioContext.competition,
      GtexAudioContext.matchday,
      GtexAudioContext.world,
      GtexAudioContext.celebration,
    ],
    assetPath: 'assets/media/gtex_stadium_ambient.mp3',
    source: 'GTEX First-Party Sound Production',
    licence: 'GTEX Proprietary Bundled Sound Asset',
    licenceUrl: 'https://gtex.io/legal/audio-licensing',
    attributionRequired: false,
    provenance: 'Bundled repository asset (frontend/assets/media/gtex_stadium_ambient.mp3)',
  );

  static const GtexTrackMetadata fallbackTrack = defaultBundledTrack;

  static final List<GtexTrackMetadata> defaultStarterCatalogue = <GtexTrackMetadata>[
    defaultBundledTrack,
  ];

  List<GtexTrackMetadata> tracksForContext(GtexAudioContext context) {
    final List<GtexTrackMetadata> filtered = _tracks
        .where((track) => track.contexts.contains(context))
        .toList();
    if (filtered.isEmpty) {
      return <GtexTrackMetadata>[fallbackTrack];
    }
    return filtered;
  }

  GtexTrackMetadata selectTrackForContext(
    GtexAudioContext context, {
    GtexTrackMetadata? currentTrack,
    bool shuffle = false,
  }) {
    final List<GtexTrackMetadata> pool = tracksForContext(context);
    if (pool.length == 1) {
      return pool.first;
    }

    if (shuffle) {
      final Random random = Random();
      final List<GtexTrackMetadata> remaining =
          pool.where((t) => t.id != currentTrack?.id).toList();
      if (remaining.isEmpty) {
        return pool.first;
      }
      return remaining[random.nextInt(remaining.length)];
    }

    // Default: find current track index in pool or pick first
    if (currentTrack != null) {
      final int currentIndex = pool.indexWhere((t) => t.id == currentTrack.id);
      if (currentIndex != -1) {
        // Current track is already in the matching context pool, keep playing it!
        return pool[currentIndex];
      }
    }
    return pool.first;
  }

  void registerTrack(GtexTrackMetadata track) {
    final int existingIndex = _tracks.indexWhere((t) => t.id == track.id);
    if (existingIndex >= 0) {
      _tracks[existingIndex] = track;
    } else {
      _tracks.add(track);
    }
  }

  void registerAll(List<GtexTrackMetadata> tracks) {
    for (final track in tracks) {
      registerTrack(track);
    }
  }
}
