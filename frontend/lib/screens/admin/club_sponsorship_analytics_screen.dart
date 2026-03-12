import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/sponsorship_models.dart';
import 'package:gte_frontend/screens/clubs/club_ops_screen_host.dart';
import 'package:gte_frontend/widgets/admin/sponsorship_revenue_summary_card.dart';
import 'package:gte_frontend/widgets/clubs/sponsor_asset_slot_card.dart';
import 'package:gte_frontend/widgets/clubs/sponsorship_contract_card.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

class ClubSponsorshipAnalyticsScreen extends StatelessWidget {
  const ClubSponsorshipAnalyticsScreen({
    super.key,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.mode = GteBackendMode.liveThenFixture,
    this.api,
    this.controller,
  });

  final String baseUrl;
  final GteBackendMode mode;
  final ClubOpsApi? api;
  final ClubOpsController? controller;

  @override
  Widget build(BuildContext context) {
    return ClubOpsScreenHost(
      title: 'Sponsorship analytics',
      subtitle: 'Contract concentration, renewals, and moderation queue.',
      baseUrl: baseUrl,
      mode: mode,
      api: api,
      controller: controller,
      adminData: true,
      builder: (BuildContext context, ClubOpsController controller) {
        if (controller.isLoadingAdminData && !controller.hasAdminData) {
          return const Padding(
            padding: EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Loading sponsorship analytics',
              message: 'Preparing renewal and moderation metrics.',
              icon: Icons.query_stats_outlined,
            ),
          );
        }
        final analytics = controller.sponsorshipAnalytics!;
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          children: <Widget>[
            SponsorshipRevenueSummaryCard(analytics: analytics),
            const SizedBox(height: 16),
            for (final SponsorshipContract contract in analytics.topContracts) ...<Widget>[
              SponsorshipContractCard(contract: contract),
              if (contract != analytics.topContracts.last) const SizedBox(height: 12),
            ],
            const SizedBox(height: 16),
            for (final SponsorAssetSlot slot in analytics.reviewQueue) ...<Widget>[
              SponsorAssetSlotCard(slot: slot),
              if (slot != analytics.reviewQueue.last) const SizedBox(height: 12),
            ],
          ],
        );
      },
    );
  }
}
