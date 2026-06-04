import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/app_breakpoints.dart';
import '../../core/constants/app_spacing.dart';
import '../../shared/state/gtex_async_surface_state.dart';
import '../../shared/widgets/async_state_widget.dart';
import 'domain/club_hq_models.dart';
import 'providers/club_hq_providers.dart';
import 'widgets/club_hq_widgets.dart';

class ClubScreen extends ConsumerWidget {
  const ClubScreen({
    super.key,
    this.clubId = 'current',
    this.role = 'club.owner',
  });

  final String clubId;
  final String role;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ClubHqRequest request = ClubHqRequest(clubId: clubId, role: role);
    final AsyncValue<GtexSurfaceState<ClubHqSnapshot>> asyncState = ref.watch(
      clubHqProvider(request),
    );
    final GtexSurfaceState<ClubHqSnapshot> state = asyncState.when(
      data: (GtexSurfaceState<ClubHqSnapshot> value) => value,
      loading: () => const GtexLoading<ClubHqSnapshot>(),
      error:
          (Object error, StackTrace stackTrace) => GtexError<ClubHqSnapshot>(
            code: 'club_hq_provider',
            message: error.toString(),
          ),
    );
    final ClubHqRole resolvedRole =
        clubHqRoleFromRaw(role) ?? ClubHqRole.viewer;

    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final double horizontalPadding =
            constraints.maxWidth >= AppBreakpoints.medium
                ? spacingLG
                : spacingMD;
        final double bottomPadding = MediaQuery.paddingOf(context).bottom + 88;

        return Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1440),
            child: Padding(
              padding: EdgeInsets.fromLTRB(
                horizontalPadding,
                spacingLG,
                horizontalPadding,
                0,
              ),
              child: AsyncStateWidget<ClubHqSnapshot>(
                state: state,
                onLoading:
                    () => const ClubHqStatusPanel(
                      title: 'Loading Club HQ',
                      message: 'Fetching the latest club operations data.',
                      icon: Icons.downloading_rounded,
                    ),
                onEmpty:
                    (String? reason) => ClubHqStatusPanel(
                      title: 'Club Profile Empty',
                      message: reason ?? 'Club profile not yet configured.',
                      icon: Icons.inbox_rounded,
                    ),
                onBlocked:
                    (String reason, String? ctaRoute) => ClubHqStatusPanel(
                      title: 'Club HQ Blocked',
                      message: reason,
                      icon: Icons.lock_rounded,
                      color: Colors.redAccent,
                    ),
                onPending: (ClubHqSnapshot? stale) {
                  if (stale == null) {
                    return const ClubHqStatusPanel(
                      title: 'Club HQ Pending',
                      message: 'Waiting for backend confirmation.',
                      icon: Icons.schedule_rounded,
                    );
                  }
                  return ClubDashboardView(
                    snapshot: stale,
                    role: resolvedRole,
                    bottomPadding: bottomPadding,
                  );
                },
                onSyncing:
                    (ClubHqSnapshot current) => ClubDashboardView(
                      snapshot: current,
                      role: resolvedRole,
                      bottomPadding: bottomPadding,
                    ),
                onReconnecting: (ClubHqSnapshot? lastKnown, int attempt) {
                  if (lastKnown == null) {
                    return ClubHqStatusPanel(
                      title: 'Reconnecting Club HQ',
                      message:
                          'Trying to restore club updates. Attempt $attempt.',
                      icon: Icons.wifi_find_rounded,
                    );
                  }
                  return ClubDashboardView(
                    snapshot: lastKnown,
                    role: resolvedRole,
                    bottomPadding: bottomPadding,
                  );
                },
                onDegraded:
                    (ClubHqSnapshot current, String warning) =>
                        ClubDashboardView(
                          snapshot: current,
                          role: resolvedRole,
                          bottomPadding: bottomPadding,
                        ),
                onConfirmed:
                    (ClubHqSnapshot data, String? auditRef) =>
                        ClubDashboardView(
                          snapshot: data,
                          role: resolvedRole,
                          bottomPadding: bottomPadding,
                        ),
                onError:
                    (String code, String message, VoidCallback retry) =>
                        ClubHqStatusPanel(
                          title: 'Club HQ Error',
                          message: '$code: $message',
                          icon: Icons.error_rounded,
                          color: Colors.redAccent,
                        ),
                onData:
                    (ClubHqSnapshot data) => ClubDashboardView(
                      snapshot: data,
                      role: resolvedRole,
                      bottomPadding: bottomPadding,
                    ),
              ),
            ),
          ),
        );
      },
    );
  }
}
