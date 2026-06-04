import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/app_breakpoints.dart';
import '../../core/constants/app_spacing.dart';
import '../../shared/state/gtex_async_surface_state.dart';
import '../../shared/widgets/async_state_widget.dart';
import 'domain/squad_models.dart';
import 'providers/squad_providers.dart';
import 'widgets/squad_widgets.dart';

class SquadScreen extends ConsumerWidget {
  const SquadScreen({
    super.key,
    this.clubId = 'current',
    this.role = 'club.owner',
  });

  final String clubId;
  final String role;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final SquadRequest request = SquadRequest(clubId: clubId, role: role);
    final AsyncValue<GtexSurfaceState<SquadOperationsSnapshot>> asyncState = ref
        .watch(squadOperationsProvider(request));
    final GtexSurfaceState<SquadOperationsSnapshot> state = asyncState.when(
      data: (GtexSurfaceState<SquadOperationsSnapshot> value) => value,
      loading: () => const GtexLoading<SquadOperationsSnapshot>(),
      error:
          (Object error, StackTrace stackTrace) =>
              GtexError<SquadOperationsSnapshot>(
                code: 'squad_provider',
                message: error.toString(),
              ),
    );

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
              child: AsyncStateWidget<SquadOperationsSnapshot>(
                state: state,
                onLoading:
                    () => const SquadStatusPanel(
                      title: 'Loading Squad',
                      message: 'Fetching roster and availability data.',
                      icon: Icons.downloading_rounded,
                    ),
                onEmpty:
                    (String? reason) => SquadStatusPanel(
                      title: 'Squad Empty',
                      message: reason ?? 'No players in squad.',
                      icon: Icons.inbox_rounded,
                    ),
                onBlocked:
                    (String reason, String? ctaRoute) => SquadStatusPanel(
                      title: 'Squad Blocked',
                      message: reason,
                      icon: Icons.lock_rounded,
                      color: Colors.redAccent,
                    ),
                onPending: (SquadOperationsSnapshot? stale) {
                  if (stale == null) {
                    return const SquadStatusPanel(
                      title: 'Squad Pending',
                      message: 'Waiting for backend confirmation.',
                      icon: Icons.schedule_rounded,
                    );
                  }
                  return SquadOperationsView(
                    snapshot: stale,
                    request: request,
                    bottomPadding: bottomPadding,
                  );
                },
                onSyncing:
                    (SquadOperationsSnapshot current) => SquadOperationsView(
                      snapshot: current,
                      request: request,
                      bottomPadding: bottomPadding,
                    ),
                onReconnecting: (
                  SquadOperationsSnapshot? lastKnown,
                  int attempt,
                ) {
                  if (lastKnown == null) {
                    return SquadStatusPanel(
                      title: 'Reconnecting Squad',
                      message:
                          'Trying to restore squad updates. Attempt $attempt.',
                      icon: Icons.wifi_find_rounded,
                    );
                  }
                  return SquadOperationsView(
                    snapshot: lastKnown,
                    request: request,
                    bottomPadding: bottomPadding,
                  );
                },
                onDegraded:
                    (SquadOperationsSnapshot current, String warning) =>
                        SquadOperationsView(
                          snapshot: current,
                          request: request,
                          bottomPadding: bottomPadding,
                        ),
                onConfirmed:
                    (SquadOperationsSnapshot data, String? auditRef) =>
                        SquadOperationsView(
                          snapshot: data,
                          request: request,
                          bottomPadding: bottomPadding,
                        ),
                onError:
                    (String code, String message, VoidCallback retry) =>
                        SquadStatusPanel(
                          title: 'Squad Error',
                          message: '$code: $message',
                          icon: Icons.error_rounded,
                          color: Colors.redAccent,
                        ),
                onData:
                    (SquadOperationsSnapshot data) => SquadOperationsView(
                      snapshot: data,
                      request: request,
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
