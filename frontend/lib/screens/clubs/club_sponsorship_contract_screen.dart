import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/sponsorship_models.dart';
import 'package:gte_frontend/screens/clubs/club_ops_screen_host.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_formatters.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ClubSponsorshipContractScreen extends StatelessWidget {
  const ClubSponsorshipContractScreen({
    super.key,
    required this.contractId,
    this.clubId = 'royal-lagos-fc',
    this.clubName,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.mode = GteBackendMode.liveThenFixture,
    this.api,
    this.controller,
  });

  final String contractId;
  final String clubId;
  final String? clubName;
  final String baseUrl;
  final GteBackendMode mode;
  final ClubOpsApi? api;
  final ClubOpsController? controller;

  @override
  Widget build(BuildContext context) {
    return ClubOpsScreenHost(
      title: 'Sponsorship contract',
      subtitle: 'Value, term, deliverables, and moderation status.',
      clubId: clubId,
      clubName: clubName,
      baseUrl: baseUrl,
      mode: mode,
      api: api,
      controller: controller,
      builder: (BuildContext context, ClubOpsController controller) {
        final SponsorshipContract? contract = controller.contractById(contractId);
        if (contract == null) {
          return const Padding(
            padding: EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Contract not found',
              message: 'This sponsorship contract is not available in the current club snapshot.',
              icon: Icons.info_outline,
            ),
          );
        }
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          children: <Widget>[
            GteSurfacePanel(
              emphasized: true,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(contract.sponsorName,
                      style: Theme.of(context).textTheme.headlineSmall),
                  const SizedBox(height: 8),
                  Text(
                    '${clubOpsFormatCurrency(contract.totalValue)} · ${clubOpsFormatDate(contract.startDate)} to ${clubOpsFormatDate(contract.endDate)}',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  Text(contract.renewalWindowLabel,
                      style: Theme.of(context).textTheme.bodyMedium),
                ],
              ),
            ),
            const SizedBox(height: 16),
            GteSurfacePanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Deliverables',
                      style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 12),
                  for (final String item in contract.deliverables) ...<Widget>[
                    Text(item, style: Theme.of(context).textTheme.bodyMedium),
                    if (item != contract.deliverables.last)
                      const SizedBox(height: 8),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 16),
            GteSurfacePanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Operational notes',
                      style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 12),
                  Text('Contact: ${contract.contactName}',
                      style: Theme.of(context).textTheme.bodyMedium),
                  const SizedBox(height: 8),
                  Text('Visibility: ${contract.visibilityLabel}',
                      style: Theme.of(context).textTheme.bodyMedium),
                  const SizedBox(height: 12),
                  for (final String note in contract.notes) ...<Widget>[
                    Text(note, style: Theme.of(context).textTheme.bodyMedium),
                    if (note != contract.notes.last) const SizedBox(height: 8),
                  ],
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}
