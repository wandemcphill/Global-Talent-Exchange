import 'package:flutter/material.dart';

import '../../core/constants/app_spacing.dart';
import '../../navigation/app_destinations.dart';
import 'match_viewer_capability.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import '../../shared/widgets/route_surface_badge.dart';

class MatchNative3dBlockedScreen extends StatelessWidget {
  const MatchNative3dBlockedScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final AppRouteSurface surface =
        appRouteSurfaceFor(AppRoutes.matchesNativeThreeD)!;
    return AppPageLayout(
      title: 'Native 3D',
      subtitle:
          'Coming soon. The active Flutter shell does not have a verified native 3D runtime mounted, so this route stays disclosed instead of pretending support exists.',
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
        Card(
          child: Padding(
            padding: const EdgeInsets.all(spacingLG),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Native 3D is coming soon',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: spacingSM),
                Text(surface.summary),
                const SizedBox(height: spacingSM),
                const Text(
                  'The repo contains Flutter-rendered match viewers, but the active shipped shell does not mount a verified native MethodChannel/EventChannel bridge for match_3d and match_3d/events. Use the Flutter 3D route for the existing in-app 3D surface.',
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
