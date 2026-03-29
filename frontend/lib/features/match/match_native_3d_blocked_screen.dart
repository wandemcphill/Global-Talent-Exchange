import 'package:flutter/material.dart';

import '../../core/constants/app_spacing.dart';
import 'match_viewer_capability.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';

class MatchNative3dBlockedScreen extends StatelessWidget {
  const MatchNative3dBlockedScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return AppPageLayout(
      title: 'Native 3D',
      subtitle:
          'BLOCKED route. The active Flutter shell does not have a verified native 3D runtime mounted, so native 3D stays blocked instead of being mislabeled as the Flutter viewer.',
      trailing: const Wrap(
        spacing: spacingSM,
        runSpacing: spacingSM,
        children: <Widget>[
          DataSourceBadge(status: DataSourceStatus.blocked),
          MatchViewerCapabilityBadge(capability: MatchViewerCapability.blocked),
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
                  'Native 3D is blocked',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
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
