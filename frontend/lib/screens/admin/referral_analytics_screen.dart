import 'package:flutter/material.dart';

import '../../data/referral_api.dart';
import '../../models/referral_models.dart';
import '../../widgets/admin/referral_flag_card.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';

class ReferralAnalyticsScreen extends StatefulWidget {
  const ReferralAnalyticsScreen({
    super.key,
    required this.api,
  });

  final ReferralApi api;

  @override
  State<ReferralAnalyticsScreen> createState() => _ReferralAnalyticsScreenState();
}

class _ReferralAnalyticsScreenState extends State<ReferralAnalyticsScreen> {
  late Future<ReferralAnalyticsSnapshot> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.api.fetchReferralAnalytics();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Referral analytics')),
      body: FutureBuilder<ReferralAnalyticsSnapshot>(
        future: _future,
        builder: (BuildContext context, AsyncSnapshot<ReferralAnalyticsSnapshot> snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Padding(
              padding: EdgeInsets.all(20),
              child: GteStatePanel(
                title: 'Loading referral analytics',
                message: 'Calculating community growth, qualified participation, and review workload.',
                icon: Icons.insights_outlined,
              ),
            );
          }
          if (snapshot.hasError || !snapshot.hasData) {
            return Padding(
              padding: const EdgeInsets.all(20),
              child: GteStatePanel(
                title: 'Referral analytics unavailable',
                message: '${snapshot.error ?? 'Unknown error'}',
                icon: Icons.error_outline,
              ),
            );
          }

          final ReferralAnalyticsSnapshot analytics = snapshot.data!;
          return SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                GteSurfacePanel(
                  emphasized: true,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        analytics.growthHeadline,
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        analytics.growthDetail,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: <Widget>[
                    _MetricCard(label: 'Active share codes', value: analytics.activeShareCodes),
                    _MetricCard(label: 'Qualified participation', value: analytics.qualifiedParticipationLabel),
                    _MetricCard(label: 'Reward review load', value: analytics.communityRewardReviewLabel),
                    _MetricCard(label: 'Top channel', value: analytics.topChannelLabel),
                  ],
                ),
                const SizedBox(height: 16),
                for (final ReferralFlagEntry flag in analytics.flags) ...<Widget>[
                  ReferralFlagCard(flag: flag),
                  if (flag != analytics.flags.last) const SizedBox(height: 12),
                ],
              ],
            ),
          );
        },
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 220,
      child: GteSurfacePanel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              value,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 6),
            Text(
              label,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }
}
