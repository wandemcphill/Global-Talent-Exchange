import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/features/club_identity/jerseys/widgets/identity_color_utils.dart';
import 'package:gte_frontend/features/shell/domain/gtex_surface_state.dart';
import 'package:gte_frontend/models/academy_models.dart';
import 'package:gte_frontend/models/club_finance_models.dart';
import 'package:gte_frontend/models/club_models.dart';
import 'package:gte_frontend/models/sponsorship_models.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ClubHqOperationsPanel extends StatelessWidget {
  const ClubHqOperationsPanel({
    super.key,
    required this.data,
    required this.operationsController,
    this.onRefresh,
  });

  final ClubDashboardData? data;
  final ClubOpsController? operationsController;
  final VoidCallback? onRefresh;

  @override
  Widget build(BuildContext context) {
    final ClubOpsController? controller = operationsController;
    if (controller != null) {
      return AnimatedBuilder(
        animation: controller,
        builder: (BuildContext context, Widget? child) => _buildPanel(context),
      );
    }
    return _buildPanel(context);
  }

  Widget _buildPanel(BuildContext context) {
    final ClubOpsController? controller = operationsController;
    final bool isLoading = controller?.isLoadingClubData == true;
    final String? error = controller?.clubErrorMessage;
    final ClubFinanceSnapshot? finance = controller?.finance;
    final SponsorshipDashboard? sponsorships = controller?.sponsorships;
    final AcademyDashboard? academy = controller?.academy;
    final bool hasOpsData = controller?.hasClubData == true;

    final List<_ClubHqOpsSignal> signals = <_ClubHqOpsSignal>[
      _readinessSignal(isLoading: isLoading),
      _financeSignal(finance, isLoading: isLoading, error: error),
      _academySignal(academy, isLoading: isLoading, error: error),
      _staffSignal(academy, isLoading: isLoading, error: error),
      _sponsorshipSignal(sponsorships, isLoading: isLoading, error: error),
      _brandingSignal(isLoading: isLoading),
      _trophiesSignal(isLoading: isLoading),
      _rankingsSignal(isLoading: isLoading),
    ];

    return GteSurfacePanel(
      key: const Key('club-hq-operations-panel'),
      accentColor: GteShellTheme.accentClub,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Icon(Icons.account_tree_outlined),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Club HQ readiness',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Production lanes render only from club dashboard and club operations payloads. Missing backend data stays visible as blocked, syncing, degraded, empty, or error.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              if (onRefresh != null) ...<Widget>[
                const SizedBox(width: 12),
                IconButton.filledTonal(
                  onPressed: isLoading ? null : onRefresh,
                  icon: const Icon(Icons.refresh_outlined),
                  tooltip: 'Refresh club operations',
                ),
              ],
            ],
          ),
          if (error != null) ...<Widget>[
            const SizedBox(height: 14),
            Text(
              error,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: GteShellTheme.negative),
            ),
          ] else if (controller == null) ...<Widget>[
            const SizedBox(height: 14),
            Text(
              'Club operations controller is not mounted on this route yet.',
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: GteShellTheme.warning),
            ),
          ] else if (!hasOpsData && !isLoading) ...<Widget>[
            const SizedBox(height: 14),
            Text(
              'Waiting for the finance, academy, staff, and sponsorship payloads to sync.',
              style: Theme.of(context).textTheme.bodyMedium,
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
                children: signals
                    .map(
                      (_ClubHqOpsSignal signal) => SizedBox(
                        width: width,
                        child: _ClubHqOpsTile(signal: signal),
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

  _ClubHqOpsSignal _readinessSignal({required bool isLoading}) {
    final int? playerCount = data?.playerCount;
    if (isLoading) {
      return const _ClubHqOpsSignal.syncing(
        title: 'Readiness',
        value: 'SYNCING',
        message: 'Club operations are refreshing from the backend.',
        icon: Icons.groups_outlined,
      );
    }
    if (data == null) {
      return const _ClubHqOpsSignal(
        title: 'Readiness',
        value: 'BLOCKED',
        state: GtexSurfaceState.blocked,
        message:
            'Club dashboard payload is required before HQ readiness can open.',
        icon: Icons.groups_outlined,
      );
    }
    if (playerCount == null) {
      return const _ClubHqOpsSignal(
        title: 'Readiness',
        value: 'UNKNOWN',
        state: GtexSurfaceState.degraded,
        message: 'Registered squad count is missing from the club record.',
        icon: Icons.groups_outlined,
      );
    }
    return _ClubHqOpsSignal(
      title: 'Readiness',
      value: '$playerCount',
      state:
          playerCount > 0 ? GtexSurfaceState.confirmed : GtexSurfaceState.empty,
      message:
          playerCount > 0
              ? 'Registered player count is confirmed by the club payload.'
              : 'The club payload returned no registered players.',
      icon: Icons.groups_outlined,
    );
  }

  _ClubHqOpsSignal _financeSignal(
    ClubFinanceSnapshot? finance, {
    required bool isLoading,
    required String? error,
  }) {
    if (error != null) {
      return const _ClubHqOpsSignal.error(
        title: 'Finance snapshot',
        message: 'Finance payload failed to load from club operations.',
        icon: Icons.account_balance_wallet_outlined,
      );
    }
    if (isLoading) {
      return const _ClubHqOpsSignal.syncing(
        title: 'Finance snapshot',
        value: 'SYNCING',
        message: 'Waiting for operating cash, budget, and ledger payloads.',
        icon: Icons.account_balance_wallet_outlined,
      );
    }
    if (finance == null) {
      return const _ClubHqOpsSignal(
        title: 'Finance snapshot',
        value: 'BLOCKED',
        state: GtexSurfaceState.blocked,
        message: 'No finance payload is mounted; HQ will not infer cashflow.',
        icon: Icons.account_balance_wallet_outlined,
      );
    }
    final ClubBalanceSummary summary = finance.balanceSummary;
    return _ClubHqOpsSignal(
      title: 'Finance snapshot',
      value: _money(summary.currentBalance),
      state:
          finance.ledgerEntries.isEmpty
              ? GtexSurfaceState.degraded
              : GtexSurfaceState.confirmed,
      message:
          'Net monthly movement ${_money(summary.netMonthlyMovement)} with ${summary.cashRunwayMonths.toStringAsFixed(1)} months runway.',
      icon: Icons.account_balance_wallet_outlined,
    );
  }

  _ClubHqOpsSignal _academySignal(
    AcademyDashboard? academy, {
    required bool isLoading,
    required String? error,
  }) {
    if (error != null) {
      return const _ClubHqOpsSignal.error(
        title: 'Academy',
        message: 'Academy payload failed to load from club operations.',
        icon: Icons.school_outlined,
      );
    }
    if (isLoading) {
      return const _ClubHqOpsSignal.syncing(
        title: 'Academy',
        value: 'SYNCING',
        message: 'Waiting for pathway summary, players, and promotions.',
        icon: Icons.school_outlined,
      );
    }
    if (academy == null) {
      return const _ClubHqOpsSignal(
        title: 'Academy',
        value: 'BLOCKED',
        state: GtexSurfaceState.blocked,
        message: 'No academy payload is mounted for this club.',
        icon: Icons.school_outlined,
      );
    }
    final AcademyPathwaySummary summary = academy.pathwaySummary;
    return _ClubHqOpsSignal(
      title: 'Academy',
      value: '${summary.squadSize}',
      state:
          summary.squadSize > 0
              ? GtexSurfaceState.confirmed
              : GtexSurfaceState.empty,
      message:
          '${summary.promotionsThisSeason} promotions this season; ${summary.graduationRatePercent.toStringAsFixed(1)}% graduation rate.',
      icon: Icons.school_outlined,
    );
  }

  _ClubHqOpsSignal _staffSignal(
    AcademyDashboard? academy, {
    required bool isLoading,
    required String? error,
  }) {
    if (error != null) {
      return const _ClubHqOpsSignal.error(
        title: 'Staff',
        message: 'Staff coverage could not be resolved from operations data.',
        icon: Icons.badge_outlined,
      );
    }
    if (isLoading) {
      return const _ClubHqOpsSignal.syncing(
        title: 'Staff',
        value: 'SYNCING',
        message: 'Waiting for backend-authored academy staff coverage.',
        icon: Icons.badge_outlined,
      );
    }
    if (academy == null) {
      return const _ClubHqOpsSignal(
        title: 'Staff',
        value: 'BLOCKED',
        state: GtexSurfaceState.blocked,
        message:
            'No dedicated staff roster or academy staff coverage payload is mounted.',
        icon: Icons.badge_outlined,
      );
    }
    final int namedLeads =
        academy.programs
            .where(
              (AcademyProgram program) => program.staffLead.trim().isNotEmpty,
            )
            .length;
    return _ClubHqOpsSignal(
      title: 'Staff',
      value: namedLeads == 0 ? 'COVERAGE' : '$namedLeads leads',
      state:
          namedLeads == 0
              ? GtexSurfaceState.degraded
              : GtexSurfaceState.confirmed,
      message:
          '${academy.pathwaySummary.staffCoverageLabel}; dedicated staff roster endpoint still pending.',
      icon: Icons.badge_outlined,
    );
  }

  _ClubHqOpsSignal _sponsorshipSignal(
    SponsorshipDashboard? sponsorships, {
    required bool isLoading,
    required String? error,
  }) {
    if (error != null) {
      return const _ClubHqOpsSignal.error(
        title: 'Sponsorships',
        message: 'Sponsorship overview failed to load from club operations.',
        icon: Icons.handshake_outlined,
      );
    }
    if (isLoading) {
      return const _ClubHqOpsSignal.syncing(
        title: 'Sponsorships',
        value: 'SYNCING',
        message: 'Waiting for contracts, catalog, and visible assets.',
        icon: Icons.handshake_outlined,
      );
    }
    if (sponsorships == null) {
      return const _ClubHqOpsSignal(
        title: 'Sponsorships',
        value: 'BLOCKED',
        state: GtexSurfaceState.blocked,
        message: 'No sponsorship payload is mounted for this club.',
        icon: Icons.handshake_outlined,
      );
    }
    return _ClubHqOpsSignal(
      title: 'Sponsorships',
      value: '${sponsorships.activeContractCount}',
      state:
          sponsorships.activeContractCount > 0
              ? GtexSurfaceState.confirmed
              : GtexSurfaceState.empty,
      message:
          '${_money(sponsorships.activeContractValue)} active value and ${sponsorships.assetSlots.length} visible asset slots.',
      icon: Icons.handshake_outlined,
    );
  }

  _ClubHqOpsSignal _brandingSignal({required bool isLoading}) {
    if (isLoading) {
      return const _ClubHqOpsSignal.syncing(
        title: 'Branding',
        value: 'SYNCING',
        message: 'Waiting for club dashboard identity and branding state.',
        icon: Icons.palette_outlined,
      );
    }
    final ClubDashboardData? value = data;
    if (value == null) {
      return const _ClubHqOpsSignal(
        title: 'Branding',
        value: 'BLOCKED',
        state: GtexSurfaceState.blocked,
        message:
            'Club identity payload is required before branding can render.',
        icon: Icons.palette_outlined,
      );
    }
    return _ClubHqOpsSignal(
      title: 'Branding',
      value:
          value.branding.reviewStatus.trim().isEmpty
              ? 'UNKNOWN'
              : value.branding.reviewStatus,
      state:
          value.branding.reviewStatus.trim().isEmpty
              ? GtexSurfaceState.degraded
              : GtexSurfaceState.confirmed,
      message:
          '${value.branding.selectedTheme.name}; ${value.branding.reviewNote}',
      icon: Icons.palette_outlined,
    );
  }

  _ClubHqOpsSignal _trophiesSignal({required bool isLoading}) {
    if (isLoading) {
      return const _ClubHqOpsSignal.syncing(
        title: 'Trophies',
        value: 'SYNCING',
        message: 'Waiting for trophy cabinet payload.',
        icon: Icons.emoji_events_outlined,
      );
    }
    final ClubDashboardData? value = data;
    if (value == null) {
      return const _ClubHqOpsSignal(
        title: 'Trophies',
        value: 'BLOCKED',
        state: GtexSurfaceState.blocked,
        message: 'Trophy cabinet payload is not available yet.',
        icon: Icons.emoji_events_outlined,
      );
    }
    final int honors = value.trophyCabinet.totalHonorsCount;
    return _ClubHqOpsSignal(
      title: 'Trophies',
      value: '$honors',
      state: honors > 0 ? GtexSurfaceState.confirmed : GtexSurfaceState.empty,
      message:
          '${value.trophyCabinet.majorHonorsCount} major and ${value.trophyCabinet.academyHonorsCount} academy honors from the cabinet payload.',
      icon: Icons.emoji_events_outlined,
    );
  }

  _ClubHqOpsSignal _rankingsSignal({required bool isLoading}) {
    if (isLoading) {
      return const _ClubHqOpsSignal.syncing(
        title: 'Rankings',
        value: 'SYNCING',
        message: 'Waiting for reputation leaderboard entries.',
        icon: Icons.leaderboard_outlined,
      );
    }
    final ClubDashboardData? value = data;
    if (value == null) {
      return const _ClubHqOpsSignal(
        title: 'Rankings',
        value: 'BLOCKED',
        state: GtexSurfaceState.blocked,
        message:
            'Leaderboard context is not available without a club dashboard payload.',
        icon: Icons.leaderboard_outlined,
      );
    }
    final int? globalRank = value.reputation.globalRank?.rank;
    final int? regionalRank = value.reputation.regionalRank?.rank;
    if (globalRank == null && regionalRank == null) {
      return const _ClubHqOpsSignal(
        title: 'Rankings',
        value: 'UNRANKED',
        state: GtexSurfaceState.empty,
        message:
            'No global or regional leaderboard entry was returned for this club.',
        icon: Icons.leaderboard_outlined,
      );
    }
    return _ClubHqOpsSignal(
      title: 'Rankings',
      value:
          globalRank == null
              ? 'Regional #$regionalRank'
              : 'Global #$globalRank',
      state: GtexSurfaceState.confirmed,
      message:
          regionalRank == null
              ? 'Global leaderboard entry is present; regional rank is missing.'
              : 'Regional #$regionalRank is present in reputation leaderboard data.',
      icon: Icons.leaderboard_outlined,
    );
  }

  static String _money(double value) {
    final String sign = value < 0 ? '-' : '';
    final double absolute = value.abs();
    if (absolute >= 1000000) {
      return '${sign}\$${(absolute / 1000000).toStringAsFixed(1)}M';
    }
    if (absolute >= 1000) {
      return '${sign}\$${(absolute / 1000).toStringAsFixed(1)}K';
    }
    return '${sign}\$${absolute.toStringAsFixed(0)}';
  }
}

class _ClubHqOpsSignal {
  const _ClubHqOpsSignal({
    required this.title,
    required this.value,
    required this.state,
    required this.message,
    required this.icon,
  });

  const _ClubHqOpsSignal.syncing({
    required this.title,
    required this.value,
    required this.message,
    required this.icon,
  }) : state = GtexSurfaceState.syncing;

  const _ClubHqOpsSignal.error({
    required this.title,
    required this.message,
    required this.icon,
  }) : value = 'ERROR',
       state = GtexSurfaceState.error;

  final String title;
  final String value;
  final GtexSurfaceState state;
  final String message;
  final IconData icon;
}

class _ClubHqOpsTile extends StatelessWidget {
  const _ClubHqOpsTile({required this.signal});

  final _ClubHqOpsSignal signal;

  @override
  Widget build(BuildContext context) {
    final Color color = _colorFor(signal.state);
    return Container(
      constraints: const BoxConstraints(minHeight: 190),
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
              Icon(signal.icon, color: color, size: 18),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  signal.state.name.toUpperCase(),
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: color,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(signal.title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Text(
            signal.value,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Text(signal.message, style: Theme.of(context).textTheme.bodyMedium),
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

class ClubHubStatCard extends StatelessWidget {
  const ClubHubStatCard({
    super.key,
    required this.label,
    required this.value,
    required this.detail,
    required this.icon,
  });

  final String label;
  final String value;
  final String detail;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final Color accent = tokens.accentClub;

    return ConstrainedBox(
      constraints: const BoxConstraints(minWidth: 220, maxWidth: 260),
      child: GteSurfacePanel(
        accentColor: accent,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(tokens.radiusMedium - 2),
                color: accent.withValues(alpha: 0.14),
                border: Border.all(color: accent.withValues(alpha: 0.2)),
              ),
              child: Icon(icon, color: accent),
            ),
            const SizedBox(height: 14),
            Text(
              label.toUpperCase(),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: accent,
                letterSpacing: 0.9,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 10),
            Text(value, style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 6),
            Text(
              detail,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }
}

class ClubHubMetricRow extends StatelessWidget {
  const ClubHubMetricRow({super.key, required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Row(
              children: <Widget>[
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: GteShellTheme.accentClub,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    label,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ),
        ],
      ),
    );
  }
}

class ClubHubPill extends StatelessWidget {
  const ClubHubPill({super.key, required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: GteShellTheme.accentClub.withValues(alpha: 0.14),
        border: Border.all(
          color: GteShellTheme.accentClub.withValues(alpha: 0.22),
        ),
      ),
      child: Text(
        label,
        style: Theme.of(
          context,
        ).textTheme.labelLarge?.copyWith(color: GteShellTheme.accentClub),
      ),
    );
  }
}

class ClubColorPill extends StatelessWidget {
  const ClubColorPill({super.key, required this.label, required this.colorHex});

  final String label;
  final String colorHex;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: GteShellTheme.stroke),
        color: GteShellTheme.panel.withValues(alpha: 0.86),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Container(
            width: 12,
            height: 12,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: identityColorFromHex(colorHex),
            ),
          ),
          const SizedBox(width: 8),
          Text(label, style: Theme.of(context).textTheme.labelLarge),
        ],
      ),
    );
  }
}

class TimelineListTile extends StatelessWidget {
  const TimelineListTile({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.value,
    required this.valueColor,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final String value;
  final Color valueColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: GteShellTheme.stroke),
        color: GteShellTheme.panel.withValues(alpha: 0.82),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: GteShellTheme.accent.withValues(alpha: 0.12),
            ),
            child: Icon(icon, size: 18, color: GteShellTheme.accent),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(title, style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 4),
                Text(subtitle, style: Theme.of(context).textTheme.bodyMedium),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Text(
            value,
            style: Theme.of(
              context,
            ).textTheme.labelLarge?.copyWith(color: valueColor),
          ),
        ],
      ),
    );
  }
}
