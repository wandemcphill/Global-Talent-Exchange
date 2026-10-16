import 'package:flutter/material.dart';

import '../data/gtex_match_models.dart';
import 'gtex_match_visual_tokens.dart';

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
    if (match.pitchPlayers.isEmpty) {
      return const AspectRatio(
        aspectRatio: 16 / 9,
        child: GtexMatchEmptyFeed(
          icon: Icons.grid_on_rounded,
          title: 'Pitch feed unavailable',
          message:
              'Player positions have not been supplied by the live match authority.',
        ),
      );
    }

    return LayoutBuilder(
      builder: (context, outerConstraints) {
        final bool compact = outerConstraints.maxWidth < 620;
        return AspectRatio(
          aspectRatio: 16 / 9,
          child: LayoutBuilder(
            builder: (context, constraints) {
              return Container(
                decoration: BoxDecoration(
                  color: const Color(0xFF12371F),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: GtexMatchVisualTokens.borderStrong),
                  boxShadow: const [
                    BoxShadow(
                      color: Color(0x66000000),
                      blurRadius: 16,
                      offset: Offset(0, 8),
                    ),
                  ],
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: Stack(
                    children: [
                      const Positioned.fill(child: _PitchPainterLayer()),
                      Positioned(
                        left: 12,
                        top: 12,
                        child: _PitchFeedTag(matchId: match.matchId),
                      ),
                      for (final GtexPitchPlayer player in match.pitchPlayers)
                        Positioned(
                          left: player.x * constraints.maxWidth - 16,
                          top: player.y * constraints.maxHeight - 16,
                          child: _PitchPlayerMarker(
                            player: player,
                            selected: match.selectedPlayerId == player.playerId,
                            compact: compact,
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
      },
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
    final Paint line =
        Paint()
          ..color = const Color(0xFFE8EDF4).withOpacity(.64)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.2;
    final Paint grid =
        Paint()
          ..color = const Color(0xFFE8EDF4).withOpacity(.08)
          ..strokeWidth = .8;
    final Paint band = Paint()..style = PaintingStyle.fill;

    for (var i = 0; i < 8; i++) {
      band.color = Color(i.isEven ? 0xFF12371F : 0xFF0F301B);
      canvas.drawRect(
        Rect.fromLTWH(size.width * i / 8, 0, size.width / 8, size.height),
        band,
      );
    }
    for (var i = 1; i < 8; i++) {
      final double x = size.width * i / 8;
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), grid);
    }
    for (var i = 1; i < 6; i++) {
      final double y = size.height * i / 6;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), grid);
    }

    canvas.drawRect(
      Rect.fromLTWH(16, 16, size.width - 32, size.height - 32),
      line,
    );
    canvas.drawLine(
      Offset(size.width / 2, 16),
      Offset(size.width / 2, size.height - 16),
      line,
    );
    canvas.drawCircle(
      Offset(size.width / 2, size.height / 2),
      size.height * .13,
      line,
    );
    canvas.drawCircle(
      Offset(size.width / 2, size.height / 2),
      3,
      Paint()..color = const Color(0xFFE8EDF4),
    );

    canvas.drawRect(
      Rect.fromLTWH(16, size.height * .31, size.width * .12, size.height * .38),
      line,
    );
    canvas.drawRect(
      Rect.fromLTWH(
        size.width - 16 - size.width * .12,
        size.height * .31,
        size.width * .12,
        size.height * .38,
      ),
      line,
    );
    canvas.drawRect(
      Rect.fromLTWH(
        16,
        size.height * .40,
        size.width * .045,
        size.height * .20,
      ),
      line,
    );
    canvas.drawRect(
      Rect.fromLTWH(
        size.width - 16 - size.width * .045,
        size.height * .40,
        size.width * .045,
        size.height * .20,
      ),
      line,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _PitchPlayerMarker extends StatelessWidget {
  const _PitchPlayerMarker({
    required this.player,
    required this.selected,
    required this.compact,
    required this.onTap,
  });

  final GtexPitchPlayer player;
  final bool selected;
  final bool compact;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final Color color =
        player.isHome
            ? GtexMatchVisualTokens.live
            : GtexMatchVisualTokens.amber;
    final Widget marker = AnimatedContainer(
      duration: const Duration(milliseconds: 160),
      width: selected ? 32 : 24,
      height: selected ? 32 : 24,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: color,
        border: Border.all(
          color:
              player.hasBall
                  ? GtexMatchVisualTokens.textPrimary
                  : GtexMatchVisualTokens.surfaceBase,
          width: player.hasBall ? 3 : 1.5,
        ),
        boxShadow: [
          if (selected || player.hasBall)
            BoxShadow(color: color.withOpacity(.45), blurRadius: 14),
        ],
      ),
      child: Center(
        child: Text(
          '${player.shirtNumber}',
          style: const TextStyle(
            color: GtexMatchVisualTokens.surfaceBase,
            fontWeight: FontWeight.w900,
            fontSize: 10,
            fontFamily: 'JetBrains Mono',
          ),
        ),
      ),
    );
    return Tooltip(
      message: '${player.name} #${player.shirtNumber}',
      child: GestureDetector(
        onTap: onTap,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            marker,
            if (!compact) ...[
              const SizedBox(height: 3),
              Container(
                constraints: const BoxConstraints(maxWidth: 74),
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                color: const Color(0xCC0A0C0F),
                child: Text(
                  _surname(player.name).toUpperCase(),
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: GtexMatchVisualTokens.textPrimary,
                    fontSize: 9,
                    fontWeight: FontWeight.w700,
                    letterSpacing: .4,
                  ),
                ),
              ),
            ],
            if (player.hasBall)
              Container(
                margin: const EdgeInsets.only(top: 3),
                width: 8,
                height: 8,
                decoration: const BoxDecoration(
                  color: GtexMatchVisualTokens.textPrimary,
                  shape: BoxShape.circle,
                ),
              ),
          ],
        ),
      ),
    );
  }

  String _surname(String name) {
    final List<String> parts = name.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty) {
      return name;
    }
    return parts.last;
  }
}

class _PitchFeedTag extends StatelessWidget {
  const _PitchFeedTag({required this.matchId});

  final String matchId;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: const Color(0xCC0A0C0F),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: const Color(0x6600E87A)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: const BoxDecoration(
              color: GtexMatchVisualTokens.live,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            'LIVE POSITION FEED  ${_shortMatchId(matchId)}',
            style: const TextStyle(
              color: GtexMatchVisualTokens.textPrimary,
              fontSize: 10,
              fontWeight: FontWeight.w900,
              letterSpacing: .7,
            ),
          ),
        ],
      ),
    );
  }

  static String _shortMatchId(String matchId) {
    if (matchId.length <= 8) {
      return matchId.toUpperCase();
    }
    return matchId.substring(0, 8).toUpperCase();
  }
}
