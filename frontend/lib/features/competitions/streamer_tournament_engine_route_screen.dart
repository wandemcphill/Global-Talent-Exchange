import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/constants/app_spacing.dart';
import '../../features/streamer_tournament_engine/presentation/streamer_tournament_engine_screen.dart';
import '../../navigation/app_destinations.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';

class StreamerTournamentEngineRouteScreen extends ConsumerWidget {
  const StreamerTournamentEngineRouteScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final bool authenticated = ref.watch(isAuthenticatedProvider);
    final String? accessToken = ref.watch(accessTokenProvider);
    final String? currentUserId = ref.watch(currentUserIdProvider);
    final String currentUserRole = ref.watch(currentUserRoleProvider);

    return AppPageLayout(
      title: 'Streamer Tournament Engine',
      subtitle:
          'LIVE route bridge. Public discovery works without auth; hosting, joining, and admin review reuse the existing streamer tournament engine screen and its live endpoints.',
      trailing: const DataSourceBadge(status: DataSourceStatus.live),
      children: <Widget>[
        Card(
          child: Padding(
            padding: const EdgeInsets.all(spacingLG),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Wrap(
                  spacing: spacingSM,
                  runSpacing: spacingSM,
                  children: <Widget>[
                    Chip(
                      label: Text(
                        authenticated
                            ? 'Authenticated session'
                            : 'Guest session',
                      ),
                    ),
                    Chip(label: Text('Role $currentUserRole')),
                    Chip(
                      label: Text(
                        accessToken == null || accessToken.trim().isEmpty
                            ? 'No access token'
                            : 'Access token present',
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: spacingMD),
                const Text(
                  'This route reuses the existing streamer tournament engine without switching back to the old shell. The public ladder and tournament discovery surfaces are live; protected actions rely on your current session state.',
                ),
                const SizedBox(height: spacingMD),
                Wrap(
                  spacing: spacingSM,
                  runSpacing: spacingSM,
                  children: <Widget>[
                    FilledButton(
                      onPressed:
                          () => Navigator.of(context).push<void>(
                            MaterialPageRoute<void>(
                              builder:
                                  (BuildContext context) =>
                                      StreamerTournamentEngineScreen(
                                        baseUrl: ref.read(apiBaseUrlProvider),
                                        backendMode: ref.read(
                                          criticalBackendModeProvider,
                                        ),
                                        accessToken: accessToken,
                                        currentUserId: currentUserId,
                                        currentUserRole: currentUserRole,
                                        onOpenLogin:
                                            () => context.push(
                                              AppRoutes.profileLogin,
                                            ),
                                      ),
                            ),
                          ),
                      child: const Text('Open full engine'),
                    ),
                    if (!authenticated)
                      OutlinedButton(
                        onPressed: () => context.push(AppRoutes.profileLogin),
                        child: const Text('Sign in'),
                      ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
