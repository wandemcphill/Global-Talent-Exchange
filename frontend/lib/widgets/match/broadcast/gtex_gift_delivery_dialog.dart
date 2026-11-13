import 'dart:async';

import 'package:flutter/material.dart';
import 'package:just_audio/just_audio.dart';
import 'package:video_player/video_player.dart';

import '../../../data/match_gift_api.dart';
import '../../../ui_gtex/ui_gtex.dart';

const Map<String, String> _giftFilms = <String, String>{
  'super_eagle': 'assets/gifting/films/gtex-gift-super-eagle.mp4',
  'black_jaguar': 'assets/gifting/films/gtex-gift-black-jaguar.mp4',
  'white_tiger': 'assets/gifting/films/gtex-gift-white-tiger.mp4',
  'polar_bear': 'assets/gifting/films/gtex-gift-polar-bear.mp4',
};

const Map<String, String> _giftSounds = <String, String>{
  'super_eagle': 'assets/gifting/sounds/eagle_scream.wav',
  'black_jaguar': 'assets/gifting/sounds/jaguar_roar.wav',
  'white_tiger': 'assets/gifting/sounds/white_tiger_roar.wav',
  'polar_bear': 'assets/gifting/sounds/polar_bear_roar.wav',
};

/// Animated confirmation shown after the gift API confirms a send.
class GtexGiftDeliveryDialog extends StatefulWidget {
  const GtexGiftDeliveryDialog({
    super.key,
    required this.gift,
    required this.receipt,
  });

  final MatchGiftCatalogItem gift;
  final MatchGiftReceipt receipt;

  static Future<void> show(
    BuildContext context, {
    required MatchGiftCatalogItem gift,
    required MatchGiftReceipt receipt,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      barrierColor: Colors.black.withValues(alpha: 0.78),
      builder: (BuildContext context) => GtexGiftDeliveryDialog(
        gift: gift,
        receipt: receipt,
      ),
    );
  }

  @override
  State<GtexGiftDeliveryDialog> createState() => _GtexGiftDeliveryDialogState();
}

class _GtexGiftDeliveryDialogState extends State<GtexGiftDeliveryDialog> {
  VideoPlayerController? _video;
  AudioPlayer? _audio;
  bool _videoReady = false;

  @override
  void initState() {
    super.initState();
    final String? film = _giftFilms[widget.gift.key];
    final String? sound = _giftSounds[widget.gift.key];
    if (film != null) unawaited(_startFilm(film));
    if (sound != null) unawaited(_startSound(sound));
  }

  Future<void> _startFilm(String film) async {
    final VideoPlayerController controller = VideoPlayerController.asset(film);
    _video = controller;
    try {
      await controller.initialize();
      if (!mounted) return;
      await controller.setLooping(false);
      setState(() => _videoReady = true);
      await controller.play();
    } catch (_) {
      // The receipt still confirms the gift if the film cannot start.
    }
  }

  Future<void> _startSound(String sound) async {
    final AudioPlayer player = AudioPlayer();
    _audio = player;
    try {
      await player.setAsset(sound);
      await player.play();
    } catch (_) {
      // A missing sound file must not block the gift receipt.
    }
  }

  @override
  void dispose() {
    unawaited(_video?.dispose() ?? Future<void>.value());
    unawaited(_audio?.dispose() ?? Future<void>.value());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final MatchGiftCatalogItem gift = widget.gift;
    final MatchGiftReceipt receipt = widget.receipt;
    final Color accent = switch (gift.rarity.toLowerCase()) {
      'rare' => const Color(0xFF69C7FF),
      'epic' => const Color(0xFFC29BFF),
      'legendary' => const Color(0xFFFFC96B),
      'mythic' => const Color(0xFFFF8EAB),
      _ => GtexColors.gold,
    };
    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.symmetric(horizontal: 22, vertical: 24),
      child: TweenAnimationBuilder<double>(
        tween: Tween<double>(begin: 0.82, end: 1),
        duration: const Duration(milliseconds: 420),
        curve: Curves.easeOutBack,
        builder: (BuildContext context, double value, Widget? child) =>
            Transform.scale(scale: value, child: child),
        child: Container(
          padding: const EdgeInsets.all(22),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[Color(0xFF192942), Color(0xFF0B1321), Color(0xFF080E18)],
            ),
            borderRadius: BorderRadius.circular(26),
            border: Border.all(color: accent.withValues(alpha: 0.8), width: 1.4),
            boxShadow: <BoxShadow>[
              BoxShadow(color: accent.withValues(alpha: 0.22), blurRadius: 36),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              const Text(
                'GTEX GIFT DELIVERY',
                style: TextStyle(color: Color(0xFFE8C979), fontSize: 10, letterSpacing: 2.5, fontWeight: FontWeight.w900),
              ),
              const SizedBox(height: 18),
              if (_videoReady && _video != null)
                ClipRRect(
                  borderRadius: BorderRadius.circular(18),
                  child: AspectRatio(
                    aspectRatio: _video!.value.aspectRatio == 0 ? 16 / 9 : _video!.value.aspectRatio,
                    child: VideoPlayer(_video!),
                  ),
                )
              else
                Stack(
                alignment: Alignment.center,
                children: <Widget>[
                  Container(
                    width: 150,
                    height: 150,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(colors: <Color>[accent.withValues(alpha: 0.25), Colors.transparent]),
                      border: Border.all(color: accent.withValues(alpha: 0.35)),
                    ),
                  ),
                  Container(
                    width: 104,
                    height: 104,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(32),
                      color: accent.withValues(alpha: 0.12),
                      border: Border.all(color: accent, width: 1.5),
                    ),
                    child: Icon(_icon(gift.key), size: 56, color: accent),
                  ),
                  const Positioned(
                    right: 6,
                    bottom: 6,
                    child: CircleAvatar(
                      radius: 18,
                      backgroundColor: Color(0xFF0D1A2A),
                      child: Icon(Icons.check_rounded, color: Color(0xFF7DE0AD)),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 18),
              const Text('GIFT SENT SUCCESSFULLY', style: TextStyle(color: Color(0xFF7DE0AD), fontWeight: FontWeight.w900, fontSize: 11, letterSpacing: 1.6)),
              const SizedBox(height: 7),
              Text(receipt.giftDisplayName, textAlign: TextAlign.center, style: Theme.of(context).textTheme.headlineSmall?.copyWith(color: Colors.white, fontWeight: FontWeight.w900)),
              const SizedBox(height: 7),
              Text('Delivered to ${receipt.recipientLabel}', textAlign: TextAlign.center, style: const TextStyle(color: Color(0xFFB3C0D2), fontSize: 13)),
              const SizedBox(height: 18),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 13),
                decoration: BoxDecoration(color: Colors.black.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(14), border: Border.all(color: accent.withValues(alpha: 0.28))),
                child: Row(
                  children: <Widget>[
                    Icon(Icons.account_balance_wallet_outlined, color: accent, size: 20),
                    const SizedBox(width: 10),
                    const Expanded(child: Text('Confirmed total', style: TextStyle(color: Color(0xFFB3C0D2), fontSize: 12))),
                    Text('${receipt.grossAmount} ${receipt.currencyLabel}', style: TextStyle(color: accent, fontWeight: FontWeight.w900, fontSize: 13)),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              const Text('GTEX has confirmed the gift transaction.', textAlign: TextAlign.center, style: TextStyle(color: Color(0xFF8798AE), fontSize: 11)),
              const SizedBox(height: 18),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  key: const Key('gtex-gift-delivery-close'),
                  onPressed: () => Navigator.of(context).pop(),
                  style: FilledButton.styleFrom(backgroundColor: accent, foregroundColor: const Color(0xFF10131B), padding: const EdgeInsets.symmetric(vertical: 14)),
                  child: const Text('Back to the match', style: TextStyle(fontWeight: FontWeight.w900)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  IconData _icon(String key) {
    if (key.contains('whistle')) return Icons.sports;
    if (key.contains('chant')) return Icons.campaign_rounded;
    if (key.contains('goal') || key.contains('boot')) return Icons.sports_soccer_rounded;
    if (key.contains('legend') || key.contains('award') || key.contains('dor')) return Icons.workspace_premium_rounded;
    if (key.contains('tactic') || key.contains('midfield')) return Icons.auto_awesome_motion_rounded;
    return Icons.card_giftcard_rounded;
  }
}
