import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../navigation/app_destinations.dart';
import '../../../shared/models/data_source_status.dart';
import '../../../shared/widgets/app_page_layout.dart';
import '../../../shared/widgets/data_source_badge.dart';
import '../../../shared/widgets/gtex_premium_panels.dart';

class ClipsBlockedScreen extends StatelessWidget {
  const ClipsBlockedScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return AppPageLayout(
      title: 'Clips',
      subtitle:
          'The active shell only exposes the live clips feed when the authenticated session can satisfy the backend identity contract.',
      trailing: const DataSourceBadge(status: DataSourceStatus.blocked),
      children: <Widget>[
        GtexHeroPanel(
          eyebrow: 'CLIPS BLOCKED',
          title: 'Clips are blocked',
          description:
              'Sign in to open the live feed. Guest sessions cannot fetch personalized clips from the shipped backend.',
          actions: <Widget>[
            FilledButton(
              onPressed: () => context.push(AppRoutes.profileLogin),
              child: const Text('Sign in'),
            ),
          ],
        ),
      ],
    );
  }
}
