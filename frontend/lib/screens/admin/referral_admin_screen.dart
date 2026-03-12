import 'package:flutter/material.dart';

import '../../data/referral_api.dart';
import '../../models/referral_models.dart';
import '../../widgets/admin/referral_flag_card.dart';
import '../../widgets/gte_state_panel.dart';

class ReferralAdminScreen extends StatefulWidget {
  const ReferralAdminScreen({
    super.key,
    required this.api,
  });

  final ReferralApi api;

  @override
  State<ReferralAdminScreen> createState() => _ReferralAdminScreenState();
}

class _ReferralAdminScreenState extends State<ReferralAdminScreen> {
  late Future<ReferralAnalyticsSnapshot> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.api.fetchReferralAnalytics();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Referral admin')),
      body: FutureBuilder<ReferralAnalyticsSnapshot>(
        future: _future,
        builder: (BuildContext context, AsyncSnapshot<ReferralAnalyticsSnapshot> snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Padding(
              padding: EdgeInsets.all(20),
              child: GteStatePanel(
                title: 'Loading referral admin',
                message: 'Preparing flagged codes, growth reviews, and milestone reward checks.',
                icon: Icons.admin_panel_settings_outlined,
              ),
            );
          }
          if (snapshot.hasError || !snapshot.hasData) {
            return Padding(
              padding: const EdgeInsets.all(20),
              child: GteStatePanel(
                title: 'Referral admin unavailable',
                message: '${snapshot.error ?? 'Unknown error'}',
                icon: Icons.error_outline,
              ),
            );
          }

          final ReferralAnalyticsSnapshot analytics = snapshot.data!;
          return ListView.separated(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
            itemBuilder: (BuildContext context, int index) {
              if (index == 0) {
                return Column(
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
                );
              }
              return ReferralFlagCard(flag: analytics.flags[index - 1]);
            },
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemCount: analytics.flags.length + 1,
          );
        },
      ),
    );
  }
}
