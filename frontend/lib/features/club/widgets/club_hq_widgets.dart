import 'package:flutter/material.dart';

import '../../../core/constants/app_breakpoints.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/widgets/gtex_surface_card.dart';
import '../../../shared/state/gtex_async_surface_state.dart';
import '../../../shared/widgets/async_state_widget.dart';
import '../domain/club_hq_models.dart';
import '../providers/club_hq_providers.dart';

class ClubHqStatusPanel extends StatelessWidget {
  const ClubHqStatusPanel({
    super.key,
    required this.title,
    required this.message,
    required this.icon,
    this.color = AppColors.primary,
  });

  final String title;
  final String message;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 680),
        child: GtexSurfaceCard(
          glowColor: color,
          padding: const EdgeInsets.all(spacingLG),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Icon(icon, color: color, size: 34),
              const SizedBox(height: spacingMD),
              Text(title, style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: spacingSM),
              Text(
                message,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class ClubDashboardView extends StatelessWidget {
  const ClubDashboardView({
    super.key,
    required this.snapshot,
    required this.role,
    required this.bottomPadding,
  });

  final ClubHqSnapshot snapshot;
  final ClubHqRole role;
  final double bottomPadding;

  @override
  Widget build(BuildContext context) {
    final GtexSurfaceState<ClubFinanceDTO> financeState =
        role.canViewFinance
            ? clubFinanceSurfaceState(snapshot.finance)
            : const GtexBlocked<ClubFinanceDTO>(
              reason: 'Finance is restricted to club owners.',
            );

    return ListView(
      key: const Key('club-hq-dashboard'),
      padding: EdgeInsets.only(bottom: bottomPadding),
      children: <Widget>[
        ClubHeaderBanner(dashboard: snapshot.dashboard),
        const SizedBox(height: spacingLG),
        ClubKpiGrid(snapshot: snapshot, financeState: financeState),
        const SizedBox(height: spacingLG),
        _ResponsivePair(
          left: ClubSquadReadinessSection(readiness: snapshot.readiness),
          right: ClubFinanceSection(state: financeState),
        ),
        const SizedBox(height: spacingLG),
        ClubPublicProfileSection(dashboard: snapshot.dashboard),
        const SizedBox(height: spacingLG),
        if (role.canViewStaffAndAcademy)
          _ResponsivePair(
            left: ClubAcademySection(academy: snapshot.academy),
            right: ClubStaffSection(staff: snapshot.staff),
          )
        else
          const _ResponsivePair(
            left: ClubBlockedSection(
              title: 'Academy',
              reason: 'Academy operations are blocked for this role.',
            ),
            right: ClubBlockedSection(
              title: 'Staff',
              reason: 'Staff operations are blocked for this role.',
            ),
          ),
        const SizedBox(height: spacingLG),
        if (role.canViewSponsorships || role.canManageBranding)
          _ResponsivePair(
            left:
                role.canViewSponsorships
                    ? ClubSponsorshipSection(
                      sponsorships: snapshot.sponsorships,
                    )
                    : const ClubBlockedSection(
                      title: 'Sponsorships',
                      reason: 'Sponsorships are restricted to club owners.',
                    ),
            right:
                role.canManageBranding
                    ? ClubBrandingSection(branding: snapshot.branding)
                    : const ClubBlockedSection(
                      title: 'Branding',
                      reason: 'Branding changes are restricted to club owners.',
                    ),
          )
        else
          const _ResponsivePair(
            left: ClubBlockedSection(
              title: 'Sponsorships',
              reason: 'Sponsorships are restricted to club owners.',
            ),
            right: ClubBlockedSection(
              title: 'Branding',
              reason: 'Branding changes are restricted to club owners.',
            ),
          ),
        const SizedBox(height: spacingLG),
        _ResponsivePair(
          left: ClubTrophySection(trophies: snapshot.trophies),
          right: ClubRankingsSection(rankings: snapshot.rankings),
        ),
      ],
    );
  }
}

class ClubHeaderBanner extends StatelessWidget {
  const ClubHeaderBanner({super.key, required this.dashboard});

  final ClubDashboardDTO dashboard;

  @override
  Widget build(BuildContext context) {
    return GtexSurfaceCard(
      glowColor: AppColors.primary,
      padding: const EdgeInsets.all(spacingLG),
      child: Wrap(
        spacing: spacingLG,
        runSpacing: spacingLG,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: <Widget>[
          Container(
            width: 86,
            height: 86,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(cardRadius),
              color: AppColors.surfaceMuted,
              border: Border.all(color: AppColors.divider),
            ),
            child: Text(
              dashboard.name.isEmpty ? 'HQ' : dashboard.name[0].toUpperCase(),
              style: Theme.of(
                context,
              ).textTheme.headlineMedium?.copyWith(color: AppColors.gold),
            ),
          ),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 720),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('Club HQ', style: Theme.of(context).textTheme.bodySmall),
                const SizedBox(height: spacingXS),
                Text(
                  dashboard.name,
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
                const SizedBox(height: spacingSM),
                Text(
                  <String?>[
                    dashboard.league,
                    dashboard.division,
                    if (dashboard.foundedYear != null)
                      'Founded ${dashboard.foundedYear}',
                  ].whereType<String>().join(' | '),
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class ClubKpiGrid extends StatelessWidget {
  const ClubKpiGrid({
    super.key,
    required this.snapshot,
    required this.financeState,
  });

  final ClubHqSnapshot snapshot;
  final GtexSurfaceState<ClubFinanceDTO> financeState;

  @override
  Widget build(BuildContext context) {
    final String balanceLabel =
        financeState is GtexData<ClubFinanceDTO>
            ? clubMoney((financeState as GtexData<ClubFinanceDTO>).data.balance)
            : 'Blocked';
    final ClubRankingDTO? ranking =
        snapshot.rankings.isEmpty ? null : snapshot.rankings.first;

    return Wrap(
      spacing: spacingMD,
      runSpacing: spacingMD,
      children: <Widget>[
        _KpiCard(
          label: 'Squad Value',
          value: clubMoney(snapshot.dashboard.totalSquadValue),
          fallback: snapshot.dashboard.totalSquadValue == null,
        ),
        _KpiCard(
          key: const Key('club-kpi-balance'),
          label: 'Balance',
          value: balanceLabel,
          fallback: financeState is! GtexData<ClubFinanceDTO>,
          color:
              financeState is GtexBlocked<ClubFinanceDTO>
                  ? AppColors.danger
                  : AppColors.gold,
        ),
        _KpiCard(
          label: 'Rank',
          value: ranking == null ? 'Backend pending' : '#${ranking.rank}',
          fallback: ranking == null,
        ),
        _KpiCard(
          label: 'Active Competitions',
          value: '${snapshot.dashboard.activeCompetitions}',
        ),
      ],
    );
  }
}

class ClubPublicProfileSection extends StatelessWidget {
  const ClubPublicProfileSection({super.key, required this.dashboard});

  final ClubDashboardDTO dashboard;

  @override
  Widget build(BuildContext context) {
    return _SectionCard(
      title: 'Public Profile',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          _InfoRow(label: 'Club', value: dashboard.name),
          _InfoRow(
            label: 'League',
            value: dashboard.league ?? 'Backend pending',
          ),
          _InfoRow(
            label: 'Division',
            value: dashboard.division ?? 'Backend pending',
          ),
          _InfoRow(
            label: 'Badge',
            value: dashboard.badge == null ? 'Backend pending' : 'Synced',
          ),
          if (dashboard.alerts.isNotEmpty) ...<Widget>[
            const SizedBox(height: spacingMD),
            Text('Alerts', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: spacingSM),
            ...dashboard.alerts.map(_BulletText.new),
          ],
        ],
      ),
    );
  }
}

class ClubFinanceSection extends StatelessWidget {
  const ClubFinanceSection({super.key, required this.state});

  final GtexSurfaceState<ClubFinanceDTO> state;

  @override
  Widget build(BuildContext context) {
    return _SectionCard(
      title: 'Finance',
      child: AsyncStateWidget<ClubFinanceDTO>(
        state: state,
        onLoading: () => const _InlineState(message: 'Loading finance...'),
        onEmpty:
            (String? reason) =>
                _InlineState(message: reason ?? 'Finance data is empty.'),
        onBlocked:
            (String reason, String? ctaRoute) => _InlineState(
              key: const Key('club-finance-balance-blocked'),
              message: reason,
              color: AppColors.danger,
              icon: Icons.lock_rounded,
            ),
        onPending:
            (ClubFinanceDTO? stale) => const _InlineState(
              message: 'Finance update pending backend confirmation.',
            ),
        onSyncing:
            (ClubFinanceDTO current) => _FinanceDetails(finance: current),
        onReconnecting:
            (ClubFinanceDTO? lastKnown, int attempt) =>
                lastKnown == null
                    ? _InlineState(
                      message: 'Reconnecting finance feed: $attempt',
                    )
                    : _FinanceDetails(finance: lastKnown),
        onDegraded:
            (ClubFinanceDTO current, String warning) => Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                _InlineState(message: warning, color: AppColors.gold),
                const SizedBox(height: spacingMD),
                _FinanceDetails(finance: current),
              ],
            ),
        onConfirmed:
            (ClubFinanceDTO data, String? auditRef) =>
                _FinanceDetails(finance: data),
        onError:
            (String code, String message, VoidCallback retry) => _InlineState(
              message: '$code: $message',
              color: AppColors.danger,
            ),
        onData: (ClubFinanceDTO data) => _FinanceDetails(finance: data),
      ),
    );
  }
}

class ClubSquadReadinessSection extends StatelessWidget {
  const ClubSquadReadinessSection({super.key, required this.readiness});

  final SquadReadinessDTO readiness;

  @override
  Widget build(BuildContext context) {
    return _SectionCard(
      title: 'Squad Readiness',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          _BigNumber(
            label: 'Readiness score',
            value:
                readiness.readinessScore == null
                    ? 'Syncing'
                    : '${readiness.readinessScore!.round()}%',
          ),
          const SizedBox(height: spacingMD),
          _InfoRow(label: 'Eligible', value: '${readiness.eligibleCount}'),
          _InfoRow(
            label: 'Available next fixture',
            value: '${readiness.availableForNextFixture}',
          ),
          _InfoRow(label: 'Injured', value: '${readiness.injuredCount}'),
          _InfoRow(label: 'Suspended', value: '${readiness.suspendedCount}'),
        ],
      ),
    );
  }
}

class ClubAcademySection extends StatelessWidget {
  const ClubAcademySection({super.key, required this.academy});

  final ClubAcademyDTO academy;

  @override
  Widget build(BuildContext context) {
    return _SectionCard(
      title: 'Academy',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          _InfoRow(
            label: 'Facilities',
            value:
                academy.facilitiesRating == null
                    ? 'Backend pending'
                    : '${academy.facilitiesRating!.round()}/100',
          ),
          _InfoRow(label: 'Players', value: '${academy.players.length}'),
          const SizedBox(height: spacingMD),
          if (academy.players.isEmpty)
            const _InlineState(message: 'Academy players are empty.')
          else
            ...academy.players
                .take(4)
                .map(
                  (AcademyPlayerDTO player) => _ListTileLine(
                    title: player.name,
                    subtitle: <String?>[
                      player.position,
                      if (player.age != null) 'Age ${player.age}',
                      player.status,
                    ].whereType<String>().join(' | '),
                  ),
                ),
        ],
      ),
    );
  }
}

class ClubStaffSection extends StatelessWidget {
  const ClubStaffSection({super.key, required this.staff});

  final ClubStaffDTO staff;

  @override
  Widget build(BuildContext context) {
    return _SectionCard(
      title: 'Staff',
      child:
          staff.members.isEmpty
              ? const _InlineState(message: 'Staff roster is empty.')
              : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: staff.members
                    .map(
                      (StaffMemberDTO member) => _ListTileLine(
                        title: member.name,
                        subtitle: <String?>[
                          member.role,
                          member.status,
                          dateLabel(member.contractEnd),
                        ].whereType<String>().join(' | '),
                      ),
                    )
                    .toList(growable: false),
              ),
    );
  }
}

class ClubSponsorshipSection extends StatelessWidget {
  const ClubSponsorshipSection({super.key, required this.sponsorships});

  final List<SponsorshipDTO> sponsorships;

  @override
  Widget build(BuildContext context) {
    return _SectionCard(
      title: 'Sponsorships',
      child:
          sponsorships.isEmpty
              ? const _InlineState(message: 'No backend sponsorships yet.')
              : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: sponsorships
                    .map(
                      (SponsorshipDTO sponsorship) => _ListTileLine(
                        title: sponsorship.sponsor,
                        subtitle: <String?>[
                          clubMoney(sponsorship.value),
                          sponsorship.status,
                          dateLabel(sponsorship.endDate),
                        ].whereType<String>().join(' | '),
                      ),
                    )
                    .toList(growable: false),
              ),
    );
  }
}

class ClubBrandingSection extends StatelessWidget {
  const ClubBrandingSection({super.key, required this.branding});

  final ClubBrandingDTO branding;

  @override
  Widget build(BuildContext context) {
    return _SectionCard(
      title: 'Branding',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          _InfoRow(
            label: 'Badge',
            value: branding.badge == null ? 'Backend pending' : 'Synced',
          ),
          _InfoRow(label: 'Kit', value: branding.kit ?? 'Backend pending'),
          const SizedBox(height: spacingMD),
          Wrap(
            spacing: spacingSM,
            runSpacing: spacingSM,
            children:
                branding.colors.isEmpty
                    ? const <Widget>[Text('Colors backend pending')]
                    : branding.colors
                        .map(_BrandSwatch.new)
                        .toList(growable: false),
          ),
        ],
      ),
    );
  }
}

class ClubTrophySection extends StatelessWidget {
  const ClubTrophySection({super.key, required this.trophies});

  final List<TrophyDTO> trophies;

  @override
  Widget build(BuildContext context) {
    return _SectionCard(
      title: 'Trophies',
      child:
          trophies.isEmpty
              ? const _InlineState(message: 'Trophy cabinet is empty.')
              : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: trophies
                    .map(
                      (TrophyDTO trophy) => _ListTileLine(
                        title: trophy.name,
                        subtitle: <String?>[
                          trophy.competition,
                          trophy.season,
                          trophy.type,
                        ].whereType<String>().join(' | '),
                      ),
                    )
                    .toList(growable: false),
              ),
    );
  }
}

class ClubRankingsSection extends StatelessWidget {
  const ClubRankingsSection({super.key, required this.rankings});

  final List<ClubRankingDTO> rankings;

  @override
  Widget build(BuildContext context) {
    return _SectionCard(
      title: 'Rankings',
      child: AsyncStateWidget<List<ClubRankingDTO>>(
        state: clubRankingsSurfaceState(rankings),
        onLoading: () => const _InlineState(message: 'Loading rankings...'),
        onEmpty:
            (String? reason) =>
                _InlineState(message: reason ?? 'No rankings available.'),
        onBlocked:
            (String reason, String? ctaRoute) =>
                _InlineState(message: reason, color: AppColors.danger),
        onPending:
            (List<ClubRankingDTO>? stale) =>
                const _InlineState(message: 'Rankings update pending.'),
        onSyncing: _RankingList.new,
        onReconnecting:
            (List<ClubRankingDTO>? lastKnown, int attempt) =>
                lastKnown == null
                    ? _InlineState(message: 'Reconnecting rankings: $attempt')
                    : _RankingList(lastKnown),
        onDegraded:
            (List<ClubRankingDTO> current, String warning) =>
                _RankingList(current),
        onConfirmed:
            (List<ClubRankingDTO> data, String? auditRef) => _RankingList(data),
        onError:
            (String code, String message, VoidCallback retry) => _InlineState(
              message: '$code: $message',
              color: AppColors.danger,
            ),
        onData: _RankingList.new,
      ),
    );
  }
}

class ClubBlockedSection extends StatelessWidget {
  const ClubBlockedSection({
    super.key,
    required this.title,
    required this.reason,
  });

  final String title;
  final String reason;

  @override
  Widget build(BuildContext context) {
    return _SectionCard(
      title: title,
      child: _InlineState(
        message: reason,
        color: AppColors.danger,
        icon: Icons.lock_rounded,
      ),
    );
  }
}

class _ResponsivePair extends StatelessWidget {
  const _ResponsivePair({required this.left, required this.right});

  final Widget left;
  final Widget right;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        if (constraints.maxWidth >= AppBreakpoints.medium) {
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(child: left),
              const SizedBox(width: spacingMD),
              Expanded(child: right),
            ],
          );
        }
        return Column(
          children: <Widget>[left, const SizedBox(height: spacingMD), right],
        );
      },
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return GtexSurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: spacingMD),
          child,
        ],
      ),
    );
  }
}

class _KpiCard extends StatelessWidget {
  const _KpiCard({
    super.key,
    required this.label,
    required this.value,
    this.fallback = false,
    this.color = AppColors.primary,
  });

  final String label;
  final String value;
  final bool fallback;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 240,
      child: GtexSurfaceCard(
        glowColor: fallback ? AppColors.gold : color,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(label, style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: spacingSM),
            Text(
              value,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                color: fallback ? AppColors.textSecondary : color,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _FinanceDetails extends StatelessWidget {
  const _FinanceDetails({required this.finance});

  final ClubFinanceDTO finance;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        _BigNumber(
          key: const Key('club-finance-balance-value'),
          label: 'Backend balance',
          value: clubMoney(finance.balance),
        ),
        const SizedBox(height: spacingMD),
        _InfoRow(label: 'Revenue', value: clubMoney(finance.revenue)),
        _InfoRow(label: 'Expenses', value: clubMoney(finance.expenses)),
        _InfoRow(
          label: 'Transfer budget',
          value: clubMoney(finance.transferBudget),
        ),
        _InfoRow(label: 'Wages', value: clubMoney(finance.wages)),
        _InfoRow(
          label: 'Last synced',
          value: dateLabel(finance.lastSyncedAt) ?? 'Backend pending',
        ),
        if (finance.alerts.isNotEmpty) ...<Widget>[
          const SizedBox(height: spacingMD),
          ...finance.alerts.map(_BulletText.new),
        ],
      ],
    );
  }
}

class _RankingList extends StatelessWidget {
  const _RankingList(this.rankings);

  final List<ClubRankingDTO> rankings;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: rankings
          .map(
            (ClubRankingDTO ranking) => _ListTileLine(
              title: '#${ranking.rank} ${ranking.division ?? 'Division'}',
              subtitle: <String>[
                if (ranking.points != null) '${ranking.points!.round()} pts',
                if (ranking.previousRank != null)
                  'Previous #${ranking.previousRank}',
              ].join(' | '),
            ),
          )
          .toList(growable: false),
    );
  }
}

class _BigNumber extends StatelessWidget {
  const _BigNumber({super.key, required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(label, style: Theme.of(context).textTheme.bodySmall),
        const SizedBox(height: spacingXS),
        Text(
          value,
          style: Theme.of(
            context,
          ).textTheme.headlineSmall?.copyWith(color: AppColors.gold),
        ),
      ],
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: spacingSM),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Text(
              label,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
            ),
          ),
          const SizedBox(width: spacingMD),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }
}

class _ListTileLine extends StatelessWidget {
  const _ListTileLine({required this.title, required this.subtitle});

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: spacingSM),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: AppColors.surfaceMuted.withValues(alpha: 0.58),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.divider),
        ),
        child: Padding(
          padding: const EdgeInsets.all(spacingMD),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(title, style: Theme.of(context).textTheme.titleMedium),
              if (subtitle.isNotEmpty) ...<Widget>[
                const SizedBox(height: spacingXS),
                Text(
                  subtitle,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _InlineState extends StatelessWidget {
  const _InlineState({
    super.key,
    required this.message,
    this.color = AppColors.gold,
    this.icon = Icons.info_rounded,
  });

  final String message;
  final Color color;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.09),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.28)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(spacingMD),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Icon(icon, color: color, size: 20),
            const SizedBox(width: spacingSM),
            Expanded(child: Text(message)),
          ],
        ),
      ),
    );
  }
}

class _BulletText extends StatelessWidget {
  const _BulletText(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: spacingXS),
      child: Text('- $text'),
    );
  }
}

class _BrandSwatch extends StatelessWidget {
  const _BrandSwatch(this.label);

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: spacingSM,
        vertical: spacingXS,
      ),
      decoration: BoxDecoration(
        color: AppColors.surfaceMuted,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: AppColors.divider),
      ),
      child: Text(label),
    );
  }
}

String clubMoney(double? value) {
  if (value == null) {
    return 'Backend pending';
  }
  final String fixed = value.toStringAsFixed(
    value.truncateToDouble() == value ? 0 : 1,
  );
  return '\$$fixed';
}

String? dateLabel(DateTime? value) {
  if (value == null) {
    return null;
  }
  final String month = value.month.toString().padLeft(2, '0');
  final String day = value.day.toString().padLeft(2, '0');
  return '${value.year}-$month-$day';
}
