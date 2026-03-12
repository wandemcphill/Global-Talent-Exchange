import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/screens/admin/club_analytics_screen.dart';
import 'package:gte_frontend/screens/admin/club_branding_moderation_screen.dart';
import 'package:gte_frontend/widgets/admin/club_revenue_summary_card.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ClubAdminScreen extends StatefulWidget {
  const ClubAdminScreen({
    super.key,
    this.controller,
    this.clubId = 'royal-lagos-fc',
    this.baseUrl = 'http://127.0.0.1:8000',
    this.backendMode = GteBackendMode.liveThenFixture,
  });

  final ClubController? controller;
  final String clubId;
  final String baseUrl;
  final GteBackendMode backendMode;

  @override
  State<ClubAdminScreen> createState() => _ClubAdminScreenState();
}

class _ClubAdminScreenState extends State<ClubAdminScreen> {
  late final ClubController _controller;
  late final bool _ownsController;

  @override
  void initState() {
    super.initState();
    _ownsController = widget.controller == null;
    _controller = widget.controller ??
        ClubController.standard(
          clubId: widget.clubId,
          baseUrl: widget.baseUrl,
          backendMode: widget.backendMode,
        );
    _controller.ensureLoaded();
    _controller.loadAdmin();
  }

  @override
  void dispose() {
    if (_ownsController) {
      _controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (BuildContext context, _) {
        final analytics = _controller.adminAnalytics;
        return Container(
          decoration: gteBackdropDecoration(),
          child: Scaffold(
            backgroundColor: Colors.transparent,
            appBar: AppBar(
              title: const Text('Club admin'),
            ),
            body: analytics == null
                ? Padding(
                    padding: const EdgeInsets.all(20),
                    child: GteStatePanel(
                      title: 'Loading club admin',
                      message: _controller.errorMessage ??
                          'Preparing analytics, moderation queue, and cosmetic catalog summaries.',
                      icon: Icons.admin_panel_settings_outlined,
                    ),
                  )
                : ListView(
                    padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                    children: <Widget>[
                      GteSurfacePanel(
                        emphasized: true,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(
                              analytics.moderationHeadline,
                              style: Theme.of(context).textTheme.headlineSmall,
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Admin copy stays focused on club identity, community prestige, legacy milestones, and cosmetic catalog transparency.',
                              style: Theme.of(context).textTheme.bodyMedium,
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 18),
                      Wrap(
                        spacing: 14,
                        runSpacing: 14,
                        children: analytics.revenueSummaries.map((summary) {
                          return ClubRevenueSummaryCard(summary: summary);
                        }).toList(growable: false),
                      ),
                      const SizedBox(height: 18),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: <Widget>[
                          FilledButton.tonalIcon(
                            onPressed: () => Navigator.of(context).push<void>(
                              MaterialPageRoute<void>(
                                builder: (BuildContext context) =>
                                    ClubAnalyticsScreen(controller: _controller),
                              ),
                            ),
                            icon: const Icon(Icons.insights_outlined),
                            label: const Text('Open analytics'),
                          ),
                          FilledButton.tonalIcon(
                            onPressed: () => Navigator.of(context).push<void>(
                              MaterialPageRoute<void>(
                                builder: (BuildContext context) =>
                                    ClubBrandingModerationScreen(
                                  controller: _controller,
                                ),
                              ),
                            ),
                            icon: const Icon(Icons.fact_check_outlined),
                            label: const Text('Branding review'),
                          ),
                        ],
                      ),
                    ],
                  ),
          ),
        );
      },
    );
  }
}
