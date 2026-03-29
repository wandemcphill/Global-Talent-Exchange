import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/platform/gtex_platform_experience_controller.dart';
import 'package:gte_frontend/models/platform/gtex_platform_experience.dart';

class GtexTvModeShell extends StatelessWidget {
  const GtexTvModeShell({
    super.key,
    required this.controller,
    required this.matchTitle,
    this.onChannelSelected,
  });

  static const Key shellKey = Key('gtex-tv-mode-shell');

  final GtexPlatformExperienceController controller;
  final String matchTitle;
  final ValueChanged<GtexTvChannel>? onChannelSelected;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (BuildContext context, _) {
        final GtexTvChannel? currentChannel = controller.currentChannel;
        final GtexPlatformSyncState syncState = controller.syncState;
        return Stack(
          key: shellKey,
          children: <Widget>[
            Positioned(
              top: 24,
              left: 24,
              child: _GlassCard(
                width: 320,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    const Text(
                      'What\'s Live Now',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 24,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Text(
                      currentChannel?.headline ?? matchTitle,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      currentChannel?.subheadline ??
                          'Full-screen ceremonial broadcast',
                      style: const TextStyle(
                        color: Colors.white70,
                        fontSize: 13,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Text(
                      '${currentChannel?.viewerCount ?? 0} viewers  •  Auto-play on',
                      style: const TextStyle(
                        color: Colors.white60,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            Positioned(
              top: 24,
              right: 24,
              bottom: 24,
              child: _GlassCard(
                width: 256,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const Text(
                      'Channels',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 20,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Expanded(
                      child: ListView.separated(
                        itemCount: controller.channels.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 10),
                        itemBuilder: (BuildContext context, int index) {
                          final GtexTvChannel channel =
                              controller.channels[index];
                          final bool selected =
                              channel.channelId == currentChannel?.channelId;
                          return FilledButton.tonal(
                            style: FilledButton.styleFrom(
                              backgroundColor:
                                  selected
                                      ? const Color(0xFFE7F0FF)
                                      : const Color(0x1AFFFFFF),
                              foregroundColor:
                                  selected
                                      ? const Color(0xFF07111A)
                                      : Colors.white,
                              padding: const EdgeInsets.symmetric(
                                horizontal: 14,
                                vertical: 14,
                              ),
                              alignment: Alignment.centerLeft,
                            ),
                            onPressed: () {
                              controller.selectChannel(channel.channelId);
                              onChannelSelected?.call(channel);
                            },
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                Text(
                                  channel.name,
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w800,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  channel.headline,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                                Text(
                                  channel.highlightLabel ??
                                      '${channel.viewerCount} viewers',
                                  style: TextStyle(
                                    color:
                                        selected
                                            ? const Color(0xCC07111A)
                                            : Colors.white70,
                                    fontSize: 12,
                                  ),
                                ),
                              ],
                            ),
                          );
                        },
                      ),
                    ),
                  ],
                ),
              ),
            ),
            Positioned(
              left: 24,
              bottom: 24,
              child: _GlassCard(
                width: 320,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    const Text(
                      'Cross-Device Sync',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      syncState.sourceDeviceLabel == null
                          ? 'Resume and commentary sync will appear here.'
                          : 'Resuming from ${syncState.sourceDeviceLabel} at ${syncState.resumePositionSeconds.toStringAsFixed(0)}s',
                      style: const TextStyle(color: Colors.white70),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Commentary cursor: ${syncState.commentaryCursor}',
                      style: const TextStyle(
                        color: Colors.white60,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            if (controller.autoSwitchMessage != null)
              Positioned(
                bottom: 28,
                right: 300,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: const Color(0xFFF4B740),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 18,
                      vertical: 10,
                    ),
                    child: Text(
                      controller.autoSwitchMessage!,
                      style: const TextStyle(
                        color: Color(0xFF07111A),
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}

class _GlassCard extends StatelessWidget {
  const _GlassCard({required this.child, this.width});

  final Widget child;
  final double? width;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xCC09131E),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: const Color(0x33FFFFFF)),
      ),
      child: child,
    );
  }
}
