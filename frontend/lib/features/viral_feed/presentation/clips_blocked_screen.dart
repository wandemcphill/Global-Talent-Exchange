import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/constants/app_spacing.dart';
import '../../../navigation/app_destinations.dart';
import '../../../shared/models/data_source_status.dart';
import '../../../shared/widgets/app_page_layout.dart';
import '../../../shared/widgets/data_source_badge.dart';

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
        Card(
          child: Padding(
            padding: const EdgeInsets.all(spacingLG),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Clips are blocked',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: spacingSM),
                const Text(
                  'Sign in to open the live feed. Guest sessions cannot fetch personalized clips from the shipped backend.',
                ),
                const SizedBox(height: spacingMD),
                FilledButton(
                  onPressed: () => context.push(AppRoutes.profileLogin),
                  child: const Text('Sign in'),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
