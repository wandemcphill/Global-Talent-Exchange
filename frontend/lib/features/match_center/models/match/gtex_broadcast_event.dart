enum GtexBroadcastEventType {
  goal,
  missedChance,
  yellowCard,
  redCard,
  offside,
  varChecking,
  varConfirmed,
  varDisallowed,
  intro,
  fullTime,
  commentaryBeat,
}

class GtexBroadcastEvent {
  const GtexBroadcastEvent({
    required this.id,
    required this.type,
    required this.title,
    required this.startViewerSeconds,
    required this.endViewerSeconds,
    this.subtitle,
    this.teamId,
    this.viewerOnly = false,
  });

  final String id;
  final GtexBroadcastEventType type;
  final String title;
  final String? subtitle;
  final String? teamId;
  final double startViewerSeconds;
  final double endViewerSeconds;
  final bool viewerOnly;

  bool isVisibleAt(double viewerSeconds) {
    return viewerSeconds >= startViewerSeconds &&
        viewerSeconds <= endViewerSeconds;
  }

  GtexBroadcastEvent copyWith({
    String? title,
    Object? subtitle = _gtexBroadcastEventUnset,
    double? startViewerSeconds,
    double? endViewerSeconds,
  }) {
    return GtexBroadcastEvent(
      id: id,
      type: type,
      title: title ?? this.title,
      subtitle:
          identical(subtitle, _gtexBroadcastEventUnset)
              ? this.subtitle
              : subtitle as String?,
      teamId: teamId,
      startViewerSeconds: startViewerSeconds ?? this.startViewerSeconds,
      endViewerSeconds: endViewerSeconds ?? this.endViewerSeconds,
      viewerOnly: viewerOnly,
    );
  }
}

const Object _gtexBroadcastEventUnset = Object();
