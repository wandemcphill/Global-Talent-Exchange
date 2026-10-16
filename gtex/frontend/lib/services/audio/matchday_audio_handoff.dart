import 'dart:async';

import 'gtex_audio_context.dart';
import 'gtex_audio_mixer.dart';

/// Broadcast Audio Stem Frame Contract (aligns with backend schemas)
class BroadcastAudioStemFrame {
  const BroadcastAudioStemFrame({
    required this.stemType,
    required this.cueText,
    required this.speakerRole,
    required this.voiceProfile,
    required this.speechRate,
    required this.intensity,
    required this.interruptPriority,
    this.audioUrl,
  });

  final String stemType; // commentary, crowd, stadium_fx
  final String cueText;
  final String speakerRole; // lead, analyst, stadium_announcer
  final String voiceProfile;
  final double speechRate;
  final double intensity; // 0.0 - 1.0
  final int interruptPriority; // 0 - 100
  final String? audioUrl;

  Map<String, Object?> toJson() => <String, Object?>{
        'stem_type': stemType,
        'cue_text': cueText,
        'speaker_role': speakerRole,
        'voice_profile': voiceProfile,
        'speech_rate': speechRate,
        'intensity': intensity,
        'interrupt_priority': interruptPriority,
        'audio_url': audioUrl,
      };

  factory BroadcastAudioStemFrame.fromJson(Map<String, Object?> json) {
    return BroadcastAudioStemFrame(
      stemType: json['stem_type'] as String? ?? 'commentary',
      cueText: json['cue_text'] as String? ?? '',
      speakerRole: json['speaker_role'] as String? ?? 'lead',
      voiceProfile: json['voice_profile'] as String? ?? 'standard',
      speechRate: (json['speech_rate'] as num?)?.toDouble() ?? 1.0,
      intensity: (json['intensity'] as num?)?.toDouble() ?? 0.5,
      interruptPriority: json['interrupt_priority'] as int? ?? 50,
      audioUrl: json['audio_url'] as String?,
    );
  }
}

class MatchdayAudioHandoff {
  MatchdayAudioHandoff({
    required GtexAudioMixer mixer,
    required Function(GtexAudioContext context) onContextChanged,
    required Function() onMixerUpdated,
  })  : _mixer = mixer,
        _onContextChanged = onContextChanged,
        _onMixerUpdated = onMixerUpdated;

  final GtexAudioMixer _mixer;
  final Function(GtexAudioContext context) _onContextChanged;
  final Function() _onMixerUpdated;

  bool _inMatchContext = false;
  String? _activeMatchKey;
  BroadcastAudioStemFrame? _lastStemFrame;
  GtexAudioContext? _previousContext;
  Timer? _duckRestoreTimer;

  bool get inMatchContext => _inMatchContext;
  String? get activeMatchKey => _activeMatchKey;
  BroadcastAudioStemFrame? get lastStemFrame => _lastStemFrame;
  GtexAudioContext? get previousContext => _previousContext;

  void duckMusic({
    double factor = 0.125,
    Duration? autoRestoreDuration,
  }) {
    _duckRestoreTimer?.cancel();
    _mixer.duckMusic(factor: factor);
    _onMixerUpdated();

    if (autoRestoreDuration != null) {
      _duckRestoreTimer = Timer(autoRestoreDuration, () {
        restoreMusic();
      });
    }
  }

  void restoreMusic() {
    _duckRestoreTimer?.cancel();
    _mixer.restoreMusic();
    _onMixerUpdated();
  }

  void enterMatchContext(
    String matchKey, {
    GtexAudioContext? currentContext,
  }) {
    _inMatchContext = true;
    _activeMatchKey = matchKey;
    if (currentContext != null && currentContext != GtexAudioContext.matchday) {
      _previousContext = currentContext;
    }
    duckMusic(factor: 0.125);
    _onContextChanged(GtexAudioContext.matchday);
    _onMixerUpdated();
  }

  void leaveMatchContext() {
    _duckRestoreTimer?.cancel();
    _inMatchContext = false;
    _activeMatchKey = null;
    _mixer.restoreMusic();

    final GtexAudioContext targetContext =
        _previousContext ?? GtexAudioContext.home;
    _previousContext = null;

    _onContextChanged(targetContext);
    _onMixerUpdated();
  }

  /// Process incoming backend audio stem frame metadata without pretending
  /// un-implemented audio playback is occurring.
  void processStemFrame(BroadcastAudioStemFrame frame) {
    _lastStemFrame = frame;
    if (frame.stemType == 'commentary' && frame.interruptPriority >= 80) {
      // High priority commentary deep duck with deterministic 3.5s auto-restore
      duckMusic(
        factor: 0.05,
        autoRestoreDuration: const Duration(milliseconds: 3500),
      );
    }
  }

  /// Event sting support (e.g. goal whistle, full time)
  void triggerEventSting(String stingType) {
    if (stingType == 'goal') {
      // Complete silence music for goal cheer with deterministic 4s auto-restore
      duckMusic(
        factor: 0.0,
        autoRestoreDuration: const Duration(seconds: 4),
      );
    } else if (stingType == 'whistle' || stingType == 'foul') {
      duckMusic(
        factor: 0.1,
        autoRestoreDuration: const Duration(seconds: 2),
      );
    }
  }
}
