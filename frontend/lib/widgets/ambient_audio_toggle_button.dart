import 'package:flutter/material.dart';
import 'package:gte_frontend/services/ambient_audio_controller.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

class AmbientAudioToggleButton extends StatelessWidget {
  const AmbientAudioToggleButton({
    super.key,
    required this.controller,
    this.padding = const EdgeInsets.only(right: 8),
  });

  final AmbientAudioState controller;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (BuildContext context, Widget? child) {
        final bool enabled = !controller.isMuted;
        final bool active = enabled && controller.isPlaying;
        return Padding(
          padding: padding,
          child: IconButton(
            key: const Key('ambient-audio-toggle'),
            tooltip:
                enabled
                    ? 'Stadium atmosphere enabled'
                    : 'Enable stadium atmosphere',
            onPressed: controller.toggleMuted,
            icon: Icon(
              active ? Icons.surround_sound_rounded : Icons.volume_off_rounded,
              color:
                  enabled
                      ? GteShellTheme.tokensOf(context).accentCapital
                      : null,
            ),
          ),
        );
      },
    );
  }
}
