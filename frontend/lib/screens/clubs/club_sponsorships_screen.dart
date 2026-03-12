import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/sponsorship_models.dart';
import 'package:gte_frontend/screens/clubs/club_ops_screen_host.dart';
import 'package:gte_frontend/screens/clubs/club_sponsorship_catalog_screen.dart';
import 'package:gte_frontend/screens/clubs/club_sponsorship_contract_screen.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_formatters.dart';
import 'package:gte_frontend/widgets/clubs/sponsor_asset_slot_card.dart';
import 'package:gte_frontend/widgets/clubs/sponsorship_contract_card.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_scaffold.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ClubSponsorshipsScreen extends StatelessWidget {
  const ClubSponsorshipsScreen({
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
      title: 'Sponsorship contracts',
      subtitle: 'Catalog, active agreements, and asset visibility.',
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
              title: 'Loading sponsorships',
              message: 'Preparing contract values, packages, and asset moderation status.',
              icon: Icons.handshake_outlined,
            ),
          );
        }
        final SponsorshipDashboard dashboard = controller.sponsorships!;
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          children: <Widget>[
            GteSurfacePanel(
              emphasized: true,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    clubOpsFormatCurrency(dashboard.activeContractValue),
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Active sponsorship contract value with ${clubOpsFormatCurrency(dashboard.projectedRenewalValue)} projected into the next renewal cycle.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            ClubOpsSectionHeader(
              title: 'Contract views',
              subtitle: 'Open the full catalog or review one contract at a time.',
              action: FilledButton.tonal(
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (BuildContext context) => ClubSponsorshipCatalogScreen(
                      controller: controller,
                      clubId: clubId,
                      clubName: clubName,
                    ),
                  ),
                ),
                child: const Text('Open catalog'),
              ),
            ),
            const SizedBox(height: 16),
            for (final SponsorshipContract contract in dashboard.contracts) ...<Widget>[
              SponsorshipContractCard(
                contract: contract,
                onOpen: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (BuildContext context) => ClubSponsorshipContractScreen(
                      contractId: contract.id,
                      controller: controller,
                      clubId: clubId,
                      clubName: clubName,
                    ),
                  ),
                ),
              ),
              if (contract != dashboard.contracts.last) const SizedBox(height: 12),
            ],
            const SizedBox(height: 16),
            Text('Asset slot visibility',
                style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
            for (final SponsorAssetSlot slot in dashboard.assetSlots) ...<Widget>[
              SponsorAssetSlotCard(slot: slot),
              if (slot != dashboard.assetSlots.last) const SizedBox(height: 12),
            ],
          ],
        );
      },
    );
  }
}
