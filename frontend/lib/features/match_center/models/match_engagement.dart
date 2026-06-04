import 'package:gte_frontend/data/gte_models.dart';

class MatchViewerEngagement {
  const MatchViewerEngagement({this.metadata = const <String, Object?>{}});

  final Map<String, Object?> metadata;

  bool get hasPlacements => false;

  factory MatchViewerEngagement.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value ?? const <String, Object?>{},
      label: 'match engagement',
    );
    final Object? rawMetadata =
        GteJson.value(json, <String>['metadata']) ?? const <String, Object?>{};
    return MatchViewerEngagement(
      metadata: Map<String, Object?>.from(
        rawMetadata is Map ? rawMetadata : const <String, Object?>{},
      ),
    );
  }
}
