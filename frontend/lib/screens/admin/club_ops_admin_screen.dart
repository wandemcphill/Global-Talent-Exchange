import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/screens/admin/academy_analytics_screen.dart';
import 'package:gte_frontend/screens/admin/club_finance_analytics_screen.dart';
import 'package:gte_frontend/screens/admin/club_sponsorship_analytics_screen.dart';
import 'package:gte_frontend/screens/admin/scouting_analytics_screen.dart';
import 'package:gte_frontend/screens/clubs/club_ops_screen_host.dart';
import 'package:gte_frontend/widgets/admin/academy_conversion_card.dart';
import 'package:gte_frontend/widgets/admin/club_ops_summary_card.dart';
import 'package:gte_frontend/widgets/admin/sponsorship_revenue_summary_card.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

class ClubOpsAdminScreen extends StatelessWidget {
  const ClubOpsAdminScreen({
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
      title: 'Club operations admin',
      subtitle: 'Finance, sponsorship, academy, and scouting oversight.',
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
              title: 'Loading club operations admin',
              message: 'Preparing finance, sponsorship, academy, and scouting oversight metrics.',
              icon: Icons.admin_panel_settings_outlined,
            ),
          );
        }
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          children: <Widget>[
            ClubOpsSummaryCard(summary: controller.adminSummary!),
            const SizedBox(height: 16),
            SponsorshipRevenueSummaryCard(analytics: controller.sponsorshipAnalytics!),
            const SizedBox(height: 16),
            AcademyConversionCard(analytics: controller.academyAnalytics!),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: <Widget>[
                FilledButton.tonal(
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (BuildContext context) => ClubFinanceAnalyticsScreen(
                        controller: controller,
                        baseUrl: baseUrl,
                        mode: mode,
                      ),
                    ),
                  ),
                  child: const Text('Finance analytics'),
                ),
                FilledButton.tonal(
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (BuildContext context) => ClubSponsorshipAnalyticsScreen(
                        controller: controller,
                        baseUrl: baseUrl,
                        mode: mode,
                      ),
                    ),
                  ),
                  child: const Text('Sponsorship analytics'),
                ),
                FilledButton.tonal(
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (BuildContext context) => AcademyAnalyticsScreen(
                        controller: controller,
                        baseUrl: baseUrl,
                        mode: mode,
                      ),
                    ),
                  ),
                  child: const Text('Academy analytics'),
                ),
                FilledButton.tonal(
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (BuildContext context) => ScoutingAnalyticsScreen(
                        controller: controller,
                        baseUrl: baseUrl,
                        mode: mode,
                      ),
                    ),
                  ),
                  child: const Text('Scouting analytics'),
                ),
              ],
            ),
          ],
        );
      },
    );
  }
}
