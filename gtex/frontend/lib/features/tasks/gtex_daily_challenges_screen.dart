import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/app_feedback.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../ui_gtex/ui_gtex.dart';
import '../../widgets/gte_state_panel.dart';
import 'live_tasks_provider.dart';

/// The daily-challenge desk: what is claimable today, what the account has
/// already claimed, and where the login streak stands.
///
/// `/tasks` was published in the route inventory as a live surface and
/// rendered as a quick action on Home, but `lib/features/tasks/` held only a
/// provider - there was no screen for the route to open, so the button led to
/// the router's "Route unavailable" page. The data layer was already complete
/// against `/api/daily-challenges`; this is the surface it was missing.
class GtexDailyChallengesScreen extends ConsumerStatefulWidget {
  const GtexDailyChallengesScreen({super.key, this.onSignIn});

  /// Opens the sign-in flow. Challenges are public, but claiming and the
  /// streak are not, so a visitor needs a way in.
  final VoidCallback? onSignIn;

  @override
  ConsumerState<GtexDailyChallengesScreen> createState() =>
      _GtexDailyChallengesScreenState();
}

class _GtexDailyChallengesScreenState
    extends ConsumerState<GtexDailyChallengesScreen> {
  /// The challenge currently being claimed, if any. Only one claim is in
  /// flight at a time, so a double tap cannot settle twice.
  String? _claimingKey;

  Future<void> _claim(DailyChallengeSummary challenge) async {
    if (_claimingKey != null) {
      return;
    }
    setState(() => _claimingKey = challenge.challengeKey);
    try {
      final DailyChallengeClaimFeedback feedback = await claimDailyChallenge(
        ref,
        challengeKey: challenge.challengeKey,
      );
      if (!mounted) {
        return;
      }
      AppFeedback.showSuccess(context, feedback.statusMessage);
    } catch (error) {
      if (!mounted) {
        return;
      }
      // The backend refuses a claim with its own reason - already claimed
      // today, challenge closed, feature disabled. That reason is what the
      // reader needs, so it is surfaced rather than replaced.
      AppFeedback.showError(context, _claimFailureMessage(error));
    } finally {
      if (mounted) {
        setState(() => _claimingKey = null);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final AsyncValue<LiveTasksData> tasksValue = ref.watch(liveTasksProvider);

    return AppPageLayout(
      title: 'Daily challenges',
      subtitle:
          'Claim today\'s challenges and keep the login streak alive. Rewards '
          'settle through the backend.',
      children: <Widget>[_buildBody(tasksValue)],
    );
  }

  /// `AsyncValue.when` hands the loading branch precedence whenever a reload
  /// is in flight, so a failing refresh would spin forever instead of saying
  /// what went wrong. The states are read directly: data wins while it is
  /// held, an error with nothing behind it is reported, and only a genuinely
  /// empty first load shows the spinner.
  Widget _buildBody(AsyncValue<LiveTasksData> tasksValue) {
    final LiveTasksData? data = tasksValue.asData?.value;
    if (data != null) {
      return _buildLoaded(data);
    }
    if (tasksValue.hasError) {
      return GteStatePanel(
        eyebrow: 'CHALLENGES UNAVAILABLE',
        title: 'Daily challenges could not be loaded',
        message: '${tasksValue.error}',
        icon: Icons.warning_amber_rounded,
        accentColor: GtexColors.gold,
        actionLabel: 'Retry',
        onAction: () => ref.invalidate(liveTasksProvider),
      );
    }
    return const GteStatePanel(
      eyebrow: 'LIVE SYNC',
      title: 'Loading daily challenges',
      message: 'Reading the live challenge pool and claim state.',
      isLoading: true,
    );
  }

  Widget _buildLoaded(LiveTasksData data) {
    if (!data.featureEnabled) {
      // Launch Control owns the `daily-challenges` flag. When it is off the
      // pool is genuinely closed, which is a different thing from empty.
      return const GtexBlockedState(
        title: 'Daily challenges are switched off',
        reason:
            'The daily-challenge programme is disabled for this environment.',
        resolution:
            'Nothing is claimable while it is off. It reopens when the '
            'programme is switched back on.',
        icon: Icons.pause_circle_outline,
      );
    }

    if (data.challenges.isEmpty) {
      return const GtexEmptyState(
        title: 'No challenges in today\'s pool',
        message:
            'The backend published no daily challenges for today. New ones '
            'appear here as soon as they are live.',
        icon: Icons.event_available_outlined,
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        _StreakPanel(data: data, onSignIn: widget.onSignIn),
        const SizedBox(height: GtexSpacing.md),
        _ChallengePool(
          data: data,
          claimingKey: _claimingKey,
          onClaim: _claim,
          onSignIn: widget.onSignIn,
        ),
        if (data.claimsToday.isNotEmpty) ...<Widget>[
          const SizedBox(height: GtexSpacing.md),
          _ClaimsToday(claims: data.claimsToday),
        ],
      ],
    );
  }
}

String _claimFailureMessage(Object error) {
  final String text = error.toString().trim();
  return text.isEmpty ? 'The claim could not be settled.' : text;
}

/// Login streak and the bonus riding on it.
///
/// Every number here comes from `/api/daily-challenges/me`, which is only
/// fetched for a signed-in session. A visitor is shown the way in rather than
/// a streak of zero, which would be a figure about them that nothing measured.
class _StreakPanel extends StatelessWidget {
  const _StreakPanel({required this.data, this.onSignIn});

  final LiveTasksData data;
  final VoidCallback? onSignIn;

  @override
  Widget build(BuildContext context) {
    if (!data.authenticated) {
      return GtexPanel(
        title: 'Login streak',
        subtitle: 'Streaks and claims belong to an account.',
        accent: GtexColors.gold,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Sign in to claim today\'s challenges and start a login streak. '
              'The pool below is what is live right now.',
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: GtexColors.textSecondary),
            ),
            const SizedBox(height: GtexSpacing.md),
            if (onSignIn != null)
              Align(
                alignment: Alignment.centerLeft,
                child: GtexActionButton(
                  key: const Key('daily-challenges-sign-in'),
                  label: 'Sign in',
                  icon: Icons.login,
                  accent: GtexColors.gold,
                  onPressed: onSignIn,
                ),
              ),
          ],
        ),
      );
    }

    return GtexPanel(
      title: 'Login streak',
      subtitle: 'Settled by the backend as claims land.',
      accent: GtexColors.gold,
      child: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          // Measured against the panel's own box: this surface renders at
          // every width the product has, and the tiles read badly in a
          // single narrow column only when there is genuinely no room.
          final bool wide = constraints.maxWidth >= 560;
          final List<Widget> tiles = <Widget>[
            GtexMetricTile(
              label: 'CURRENT STREAK',
              value: '${data.currentStreak}',
              helper: 'Consecutive claim days',
              icon: Icons.local_fire_department_outlined,
              accent: GtexColors.gold,
            ),
            GtexMetricTile(
              label: 'LONGEST STREAK',
              value: '${data.longestStreak}',
              helper: 'Best run on this account',
              icon: Icons.emoji_events_outlined,
              accent: GtexColors.cyan,
            ),
            GtexMetricTile(
              label: 'NEXT BONUS',
              value: _formatAmount(data.nextBonusAmount),
              helper: 'Rides on the next claim',
              icon: Icons.auto_awesome_outlined,
              accent: GtexColors.pitch,
            ),
          ];
          if (!wide) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                for (int i = 0; i < tiles.length; i += 1) ...<Widget>[
                  if (i > 0) const SizedBox(height: GtexSpacing.sm),
                  tiles[i],
                ],
              ],
            );
          }
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              for (int i = 0; i < tiles.length; i += 1) ...<Widget>[
                if (i > 0) const SizedBox(width: GtexSpacing.sm),
                Expanded(child: tiles[i]),
              ],
            ],
          );
        },
      ),
    );
  }
}

/// Today's claimable pool.
class _ChallengePool extends StatelessWidget {
  const _ChallengePool({
    required this.data,
    required this.claimingKey,
    required this.onClaim,
    this.onSignIn,
  });

  final LiveTasksData data;
  final String? claimingKey;
  final ValueChanged<DailyChallengeSummary> onClaim;
  final VoidCallback? onSignIn;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      title: 'Today\'s challenges',
      subtitle: '${data.challenges.length} live in the pool.',
      accent: GtexColors.pitch,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          for (int i = 0; i < data.challenges.length; i += 1) ...<Widget>[
            if (i > 0) const SizedBox(height: GtexSpacing.sm),
            _ChallengeCard(
              challenge: data.challenges[i],
              authenticated: data.authenticated,
              isClaiming: claimingKey == data.challenges[i].challengeKey,
              claimBlocked:
                  claimingKey != null &&
                  claimingKey != data.challenges[i].challengeKey,
              onClaim: () => onClaim(data.challenges[i]),
              onSignIn: onSignIn,
            ),
          ],
        ],
      ),
    );
  }
}

class _ChallengeCard extends StatelessWidget {
  const _ChallengeCard({
    required this.challenge,
    required this.authenticated,
    required this.isClaiming,
    required this.claimBlocked,
    required this.onClaim,
    this.onSignIn,
  });

  final DailyChallengeSummary challenge;
  final bool authenticated;
  final bool isClaiming;

  /// Another claim is settling. The action waits rather than racing it.
  final bool claimBlocked;
  final VoidCallback onClaim;
  final VoidCallback? onSignIn;

  @override
  Widget build(BuildContext context) {
    final bool claimable =
        authenticated && !challenge.claimedToday && challenge.availableToday;

    return GtexPageSurface(
      padding: const EdgeInsets.all(GtexSpacing.md),
      accent: challenge.claimedToday ? GtexColors.cyan : GtexColors.pitch,
      child: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          // The action drops under the copy where a row would squeeze both.
          final bool stack = constraints.maxWidth < 520;
          final Widget copy = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Text(
                challenge.title,
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  color: GtexColors.text,
                  fontWeight: FontWeight.w900,
                ),
              ),
              if (challenge.description.trim().isNotEmpty) ...<Widget>[
                const SizedBox(height: GtexSpacing.xxs),
                Text(
                  challenge.description,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: GtexColors.textSecondary,
                    height: 1.35,
                  ),
                ),
              ],
              const SizedBox(height: GtexSpacing.xs),
              Wrap(
                spacing: GtexSpacing.xs,
                runSpacing: GtexSpacing.xxs,
                children: <Widget>[
                  if (challenge.rewardSummary.trim().isNotEmpty)
                    GtexStatusChip(
                      label: 'Reward ${challenge.rewardSummary}',
                      icon: Icons.redeem_outlined,
                      color: GtexColors.gold,
                    ),
                  // Shown only when the backend gave a limit; a zero here
                  // means the field was absent, not that nothing may be
                  // claimed.
                  if (challenge.claimLimitPerDay > 0)
                    GtexStatusChip(
                      label: '${challenge.claimLimitPerDay} per day',
                      icon: Icons.repeat_rounded,
                      color: GtexColors.textSecondary,
                    ),
                  if (challenge.claimedToday)
                    const GtexStatusChip(
                      label: 'Claimed today',
                      icon: Icons.check_circle_outline,
                      color: GtexColors.cyan,
                    )
                  else if (authenticated && !challenge.availableToday)
                    const GtexStatusChip(
                      label: 'Not available today',
                      icon: Icons.schedule_outlined,
                      color: GtexColors.textMuted,
                    ),
                ],
              ),
            ],
          );

          final Widget action = _buildAction(claimable: claimable);
          if (stack) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                copy,
                const SizedBox(height: GtexSpacing.sm),
                Align(alignment: Alignment.centerLeft, child: action),
              ],
            );
          }
          return Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: <Widget>[
              Expanded(child: copy),
              const SizedBox(width: GtexSpacing.md),
              action,
            ],
          );
        },
      ),
    );
  }

  Widget _buildAction({required bool claimable}) {
    if (!authenticated) {
      return GtexActionButton(
        label: 'Sign in to claim',
        icon: Icons.login,
        secondary: true,
        accent: GtexColors.gold,
        onPressed: onSignIn,
      );
    }
    if (isClaiming) {
      return const SizedBox(
        width: 22,
        height: 22,
        child: CircularProgressIndicator(strokeWidth: 2.4),
      );
    }
    return GtexActionButton(
      key: Key('daily-challenge-claim-${challenge.challengeKey}'),
      label: challenge.claimedToday ? 'Claimed' : 'Claim',
      icon:
          challenge.claimedToday
              ? Icons.check_rounded
              : Icons.card_giftcard_outlined,
      secondary: !claimable,
      accent: claimable ? GtexColors.pitch : GtexColors.textMuted,
      // A disabled button is the honest state for a challenge that is
      // already claimed, closed for today, or waiting on another claim.
      onPressed: claimable && !claimBlocked ? onClaim : null,
    );
  }
}

/// What this account has already settled today.
class _ClaimsToday extends StatelessWidget {
  const _ClaimsToday({required this.claims});

  final List<DailyChallengeClaimSummary> claims;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      title: 'Claimed today',
      subtitle: '${claims.length} settled by the backend.',
      accent: GtexColors.cyan,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          for (int i = 0; i < claims.length; i += 1) ...<Widget>[
            if (i > 0) const SizedBox(height: GtexSpacing.sm),
            _ClaimRow(claim: claims[i]),
          ],
        ],
      ),
    );
  }
}

class _ClaimRow extends StatelessWidget {
  const _ClaimRow({required this.claim});

  final DailyChallengeClaimSummary claim;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const Icon(
          Icons.check_circle_outline,
          size: 18,
          color: GtexColors.cyan,
        ),
        const SizedBox(width: GtexSpacing.xs),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Text(
                claim.challengeTitle,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: GtexColors.text,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: GtexSpacing.xxs),
              Text(
                claim.rewardDetail,
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: GtexColors.textSecondary),
              ),
            ],
          ),
        ),
        if (claim.bonusAwarded) ...<Widget>[
          const SizedBox(width: GtexSpacing.xs),
          GtexStatusChip(
            label: 'Bonus ${claim.bonusAwardedLabel}',
            icon: Icons.auto_awesome_outlined,
            color: GtexColors.gold,
          ),
        ],
      ],
    );
  }
}

String _formatAmount(double value) {
  if (value == value.roundToDouble()) {
    return value.toStringAsFixed(0);
  }
  return value.toStringAsFixed(2);
}
