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
    );
  }
}
