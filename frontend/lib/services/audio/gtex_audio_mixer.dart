import 'dart:math';

class GtexAudioMixer {
  GtexAudioMixer({
    double masterVolume = 1.0,
    double musicVolume = 0.22,
    double commentaryVolume = 1.0,
    double crowdVolume = 0.8,
    double effectsVolume = 0.8,
  })  : _masterVolume = masterVolume.clamp(0.0, 1.0),
        _musicVolume = musicVolume.clamp(0.0, 1.0),
        _commentaryVolume = commentaryVolume.clamp(0.0, 1.0),
        _crowdVolume = crowdVolume.clamp(0.0, 1.0),
        _effectsVolume = effectsVolume.clamp(0.0, 1.0);

  double _masterVolume;
  double _musicVolume;
  double _commentaryVolume;
  double _crowdVolume;
  double _effectsVolume;

  /// Ducking factor applied to music channel (1.0 = normal, ~0.125 = -18dB ducked)
  double _musicDuckingFactor = 1.0;

  double get masterVolume => _masterVolume;
  set masterVolume(double value) => _masterVolume = value.clamp(0.0, 1.0);

  double get musicVolume => _musicVolume;
  set musicVolume(double value) => _musicVolume = value.clamp(0.0, 1.0);

  double get commentaryVolume => _commentaryVolume;
  set commentaryVolume(double value) => _commentaryVolume = value.clamp(0.0, 1.0);

  double get crowdVolume => _crowdVolume;
  set crowdVolume(double value) => _crowdVolume = value.clamp(0.0, 1.0);

  double get effectsVolume => _effectsVolume;
  set effectsVolume(double value) => _effectsVolume = value.clamp(0.0, 1.0);

  double get musicDuckingFactor => _musicDuckingFactor;
  set musicDuckingFactor(double value) => _musicDuckingFactor = value.clamp(0.0, 1.0);

  /// Calculated output volume for Music channel
  double get effectiveMusicVolume =>
      (_masterVolume * _musicVolume * _musicDuckingFactor).clamp(0.0, 1.0);

  /// Calculated output volume for Commentary channel
  double get effectiveCommentaryVolume =>
      (_masterVolume * _commentaryVolume).clamp(0.0, 1.0);

  /// Calculated output volume for Crowd channel
  double get effectiveCrowdVolume =>
      (_masterVolume * _crowdVolume).clamp(0.0, 1.0);

  /// Calculated output volume for Effects channel
  double get effectiveEffectsVolume =>
      (_masterVolume * _effectsVolume).clamp(0.0, 1.0);

  void duckMusic({double factor = 0.125}) {
    _musicDuckingFactor = factor.clamp(0.0, 1.0);
  }

  void restoreMusic() {
    _musicDuckingFactor = 1.0;
  }

  Map<String, double> toMap() {
    return <String, double>{
      'master': _masterVolume,
      'music': _musicVolume,
      'commentary': _commentaryVolume,
      'crowd': _crowdVolume,
      'effects': _effectsVolume,
    };
  }

  void updateFromMap(Map<String, dynamic> map) {
    if (map.containsKey('master') && map['master'] is num) {
      _masterVolume = (map['master'] as num).toDouble().clamp(0.0, 1.0);
    }
    if (map.containsKey('music') && map['music'] is num) {
      _musicVolume = (map['music'] as num).toDouble().clamp(0.0, 1.0);
    }
    if (map.containsKey('commentary') && map['commentary'] is num) {
      _commentaryVolume = (map['commentary'] as num).toDouble().clamp(0.0, 1.0);
    }
    if (map.containsKey('crowd') && map['crowd'] is num) {
      _crowdVolume = (map['crowd'] as num).toDouble().clamp(0.0, 1.0);
    }
    if (map.containsKey('effects') && map['effects'] is num) {
      _effectsVolume = (map['effects'] as num).toDouble().clamp(0.0, 1.0);
    }
  }
}
