import 'package:flutter/services.dart';
import 'package:gte_frontend/models/match_3d_scene_graph.dart';
import 'package:gte_frontend/models/match_event.dart';

abstract interface class Match3dBridgeBackend {
  const Match3dBridgeBackend();

  Stream<dynamic> get events;

  Future<bool> isAvailable();

  Future<void> handleEvent(Map<String, dynamic> event);
}

class PlatformMatch3dBridgeBackend implements Match3dBridgeBackend {
  const PlatformMatch3dBridgeBackend();

  static const MethodChannel _channel = MethodChannel('match_3d');
  static const EventChannel _events = EventChannel('match_3d/events');

  @override
  Stream<dynamic> get events => _events.receiveBroadcastStream();

  @override
  Future<bool> isAvailable() async {
    try {
      await _channel.invokeMethod<Object?>('ping');
      return true;
    } on MissingPluginException {
      return false;
    } on PlatformException {
      return false;
    }
  }

  @override
  Future<void> handleEvent(Map<String, dynamic> event) async {
    try {
      await _channel.invokeMethod<void>('handleEvent', event);
    } on MissingPluginException {
      // Native 3D engine integration is optional; Flutter fallback remains active.
    }
  }
}

class Match3DBridge {
  Match3DBridge({Match3dBridgeBackend? backend})
    : _backend = backend ?? const PlatformMatch3dBridgeBackend();

  final Match3dBridgeBackend _backend;

  Stream<dynamic> get events => _backend.events;

  Future<bool> isNativeAvailable() => _backend.isAvailable();

  Future<void> sendEvent(Map<String, dynamic> event) async {
    await _backend.handleEvent(event);
  }

  Future<void> syncFrame({
    required Match3dSceneGraph sceneGraph,
    MatchEvent? activeEvent,
  }) async {
    final Map<String, dynamic> payload = Map<String, dynamic>.from(
      sceneGraph.toBridgePayload(),
    );
    if (activeEvent != null) {
      payload['matchEvent'] = _eventPayload(activeEvent);
    }
    await sendEvent(payload);
  }

  Map<String, dynamic> _eventPayload(MatchEvent event) {
    return <String, dynamic>{
      'id': event.id,
      'type': event.type.name,
      'sequence': event.sequence,
      'minute': event.minute,
      'addedTime': event.addedTime,
      'clockLabel': event.clockLabel,
      'timeSeconds': event.timeSeconds,
      'teamId': event.teamId,
      'teamName': event.teamName,
      'primaryPlayerId': event.primaryPlayerId,
      'primaryPlayerName': event.primaryPlayerName,
      'secondaryPlayerId': event.secondaryPlayerId,
      'secondaryPlayerName': event.secondaryPlayerName,
      'homeScore': event.homeScore,
      'awayScore': event.awayScore,
      'bannerText': event.bannerText,
      'commentary': event.commentary,
      'emphasisLevel': event.emphasisLevel,
      'highlightedPlayerIds': event.highlightedPlayerIds,
      'flags': event.flags,
      'playbackProfile': event.playbackProfile,
      'missVariant': event.missVariant,
      'reviewable': event.reviewable,
      'reviewReason': event.reviewReason,
      'reviewDecision': event.reviewDecision,
      'scoreCommit': event.scoreCommit,
    };
  }
}
