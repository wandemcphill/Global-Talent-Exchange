import '../models/gtex_profile_models.dart';

typedef GtexProfileLoader = Future<GtexProfileSummary> Function();

class GtexProfileController {
  const GtexProfileController({GtexProfileLoader? loader}) : _loader = loader;

  final GtexProfileLoader? _loader;

  Future<GtexProfileSummary> loadProfile() async {
    final GtexProfileLoader? loader = _loader;
    if (loader != null) {
      return loader();
    }
    throw StateError(
      'Live profile data is required. Test fixture data must be injected from frontend/test.',
    );
  }

  List<GtexSettingSection> settingSections() => const [
    GtexSettingSection(
      id: 'account',
      title: 'Account',
      subtitle: 'Identity, profile, and public GTEX presence.',
      items: [
        GtexSettingItem(
          id: 'profile_details',
          title: 'Profile details',
          description: 'Name, avatar, country, and public display preferences.',
          status: '76% complete',
        ),
        GtexSettingItem(
          id: 'club_identity',
          title: 'Club identity',
          description:
              'Linked club, public owner identity, and club owner status.',
          status: 'Active',
        ),
      ],
    ),
    GtexSettingSection(
      id: 'security',
      title: 'Security',
      subtitle:
          'Protect access to wallets, clubs, orders, and admin workflows.',
      items: [
        GtexSettingItem(
          id: 'password',
          title: 'Password and recovery',
          description: 'Update password and account recovery details.',
          status: 'Good',
        ),
        GtexSettingItem(
          id: 'sessions',
          title: 'Active sessions',
          description: 'Review devices currently signed in to GTEX.',
          status: '2 sessions',
        ),
        GtexSettingItem(
          id: 'two_factor',
          title: 'Two-factor authentication',
          description: 'Protect high-value wallet and club actions.',
          status: 'Recommended',
        ),
      ],
    ),
    GtexSettingSection(
      id: 'preferences',
      title: 'Preferences',
      subtitle:
          'Control notifications, news, market alerts, and display defaults.',
      items: [
        GtexSettingItem(
          id: 'notifications',
          title: 'Notification preferences',
          description:
              'Choose alerts for market, club, wallet, news, and competitions.',
          status: 'Custom',
        ),
        GtexSettingItem(
          id: 'news',
          title: 'AI news personalization',
          description: 'Tune which GTEX stories appear first.',
          status: 'Enabled',
        ),
      ],
    ),
    GtexSettingSection(
      id: 'danger',
      title: 'Account risk controls',
      subtitle: 'Sensitive settings that require re-authentication.',
      items: [
        GtexSettingItem(
          id: 'deactivate',
          title: 'Deactivate account',
          description: 'Suspend sign-in and hide public profile where allowed.',
          status: 'Locked',
          isDanger: true,
        ),
      ],
    ),
  ];

  List<GtexSystemStateSpec> systemStateGallery() => const [
    GtexSystemStateSpec(
      kind: GtexSystemStateKind.loading,
      title: 'Loading GTEX data',
      message: 'We are preparing the football workspace.',
      primaryActionLabel: 'Loading',
    ),
    GtexSystemStateSpec(
      kind: GtexSystemStateKind.empty,
      title: 'Nothing here yet',
      message:
          'Once activity starts, this space will become your GTEX command view.',
      primaryActionLabel: 'Explore GTEX',
    ),
    GtexSystemStateSpec(
      kind: GtexSystemStateKind.error,
      title: 'Something failed',
      message: 'The data could not be loaded. Retry before changing routes.',
      primaryActionLabel: 'Retry',
      secondaryActionLabel: 'Report issue',
    ),
    GtexSystemStateSpec(
      kind: GtexSystemStateKind.offline,
      title: 'Connection interrupted',
      message:
          'GTEX needs a stable connection for market, wallet, and match data.',
      primaryActionLabel: 'Try again',
    ),
    GtexSystemStateSpec(
      kind: GtexSystemStateKind.accessDenied,
      title: 'Access restricted',
      message: 'This GTEX module requires a different role or verified status.',
      primaryActionLabel: 'View requirements',
    ),
    GtexSystemStateSpec(
      kind: GtexSystemStateKind.maintenance,
      title: 'Module in maintenance',
      message:
          'This area is temporarily paused while GTEX operations complete checks.',
      primaryActionLabel: 'Go home',
    ),
    GtexSystemStateSpec(
      kind: GtexSystemStateKind.success,
      title: 'Action complete',
      message: 'The GTEX operation was completed successfully.',
      primaryActionLabel: 'Continue',
    ),
  ];
}
