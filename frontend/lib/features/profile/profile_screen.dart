import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_feedback.dart';
import '../../core/constants/app_spacing.dart';
import '../../navigation/app_destinations.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/providers/live_clients_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import 'live_profile_provider.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<ProfileData> profileValue = ref.watch(profileDataProvider);
    return AppPageLayout(
      title: 'Profile',
      subtitle:
          'The active shell profile now reflects the live session, user, club, and admin affordances instead of synthetic match and transfer stories.',
      trailing: DataSourceBadge(
        status:
            profileValue.hasError
                ? DataSourceStatus.blocked
                : DataSourceStatus.live,
      ),
      children: <Widget>[
        profileValue.when(
          data:
              (ProfileData profile) =>
                  profile.authenticated
                      ? _AuthenticatedProfile(profile: profile)
                      : _GuestProfile(),
          loading:
              () => const Center(
                child: Padding(
                  padding: EdgeInsets.all(spacingLG),
                  child: CircularProgressIndicator(),
                ),
              ),
          error:
              (Object error, StackTrace stackTrace) => _BlockedCard(
                title: 'Profile is blocked',
                message: AppFeedback.messageFor(error),
              ),
        ),
      ],
    );
  }
}

class _GuestProfile extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(spacingLG),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'This session is not signed in.',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: spacingSM),
            const Text(
              'Protected user, wallet, admin, and club-context actions stay blocked until authentication succeeds.',
            ),
            const SizedBox(height: spacingMD),
            Wrap(
              spacing: spacingSM,
              runSpacing: spacingSM,
              children: <Widget>[
                FilledButton(
                  onPressed: () => context.push(AppRoutes.profileLogin),
                  child: const Text('Sign in'),
                ),
                OutlinedButton(
                  onPressed: () => context.push(AppRoutes.profileSignup),
                  child: const Text('Create account'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _AuthenticatedProfile extends ConsumerWidget {
  const _AuthenticatedProfile({required this.profile});

  final ProfileData profile;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final String role = ref.watch(currentUserRoleProvider);
    final List<String> permissions = ref.watch(currentUserPermissionsProvider);
    final bool isAdmin = ref.watch(isAdminProvider);

    return Column(
      children: <Widget>[
        Card(
          child: Padding(
            padding: const EdgeInsets.all(spacingLG),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  profile.user['display_name']?.toString() ??
                      profile.user['username']?.toString() ??
                      profile.user['email']?.toString() ??
                      'Authenticated user',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: spacingSM),
                Wrap(
                  spacing: spacingSM,
                  runSpacing: spacingSM,
                  children: <Widget>[
                    Chip(label: Text('Role: $role')),
                    Chip(label: Text('Followers: ${profile.followers}')),
                    Chip(label: Text('Following: ${profile.following}')),
                    if (profile.club != null)
                      Chip(
                        label: Text(
                          'Club: ${profile.club!['name'] ?? profile.club!['id']}',
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: spacingMD),
                Text(
                  profile.user.entries
                      .where(
                        (MapEntry<String, Object?> entry) => <String>{
                          'id',
                          'email',
                          'username',
                          'role',
                          'display_name',
                        }.contains(entry.key),
                      )
                      .map(
                        (MapEntry<String, Object?> entry) =>
                            '${entry.key}: ${entry.value}',
                      )
                      .join('\n'),
                ),
                const SizedBox(height: spacingMD),
                Wrap(
                  spacing: spacingSM,
                  runSpacing: spacingSM,
                  children: <Widget>[
                    if (isAdmin)
                      FilledButton(
                        onPressed: () => context.push(AppRoutes.profileAdmin),
                        child: const Text('Open Admin'),
                      ),
                    OutlinedButton(
                      onPressed: () => _signOut(context, ref),
                      child: const Text('Sign out'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
        if (permissions.isNotEmpty) ...<Widget>[
          const SizedBox(height: spacingMD),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(spacingLG),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Permissions',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: spacingSM),
                  Wrap(
                    spacing: spacingSM,
                    runSpacing: spacingSM,
                    children: permissions
                        .map(
                          (String permission) => Chip(label: Text(permission)),
                        )
                        .toList(growable: false),
                  ),
                ],
              ),
            ),
          ),
        ],
        if (profile.club != null) ...<Widget>[
          const SizedBox(height: spacingMD),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(spacingLG),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Club context',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: spacingSM),
                  Text(
                    profile.club!.entries
                        .take(12)
                        .map(
                          (MapEntry<String, Object?> entry) =>
                              '${entry.key}: ${entry.value}',
                        )
                        .join('\n'),
                  ),
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }

  Future<void> _signOut(BuildContext context, WidgetRef ref) async {
    try {
      await ref.read(exchangeApiClientProvider).logout();
      await ref.read(appSessionControllerProvider.notifier).clear();
      if (context.mounted) {
        context.go(AppRoutes.profile);
      }
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(AppFeedback.messageFor(error))));
      }
    }
  }
}

class _BlockedCard extends StatelessWidget {
  const _BlockedCard({required this.title, required this.message});

  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(spacingLG),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: spacingSM),
            Text(message),
          ],
        ),
      ),
    );
  }
}
