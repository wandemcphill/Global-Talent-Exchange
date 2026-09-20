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

  static const GtexTrackMetadata fallbackTrack = GtexTrackMetadata(
    id: 'gtex-stadium-ambient',
    title: 'GTEX Stadium Atmosphere',
    artist: 'GTEX Sound Design',
    album: 'GTEX Football OS Vol. 1',
    genre: 'Stadium Ambience',
    bpm: 110,
    durationSeconds: 120,
    contexts: <GtexAudioContext>[
      GtexAudioContext.home,
      GtexAudioContext.matchday,
    ],
    assetPath: 'assets/media/gtex_stadium_ambient.mp3',
    source: 'GTEX Internal Production',
    licence: 'GTEX First-Party Commercial Game Licence',
    licenceUrl: 'https://gtex.io/legal/audio-licensing',
    attributionRequired: false,
    provenance: 'Bundled in-repo asset assets/media/gtex_stadium_ambient.mp3',
  );

  static final List<GtexTrackMetadata> defaultStarterCatalogue = <GtexTrackMetadata>[
    fallbackTrack,
    const GtexTrackMetadata(
      id: 'gtex-tactical-hq',
      title: 'Tactical HQ Pulse',
      artist: 'GTEX Audio Team',
      album: 'GTEX Football OS Vol. 1',
      genre: 'Electronic Ambient',
      bpm: 112,
      durationSeconds: 165,
      contexts: <GtexAudioContext>[
        GtexAudioContext.club,
        GtexAudioContext.home,
      ],
      assetPath: 'assets/media/gtex_stadium_ambient.mp3',
      source: 'GTEX Internal Production',
      licence: 'GTEX First-Party Commercial Game Licence',
      licenceUrl: 'https://gtex.io/legal/audio-licensing',
      attributionRequired: false,
      provenance: 'Bundled starter track (HQ theme)',
    ),
    const GtexTrackMetadata(
      id: 'gtex-trading-floor',
      title: 'Trading Floor Dynamics',
      artist: 'GTEX Audio Team',
      album: 'GTEX Football OS Vol. 1',
      genre: 'Cyber Synth',
      bpm: 124,
      durationSeconds: 180,
      contexts: <GtexAudioContext>[
        GtexAudioContext.market,
      ],
      assetPath: 'assets/media/gtex_stadium_ambient.mp3',
      source: 'GTEX Internal Production',
      licence: 'GTEX First-Party Commercial Game Licence',
      licenceUrl: 'https://gtex.io/legal/audio-licensing',
      attributionRequired: false,
      provenance: 'Bundled starter track (Market theme)',
    ),
    const GtexTrackMetadata(
      id: 'gtex-arena-pressure',
      title: 'Arena Pressure',
      artist: 'GTEX Audio Team',
      album: 'GTEX Football OS Vol. 1',
      genre: 'Orchestral Hybrid',
      bpm: 128,
      durationSeconds: 195,
      contexts: <GtexAudioContext>[
        GtexAudioContext.competition,
      ],
      assetPath: 'assets/media/gtex_stadium_ambient.mp3',
      source: 'GTEX Internal Production',
      licence: 'GTEX First-Party Commercial Game Licence',
      licenceUrl: 'https://gtex.io/legal/audio-licensing',
      attributionRequired: false,
      provenance: 'Bundled starter track (Competition theme)',
    ),
    const GtexTrackMetadata(
      id: 'gtex-scouting-pulse',
      title: 'Global Scouting Pulse',
      artist: 'GTEX Audio Team',
      album: 'GTEX Football OS Vol. 1',
      genre: 'Deep House / Ethnic',
      bpm: 118,
      durationSeconds: 170,
      contexts: <GtexAudioContext>[
        GtexAudioContext.world,
      ],
      assetPath: 'assets/media/gtex_stadium_ambient.mp3',
      source: 'GTEX Internal Production',
      licence: 'GTEX First-Party Commercial Game Licence',
      licenceUrl: 'https://gtex.io/legal/audio-licensing',
      attributionRequired: false,
      provenance: 'Bundled starter track (World / Regens theme)',
    ),
    const GtexTrackMetadata(
      id: 'gtex-champions-triumph',
      title: 'Champions Triumph Fanfare',
      artist: 'GTEX Audio Team',
      album: 'GTEX Football OS Vol. 1',
      genre: 'Brass Orchestral',
      bpm: 132,
      durationSeconds: 140,
      contexts: <GtexAudioContext>[
        GtexAudioContext.celebration,
      ],
      assetPath: 'assets/media/gtex_stadium_ambient.mp3',
      source: 'GTEX Internal Production',
      licence: 'GTEX First-Party Commercial Game Licence',
      licenceUrl: 'https://gtex.io/legal/audio-licensing',
      attributionRequired: false,
      provenance: 'Bundled starter track (Celebration theme)',
    ),
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
