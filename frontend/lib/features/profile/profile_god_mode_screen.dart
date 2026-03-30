import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/app_feedback.dart';
import '../../data/gte_api_repository.dart';
import '../../screens/admin/god_mode_admin_screen.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import '../../shared/widgets/gtex_premium_panels.dart';
import '../../widgets/gte_state_panel.dart';

class GodModeAccessGate {
  const GodModeAccessGate._({required this.allowed, this.reason});

  const GodModeAccessGate.allowed() : this._(allowed: true);

  const GodModeAccessGate.blocked(String reason)
    : this._(allowed: false, reason: reason);

  final bool allowed;
  final String? reason;
}

final godModeAccessGateProvider = FutureProvider.autoDispose<GodModeAccessGate>(
  (Ref ref) async {
    final String? blockedReason = ref.watch(godModeBlockedReasonProvider);
    if (blockedReason != null) {
      return GodModeAccessGate.blocked(blockedReason);
    }
    try {
      await ref
          .watch(authedApiProvider)
          .getMap('/api/admin/god-mode/bootstrap');
      return const GodModeAccessGate.allowed();
    } catch (error) {
      return GodModeAccessGate.blocked(_probeBlockedReason(error));
    }
  },
);

class ProfileGodModeScreen extends ConsumerWidget {
  const ProfileGodModeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<GodModeAccessGate> access = ref.watch(
      godModeAccessGateProvider,
    );

    return access.when(
      data: (GodModeAccessGate gate) {
        if (!gate.allowed) {
          return _GodModeBlockedScreen(reason: gate.reason ?? 'admin required');
        }
        final String? accessToken = ref.watch(accessTokenProvider);
        if (accessToken == null || accessToken.trim().isEmpty) {
          return const _GodModeBlockedScreen(reason: 'missing session claims');
        }
        return GodModeAdminScreen(
          baseUrl: ref.read(apiBaseUrlProvider),
          accessToken: accessToken,
          backendMode: ref.read(criticalBackendModeProvider),
        );
      },
      loading:
          () => const AppPageLayout(
            title: 'God Mode',
            subtitle:
                'Verifying admin bootstrap access before exposing the shipped God Mode console.',
            trailing: DataSourceBadge(status: DataSourceStatus.live),
            children: <Widget>[
              GteStatePanel(
                eyebrow: 'GOD MODE ACCESS',
                title: 'Verifying bootstrap route',
                message:
                    'Checking the backend bootstrap before exposing any deeper admin console surface.',
                icon: Icons.admin_panel_settings_outlined,
                isLoading: true,
              ),
            ],
          ),
      error:
          (Object error, StackTrace stackTrace) =>
              _GodModeBlockedScreen(reason: AppFeedback.messageFor(error)),
    );
  }
}

class _GodModeBlockedScreen extends ConsumerWidget {
  const _GodModeBlockedScreen({required this.reason});

  final String reason;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final List<String> permissions = ref.watch(currentUserPermissionsProvider);
    return AppPageLayout(
      title: 'God Mode',
      subtitle:
          'The active shell only exposes God Mode when the authenticated admin session can actually reach the backend bootstrap route.',
      trailing: const DataSourceBadge(status: DataSourceStatus.blocked),
      children: <Widget>[
        GtexHeroPanel(
          eyebrow: 'GOD MODE ACCESS',
          title: 'God Mode blocked',
          description: reason,
          metrics: <Widget>[
            const GtexPill(label: 'BLOCKED', tone: GtexSurfaceTone.danger),
            if (permissions.isNotEmpty)
              ...permissions.map(
                (String value) =>
                    GtexPill(label: value, tone: GtexSurfaceTone.warning),
              ),
          ],
        ),
        GtexSectionPanel(
          eyebrow: 'ACCESS TRUTH',
          title: 'Bootstrap route required',
          subtitle:
              'The active shell keeps God Mode behind a real backend bootstrap check instead of exposing a disconnected admin shell.',
          child: GteStatePanel(
            eyebrow: 'GOD MODE',
            title: 'Backend access not available',
            message: reason,
            icon: Icons.lock_outline_rounded,
            accentColor: Theme.of(context).colorScheme.error,
          ),
        ),
      ],
    );
  }
}

String _probeBlockedReason(Object error) {
  if (error is GteApiException) {
    switch (error.statusCode) {
      case 401:
      case 403:
        return 'admin required';
      case 404:
        return 'backend route unavailable';
      default:
        break;
    }
  }
  return AppFeedback.messageFor(error);
}
