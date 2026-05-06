import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_feedback.dart';
import '../../navigation/app_destinations.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/providers/live_clients_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import '../../shared/widgets/gtex_premium_panels.dart';
import '../../theme/gte_theme_picker_sheet.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import 'live_profile_provider.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<ProfileData> profileValue = ref.watch(profileDataProvider);
    return AppPageLayout(
      title: 'Profile',
      subtitle:
          'Identity desk for live session truth, permissions, club context, and shell settings.',
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
                      : const _GuestProfile(),
          loading:
              () => const GteStatePanel(
                title: 'Loading profile',
                message:
                    'The active shell is syncing session identity, affinity, and club context.',
                isLoading: true,
              ),
          error:
              (Object error, StackTrace stackTrace) => GteStatePanel(
                title: 'Profile is blocked',
                message: AppFeedback.messageFor(error),
                icon: Icons.error_outline_rounded,
                accentColor: Theme.of(context).colorScheme.error,
              ),
        ),
      ],
    );
  }
}

class _GuestProfile extends StatelessWidget {
  const _GuestProfile();

  @override
  Widget build(BuildContext context) {
    final theme = GteShellTheme.definitionOf(context);
    return Column(
      children: <Widget>[
        GtexHeroPanel(
          eyebrow: 'GUEST IDENTITY',
          title: 'This session is still in visitor mode.',
          description:
              'Sign in to unlock club ownership, wallet actions, admin tools, and live account controls.',
          metrics: <Widget>[
            GtexStatTile(
              label: 'Shell',
              value: theme.metadata.label,
              support: 'Global theme selection persists',
              tone: GtexSurfaceTone.info,
            ),
            const GtexStatTile(
              label: 'Admin',
              value: 'Sign in',
              support: 'Authentication required',
              tone: GtexSurfaceTone.warning,
            ),
          ],
          actions: <Widget>[
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
        const SizedBox(height: 24),
        _ThemeSettingsPanel(),
      ],
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
    final federation = ref.watch(federationContextProvider);
    final String identityLabel =
        profile.user['display_name']?.toString() ??
        profile.user['username']?.toString() ??
        profile.user['email']?.toString() ??
        'Authenticated user';

    return Column(
      children: <Widget>[
        GtexHeroPanel(
          eyebrow: 'IDENTITY DESK',
          title: identityLabel,
          description:
              'Live identity, permissions, and club context stay grounded in backend-backed session truth.',
          metrics: <Widget>[
            GtexStatTile(
              label: 'Role',
              value: role.toUpperCase(),
              support: 'Session authority',
              tone: GtexSurfaceTone.live,
            ),
            GtexStatTile(
              label: 'Followers',
              value: '${profile.followers}',
              support: 'Social graph',
              tone: GtexSurfaceTone.info,
            ),
            GtexStatTile(
              label: 'Following',
              value: '${profile.following}',
              support: 'Tracked operators',
              tone: GtexSurfaceTone.info,
            ),
            GtexStatTile(
              label: 'Club',
              value:
                  profile.club == null
                      ? 'None'
                      : '${profile.club!['name'] ?? profile.club!['id']}',
              support:
                  federation == null
                      ? 'No federation context'
                      : 'Federation ${federation.name ?? federation.id}',
              tone:
                  profile.club == null
                      ? GtexSurfaceTone.warning
                      : GtexSurfaceTone.success,
            ),
          ],
          actions: <Widget>[
            if (isAdmin)
              FilledButton(
                onPressed: () => context.push(AppRoutes.profileAdmin),
                child: const Text('Open command center'),
              ),
            OutlinedButton(
              onPressed: () => _signOut(context, ref),
              child: const Text('Sign out'),
            ),
          ],
        ),
        const SizedBox(height: 24),
        _ThemeSettingsPanel(),
        const SizedBox(height: 24),
        GtexSectionPanel(
          eyebrow: 'SESSION DETAIL',
          title: 'Account detail',
          subtitle: 'Critical identity fields from /api/auth/me and /users/me.',
          child: Text(
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
        ),
        if (permissions.isNotEmpty) ...<Widget>[
          const SizedBox(height: 24),
          GtexSectionPanel(
            eyebrow: 'ACCESS',
            title: 'Permissions',
            subtitle:
                'Every admin and advanced action in the active shell stays tied to explicit session claims.',
            child: Wrap(
              spacing: 12,
              runSpacing: 12,
              children: permissions
                  .map(
                    (String permission) =>
                        GtexPill(label: permission, tone: GtexSurfaceTone.info),
                  )
                  .toList(growable: false),
            ),
          ),
        ],
        if (profile.club != null) ...<Widget>[
          const SizedBox(height: 24),
          GtexSectionPanel(
            eyebrow: 'CLUB CONTEXT',
            title: 'Club context',
            subtitle:
                'Club-backed actions use this live context and do not fake fallback access.',
            child: Text(
              profile.club!.entries
                  .take(12)
                  .map(
                    (MapEntry<String, Object?> entry) =>
                        '${entry.key}: ${entry.value}',
                  )
                  .join('\n'),
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

class _ThemeSettingsPanel extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final theme = GteShellTheme.definitionOf(context);
    return GtexSectionPanel(
      eyebrow: 'SETTINGS',
      title: 'Theme & shell settings',
      subtitle:
          'Profile is the global source for visual shell selection. One choice applies across the active app and persists after restart.',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              GtexPill(label: theme.metadata.label, tone: GtexSurfaceTone.live),
              GtexPill(
                label: theme.metadata.tagline,
                tone: GtexSurfaceTone.info,
              ),
            ],
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: () {
              showModalBottomSheet<void>(
                context: context,
                isScrollControlled: true,
                builder: (BuildContext context) => const GteThemePickerSheet(),
              );
            },
            icon: const Icon(Icons.palette_outlined),
            label: const Text('Open theme selector'),
          ),
        ],
      ),
    );
  }
}
