import 'package:flutter/material.dart';

import '../../data/referral_api.dart';
import '../../models/referral_models.dart';
import '../../widgets/admin/referral_flag_card.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import '../../widgets/gtex_branding.dart';

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
      appBar: AppBar(title: const Text('Referral integrity desk')),
      body: FutureBuilder<ReferralAnalyticsSnapshot>(
        future: _future,
        builder: (BuildContext context, AsyncSnapshot<ReferralAnalyticsSnapshot> snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Padding(
              padding: EdgeInsets.all(20),
              child: GteStatePanel(
                eyebrow: 'REFERRAL INTEGRITY',
                title: 'Loading referral integrity desk',
                message: 'Preparing flagged codes, growth reviews, and milestone reward checks.',
                icon: Icons.admin_panel_settings_outlined,
                accentColor: Color(0xFF4DE2C5),
              ),
            );
          }
          if (snapshot.hasError || !snapshot.hasData) {
            return Padding(
              padding: const EdgeInsets.all(20),
              child: GteStatePanel(
                eyebrow: 'REFERRAL INTEGRITY',
                title: 'Referral integrity desk unavailable',
                message: '${snapshot.error ?? 'Unknown error'}',
                icon: Icons.error_outline,
                accentColor: Color(0xFF4DE2C5),
                actionLabel: 'Retry',
                onAction: () => setState(() { _future = widget.api.fetchReferralAnalytics(); }),
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
                    GtexHeroBanner(
                      eyebrow: 'REFERRAL CONTROL TOWER',
                      title: 'Review code integrity, reward leakage, and growth quality before referral momentum turns noisy.',
                      description: 'This desk keeps fraud review, flagged codes, and milestone pressure in one premium admin lane so referral operations feel deliberate and trustworthy.',
                      accent: const Color(0xFF4DE2C5),
                      chips: <Widget>[
                        Chip(label: Text('Flags ${analytics.flags.length}')),
                      ],
                    ),
                    const SizedBox(height: 16),
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
                    if (analytics.flags.isEmpty) ...<Widget>[
                      const SizedBox(height: 16),
                      const GteStatePanel(
                        eyebrow: 'REFERRAL HYGIENE',
                        title: 'No referral flags need review right now',
                        message: 'Growth checks are calm. New flagged codes, suspicious bursts, or milestone anomalies will appear here for moderation review.',
                        icon: Icons.verified_user_outlined,
                        accentColor: Color(0xFF4DE2C5),
                      ),
                    ],
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
