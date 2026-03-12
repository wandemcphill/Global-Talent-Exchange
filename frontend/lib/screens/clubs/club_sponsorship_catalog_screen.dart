import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/sponsorship_models.dart';
import 'package:gte_frontend/screens/clubs/club_ops_screen_host.dart';
import 'package:gte_frontend/widgets/clubs/sponsorship_package_card.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

class ClubSponsorshipCatalogScreen extends StatelessWidget {
  const ClubSponsorshipCatalogScreen({
    super.key,
    this.clubId = 'royal-lagos-fc',
    this.clubName,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.mode = GteBackendMode.liveThenFixture,
    this.api,
    this.controller,
  });

  final String clubId;
  final String? clubName;
  final String baseUrl;
  final GteBackendMode mode;
  final ClubOpsApi? api;
  final ClubOpsController? controller;

  @override
  Widget build(BuildContext context) {
    return ClubOpsScreenHost(
      title: 'Sponsorship catalog',
      subtitle: 'Transparent package value, duration, and asset inventory.',
      clubId: clubId,
      clubName: clubName,
      baseUrl: baseUrl,
      mode: mode,
      api: api,
      controller: controller,
      builder: (BuildContext context, ClubOpsController controller) {
        if (controller.isLoadingClubData && !controller.hasClubData) {
          return const Padding(
            padding: EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Loading sponsorship catalog',
              message: 'Preparing package tiers and deliverables.',
              icon: Icons.storefront_outlined,
            ),
          );
        }
        final List<SponsorshipPackage> packages =
            controller.sponsorships?.packages ?? const <SponsorshipPackage>[];
        return ListView.separated(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          itemBuilder: (BuildContext context, int index) =>
              SponsorshipPackageCard(package: packages[index]),
          separatorBuilder: (_, __) => const SizedBox(height: 12),
          itemCount: packages.length,
        );
      },
    );
  }
}
