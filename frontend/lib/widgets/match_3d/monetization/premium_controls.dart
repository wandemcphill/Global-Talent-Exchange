import 'package:flutter/material.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';

class PremiumControls extends StatelessWidget {
  const PremiumControls({
    super.key,
    required this.entitlement,
    required this.selectedRenderMode,
    required this.effectiveRenderMode,
    required this.availableCoins,
    required this.cameraPreset,
    required this.canUsePremiumCamera,
    required this.canUseFastReplay,
    required this.onRenderModeSelected,
    required this.onCameraPresetSelected,
    required this.onUnlockSlowMotion,
    required this.onUnlockAlternateCamera,
    required this.onUnlockHighlightAttack,
    this.onUpgradeTournament,
  });

  final Match3dUserEntitlement entitlement;
  final RenderMode selectedRenderMode;
  final RenderMode effectiveRenderMode;
  final double availableCoins;
  final Match3dCameraPreset cameraPreset;
  final bool canUsePremiumCamera;
  final bool canUseFastReplay;
  final ValueChanged<RenderMode> onRenderModeSelected;
  final ValueChanged<Match3dCameraPreset> onCameraPresetSelected;
  final VoidCallback onUnlockSlowMotion;
  final VoidCallback onUnlockAlternateCamera;
  final VoidCallback onUnlockHighlightAttack;
  final VoidCallback? onUpgradeTournament;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        const bool stackedActions = true;
        return Container(
          constraints: const BoxConstraints(maxWidth: 360),
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(22),
            color: const Color(0xD7101B2A),
            border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Expanded(
                    child: Text(
                      'Match controls',
                      style: theme.textTheme.titleSmall?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (entitlement.isPremiumUser)
                    Flexible(
                      child: Align(
                        alignment: Alignment.centerRight,
                        child: FittedBox(
                          fit: BoxFit.scaleDown,
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 6,
                            ),
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(999),
                              color: const Color(0x1FFDB022),
                              border: Border.all(color: const Color(0x66FDB022)),
                            ),
                            child: const Text(
                              'Pro Manager',
                              style: TextStyle(
                                color: Color(0xFFFDB022),
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                'Render mode',
                style: theme.textTheme.labelLarge?.copyWith(color: Colors.white70),
              ),
              const SizedBox(height: 8),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: SegmentedButton<RenderMode>(
                  segments: const <ButtonSegment<RenderMode>>[
                    ButtonSegment<RenderMode>(
                      value: RenderMode.auto,
                      label: Text('Auto'),
                      icon: Icon(Icons.auto_awesome_outlined),
                    ),
                    ButtonSegment<RenderMode>(
                      value: RenderMode.twoD,
                      label: Text('2D'),
                      icon: Icon(Icons.map_outlined),
                    ),
                    ButtonSegment<RenderMode>(
                      value: RenderMode.threeD,
                      label: Text('3D'),
                      icon: Icon(Icons.view_in_ar_outlined),
                    ),
                  ],
                  selected: <RenderMode>{selectedRenderMode},
                  onSelectionChanged: (Set<RenderMode> value) {
                    onRenderModeSelected(value.first);
                  },
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Live mode: ${effectiveRenderMode == RenderMode.threeD ? '3D' : '2D'} | Balance ${availableCoins.toStringAsFixed(2)} coin',
                softWrap: true,
                style: theme.textTheme.bodySmall?.copyWith(color: Colors.white70),
              ),
              const SizedBox(height: 12),
              Text(
                'Camera',
                style: theme.textTheme.labelLarge?.copyWith(color: Colors.white70),
              ),
              const SizedBox(height: 8),
              if (canUsePremiumCamera)
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: Match3dCameraPreset.values
                      .map(
                        (Match3dCameraPreset preset) => ChoiceChip(
                          label: Text(_cameraLabel(preset)),
                          selected: cameraPreset == preset,
                          onSelected: (_) => onCameraPresetSelected(preset),
                        ),
                      )
                      .toList(growable: false),
                )
              else
                _ActionButton(
                  expanded: stackedActions,
                  icon: Icons.videocam_outlined,
                  label: 'Unlock alternate camera 0.02 coin',
                  onPressed: onUnlockAlternateCamera,
                ),
              const SizedBox(height: 12),
              if (stackedActions)
                Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    _ActionButton(
                      expanded: true,
                      icon: Icons.slow_motion_video_outlined,
                      label: 'Slow mo 0.05 coin',
                      onPressed: onUnlockSlowMotion,
                    ),
                    const SizedBox(height: 8),
                    _ActionButton(
                      expanded: true,
                      icon: Icons.flash_on_outlined,
                      label: 'Highlight attack 0.05 coin',
                      onPressed: onUnlockHighlightAttack,
                    ),
                    if (onUpgradeTournament != null) ...<Widget>[
                      const SizedBox(height: 8),
                      _ActionButton(
                        expanded: true,
                        icon: Icons.workspace_premium_outlined,
                        label: 'Tournament boost',
                        onPressed: onUpgradeTournament!,
                      ),
                    ],
                  ],
                )
              else
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: <Widget>[
                    _ActionButton(
                      icon: Icons.slow_motion_video_outlined,
                      label: 'Slow mo 0.05 coin',
                      onPressed: onUnlockSlowMotion,
                    ),
                    _ActionButton(
                      icon: Icons.flash_on_outlined,
                      label: 'Highlight attack 0.05 coin',
                      onPressed: onUnlockHighlightAttack,
                    ),
                    if (onUpgradeTournament != null)
                      _ActionButton(
                        icon: Icons.workspace_premium_outlined,
                        label: 'Tournament boost',
                        onPressed: onUpgradeTournament!,
                      ),
                  ],
                ),
              const SizedBox(height: 10),
              Text(
                canUseFastReplay
                    ? 'Fast replay unlocked up to 6x.'
                    : 'Standard replay stays capped below premium speed.',
                style: theme.textTheme.bodySmall?.copyWith(color: Colors.white70),
              ),
            ],
          ),
        );
      },
    );
  }

  String _cameraLabel(Match3dCameraPreset preset) {
    switch (preset) {
      case Match3dCameraPreset.broadcast:
        return 'Broadcast';
      case Match3dCameraPreset.sideline:
        return 'Sideline';
      case Match3dCameraPreset.goalbox:
        return 'Goalbox';
    }
  }
}

class _ActionButton extends StatelessWidget {
  const _ActionButton({
    required this.icon,
    required this.label,
    required this.onPressed,
    this.expanded = false,
  });

  final IconData icon;
  final String label;
  final VoidCallback onPressed;
  final bool expanded;

  @override
  Widget build(BuildContext context) {
    final Widget button = FilledButton.tonal(
      onPressed: onPressed,
      child: Row(
        mainAxisSize: expanded ? MainAxisSize.max : MainAxisSize.min,
        children: <Widget>[
          Icon(icon),
          const SizedBox(width: 8),
          if (expanded)
            Flexible(
              child: Text(
                label,
                maxLines: 2,
                softWrap: true,
              ),
            )
          else
            Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
        ],
      ),
    );
    if (!expanded) {
      return button;
    }
    return SizedBox(width: double.infinity, child: button);
  }
}
