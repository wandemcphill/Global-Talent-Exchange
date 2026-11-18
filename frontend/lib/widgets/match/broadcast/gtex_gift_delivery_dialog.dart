import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
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

const String _impactSound = 'assets/gifting/sounds/gift_impact.wav';
const String _exitSound = 'assets/gifting/sounds/gift_exit.wav';

/// Full-screen gift celebration shown after the gift API confirms a send.
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
    return showGeneralDialog<void>(
      context: context,
      barrierDismissible: false,
      barrierLabel: 'Gift celebration',
      barrierColor: Colors.black,
      transitionDuration: Duration.zero,
      pageBuilder: (BuildContext context, Animation<double> _, Animation<double> _) {
        return GtexGiftDeliveryDialog(gift: gift, receipt: receipt);
      },
    );
  }

  @override
  State<GtexGiftDeliveryDialog> createState() => _GtexGiftDeliveryDialogState();
}

class _GtexGiftDeliveryDialogState extends State<GtexGiftDeliveryDialog>
    with TickerProviderStateMixin {
  VideoPlayerController? _video;
  AudioPlayer? _audio;
  bool _videoReady = false;
  bool _closing = false;
  late final AnimationController _burst;
  late final AnimationController _exit;

  @override
  void initState() {
    super.initState();
    _burst = AnimationController(vsync: this, duration: const Duration(milliseconds: 1400))
      ..forward();
    _exit = AnimationController(vsync: this, duration: const Duration(milliseconds: 420));
    final bool widgetTest = WidgetsBinding.instance.runtimeType.toString().contains('Test');
    if (!widgetTest) {
      final String? film = _giftFilms[widget.gift.key];
      final String? signature = _giftSounds[widget.gift.key];
      if (film != null) unawaited(_startFilm(film));
      unawaited(_startSound(_impactSound));
      if (signature != null) unawaited(_startSound(signature, replace: false));
      HapticFeedback.heavyImpact();
    }
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

  Future<void> _startSound(String sound, {bool replace = true}) async {
    if (replace) {
      await _audio?.dispose();
      _audio = null;
    }
    final AudioPlayer player = AudioPlayer();
    if (replace) _audio = player;
    try {
      await player.setAsset(sound);
      await player.play();
      if (!replace) unawaited(player.playerStateStream.firstWhere((PlayerState state) => state.processingState == ProcessingState.completed).then((_) => player.dispose()));
    } catch (_) {
      await player.dispose();
    }
  }

  Future<void> _close() async {
    if (_closing) return;
    _closing = true;
    unawaited(_startSound(_exitSound));
    await _exit.forward();
    if (mounted) Navigator.of(context).pop();
  }

  @override
  void dispose() {
    _burst.dispose();
    _exit.dispose();
    unawaited(_video?.dispose() ?? Future<void>.value());
    unawaited(_audio?.dispose() ?? Future<void>.value());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final MatchGiftCatalogItem gift = widget.gift;
    final MatchGiftReceipt receipt = widget.receipt;
    final Color accent = _accentFor(gift.rarity);
    return Material(
      color: Colors.black,
      child: AnimatedBuilder(
        animation: Listenable.merge(<Listenable>[_burst, _exit]),
        builder: (BuildContext context, Widget? _) {
          final double exit = Curves.easeIn.transform(_exit.value);
          return Opacity(
            opacity: 1 - exit,
            child: Transform.scale(
              scale: 1 + exit * 0.08,
              child: Stack(
                fit: StackFit.expand,
                children: <Widget>[
                  if (_videoReady && _video != null)
                    FittedBox(
                      fit: BoxFit.cover,
                      child: SizedBox(
                        width: _video!.value.size.width,
                        height: _video!.value.size.height,
                        child: VideoPlayer(_video!),
                      ),
                    )
                  else
                    DecoratedBox(
                      decoration: BoxDecoration(
                        gradient: RadialGradient(
                          center: const Alignment(0, -0.15),
                          radius: 1.05,
                          colors: <Color>[accent.withValues(alpha: 0.35), const Color(0xFF070B12), Colors.black],
                        ),
                      ),
                    ),
                  CustomPaint(painter: _GiftBurstPainter(progress: _burst.value, color: accent)),
                  DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: <Color>[
                          Colors.black.withValues(alpha: 0.15),
                          Colors.transparent,
                          Colors.black.withValues(alpha: 0.82),
                        ],
                      ),
                    ),
                  ),
                  SafeArea(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(22, 18, 22, 18),
                      child: Column(
                        children: <Widget>[
                          const Spacer(),
                          if (!_videoReady) _GiftHero(gift: gift, accent: accent, progress: _burst.value),
                          const SizedBox(height: 22),
                          Text(
                            '${gift.rarity.toUpperCase()} GIFT',
                            style: TextStyle(color: accent, fontSize: 12, letterSpacing: 3.2, fontWeight: FontWeight.w900),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            receipt.giftDisplayName,
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                              color: Colors.white,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Delivered to ${receipt.recipientLabel}',
                            textAlign: TextAlign.center,
                            style: const TextStyle(color: Color(0xFFE7EDF5), fontSize: 15, fontWeight: FontWeight.w600),
                          ),
                          const SizedBox(height: 14),
                          Text(
                            '${receipt.grossAmount} ${receipt.currencyLabel}',
                            style: TextStyle(color: accent, fontWeight: FontWeight.w900, fontSize: 16),
                          ),
                          const SizedBox(height: 22),
                          SizedBox(
                            width: double.infinity,
                            child: FilledButton(
                              key: const Key('gtex-gift-delivery-close'),
                              onPressed: _close,
                              style: FilledButton.styleFrom(
                                backgroundColor: accent,
                                foregroundColor: const Color(0xFF10131B),
                                padding: const EdgeInsets.symmetric(vertical: 16),
                              ),
                              child: const Text('Back to the match', style: TextStyle(fontWeight: FontWeight.w900)),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

class _GiftHero extends StatelessWidget {
  const _GiftHero({required this.gift, required this.accent, required this.progress});

  final MatchGiftCatalogItem gift;
  final Color accent;
  final double progress;

  @override
  Widget build(BuildContext context) {
    final double scale = 0.72 + Curves.elasticOut.transform(progress.clamp(0, 1)) * 0.28;
    return Transform.scale(
      scale: scale,
      child: Container(
        width: 148,
        height: 148,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: RadialGradient(colors: <Color>[accent.withValues(alpha: 0.55), accent.withValues(alpha: 0.05)]),
          border: Border.all(color: accent, width: 2),
          boxShadow: <BoxShadow>[BoxShadow(color: accent.withValues(alpha: 0.45), blurRadius: 36)],
        ),
        child: Icon(_giftIcon(gift.key), size: 72, color: Colors.white),
      ),
    );
  }
}

class _GiftBurstPainter extends CustomPainter {
  _GiftBurstPainter({required this.progress, required this.color});

  final double progress;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final Offset center = Offset(size.width / 2, size.height * 0.38);
    final Paint ring = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3
      ..color = color.withValues(alpha: (1 - progress).clamp(0, 1));
    canvas.drawCircle(center, 40 + progress * size.shortestSide * 0.72, ring);
    if (progress > 0.12) {
      final double second = ((progress - 0.12) / 0.88).clamp(0, 1);
      canvas.drawCircle(
        center,
        20 + second * size.shortestSide * 0.5,
        ring..color = Colors.white.withValues(alpha: (1 - second) * 0.7),
      );
    }
    final Paint spark = Paint()..style = PaintingStyle.fill;
    const int count = 78;
    for (int i = 0; i < count; i += 1) {
      final double angle = (math.pi * 2 * i) / count;
      final double distance = progress * (90 + (i % 5) * 28);
      final double alpha = (1 - progress).clamp(0, 1);
      spark.color = (i.isEven ? color : Colors.white).withValues(alpha: alpha);
      canvas.drawCircle(center + Offset(math.cos(angle), math.sin(angle)) * distance, i.isEven ? 3.2 : 1.8, spark);
    }
    if (progress < 0.22) {
      canvas.drawRect(
        Offset.zero & size,
        Paint()..color = Colors.white.withValues(alpha: (1 - progress / 0.22) * 0.72),
      );
    }
  }

  @override
  bool shouldRepaint(_GiftBurstPainter oldDelegate) => oldDelegate.progress != progress || oldDelegate.color != color;
}

Color _accentFor(String rarity) {
  return switch (rarity.toLowerCase()) {
    'rare' => const Color(0xFF69C7FF),
    'epic' => const Color(0xFFC29BFF),
    'legendary' => const Color(0xFFFFC96B),
    'mythic' => const Color(0xFFFF8EAB),
    _ => GtexColors.gold,
  };
}

IconData _giftIcon(String key) {
  if (key.contains('whistle')) return Icons.sports;
  if (key.contains('chant')) return Icons.campaign_rounded;
  if (key.contains('goal') || key.contains('boot')) return Icons.sports_soccer_rounded;
  if (key.contains('legend') || key.contains('award') || key.contains('dor')) return Icons.workspace_premium_rounded;
  if (key.contains('tactic') || key.contains('midfield')) return Icons.auto_awesome_motion_rounded;
  if (key.contains('eagle')) return Icons.flight;
  if (key.contains('jet')) return Icons.flight_takeoff_rounded;
  return Icons.card_giftcard_rounded;
}
