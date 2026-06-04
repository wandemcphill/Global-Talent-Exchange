import 'package:flutter/material.dart';
import 'package:gte_frontend/features/shell/models/gtex_surface_state.dart';
import 'package:gte_frontend/models/club_models.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class SquadReadinessSnapshot {
  const SquadReadinessSnapshot({
    required this.clubName,
    required this.registeredPlayerCount,
    required this.scoutingSignalCount,
    this.isSyncing = false,
    this.errorMessage,
    this.blockedMessage,
  });

  factory SquadReadinessSnapshot.fromDashboard(
    ClubDashboardData data, {
    bool isSyncing = false,
    String? errorMessage,
  }) {
    return SquadReadinessSnapshot(
      clubName: data.clubName,
      registeredPlayerCount: data.playerCount,
      scoutingSignalCount: data.reputation.recentEvents.length,
      isSyncing: isSyncing,
      errorMessage: errorMessage,
    );
  }

  factory SquadReadinessSnapshot.blocked({
    required String clubName,
    required String message,
  }) {
    return SquadReadinessSnapshot(
      clubName: clubName,
      registeredPlayerCount: null,
      scoutingSignalCount: 0,
      blockedMessage: message,
    );
  }

  final String clubName;
  final int? registeredPlayerCount;
  final int scoutingSignalCount;
  final bool isSyncing;
  final String? errorMessage;
  final String? blockedMessage;
}

class SquadReadinessPanel extends StatelessWidget {
  const SquadReadinessPanel({super.key, required this.snapshot});

  final SquadReadinessSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final List<_SquadReadinessLane> lanes = _buildLanes();
    return GteSurfacePanel(
      key: const Key('club-squad-readiness-panel'),
      accentColor: GteShellTheme.accentClub,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Icon(Icons.health_and_safety_outlined),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Squad and player readiness',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Availability, injuries, morale, chemistry, contracts, and notes stay tied to backend squad truth for ${snapshot.clubName}.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (snapshot.errorMessage != null) ...<Widget>[
            const SizedBox(height: 12),
            Text(
              snapshot.errorMessage!,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: GteShellTheme.warning),
            ),
          ],
          const SizedBox(height: 16),
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool compact = constraints.maxWidth < 760;
              final double width =
                  compact
                      ? constraints.maxWidth
                      : (constraints.maxWidth - 24) / 3;
              return Wrap(
                spacing: 12,
                runSpacing: 12,
                children: lanes
                    .map(
                      (_SquadReadinessLane lane) => SizedBox(
                        width: width,
                        child: _SquadReadinessLaneTile(lane: lane),
                      ),
                    )
                    .toList(growable: false),
              );
            },
          ),
        ],
      ),
    );
  }

  List<_SquadReadinessLane> _buildLanes() {
    final String? blockedMessage = snapshot.blockedMessage;
    final bool blocked = blockedMessage != null;
    final GtexSurfaceState waitingState =
        blocked
            ? GtexSurfaceState.blocked
            : snapshot.isSyncing
            ? GtexSurfaceState.syncing
            : GtexSurfaceState.degraded;
    final String waitingValue =
        blocked
            ? 'BLOCKED'
            : snapshot.isSyncing
            ? 'SYNCING'
            : 'WAITING';
    final String waitingPrefix =
        blocked ? blockedMessage : 'Backend squad endpoint is not mounted yet.';

    return <_SquadReadinessLane>[
      _SquadReadinessLane(
        keyName: 'registry',
        title: 'Squad registry',
        value:
            snapshot.registeredPlayerCount == null
                ? waitingValue
                : '${snapshot.registeredPlayerCount}',
        state:
            blocked
                ? GtexSurfaceState.blocked
                : snapshot.registeredPlayerCount == null
                ? waitingState
                : snapshot.registeredPlayerCount! > 0
                ? GtexSurfaceState.confirmed
                : GtexSurfaceState.empty,
        message:
            blocked
                ? blockedMessage
                : snapshot.registeredPlayerCount == null
                ? 'Registered player count has not been returned by the backend.'
                : snapshot.registeredPlayerCount! > 0
                ? 'Registered player count is confirmed by the club payload.'
                : 'The backend returned an empty squad registry.',
        icon: Icons.groups_outlined,
      ),
      _SquadReadinessLane(
        keyName: 'availability',
        title: 'Availability',
        value: waitingValue,
        state: waitingState,
        message:
            '$waitingPrefix No local availability is inferred from squad size.',
        icon: Icons.event_available_outlined,
      ),
      _SquadReadinessLane(
        keyName: 'injuries',
        title: 'Injuries',
        value: waitingValue,
        state: waitingState,
        message:
            '$waitingPrefix Medical status remains unknown until an injury report arrives.',
        icon: Icons.personal_injury_outlined,
      ),
      _SquadReadinessLane(
        keyName: 'morale',
        title: 'Morale',
        value: waitingValue,
        state: waitingState,
        message:
            '$waitingPrefix Dressing-room mood is not derived from reputation or form.',
        icon: Icons.sentiment_satisfied_alt_outlined,
      ),
      _SquadReadinessLane(
        keyName: 'chemistry',
        title: 'Chemistry',
        value: waitingValue,
        state: waitingState,
        message:
            '$waitingPrefix Unit chemistry needs explicit squad relationship data.',
        icon: Icons.hub_outlined,
      ),
      _SquadReadinessLane(
        keyName: 'contracts',
        title: 'Contracts',
        value: waitingValue,
        state: waitingState,
        message:
            '$waitingPrefix Contract risk stays hidden until player contract rows are supplied.',
        icon: Icons.description_outlined,
      ),
      _SquadReadinessLane(
        keyName: 'scouting',
        title: 'Scouting notes',
        value:
            blocked
                ? 'BLOCKED'
                : snapshot.scoutingSignalCount > 0
                ? '${snapshot.scoutingSignalCount} signals'
                : waitingValue,
        state:
            blocked
                ? GtexSurfaceState.blocked
                : snapshot.scoutingSignalCount > 0
                ? GtexSurfaceState.degraded
                : waitingState,
        message:
            blocked
                ? blockedMessage
                : snapshot.scoutingSignalCount > 0
                ? 'Club intelligence events are present, but per-player scouting notes are still missing.'
                : '$waitingPrefix Player scouting notes have not been returned.',
        icon: Icons.manage_search_outlined,
      ),
    ];
  }
}

class _SquadReadinessLane {
  const _SquadReadinessLane({
    required this.keyName,
    required this.title,
    required this.value,
    required this.state,
    required this.message,
    required this.icon,
  });

  final String keyName;
  final String title;
  final String value;
  final GtexSurfaceState state;
  final String message;
  final IconData icon;
}

class _SquadReadinessLaneTile extends StatelessWidget {
  const _SquadReadinessLaneTile({required this.lane});

  final _SquadReadinessLane lane;

  @override
  Widget build(BuildContext context) {
    final Color color = _colorFor(lane.state);
    return Container(
      key: Key('club-squad-readiness-${lane.keyName}'),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: color.withValues(alpha: 0.24)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(lane.icon, color: color, size: 18),
              const SizedBox(width: 8),
              Text(
                lane.state.name.toUpperCase(),
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: color,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(lane.title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Text(lane.value, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          Text(lane.message, style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    );
  }

  Color _colorFor(GtexSurfaceState state) {
    switch (state) {
      case GtexSurfaceState.confirmed:
      case GtexSurfaceState.data:
        return GteShellTheme.positive;
      case GtexSurfaceState.blocked:
      case GtexSurfaceState.error:
        return GteShellTheme.negative;
      case GtexSurfaceState.pending:
      case GtexSurfaceState.degraded:
        return GteShellTheme.warning;
      case GtexSurfaceState.loading:
      case GtexSurfaceState.syncing:
      case GtexSurfaceState.reconnecting:
        return GteShellTheme.accentClub;
      case GtexSurfaceState.empty:
        return GteShellTheme.textMuted;
    }
  }
}
