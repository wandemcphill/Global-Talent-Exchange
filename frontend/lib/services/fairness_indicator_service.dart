import 'dart:convert';

import 'package:gte_frontend/features/match_center/models/match_event.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';

class FairnessBadgeState {
  const FairnessBadgeState({
    required this.status,
    required this.label,
    required this.message,
  });

  final MatchVerificationStatus status;
  final String label;
  final String message;
}

class FairnessIndicatorService {
  const FairnessIndicatorService._();

  static const int _fnvOffsetBasis32 = 0x811c9dc5;
  static const int _fnvPrime32 = 0x01000193;
  static const int _uint8Mod = 0x100;
  static const int _uint16Mod = 0x10000;
  static const int _uint32Mod = 0x100000000;

  static FairnessBadgeState build(MatchViewState viewState) {
    final MatchVerificationStatus status = verify(viewState);
    final MatchFairnessIndicator indicator = viewState.fairnessIndicator;
    switch (status) {
      case MatchVerificationStatus.verified:
        final String modeLabel = indicator.tournamentFairnessMode == null
            ? 'open mode'
            : '${indicator.tournamentFairnessMode} mode';
        return FairnessBadgeState(
          status: status,
          label: indicator.label,
          message: indicator.message ??
              'Server-authoritative replay with $modeLabel and visual-only monetization.',
        );
      case MatchVerificationStatus.tampered:
        return const FairnessBadgeState(
          status: MatchVerificationStatus.tampered,
          label: 'Integrity Mismatch',
          message:
              'Timeline proof no longer matches the revealed playback data.',
        );
      case MatchVerificationStatus.unverified:
        return FairnessBadgeState(
          status: status,
          label: indicator.label,
          message: indicator.message ??
              'Server proof metadata is incomplete for this playback session.',
        );
    }
  }

  static MatchVerificationStatus verify(MatchViewState viewState) {
    final MatchFairnessIndicator indicator = viewState.fairnessIndicator;
    final MatchTimelineProof proof = viewState.timelineProof;
    if (indicator.status == MatchVerificationStatus.tampered ||
        proof.status == MatchVerificationStatus.tampered) {
      return MatchVerificationStatus.tampered;
    }
    final bool localPreview = viewState.source == 'local_simulation' &&
        !indicator.serverAuthoritative;
    if (localPreview) {
      return MatchVerificationStatus.unverified;
    }
    if (!indicator.noPayToWin ||
        !indicator.visualOnlyMonetization ||
        !indicator.serverAuthoritative) {
      return MatchVerificationStatus.tampered;
    }
    if (proof.visibleTimelineHash.isNotEmpty) {
      final String actualHash = computeVisibleTimelineHash(viewState);
      if (actualHash != proof.visibleTimelineHash) {
        return MatchVerificationStatus.tampered;
      }
    }
    if (indicator.status == MatchVerificationStatus.verified &&
        proof.status == MatchVerificationStatus.verified &&
        proof.visibleTimelineHash.isNotEmpty) {
      return MatchVerificationStatus.verified;
    }
    return MatchVerificationStatus.unverified;
  }

  static String computeVisibleTimelineHash(MatchViewState viewState) {
    final Map<String, Object?> payload = <String, Object?>{
      'away_team': <String, Object?>{
        'accent_color': viewState.awayTeam.accentColorHex,
        'formation': viewState.awayTeam.formation,
        'goalkeeper_color': viewState.awayTeam.goalkeeperColorHex,
        'primary_color': viewState.awayTeam.primaryColorHex,
        'secondary_color': viewState.awayTeam.secondaryColorHex,
        'short_name': viewState.awayTeam.shortName,
        'side': _sideValue(viewState.awayTeam.side),
        'team_id': viewState.awayTeam.teamId,
        'team_name': viewState.awayTeam.teamName,
      },
      'duration_seconds': viewState.durationSeconds,
      'events': viewState.events.map(_eventPayload).toList(growable: false),
      'frames': viewState.frames.map(_framePayload).toList(growable: false),
      'home_team': <String, Object?>{
        'accent_color': viewState.homeTeam.accentColorHex,
        'formation': viewState.homeTeam.formation,
        'goalkeeper_color': viewState.homeTeam.goalkeeperColorHex,
        'primary_color': viewState.homeTeam.primaryColorHex,
        'secondary_color': viewState.homeTeam.secondaryColorHex,
        'short_name': viewState.homeTeam.shortName,
        'side': _sideValue(viewState.homeTeam.side),
        'team_id': viewState.homeTeam.teamId,
        'team_name': viewState.homeTeam.teamName,
      },
      'match_id': viewState.matchId,
      'source': viewState.source,
      'supports_offside': viewState.supportsOffside,
    };
    final String canonicalJson = jsonEncode(_sortedJson(payload));
    return _fnv1a32(canonicalJson);
  }

  static Map<String, Object?> _eventPayload(MatchEvent event) {
    return <String, Object?>{
      'added_time': event.addedTime,
      'away_score': event.awayScore,
      'banner_text': event.bannerText,
      'clock_label': event.clockLabel,
      'commentary': event.commentary,
      'emphasis_level': event.emphasisLevel,
      'event_id': event.id,
      'event_type': _eventTypeValue(event.type),
      'flags': event.flags,
      'highlighted_player_ids': event.highlightedPlayerIds,
      'home_score': event.homeScore,
      'minute': event.minute,
      'miss_variant': event.missVariant,
      'playback_profile': event.playbackProfile,
      'primary_player_id': event.primaryPlayerId,
      'primary_player_name': event.primaryPlayerName,
      'review_decision': event.reviewDecision,
      'review_reason': event.reviewReason,
      'reviewable': event.reviewable,
      'score_commit': event.scoreCommit,
      'secondary_player_id': event.secondaryPlayerId,
      'secondary_player_name': event.secondaryPlayerName,
      'sequence': event.sequence,
      'team_id': event.teamId,
      'team_name': event.teamName,
      'time_seconds': event.timeSeconds,
    };
  }

  static Map<String, Object?> _framePayload(MatchTimelineFrame frame) {
    return <String, Object?>{
      'active_event_id': frame.activeEventId,
      'away_score': frame.awayScore,
      'ball': <String, Object?>{
        'owner_player_id': frame.ball.ownerPlayerId,
        'position': <String, Object?>{
          'x': frame.ball.position.x,
          'y': frame.ball.position.y,
        },
        'state': frame.ball.state,
      },
      'camera_preset': _cameraPresetValue(frame.cameraPreset),
      'celebration_team_id': frame.celebrationTeamId,
      'clock_minute': frame.clockMinute,
      'event_banner': frame.eventBanner,
      'flag_animation': frame.flagAnimation,
      'frame_id': frame.id,
      'home_attacks_right': frame.homeAttacksRight,
      'home_score': frame.homeScore,
      'overlay_text': frame.overlayText,
      'pause_playback': frame.pausePlayback,
      'phase': _phaseValue(frame.phase),
      'playback_rate': frame.playbackRate,
      'players': frame.players
          .map(
            (MatchViewerPlayerFrame player) => <String, Object?>{
              'active': player.active,
              'anchor_position': <String, Object?>{
                'x': player.anchorPosition.x,
                'y': player.anchorPosition.y,
              },
              'highlighted': player.highlighted,
              'label': player.label,
              'line': _playerLineValue(player.line),
              'player_id': player.playerId,
              'position': <String, Object?>{
                'x': player.position.x,
                'y': player.position.y,
              },
              'role': _playerRoleValue(player.role),
              'shirt_number': player.shirtNumber,
              'side': _sideValue(player.side),
              'state': _playerStateValue(player.state),
              'team_id': player.teamId,
            },
          )
          .toList(growable: false),
      'possession_side': _sideValue(frame.possessionSide),
      'stage': _playbackStageValue(frame.stage),
      'time_seconds': frame.timeSeconds,
    };
  }

  static Object? _sortedJson(Object? value) {
    if (value is Map<String, Object?>) {
      final List<String> keys = value.keys.toList(growable: false)..sort();
      final Map<String, Object?> normalized = <String, Object?>{};
      for (final String key in keys) {
        normalized[key] = _sortedJson(value[key]);
      }
      return normalized;
    }
    if (value is List<Object?>) {
      return value.map(_sortedJson).toList(growable: false);
    }
    return value;
  }

  static String _fnv1a32(String value) {
    int hash = _fnvOffsetBasis32;
    for (final int codeUnit in utf8.encode(value)) {
      final int lowByte = hash % _uint8Mod;
      hash = hash - lowByte + (lowByte ^ codeUnit);
      hash = _multiplyUint32(hash, _fnvPrime32);
    }
    return hash.toRadixString(16).padLeft(8, '0');
  }

  // Split the multiply into 16-bit chunks so dart2js never needs an imprecise
  // 64-bit intermediate while still producing the same uint32 result.
  static int _multiplyUint32(int left, int right) {
    final int leftLow = left % _uint16Mod;
    final int leftHigh = left ~/ _uint16Mod;
    final int rightLow = right % _uint16Mod;
    final int rightHigh = right ~/ _uint16Mod;
    final int low = leftLow * rightLow;
    final int cross = (leftHigh * rightLow) + (leftLow * rightHigh);
    return (low + ((cross % _uint16Mod) * _uint16Mod)) % _uint32Mod;
  }

  static String _eventTypeValue(MatchViewerEventType value) {
    return switch (value) {
      MatchViewerEventType.redCard => 'red_card',
      MatchViewerEventType.yellowCard => 'yellow_card',
      MatchViewerEventType.setPiece => 'set_piece',
      _ => value.name,
    };
  }

  static String _phaseValue(MatchViewerPhase value) {
    return switch (value) {
      MatchViewerPhase.openPlay => 'open_play',
      MatchViewerPhase.setPiece => 'set_piece',
      _ => value.name,
    };
  }

  static String _sideValue(MatchViewerSide value) => value.name;

  static String _playerRoleValue(MatchViewerRole value) {
    return switch (value) {
      MatchViewerRole.goalkeeper => 'GK',
      MatchViewerRole.defender => 'DF',
      MatchViewerRole.midfielder => 'MF',
      MatchViewerRole.forward => 'FW',
    };
  }

  static String _playerLineValue(MatchPlayerLine value) {
    return switch (value) {
      MatchPlayerLine.goalkeeper => 'goalkeeper',
      MatchPlayerLine.defense => 'defense',
      MatchPlayerLine.midfield => 'midfield',
      MatchPlayerLine.attack => 'attack',
    };
  }

  static String _playerStateValue(MatchViewerPlayerState value) {
    return switch (value) {
      MatchViewerPlayerState.sentOff => 'sent_off',
      _ => value.name,
    };
  }

  static String _playbackStageValue(MatchPlaybackStage value) => value.name;

  static String _cameraPresetValue(MatchCameraPreset value) {
    return switch (value) {
      MatchCameraPreset.attackPush => 'attack_push',
      MatchCameraPreset.boxZoom => 'box_zoom',
      MatchCameraPreset.goalCelebration => 'goal_celebration',
      MatchCameraPreset.assistantFlag => 'assistant_flag',
      MatchCameraPreset.varReplay => 'var_replay',
      _ => value.name,
    };
  }
}
