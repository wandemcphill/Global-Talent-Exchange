import 'package:flutter/material.dart';
import 'package:gte_frontend/features/formation/domain/formation_models.dart';

class TacticalPitchBoard extends StatelessWidget {
  const TacticalPitchBoard({
    super.key,
    required this.formation,
    this.players = const <FormationSelectionReadyPlayerDto>[],
    this.blockedReason,
    this.pending = false,
  });

  final FormationDto? formation;
  final List<FormationSelectionReadyPlayerDto> players;
  final String? blockedReason;
  final bool pending;

  @override
  Widget build(BuildContext context) {
    final Color lineColor = Theme.of(
      context,
    ).colorScheme.onPrimary.withValues(alpha: 0.72);
    final Color pitchColor = Color.alphaBlend(
      Theme.of(context).colorScheme.primary.withValues(alpha: 0.28),
      const Color(0xFF173F35),
    );

    return AspectRatio(
      aspectRatio: 0.72,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: pitchColor,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: lineColor.withValues(alpha: 0.5)),
        ),
        child: LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            return Stack(
              children: <Widget>[
                _PitchLines(lineColor: lineColor),
                if (formation == null)
                  const _BoardPlaceholder()
                else
                  ...formation!.slots.map(
                    (FormationSlotDto slot) => _SlotMarker(
                      key: Key('formation-slot-${slot.slotId}'),
                      slot: slot,
                      label: _playerName(slot.assignedPlayerId),
                      boardWidth: constraints.maxWidth,
                      boardHeight: constraints.maxHeight,
                    ),
                  ),
                if (pending)
                  const _BoardOverlay(
                    title: 'Publishing formation',
                    message: 'Waiting for backend confirmation.',
                  ),
                if (blockedReason != null)
                  _BoardOverlay(
                    title: 'Formation blocked',
                    message: blockedReason!,
                  ),
              ],
            );
          },
        ),
      ),
    );
  }

  String _playerName(String? playerId) {
    if (playerId == null) {
      return 'Empty';
    }
    for (final FormationSelectionReadyPlayerDto player in players) {
      if (player.id == playerId) {
        return player.name;
      }
    }
    return playerId;
  }
}

class _PitchLines extends StatelessWidget {
  const _PitchLines({required this.lineColor});

  final Color lineColor;

  @override
  Widget build(BuildContext context) {
    return Positioned.fill(
      child: CustomPaint(painter: _PitchPainter(lineColor)),
    );
  }
}

class _PitchPainter extends CustomPainter {
  const _PitchPainter(this.lineColor);

  final Color lineColor;

  @override
  void paint(Canvas canvas, Size size) {
    final Paint paint =
        Paint()
          ..color = lineColor
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.4;
    final Rect bounds = Offset.zero & size;
    canvas.drawRect(bounds.deflate(14), paint);
    canvas.drawLine(
      Offset(14, size.height / 2),
      Offset(size.width - 14, size.height / 2),
      paint,
    );
    canvas.drawCircle(Offset(size.width / 2, size.height / 2), 36, paint);
    canvas.drawRect(
      Rect.fromCenter(
        center: Offset(size.width / 2, 42),
        width: size.width * 0.48,
        height: 70,
      ),
      paint,
    );
    canvas.drawRect(
      Rect.fromCenter(
        center: Offset(size.width / 2, size.height - 42),
        width: size.width * 0.48,
        height: 70,
      ),
      paint,
    );
  }

  @override
  bool shouldRepaint(_PitchPainter oldDelegate) {
    return oldDelegate.lineColor != lineColor;
  }
}

class _SlotMarker extends StatelessWidget {
  const _SlotMarker({
    super.key,
    required this.slot,
    required this.label,
    required this.boardWidth,
    required this.boardHeight,
  });

  final FormationSlotDto slot;
  final String label;
  final double boardWidth;
  final double boardHeight;

  @override
  Widget build(BuildContext context) {
    final double markerWidth = boardWidth < 360 ? 66 : 82;
    final double left = (boardWidth * slot.x) - (markerWidth / 2);
    final double top = (boardHeight * slot.y) - 24;
    return Positioned(
      left: left.clamp(8, boardWidth - markerWidth - 8),
      top: top.clamp(8, boardHeight - 56),
      child: SizedBox(
        width: markerWidth,
        height: 52,
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: Theme.of(
              context,
            ).colorScheme.surface.withValues(alpha: slot.filled ? 0.96 : 0.78),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color:
                  slot.filled
                      ? Theme.of(context).colorScheme.secondary
                      : Theme.of(context).colorScheme.outline,
            ),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: <Widget>[
                Text(
                  slot.position,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(
                    context,
                  ).textTheme.labelSmall?.copyWith(fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 2),
                Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _BoardPlaceholder extends StatelessWidget {
  const _BoardPlaceholder();

  @override
  Widget build(BuildContext context) {
    return Positioned.fill(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: List<Widget>.generate(4, (int row) {
            return Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: List<Widget>.generate(3, (int col) {
                return DecoratedBox(
                  decoration: BoxDecoration(
                    color: Theme.of(
                      context,
                    ).colorScheme.surface.withValues(alpha: 0.34),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const SizedBox(width: 58, height: 34),
                );
              }),
            );
          }),
        ),
      ),
    );
  }
}

class _BoardOverlay extends StatelessWidget {
  const _BoardOverlay({required this.title, required this.message});

  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Positioned.fill(
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.scrim.withValues(alpha: 0.56),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 340),
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surface,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    Text(
                      title,
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    Text(message, textAlign: TextAlign.center),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
