import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../shared/providers/tasks_provider.dart';
import '../constants/app_spacing.dart';
import '../theme/app_colors.dart';
import '../theme/app_motion.dart';

Future<void> showTaskRewardCelebration(
  BuildContext context,
  TaskClaimResult result,
) {
  return showGeneralDialog<void>(
    context: context,
    barrierLabel: 'Dismiss reward',
    barrierDismissible: true,
    barrierColor: Colors.black.withValues(alpha: 0.64),
    transitionDuration: AppMotion.slow,
    pageBuilder:
        (
          BuildContext context,
          Animation<double> animation,
          Animation<double> secondaryAnimation,
        ) => _TaskRewardPop(result: result),
    transitionBuilder: (
      BuildContext context,
      Animation<double> animation,
      Animation<double> secondaryAnimation,
      Widget child,
    ) {
      final Animation<double> fade = CurvedAnimation(
        parent: animation,
        curve: AppMotion.easeInOut,
      );
      final Animation<double> scale = CurvedAnimation(
        parent: animation,
        curve: AppMotion.elasticOut,
      );

      return FadeTransition(
        opacity: fade,
        child: ScaleTransition(
          scale: Tween<double>(begin: 0.72, end: 1).animate(scale),
          child: child,
        ),
      );
    },
  );
}

class _TaskRewardPop extends StatefulWidget {
  const _TaskRewardPop({required this.result});

  final TaskClaimResult result;

  @override
  State<_TaskRewardPop> createState() => _TaskRewardPopState();
}

class _TaskRewardPopState extends State<_TaskRewardPop> {
  Timer? _dismissTimer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(HapticFeedback.heavyImpact());
      unawaited(SystemSound.play(SystemSoundType.click));
    });
    _dismissTimer = Timer(const Duration(milliseconds: 1650), () {
      if (mounted && Navigator.of(context).canPop()) {
        Navigator.of(context).pop();
      }
    });
  }

  @override
  void dispose() {
    _dismissTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final bool highlightUnlock =
        widget.result.multiplierIncreased || widget.result.streakAdvanced;
    final Color accent =
        widget.result.multiplierIncreased ? AppColors.gold : AppColors.primary;

    return Material(
      color: Colors.transparent,
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(spacingLG),
          child: TweenAnimationBuilder<double>(
            tween: Tween<double>(begin: 0, end: 1),
            duration: AppMotion.slow,
            curve: AppMotion.elasticOut,
            builder: (BuildContext context, double value, Widget? child) {
              final double glow = 1 - value;
              return DecoratedBox(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(28),
                  boxShadow: <BoxShadow>[
                    BoxShadow(
                      color: accent.withValues(alpha: 0.18 + (glow * 0.28)),
                      blurRadius: 28 + (glow * 18),
                      spreadRadius: 2 + (glow * 4),
                    ),
                  ],
                ),
                child: child,
              );
            },
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Container(
                padding: const EdgeInsets.all(spacingLG),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(28),
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: <Color>[
                      AppColors.card,
                      AppColors.surfaceMuted,
                      AppColors.background,
                    ],
                  ),
                  border: Border.all(color: accent.withValues(alpha: 0.48)),
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      children: <Widget>[
                        TweenAnimationBuilder<double>(
                          tween: Tween<double>(begin: 0.82, end: 1),
                          duration: AppMotion.slow,
                          curve: AppMotion.elasticOut,
                          builder: (
                            BuildContext context,
                            double value,
                            Widget? child,
                          ) {
                            return Transform.scale(scale: value, child: child);
                          },
                          child: Container(
                            width: 64,
                            height: 64,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: accent.withValues(alpha: 0.14),
                              border: Border.all(
                                color: accent.withValues(alpha: 0.42),
                              ),
                            ),
                            child: Icon(
                              highlightUnlock
                                  ? Icons.emoji_events_rounded
                                  : Icons.monetization_on_rounded,
                              color: accent,
                              size: 32,
                            ),
                          ),
                        ),
                        const SizedBox(width: spacingMD),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(
                                highlightUnlock
                                    ? 'Achievement Unlocked'
                                    : 'Reward Claimed',
                                style: Theme.of(context).textTheme.headlineSmall
                                    ?.copyWith(color: AppColors.textPrimary),
                              ),
                              const SizedBox(height: spacingXS),
                              Text(
                                widget.result.multiplierIncreased
                                    ? 'Multiplier upgraded to ${widget.result.multiplierLabel}.'
                                    : 'Reward banked into the live loop.',
                                style: Theme.of(context).textTheme.bodyMedium
                                    ?.copyWith(color: AppColors.textSecondary),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: spacingLG),
                    Wrap(
                      spacing: spacingSM,
                      runSpacing: spacingSM,
                      children: <Widget>[
                        _RewardChip(
                          icon: Icons.monetization_on_rounded,
                          label: widget.result.reward,
                          color: AppColors.gold,
                        ),
                        _RewardChip(
                          icon: Icons.local_fire_department_rounded,
                          label: '${widget.result.currentStreak} day streak',
                          color: AppColors.primary,
                        ),
                        _RewardChip(
                          icon: Icons.bolt_rounded,
                          label: widget.result.multiplierLabel,
                          color: accent,
                        ),
                      ],
                    ),
                    const SizedBox(height: spacingLG),
                    Text(
                      widget.result.message,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: AppColors.textPrimary,
                      ),
                    ),
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

class _RewardChip extends StatelessWidget {
  const _RewardChip({
    required this.icon,
    required this.label,
    required this.color,
  });

  final IconData icon;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: spacingMD,
        vertical: spacingSM,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.36)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(icon, size: 16, color: color),
          const SizedBox(width: spacingXS),
          Text(
            label,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
