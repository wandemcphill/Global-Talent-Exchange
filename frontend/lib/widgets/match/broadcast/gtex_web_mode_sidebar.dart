import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/platform/gtex_platform_experience_controller.dart';

class GtexWebModeSidebar extends StatelessWidget {
  const GtexWebModeSidebar({
    super.key,
    required this.controller,
    required this.matchTitle,
  });

  static const Key sidebarKey = Key('gtex-web-mode-sidebar');

  final GtexPlatformExperienceController controller;
  final String matchTitle;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (BuildContext context, _) {
        final syncState = controller.syncState;
        return Container(
          key: sidebarKey,
          color: const Color(0xFF0C1723),
          padding: const EdgeInsets.fromLTRB(18, 20, 18, 20),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                const Text(
                  'Multi-Match Desk',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 8),
                Text(matchTitle, style: const TextStyle(color: Colors.white70)),
                const SizedBox(height: 16),
                const _SidebarCard(
                  title: 'Trading Desk',
                  body:
                      'Advanced stats, sentiment, and creator trading stay pinned while the live feed runs.',
                ),
                const SizedBox(height: 12),
                _SidebarCard(
                  title: 'Watch Sync',
                  body:
                      syncState.sourceDeviceLabel == null
                          ? 'No synced device yet.'
                          : 'Resuming from ${syncState.sourceDeviceLabel} with commentary cursor ${syncState.commentaryCursor}.',
                ),
                const SizedBox(height: 12),
                _SidebarCard(
                  title: 'Live Channels',
                  body:
                      controller.channels.isEmpty
                          ? 'No secondary channels loaded.'
                          : controller.channels
                              .take(3)
                              .map(
                                (channel) =>
                                    '${channel.name} - ${channel.viewerCount}',
                              )
                              .join('\n'),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _SidebarCard extends StatelessWidget {
  const _SidebarCard({required this.title, required this.body});

  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF122133),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0x1FFFFFFF)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            title,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            body,
            style: const TextStyle(color: Colors.white70, height: 1.35),
          ),
        ],
      ),
    );
  }
}
