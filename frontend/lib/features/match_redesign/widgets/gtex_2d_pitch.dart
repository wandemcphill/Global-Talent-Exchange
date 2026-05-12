import 'package:flutter/material.dart';

import '../data/gtex_match_models.dart';

class Gtex2dPitch extends StatelessWidget {
  const Gtex2dPitch({
    super.key,
    required this.match,
    required this.onPlayerSelected,
  });

  final GtexLiveMatchState match;
  final ValueChanged<String> onPlayerSelected;

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 16 / 10,
      child: LayoutBuilder(
        builder: (context, constraints) {
          return Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(28),
              gradient: const LinearGradient(
                colors: [Color(0xFF123B26), Color(0xFF0A271A)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              border: Border.all(color: Colors.white.withOpacity(.14)),
              boxShadow: const [BoxShadow(blurRadius: 36, color: Colors.black54)],
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(28),
              child: Stack(
                children: [
                  const Positioned.fill(child: _PitchPainterLayer()),
                  for (final player in match.pitchPlayers)
                    Positioned(
                      left: player.x * constraints.maxWidth - 18,
                      top: player.y * constraints.maxHeight - 18,
                      child: _PitchPlayerMarker(
                        player: player,
                        selected: match.selectedPlayerId == player.playerId,
                        onTap: () => onPlayerSelected(player.playerId),
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

class _PitchPainterLayer extends StatelessWidget {
  const _PitchPainterLayer();

  @override
  Widget build(BuildContext context) {
    return CustomPaint(painter: _PitchPainter());
  }
}

class _PitchPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final line = Paint()
      ..color = Colors.white.withOpacity(.24)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.4;
    final glow = Paint()
      ..color = const Color(0xFF18FF88).withOpacity(.06)
      ..style = PaintingStyle.fill;

    canvas.drawRect(Offset.zero & size, Paint()..color = Colors.transparent);
    for (var i = 0; i < 8; i++) {
      final left = size.width * i / 8;
      canvas.drawRect(Rect.fromLTWH(left, 0, size.width / 8, size.height), glow..color = const Color(0xFF18FF88).withOpacity(i.isEven ? .035 : .012));
    }
    canvas.drawRect(Rect.fromLTWH(16, 16, size.width - 32, size.height - 32), line);
    canvas.drawLine(Offset(size.width / 2, 16), Offset(size.width / 2, size.height - 16), line);
    canvas.drawCircle(Offset(size.width / 2, size.height / 2), size.height * .13, line);
    canvas.drawCircle(Offset(size.width / 2, size.height / 2), 3, Paint()..color = Colors.white.withOpacity(.42));

    canvas.drawRect(Rect.fromLTWH(16, size.height * .31, size.width * .12, size.height * .38), line);
    canvas.drawRect(Rect.fromLTWH(size.width - 16 - size.width * .12, size.height * .31, size.width * .12, size.height * .38), line);
    canvas.drawRect(Rect.fromLTWH(16, size.height * .40, size.width * .045, size.height * .20), line);
    canvas.drawRect(Rect.fromLTWH(size.width - 16 - size.width * .045, size.height * .40, size.width * .045, size.height * .20), line);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _PitchPlayerMarker extends StatelessWidget {
  const _PitchPlayerMarker({required this.player, required this.selected, required this.onTap});

  final GtexPitchPlayer player;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = player.isHome ? const Color(0xFF18FF88) : const Color(0xFFFFD166);
    return Tooltip(
      message: '${player.name} #${player.shirtNumber}',
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          width: selected ? 44 : 36,
          height: selected ? 44 : 36,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: color,
            border: Border.all(color: Colors.white, width: player.hasBall ? 3 : 1.5),
            boxShadow: [
              if (selected || player.hasBall) BoxShadow(color: color.withOpacity(.55), blurRadius: 18, spreadRadius: 2),
            ],
          ),
          child: Center(
            child: Text('${player.shirtNumber}', style: const TextStyle(color: Color(0xFF06100C), fontWeight: FontWeight.w900, fontSize: 12)),
          ),
        ),
      ),
    );
  }
}
