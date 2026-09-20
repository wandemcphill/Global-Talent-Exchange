import 'package:flutter/foundation.dart';
import 'package:just_audio/just_audio.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/gte_runtime_environment.dart';
import 'audio/gtex_audio_context.dart';
import 'audio/gtex_audio_mixer.dart';
import 'audio/gtex_soundtrack_catalogue.dart';
import 'audio/gtex_track_metadata.dart';
import 'audio/matchday_audio_handoff.dart';

abstract class AmbientAudioState extends ChangeNotifier {
  bool get isMuted;
  bool get isPlaying;
  bool get isReady;
  bool get isLoading;
  Object? get lastError;

  GtexAudioContext get currentContext => GtexAudioContext.home;
  GtexTrackMetadata get currentTrack => GtexSoundtrackCatalogue.fallbackTrack;
  GtexSoundtrackCatalogue get catalogue => GtexSoundtrackCatalogue();
  GtexAudioMixer get mixer => GtexAudioMixer();
  MatchdayAudioHandoff get matchdayHandoff => MatchdayAudioHandoff(
        mixer: mixer,
        onContextChanged: (_) {},
        onMixerUpdated: () {},
      );
  bool get isWebAutoplayBlocked => false;
  double get masterVolume => mixer.masterVolume;
  double get musicVolume => mixer.musicVolume;

  Future<void> bootstrap();
  Future<void> preload();
  Future<void> play();
  Future<void> pause();
  Future<void> toggleMuted();

  Future<void> setMasterVolume(double volume) async {}
  Future<void> setMusicVolume(double volume) async {}
  Future<void> setAudioContext(GtexAudioContext context) async {}
  Future<void> nextTrack() async {}
  Future<void> shuffleTrack() async {}
  Future<void> setTrack(GtexTrackMetadata track) async {}
  Future<void> resolveWebAutoplay() async {}
}

class AmbientAudioController extends ChangeNotifier
    implements AmbientAudioState {
  AmbientAudioController({
    AudioPlayer? player,
    SharedPreferences? preferences,
    GtexSoundtrackCatalogue? catalogue,
    GtexAudioMixer? mixer,
    this.assetPath = 'assets/media/gtex_stadium_ambient.mp3',
    this.defaultVolume = 0.22,
  })  : _player = player ?? AudioPlayer(),
        _preferences = preferences,
        _catalogue = catalogue ?? GtexSoundtrackCatalogue(),
        _mixer = mixer ?? GtexAudioMixer(musicVolume: defaultVolume) {
    _matchdayHandoff = MatchdayAudioHandoff(
      mixer: _mixer,
      onContextChanged: (GtexAudioContext context) {
        setAudioContext(context);
      },
      onMixerUpdated: () {
        _applyMixerVolume();
      },
    );
  }

  static const String preferenceKey = 'gtex.ambient_audio.muted';
  static const String masterVolumeKey = 'gtex.ambient_audio.master_volume';
  static const String musicVolumeKey = 'gtex.ambient_audio.music_volume';

  final AudioPlayer _player;
  SharedPreferences? _preferences;
  final GtexSoundtrackCatalogue _catalogue;
  final GtexAudioMixer _mixer;
  late final MatchdayAudioHandoff _matchdayHandoff;

  final String assetPath;
  final double defaultVolume;

  bool _isMuted = true;
  bool _isPlaying = false;
  bool _isReady = false;
  bool _isLoading = false;
  bool _bootstrapped = false;
  bool _isWebAutoplayBlocked = false;
  Object? _lastError;

  GtexAudioContext _currentContext = GtexAudioContext.home;
  late GtexTrackMetadata _currentTrack = GtexSoundtrackCatalogue.fallbackTrack;

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
  GtexAudioContext get currentContext => _currentContext;

  @override
  GtexTrackMetadata get currentTrack => _currentTrack;

  @override
  GtexSoundtrackCatalogue get catalogue => _catalogue;

  @override
  GtexAudioMixer get mixer => _mixer;

  @override
  MatchdayAudioHandoff get matchdayHandoff => _matchdayHandoff;

  @override
  bool get isWebAutoplayBlocked => _isWebAutoplayBlocked;

  @override
  double get masterVolume => _mixer.masterVolume;

  @override
  double get musicVolume => _mixer.musicVolume;

  @override
  Future<void> bootstrap() async {
    if (_bootstrapped) {
      return;
    }
    _bootstrapped = true;

    try {
      _preferences ??= await SharedPreferences.getInstance();
      _isMuted = _preferences?.getBool(preferenceKey) ?? true;
      final double storedMaster =
          _preferences?.getDouble(masterVolumeKey) ?? 1.0;
      final double storedMusic =
          _preferences?.getDouble(musicVolumeKey) ?? defaultVolume;
      _mixer.masterVolume = storedMaster;
      _mixer.musicVolume = storedMusic;
    } catch (error) {
      _lastError = error;
      _isMuted = true;
    }

    _currentTrack = _catalogue.selectTrackForContext(_currentContext);

    if (isFlutterTestEnvironment) {
      notifyListeners();
      return;
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
    if (isFlutterTestEnvironment || _isLoading) {
      return;
    }
    _isLoading = true;
    _lastError = null;
    notifyListeners();
    try {
      await _player.setAsset(_currentTrack.assetPath);
      await _player.setLoopMode(LoopMode.one);
      await _applyMixerVolume();
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
    if (isFlutterTestEnvironment) {
      return;
    }
    if (!_isReady) {
      await preload();
    }
    if (!_isReady || _isMuted) {
      return;
    }
    try {
      await _applyMixerVolume();
      await _player.play();
      _isPlaying = true;
      _isWebAutoplayBlocked = false;
    } catch (error) {
      _lastError = error;
      _isPlaying = false;
      if (kIsWeb) {
        _isWebAutoplayBlocked = true;
      }
    }
    notifyListeners();
  }

  @override
  Future<void> pause() async {
    if (isFlutterTestEnvironment) {
      return;
    }
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
    if (isFlutterTestEnvironment) {
      _isMuted = !_isMuted;
      notifyListeners();
      return;
    }
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
  Future<void> setMasterVolume(double volume) async {
    _mixer.masterVolume = volume;
    try {
      await _preferences?.setDouble(masterVolumeKey, _mixer.masterVolume);
    } catch (error) {
      _lastError = error;
    }
    await _applyMixerVolume();
    notifyListeners();
  }

  @override
  Future<void> setMusicVolume(double volume) async {
    _mixer.musicVolume = volume;
    try {
      await _preferences?.setDouble(musicVolumeKey, _mixer.musicVolume);
    } catch (error) {
      _lastError = error;
    }
    await _applyMixerVolume();
    notifyListeners();
  }

  @override
  Future<void> setAudioContext(GtexAudioContext context) async {
    if (_currentContext == context) {
      return;
    }
    _currentContext = context;

    // Check if current track supports the new context; avoid restart on rebuilds/navigation
    if (_currentTrack.contexts.contains(context)) {
      notifyListeners();
      return;
    }

    final GtexTrackMetadata nextTrack = _catalogue.selectTrackForContext(
      context,
      currentTrack: _currentTrack,
    );
    await setTrack(nextTrack);
  }

  @override
  Future<void> nextTrack() async {
    final List<GtexTrackMetadata> pool =
        _catalogue.tracksForContext(_currentContext);
    if (pool.length <= 1) {
      return;
    }
    final int currentIndex = pool.indexWhere((t) => t.id == _currentTrack.id);
    final int nextIndex = (currentIndex + 1) % pool.length;
    await setTrack(pool[nextIndex]);
  }

  @override
  Future<void> shuffleTrack() async {
    final GtexTrackMetadata nextTrack = _catalogue.selectTrackForContext(
      _currentContext,
      currentTrack: _currentTrack,
      shuffle: true,
    );
    await setTrack(nextTrack);
  }

  @override
  Future<void> setTrack(GtexTrackMetadata track) async {
    if (_currentTrack.id == track.id && _isReady) {
      return;
    }
    _currentTrack = track;
    _isReady = false;
    if (isFlutterTestEnvironment) {
      _isReady = true;
      notifyListeners();
      return;
    }
    await preload();
    if (!_isMuted) {
      await play();
    } else {
      notifyListeners();
    }
  }

  @override
  Future<void> resolveWebAutoplay() async {
    _isWebAutoplayBlocked = false;
    if (_isMuted) {
      await toggleMuted();
    } else {
      await play();
    }
  }

  Future<void> _applyMixerVolume() async {
    if (isFlutterTestEnvironment) {
      return;
    }
    final double targetVolume =
        _isMuted ? 0.0 : _mixer.effectiveMusicVolume;
    try {
      await _player.setVolume(targetVolume);
    } catch (error) {
      _lastError = error;
    }
  }

  @override
  void dispose() {
    if (!isFlutterTestEnvironment) {
      _player.dispose();
    }
    super.dispose();
  }
}
