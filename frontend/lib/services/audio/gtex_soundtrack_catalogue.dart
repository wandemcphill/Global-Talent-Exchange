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

  List<GtexTrackMetadata> get promotedTracks =>
      _tracks.where((t) => t.isPromoted).toList(growable: false);

  List<GtexTrackMetadata> get goalAnthemTracks =>
      _tracks.where((t) => t.isGoalAnthem).toList(growable: false);

  List<GtexTrackMetadata> get walkoutAnthemTracks =>
      _tracks.where((t) => t.isWalkoutAnthem).toList(growable: false);

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
    isPromoted: false,
    sponsorTier: 'Official Theme',
    artistHandle: '@gtex_sound',
    artistBio: 'In-house spatial stadium sound design and broadcast theme.',
    region: 'Global',
    hypeCount: 4120,
    streamImpressions: 192000,
    isGoalAnthem: false,
    isWalkoutAnthem: true,
  );

  static const List<GtexTrackMetadata> promotedArtistRoster = <GtexTrackMetadata>[
    GtexTrackMetadata(
      id: 'gtex-trax-afro-01',
      title: 'Lagos Nightlights (Champions Walkout VIP)',
      artist: 'Kazeem & The Sovereign Pulse',
      album: 'Echoes of Eko EP',
      genre: 'Afro-Fusion / Arena',
      bpm: 118,
      durationSeconds: 196,
      contexts: <GtexAudioContext>[
        GtexAudioContext.home,
        GtexAudioContext.competition,
        GtexAudioContext.matchday,
        GtexAudioContext.celebration,
      ],
      assetPath: 'assets/media/gtex_stadium_ambient.mp3',
      source: 'GTEX TRAX Artist Spotlight Partnership',
      licence: 'GTEX Artist Promotion & In-Game Sync Licence',
      licenceUrl: 'https://gtex.io/legal/audio-licensing',
      attributionRequired: true,
      provenance: 'Verified GTEX TRAX Artist Submission (Fallback bundled audio)',
      isPromoted: true,
      sponsorTier: 'Headliner',
      artistHandle: '@kazeemsounds',
      artistBio: 'Lagos-born Afro-arena producer blending talking drums with stadium synth brass.',
      region: 'Lagos · West Africa',
      spotifyUrl: 'https://open.spotify.com',
      appleMusicUrl: 'https://music.apple.com',
      audiomackUrl: 'https://audiomack.com',
      youtubeUrl: 'https://youtube.com',
      hypeCount: 9840,
      streamImpressions: 314500,
      isGoalAnthem: true,
      isWalkoutAnthem: true,
    ),
    GtexTrackMetadata(
      id: 'gtex-trax-ukg-02',
      title: 'Top Bins Only (Deadline Day Dub)',
      artist: 'Nova Vane',
      album: 'South London Tekkers',
      genre: 'UK Garage / Grime',
      bpm: 132,
      durationSeconds: 174,
      contexts: <GtexAudioContext>[
        GtexAudioContext.market,
        GtexAudioContext.club,
        GtexAudioContext.competition,
      ],
      assetPath: 'assets/media/gtex_stadium_ambient.mp3',
      source: 'GTEX TRAX Artist Spotlight Partnership',
      licence: 'GTEX Artist Promotion & In-Game Sync Licence',
      licenceUrl: 'https://gtex.io/legal/audio-licensing',
      attributionRequired: true,
      provenance: 'Verified GTEX TRAX Artist Submission (Fallback bundled audio)',
      isPromoted: true,
      sponsorTier: 'Spotlight',
      artistHandle: '@novavane_uk',
      artistBio: 'South London 2-step & grime vocalist crafting high-tempo football trading anthems.',
      region: 'London · UK',
      spotifyUrl: 'https://open.spotify.com',
      appleMusicUrl: 'https://music.apple.com',
      audiomackUrl: 'https://audiomack.com',
      youtubeUrl: 'https://youtube.com',
      hypeCount: 6420,
      streamImpressions: 208900,
      isGoalAnthem: true,
      isWalkoutAnthem: true,
    ),
    GtexTrackMetadata(
      id: 'gtex-trax-baile-03',
      title: 'Baila En La Cancha (Wonderkid Bounce)',
      artist: 'Fuego Sol',
      album: 'Futebol Futuro',
      genre: 'Baile Funk / Club',
      bpm: 128,
      durationSeconds: 162,
      contexts: <GtexAudioContext>[
        GtexAudioContext.world,
        GtexAudioContext.celebration,
        GtexAudioContext.matchday,
      ],
      assetPath: 'assets/media/gtex_stadium_ambient.mp3',
      source: 'GTEX TRAX Artist Spotlight Partnership',
      licence: 'GTEX Artist Promotion & In-Game Sync Licence',
      licenceUrl: 'https://gtex.io/legal/audio-licensing',
      attributionRequired: true,
      provenance: 'Verified GTEX TRAX Artist Submission (Fallback bundled audio)',
      isPromoted: true,
      sponsorTier: 'Headliner',
      artistHandle: '@fuegosol_br',
      artistBio: 'São Paulo electronic percussionist powering GTEX Regen World & Goal Celebrations.',
      region: 'São Paulo · LATAM',
      spotifyUrl: 'https://open.spotify.com',
      appleMusicUrl: 'https://music.apple.com',
      audiomackUrl: 'https://audiomack.com',
      youtubeUrl: 'https://youtube.com',
      hypeCount: 8190,
      streamImpressions: 276400,
      isGoalAnthem: true,
      isWalkoutAnthem: false,
    ),
    GtexTrackMetadata(
      id: 'gtex-trax-synth-04',
      title: 'Sovereign Liquidity (VIP Mix)',
      artist: 'Aether & Gold',
      album: 'Night Market Protocol',
      genre: 'Melodic Techno',
      bpm: 124,
      durationSeconds: 210,
      contexts: <GtexAudioContext>[
        GtexAudioContext.market,
        GtexAudioContext.club,
        GtexAudioContext.home,
      ],
      assetPath: 'assets/media/gtex_stadium_ambient.mp3',
      source: 'GTEX TRAX Artist Spotlight Partnership',
      licence: 'GTEX Artist Promotion & In-Game Sync Licence',
      licenceUrl: 'https://gtex.io/legal/audio-licensing',
      attributionRequired: true,
      provenance: 'Verified GTEX TRAX Artist Submission (Fallback bundled audio)',
      isPromoted: true,
      sponsorTier: 'Rising Star',
      artistHandle: '@aethergold',
      artistBio: 'Berlin-based melodic synth duo scoring late-night transfer negotiations.',
      region: 'Berlin · EU',
      spotifyUrl: 'https://open.spotify.com',
      appleMusicUrl: 'https://music.apple.com',
      youtubeUrl: 'https://youtube.com',
      hypeCount: 5110,
      streamImpressions: 159200,
      isGoalAnthem: false,
      isWalkoutAnthem: true,
    ),
  ];

  static const GtexTrackMetadata fallbackTrack = defaultBundledTrack;

  static final List<GtexTrackMetadata> defaultStarterCatalogue = <GtexTrackMetadata>[
    defaultBundledTrack,
    ...promotedArtistRoster,
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
