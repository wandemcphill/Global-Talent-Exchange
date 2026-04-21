import 'package:flutter/material.dart';

import '../../core/constants/app_spacing.dart';
import '../../navigation/app_destinations.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import '../../shared/widgets/gtex_premium_panels.dart';
import '../../shared/widgets/route_surface_badge.dart';
import '../../widgets/gte_state_panel.dart';
import 'match_viewer_capability.dart';

class MatchNative3dBlockedScreen extends StatelessWidget {
  const MatchNative3dBlockedScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final AppRouteSurface surface =
        appRouteSurfaceFor(AppRoutes.matchesNativeThreeD)!;
    return AppPageLayout(
      title: 'Native 3D',
      subtitle:
          'Coming soon. The dedicated native-only route is still disclosed until it can open against a specific live match session.',
      trailing: Wrap(
        spacing: spacingSM,
        runSpacing: spacingSM,
        children: <Widget>[
          const DataSourceBadge(status: DataSourceStatus.blocked),
          const MatchViewerCapabilityBadge(
            capability: MatchViewerCapability.blocked,
          ),
          RouteSurfaceBadge(state: surface.state),
        ],
      ),
      children: <Widget>[
        const GtexHeroPanel(
          eyebrow: 'NATIVE 3D DISCLOSURE',
          title: 'Native 3D is coming soon',
          description:
              'The active Flutter shell keeps this route disclosed until a verified native runtime is mounted end to end.',
          metrics: <Widget>[
            GtexPill(label: 'BLOCKED', tone: GtexSurfaceTone.danger),
            GtexPill(label: 'UNPROVEN RUNTIME', tone: GtexSurfaceTone.warning),
          ],
        ),
        GtexSectionPanel(
          eyebrow: 'RUNTIME TRUTH',
          title: 'Verified native runtime required',
          subtitle:
              'This route remains visible so capability truth stays clear while the shipped app continues to use the Flutter-rendered 3D lane.',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              GteStatePanel(
                eyebrow: 'NATIVE 3D',
                title: 'Route truth remains blocked',
                message: surface.summary,
                icon: Icons.block_outlined,
                accentColor: Theme.of(context).colorScheme.error,
              ),
              const SizedBox(height: spacingMD),
              const Text(
                'The Android host contains a native match_3d bridge scaffold, but this preview route stays blocked until a native-only route is wired to a verified live match session and backed by a shipped Android runtime instead of placeholder plumbing.',
              ),
            ],
          ),
        ),
      ],
    );
  }
}
