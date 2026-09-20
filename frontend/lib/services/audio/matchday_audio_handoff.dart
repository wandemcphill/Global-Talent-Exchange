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

  bool get inMatchContext => _inMatchContext;
  String? get activeMatchKey => _activeMatchKey;
  BroadcastAudioStemFrame? get lastStemFrame => _lastStemFrame;

  void duckMusic({double factor = 0.125}) {
    _mixer.duckMusic(factor: factor);
    _onMixerUpdated();
  }

  void restoreMusic() {
    _mixer.restoreMusic();
    _onMixerUpdated();
  }

  void enterMatchContext(String matchKey) {
    _inMatchContext = true;
    _activeMatchKey = matchKey;
    _mixer.duckMusic();
    _onContextChanged(GtexAudioContext.matchday);
    _onMixerUpdated();
  }

  void leaveMatchContext() {
    _inMatchContext = false;
    _activeMatchKey = null;
    _mixer.restoreMusic();
    _onContextChanged(GtexAudioContext.home);
    _onMixerUpdated();
  }

  /// Process incoming backend audio stem frame metadata without pretending
  /// un-implemented audio playback is occurring.
  void processStemFrame(BroadcastAudioStemFrame frame) {
    _lastStemFrame = frame;
    if (frame.stemType == 'commentary' && frame.interruptPriority >= 80) {
      duckMusic(factor: 0.05); // High priority commentary deep duck
    }
  }

  /// Event sting support (e.g. goal whistle, full time)
  void triggerEventSting(String stingType) {
    if (stingType == 'goal') {
      duckMusic(factor: 0.0); // Complete silence music for goal cheer
    } else if (stingType == 'whistle' || stingType == 'foul') {
      duckMusic(factor: 0.1);
    }
  }
}
