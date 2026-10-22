import 'package:flutter/material.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';

class GiftingOverlay extends StatelessWidget {
  const GiftingOverlay({
    super.key,
    required this.activeBursts,
    this.overflowCount = 0,
    required this.availableCoins,
    this.onSendGift,
    this.onSendReaction,
  });

  final List<Match3dOverlayBurst> activeBursts;
  final int overflowCount;
  final double availableCoins;
  final Future<void> Function(double amount)? onSendGift;
  final Future<void> Function(Match3dReaction reaction)? onSendReaction;

  @override
  Widget build(BuildContext context) {
    final bool hasActions = onSendGift != null || onSendReaction != null;
    return Stack(
      children: <Widget>[
        Positioned(
          top: 24,
          right: 18,
          child: IgnorePointer(
            child: RepaintBoundary(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: <Widget>[
                  ...activeBursts.take(3).map(
                        (Match3dOverlayBurst burst) => Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: _OverlayBurstChip(burst: burst),
                        ),
                      ),
                  if (overflowCount > 0)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: _OverflowChip(
                        count: overflowCount,
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
        if (hasActions)
          Positioned(
            right: 18,
            bottom: 18,
            child: FilledButton.tonalIcon(
              onPressed: () => _openGiftSheet(context),
              icon: Icon(
                onSendGift != null
                    ? Icons.card_giftcard_outlined
                    : Icons.emoji_emotions_outlined,
              ),
              label: Text(
                onSendGift != null
                    ? 'Gift ${availableCoins.toStringAsFixed(2)}'
                    : 'React',
              ),
            ),
          ),
      ],
    );
  }

  Future<void> _openGiftSheet(BuildContext context) async {
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (BuildContext context) {
        return _GiftSheet(
          availableCoins: availableCoins,
          onSendGift: onSendGift,
          onSendReaction: onSendReaction,
        );
      },
    );
  }
}

class _GiftSheet extends StatelessWidget {
  const _GiftSheet({
    required this.availableCoins,
    required this.onSendGift,
    required this.onSendReaction,
  });

  final double availableCoins;
  final Future<void> Function(double amount)? onSendGift;
  final Future<void> Function(Match3dReaction reaction)? onSendReaction;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final bool showGiftOptions = onSendGift != null;
    final bool showReactions = onSendReaction != null;
    final String intro = switch ((showGiftOptions, showReactions)) {
      (true, true) =>
        'Send lightweight gifts and reactions without interrupting the match. Balance ${availableCoins.toStringAsFixed(2)} coin.',
      (true, false) =>
        'Send lightweight gifts without interrupting the match. Balance ${availableCoins.toStringAsFixed(2)} coin.',
      (false, true) =>
        'Send lightweight reactions without interrupting the match.',
      (false, false) => 'Viewer support is unavailable right now.',
    };
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(28),
            color: const Color(0xFF0E1724),
            border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Support the match',
                style: theme.textTheme.headlineSmall?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                intro,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: Colors.white70,
                ),
              ),
              if (showGiftOptions) ...<Widget>[
                const SizedBox(height: 16),
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: Match3dMonetizationService.giftAmounts
                      .map(
                        (double amount) => FilledButton.tonal(
                          onPressed: () async {
                            Navigator.of(context).pop();
                            await onSendGift!(amount);
                          },
                          child: Text('${amount.toStringAsFixed(1)} coin'),
                        ),
                      )
                      .toList(growable: false),
                ),
              ],
              if (showReactions) ...<Widget>[
                const SizedBox(height: 18),
                Text(
                  'Reactions',
                  style: theme.textTheme.titleSmall?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: <Widget>[
                    _ReactionButton(
                      label: '\u{1F525} Fire',
                      onPressed: () async {
                        Navigator.of(context).pop();
                        await onSendReaction!(Match3dReaction.fire);
                      },
                    ),
                    _ReactionButton(
                      label: '\u{1F44F} Applause',
                      onPressed: () async {
                        Navigator.of(context).pop();
                        await onSendReaction!(Match3dReaction.applause);
                      },
                    ),
                    _ReactionButton(
                      label: '\u{26A1} Hype',
                      onPressed: () async {
                        Navigator.of(context).pop();
                        await onSendReaction!(Match3dReaction.hype);
                      },
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _OverlayBurstChip extends StatelessWidget {
  const _OverlayBurstChip({
    required this.burst,
  });

  final Match3dOverlayBurst burst;

  @override
  Widget build(BuildContext context) {
    final Color accent = burst.accentColor;
    return TweenAnimationBuilder<double>(
      key: ValueKey<String>(burst.id),
      duration: const Duration(milliseconds: 480),
      curve: Curves.easeOutBack,
      tween: Tween<double>(begin: 0, end: 1),
      builder: (BuildContext context, double value, Widget? child) {
        return Opacity(
          opacity: value.clamp(0.0, 1.0).toDouble(),
          child: Transform.translate(
            offset: Offset((1 - value) * 46, (1 - value) * -9),
            child: Transform.scale(
              scale: 0.88 + (0.12 * value),
              alignment: Alignment.centerRight,
              child: child,
            ),
          ),
        );
      },
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 290),
        child: Container(
          padding: const EdgeInsets.fromLTRB(10, 9, 14, 9),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(18),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[
                accent.withValues(alpha: 0.22),
                const Color(0xF2111C2B),
                const Color(0xEC0B1422),
              ],
            ),
            border: Border.all(color: accent.withValues(alpha: 0.78)),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: accent.withValues(alpha: 0.16),
                blurRadius: 22,
                spreadRadius: -4,
                offset: const Offset(0, 5),
              ),
            ],
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(13),
                  color: accent.withValues(alpha: 0.12),
                  border: Border.all(color: accent.withValues(alpha: 0.55)),
                ),
                child: Center(
                  child: Text(
                    burst.emoji,
                    style: const TextStyle(fontSize: 24),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Flexible(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const Text(
                      'GIFT ARRIVED',
                      style: TextStyle(
                        color: Color(0xFF8FA2BB),
                        fontSize: 8,
                        letterSpacing: 1.7,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      burst.label,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w900,
                        fontSize: 12,
                        height: 1.12,
                      ),
                    ),
                    if (burst.coinAmount != null) ...<Widget>[
                      const SizedBox(height: 4),
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: <Widget>[
                          Icon(Icons.circle, size: 8, color: accent),
                          const SizedBox(width: 5),
                          Text(
                            '${burst.coinAmount!.toStringAsFixed(2)} coin',
                            style: TextStyle(
                              color: accent,
                              fontSize: 10,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: 6),
              Icon(Icons.auto_awesome_rounded, size: 16, color: accent),
            ],
          ),
        ),
      ),
    );
  }
}

class _ReactionButton extends StatelessWidget {
  const _ReactionButton({
    required this.label,
    required this.onPressed,
  });

  final String label;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton(
      onPressed: onPressed,
      child: Text(label),
    );
  }
}

class _OverflowChip extends StatelessWidget {
  const _OverflowChip({
    required this.count,
  });

  final int count;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: const Color(0xCC101A28),
        border: Border.all(color: Colors.white.withValues(alpha: 0.16)),
      ),
      child: Text(
        '+$count more',
        style: const TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
