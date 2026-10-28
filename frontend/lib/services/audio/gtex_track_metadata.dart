import 'gtex_audio_context.dart';

class GtexTrackMetadata {
  const GtexTrackMetadata({
    required this.id,
    required this.title,
    required this.artist,
    required this.album,
    required this.genre,
    required this.bpm,
    required this.durationSeconds,
    required this.contexts,
    required this.assetPath,
    this.streamUrl,
    required this.source,
    required this.licence,
    required this.licenceUrl,
    required this.attributionRequired,
    required this.provenance,
    this.isPromoted = false,
    this.sponsorTier = 'Official Theme',
    this.artistHandle = '@gtex_audio',
    this.artistBio = 'Official GTEX Soundtrack OS artist.',
    this.region = 'Global',
    this.spotifyUrl,
    this.appleMusicUrl,
    this.audiomackUrl,
    this.youtubeUrl,
    this.hypeCount = 1200,
    this.streamImpressions = 45000,
    this.isGoalAnthem = false,
    this.isWalkoutAnthem = false,
  });

  final String id;
  final String title;
  final String artist;
  final String album;
  final String genre;
  final int bpm;
  final int durationSeconds;
  final List<GtexAudioContext> contexts;
  final String assetPath;
  final String? streamUrl;

  /// Licensing & provenance metadata required for every asset
  final String source;
  final String licence;
  final String licenceUrl;
  final bool attributionRequired;
  final String provenance;

  /// Artist promotion, discovery & matchday placement metadata
  final bool isPromoted;
  final String sponsorTier; // 'Headliner' | 'Spotlight' | 'Rising Star' | 'Official Theme'
  final String artistHandle;
  final String artistBio;
  final String region;
  final String? spotifyUrl;
  final String? appleMusicUrl;
  final String? audiomackUrl;
  final String? youtubeUrl;
  final int hypeCount;
  final int streamImpressions;
  final bool isGoalAnthem;
  final bool isWalkoutAnthem;

  String get durationFormatted {
    final int minutes = durationSeconds ~/ 60;
    final int seconds = durationSeconds % 60;
    return '$minutes:${seconds.toString().padLeft(2, '0')}';
  }

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'id': id,
      'title': title,
      'artist': artist,
      'album': album,
      'genre': genre,
      'bpm': bpm,
      'duration_seconds': durationSeconds,
      'contexts': contexts.map((c) => c.name).toList(),
      'asset_path': assetPath,
      'stream_url': streamUrl,
      'source': source,
      'licence': licence,
      'licence_url': licenceUrl,
      'attribution_required': attributionRequired,
      'provenance': provenance,
      'is_promoted': isPromoted,
      'sponsor_tier': sponsorTier,
      'artist_handle': artistHandle,
      'artist_bio': artistBio,
      'region': region,
      'spotify_url': spotifyUrl,
      'apple_music_url': appleMusicUrl,
      'audiomack_url': audiomackUrl,
      'youtube_url': youtubeUrl,
      'hype_count': hypeCount,
      'stream_impressions': streamImpressions,
      'is_goal_anthem': isGoalAnthem,
      'is_walkout_anthem': isWalkoutAnthem,
    };
  }

  factory GtexTrackMetadata.fromJson(Map<String, Object?> json) {
    final List<Object?> contextList = (json['contexts'] as List<Object?>?) ?? [];
    return GtexTrackMetadata(
      id: json['id'] as String? ?? 'unknown',
      title: json['title'] as String? ?? 'Untitled Track',
      artist: json['artist'] as String? ?? 'GTEX Audio',
      album: json['album'] as String? ?? 'GTEX Official',
      genre: json['genre'] as String? ?? 'Stadium / Ambient',
      bpm: json['bpm'] as int? ?? 120,
      durationSeconds: json['duration_seconds'] as int? ?? 180,
      contexts: contextList
          .map((c) => GtexAudioContext.values.firstWhere(
                (ctx) => ctx.name == c.toString(),
                orElse: () => GtexAudioContext.home,
              ))
          .toList(),
      assetPath: json['asset_path'] as String? ?? 'assets/media/gtex_stadium_ambient.mp3',
      streamUrl: json['stream_url'] as String?,
      source: json['source'] as String? ?? 'GTEX First-Party',
      licence: json['licence'] as String? ?? 'Royalty-Free Commercial',
      licenceUrl: json['licence_url'] as String? ?? 'https://gtex.io/legal/audio-licensing',
      attributionRequired: json['attribution_required'] as bool? ?? false,
      provenance: json['provenance'] as String? ?? 'GTEX In-House Asset Bundle',
      isPromoted: json['is_promoted'] as bool? ?? false,
      sponsorTier: json['sponsor_tier'] as String? ?? 'Official Theme',
      artistHandle: json['artist_handle'] as String? ?? '@gtex_audio',
      artistBio: json['artist_bio'] as String? ?? 'Official GTEX Soundtrack OS artist.',
      region: json['region'] as String? ?? 'Global',
      spotifyUrl: json['spotify_url'] as String?,
      appleMusicUrl: json['apple_music_url'] as String?,
      audiomackUrl: json['audiomack_url'] as String?,
      youtubeUrl: json['youtube_url'] as String?,
      hypeCount: json['hype_count'] as int? ?? 1200,
      streamImpressions: json['stream_impressions'] as int? ?? 45000,
      isGoalAnthem: json['is_goal_anthem'] as bool? ?? false,
      isWalkoutAnthem: json['is_walkout_anthem'] as bool? ?? false,
    );
  }
}
