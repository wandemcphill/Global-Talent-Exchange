import 'package:just_audio/just_audio.dart';
import 'package:shared_preferences/shared_preferences.dart';

const String ownerAlertWhistleAsset = 'assets/media/gtex_owner_alert_whistle.wav';
const String _mutedKey = 'gtex.owner.alerts.muted';
const String _heardKey = 'gtex.owner.alerts.heard';
const int _heardCap = 200;

/// Plays the matchday whistle for new urgent owner alerts; mute and heard ids persist per device.
abstract class OwnerAlertSound {
  Future<bool> isMuted();

  Future<void> setMuted(bool muted);

  /// Ids already whistled for on this device.
  Future<Set<String>> heard();

  Future<void> markHeard(Iterable<String> ids);

  Future<void> play();
}

class DeviceOwnerAlertSound implements OwnerAlertSound {
  DeviceOwnerAlertSound({AudioPlayer? player}) : _player = player;

  AudioPlayer? _player;

  @override
  Future<bool> isMuted() async => (await SharedPreferences.getInstance()).getBool(_mutedKey) ?? false;

  @override
  Future<void> setMuted(bool muted) async => (await SharedPreferences.getInstance()).setBool(_mutedKey, muted);

  @override
  Future<Set<String>> heard() async => ((await SharedPreferences.getInstance()).getStringList(_heardKey) ?? const <String>[]).toSet();

  @override
  Future<void> markHeard(Iterable<String> ids) async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    final List<String> all = <String>{...prefs.getStringList(_heardKey) ?? const <String>[], ...ids}.toList();
    await prefs.setStringList(_heardKey, all.length > _heardCap ? all.sublist(all.length - _heardCap) : all);
  }

  @override
  Future<void> play() async {
    try {
      final AudioPlayer player = _player ??= AudioPlayer();
      await player.setAsset(ownerAlertWhistleAsset);
      await player.setVolume(0.8);
      await player.play();
    } catch (_) {
      // Browsers can block autoplay until the first tap; the alert stays visible either way.
    }
  }
}
