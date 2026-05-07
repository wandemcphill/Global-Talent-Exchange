import 'package:flutter/foundation.dart';
import 'package:just_audio/just_audio.dart';
import 'package:shared_preferences/shared_preferences.dart';

abstract class AmbientAudioState extends ChangeNotifier {
  bool get isMuted;
  bool get isPlaying;
  bool get isReady;
  bool get isLoading;
  Object? get lastError;

  Future<void> bootstrap();
  Future<void> preload();
  Future<void> play();
  Future<void> pause();
  Future<void> toggleMuted();
}

class AmbientAudioController extends ChangeNotifier
    implements AmbientAudioState {
  AmbientAudioController({
    AudioPlayer? player,
    SharedPreferences? preferences,
    this.assetPath = 'assets/media/gtex_stadium_ambient.mp3',
    this.defaultVolume = 0.22,
  }) : _player = player ?? AudioPlayer(),
       _preferences = preferences;

  static const String preferenceKey = 'gtex.ambient_audio.muted';

  final AudioPlayer _player;
  SharedPreferences? _preferences;
  final String assetPath;
  final double defaultVolume;

  bool _isMuted = true;
  bool _isPlaying = false;
  bool _isReady = false;
  bool _isLoading = false;
  bool _bootstrapped = false;
  Object? _lastError;

  @override
  bool get isMuted => _isMuted;

  @override
  bool get isPlaying => _isPlaying;

  @override
  bool get isReady => _isReady;

  @override
  bool get isLoading => _isLoading;

  @override
  Object? get lastError => _lastError;

  @override
  Future<void> bootstrap() async {
    if (_bootstrapped) {
      return;
    }
    _bootstrapped = true;
    try {
      _preferences ??= await SharedPreferences.getInstance();
      _isMuted = _preferences?.getBool(preferenceKey) ?? true;
    } catch (error) {
      _lastError = error;
      _isMuted = true;
    }
    if (kIsWeb && _isMuted) {
      notifyListeners();
      return;
    }
    await preload();
    if (!_isMuted) {
      await play();
    }
  }

  @override
  Future<void> preload() async {
    if (_isReady || _isLoading) {
      return;
    }
    _isLoading = true;
    _lastError = null;
    notifyListeners();
    try {
      await _player.setAsset(assetPath);
      await _player.setLoopMode(LoopMode.one);
      await _player.setVolume(_isMuted ? 0 : defaultVolume);
      _isReady = true;
    } catch (error) {
      _lastError = error;
      _isReady = false;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  @override
  Future<void> play() async {
    if (!_isReady) {
      await preload();
    }
    if (!_isReady || _isMuted) {
      return;
    }
    try {
      await _player.setVolume(defaultVolume);
      await _player.play();
      _isPlaying = true;
    } catch (error) {
      _lastError = error;
      _isPlaying = false;
    }
    notifyListeners();
  }

  @override
  Future<void> pause() async {
    try {
      await _player.pause();
    } catch (error) {
      _lastError = error;
    }
    _isPlaying = false;
    notifyListeners();
  }

  @override
  Future<void> toggleMuted() async {
    final bool nextMuted = !_isMuted;
    _isMuted = nextMuted;
    try {
      await _preferences?.setBool(preferenceKey, nextMuted);
    } catch (error) {
      _lastError = error;
    }
    if (nextMuted) {
      try {
        await _player.setVolume(0);
        await _player.pause();
      } catch (error) {
        _lastError = error;
      }
      _isPlaying = false;
    } else {
      await play();
    }
    notifyListeners();
  }

  @override
  void dispose() {
    _player.dispose();
    super.dispose();
  }
}
