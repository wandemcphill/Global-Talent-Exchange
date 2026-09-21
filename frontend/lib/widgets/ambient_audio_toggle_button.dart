import 'package:flutter/material.dart';
import 'package:gte_frontend/services/ambient_audio_controller.dart';
import 'package:gte_frontend/widgets/audio/gtex_audio_settings_sheet.dart';
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
        final bool blocked = controller.isWebAutoplayBlocked;

        IconData iconData = Icons.volume_off_rounded;
        if (blocked) {
          iconData = Icons.warning_amber_rounded;
        } else if (active) {
          iconData = Icons.surround_sound_rounded;
        } else if (enabled) {
          iconData = Icons.volume_up_rounded;
        }

        final Color? iconColor = blocked
            ? Colors.amber
            : enabled
                ? GteShellTheme.tokensOf(context).accentCapital
                : null;

        final String tooltip = blocked
            ? 'Autoplay blocked by browser - tap to enable'
            : enabled
                ? 'Stadium sound: ${controller.currentTrack.title} (Long press for audio settings)'
                : 'Enable stadium sound (Long press for audio settings)';

        return Padding(
          padding: padding,
          child: InkWell(
            onLongPress: () => GtexAudioSettingsSheet.show(context, controller),
            borderRadius: BorderRadius.circular(20),
            child: IconButton(
              key: const Key('ambient-audio-toggle'),
              tooltip: tooltip,
              onPressed: () {
                if (blocked) {
                  controller.resolveWebAutoplay();
                } else {
                  controller.toggleMuted();
                }
              },
              icon: Icon(
                iconData,
                color: iconColor,
              ),
            ),
          ),
        );
      },
    );
  }
}
