import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/sponsorship_models.dart';
import 'package:gte_frontend/screens/clubs/club_ops_screen_host.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_formatters.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
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
      subtitle: 'Value, term, moderation, and live contract actions.',
      clubId: clubId,
      clubName: clubName,
      baseUrl: baseUrl,
      mode: mode,
      api: api,
      controller: controller,
      builder: (BuildContext context, ClubOpsController controller) {
        final SponsorshipContract? contract = controller.contractById(
          contractId,
        );
        if (contract == null) {
          return const Padding(
            padding: EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Contract not found',
              message:
                  'This sponsorship contract is not available in the current club snapshot.',
              icon: Icons.info_outline,
            ),
          );
        }
        final List<SponsorAssetSlot> linkedSlots =
            (controller.sponsorships?.assetSlots ?? const <SponsorAssetSlot>[])
                .where(
                  (SponsorAssetSlot slot) =>
                      contract.assetSlotCodes.contains(slot.slotCode),
                )
                .toList(growable: false);
        final bool showCreativeAction =
            contract.moderationState != SponsorModerationState.approved ||
            linkedSlots.any(
              (SponsorAssetSlot slot) =>
                  slot.moderationState != SponsorModerationState.approved,
            );
        final bool showPayoutAction =
            contract.status == SponsorshipContractStatus.active &&
            contract.outstandingValue > 0;
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          children: <Widget>[
            GteSurfacePanel(
              emphasized: true,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    contract.sponsorName,
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    contract.packageName,
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '${clubOpsFormatCurrency(contract.totalValue)} | ${clubOpsFormatDate(contract.startDate)} to ${clubOpsFormatDate(contract.endDate)}',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: <Widget>[
                      Chip(label: Text(_statusLabel(contract.status))),
                      Chip(
                        label: Text(
                          'Moderation: ${_moderationLabel(contract.moderationState)}',
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    contract.renewalWindowLabel,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
            if (showCreativeAction || showPayoutAction) ...<Widget>[
              const SizedBox(height: 16),
              GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Contract actions',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'This screen now uses the live club sponsorship patch path for moderation resubmission and payout posting.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 16),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: <Widget>[
                        if (showCreativeAction)
                          FilledButton(
                            onPressed:
                                controller.isUpdatingSponsorshipContract
                                    ? null
                                    : () => _handleCreativeUpdate(
                                      context,
                                      controller,
                                      contract,
                                      linkedSlots,
                                    ),
                            child: Text(_creativeActionLabel(linkedSlots)),
                          ),
                        if (showPayoutAction)
                          FilledButton.tonal(
                            onPressed:
                                controller.isUpdatingSponsorshipContract
                                    ? null
                                    : () => _handlePostDuePayouts(
                                      context,
                                      controller,
                                      contract,
                                    ),
                            child: const Text('Post due payouts'),
                          ),
                      ],
                    ),
                    if (controller.sponsorshipContractErrorMessage !=
                        null) ...<Widget>[
                      const SizedBox(height: 12),
                      Text(
                        controller.sponsorshipContractErrorMessage!,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: GteShellTheme.negative,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
            const SizedBox(height: 16),
            GteSurfacePanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Settlement status',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Settled to date: ${clubOpsFormatCurrency(contract.settledValue)}',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Outstanding contract value: ${clubOpsFormatCurrency(contract.outstandingValue)}',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    contract.status == SponsorshipContractStatus.active
                        ? 'Posting due payouts settles installments whose due date has passed.'
                        : 'Payout posting only occurs while the contract is active.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
            if (linkedSlots.isNotEmpty) ...<Widget>[
              const SizedBox(height: 16),
              GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Linked asset slots',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 12),
                    for (final SponsorAssetSlot slot
                        in linkedSlots) ...<Widget>[
                      Text(
                        slot.surfaceName,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        slot.placementLabel,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Moderation: ${_moderationLabel(slot.moderationState)}',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: _moderationColor(slot.moderationState),
                        ),
                      ),
                      if (slot.note != null &&
                          slot.note!.trim().isNotEmpty) ...<Widget>[
                        const SizedBox(height: 4),
                        Text(
                          slot.note!,
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ],
                      if (slot != linkedSlots.last) const SizedBox(height: 12),
                    ],
                  ],
                ),
              ),
            ],
            const SizedBox(height: 16),
            GteSurfacePanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Deliverables',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
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
                  Text(
                    'Operational notes',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Visibility: ${contract.visibilityLabel}',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  if (contract.contactName.trim().isNotEmpty) ...<Widget>[
                    const SizedBox(height: 8),
                    Text(
                      'Contact: ${contract.contactName}',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                  if (contract.customCopy != null &&
                      contract.customCopy!.trim().isNotEmpty) ...<Widget>[
                    const SizedBox(height: 8),
                    Text(
                      'Submitted copy: ${contract.customCopy!}',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                  if (contract.customLogoUrl != null &&
                      contract.customLogoUrl!.trim().isNotEmpty) ...<Widget>[
                    const SizedBox(height: 8),
                    Text(
                      'Submitted logo: ${contract.customLogoUrl!}',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                  if (contract.notes.isNotEmpty) ...<Widget>[
                    const SizedBox(height: 12),
                    for (final String note in contract.notes) ...<Widget>[
                      Text(note, style: Theme.of(context).textTheme.bodyMedium),
                      if (note != contract.notes.last)
                        const SizedBox(height: 8),
                    ],
                  ],
                ],
              ),
            ),
          ],
        );
      },
    );
  }

  Future<void> _handleCreativeUpdate(
    BuildContext context,
    ClubOpsController controller,
    SponsorshipContract contract,
    List<SponsorAssetSlot> linkedSlots,
  ) async {
    final SponsorshipContractUpdateDraft? draft =
        await _showCreativeUpdateSheet(context, contract, linkedSlots);
    if (draft == null) {
      return;
    }
    try {
      await controller.updateSponsorshipContract(
        contractId: contract.id,
        draft: draft,
      );
      if (!context.mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Creative update sent for moderation review.'),
        ),
      );
    } catch (_) {
      if (!context.mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            controller.sponsorshipContractErrorMessage ??
                'Unable to update this sponsorship contract.',
          ),
        ),
      );
    }
  }

  Future<void> _handlePostDuePayouts(
    BuildContext context,
    ClubOpsController controller,
    SponsorshipContract contract,
  ) async {
    try {
      await controller.updateSponsorshipContract(
        contractId: contract.id,
        draft: const SponsorshipContractUpdateDraft(settleDuePayouts: true),
      );
      if (!context.mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Due sponsorship payouts were checked and any matured installments were posted.',
          ),
        ),
      );
    } catch (_) {
      if (!context.mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            controller.sponsorshipContractErrorMessage ??
                'Unable to post due sponsorship payouts.',
          ),
        ),
      );
    }
  }

  Future<SponsorshipContractUpdateDraft?> _showCreativeUpdateSheet(
    BuildContext context,
    SponsorshipContract contract,
    List<SponsorAssetSlot> linkedSlots,
  ) async {
    final TextEditingController copyController = TextEditingController(
      text: contract.customCopy ?? '',
    );
    final TextEditingController logoController = TextEditingController(
      text: contract.customLogoUrl ?? '',
    );
    return showModalBottomSheet<SponsorshipContractUpdateDraft>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext sheetContext) {
        final List<String> moderationNotes = linkedSlots
            .map((SponsorAssetSlot slot) => slot.note?.trim() ?? '')
            .where((String note) => note.isNotEmpty)
            .toList(growable: false);
        return Padding(
          padding: EdgeInsets.fromLTRB(
            20,
            20,
            20,
            MediaQuery.of(sheetContext).viewInsets.bottom + 20,
          ),
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Update sponsorship creative',
                  style: Theme.of(sheetContext).textTheme.titleLarge,
                ),
                const SizedBox(height: 8),
                Text(
                  'Creative changes go back through live moderation before the contract inventory is treated as fully approved.',
                  style: Theme.of(sheetContext).textTheme.bodyMedium,
                ),
                if (moderationNotes.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 12),
                  for (final String note in moderationNotes) ...<Widget>[
                    Text(
                      note,
                      style: Theme.of(sheetContext).textTheme.bodyMedium,
                    ),
                    if (note != moderationNotes.last) const SizedBox(height: 6),
                  ],
                ],
                const SizedBox(height: 16),
                TextFormField(
                  controller: copyController,
                  maxLength: 80,
                  decoration: const InputDecoration(
                    labelText: 'Custom copy',
                    hintText:
                        'Update the sponsor text shown on approved assets',
                  ),
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: logoController,
                  maxLength: 255,
                  keyboardType: TextInputType.url,
                  decoration: const InputDecoration(
                    labelText: 'Logo URL',
                    hintText: 'https://cdn.example.com/brand-mark.png',
                  ),
                ),
                const SizedBox(height: 16),
                Row(
                  children: <Widget>[
                    TextButton(
                      onPressed: () => Navigator.of(sheetContext).pop(),
                      child: const Text('Cancel'),
                    ),
                    const Spacer(),
                    FilledButton(
                      onPressed: () {
                        final String? customCopy = _resolvedDraftValue(
                          copyController.text,
                          contract.customCopy,
                        );
                        final String? customLogoUrl = _resolvedDraftValue(
                          logoController.text,
                          contract.customLogoUrl,
                        );
                        if ((customCopy == null || customCopy.isEmpty) &&
                            (customLogoUrl == null || customLogoUrl.isEmpty)) {
                          ScaffoldMessenger.of(sheetContext).showSnackBar(
                            const SnackBar(
                              content: Text(
                                'Add updated copy or a logo URL before resubmitting creative.',
                              ),
                            ),
                          );
                          return;
                        }
                        Navigator.of(sheetContext).pop(
                          SponsorshipContractUpdateDraft(
                            customCopy: customCopy,
                            customLogoUrl: customLogoUrl,
                            moderationStatus: 'pending',
                            settleDuePayouts: false,
                          ),
                        );
                      },
                      child: const Text('Submit update'),
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

String? _resolvedDraftValue(String rawValue, String? existingValue) {
  final String trimmed = rawValue.trim();
  if (trimmed.isNotEmpty) {
    return trimmed;
  }
  final String existing = existingValue?.trim() ?? '';
  return existing.isEmpty ? null : existing;
}

String _statusLabel(SponsorshipContractStatus status) {
  switch (status) {
    case SponsorshipContractStatus.active:
      return 'Active';
    case SponsorshipContractStatus.renewalDue:
      return 'Renewal due';
    case SponsorshipContractStatus.pendingApproval:
      return 'Pending approval';
    case SponsorshipContractStatus.completed:
      return 'Completed';
  }
}

String _moderationLabel(SponsorModerationState state) {
  switch (state) {
    case SponsorModerationState.approved:
      return 'Approved';
    case SponsorModerationState.underReview:
      return 'Under review';
    case SponsorModerationState.needsChanges:
      return 'Needs changes';
    case SponsorModerationState.blocked:
      return 'Blocked';
  }
}

String _creativeActionLabel(List<SponsorAssetSlot> linkedSlots) {
  final bool hasChangeRequest = linkedSlots.any(
    (SponsorAssetSlot slot) =>
        slot.moderationState == SponsorModerationState.needsChanges,
  );
  return hasChangeRequest ? 'Resubmit creative' : 'Update creative';
}

Color _moderationColor(SponsorModerationState state) {
  switch (state) {
    case SponsorModerationState.approved:
      return GteShellTheme.positive;
    case SponsorModerationState.underReview:
      return GteShellTheme.accentWarm;
    case SponsorModerationState.needsChanges:
      return GteShellTheme.accentWarm;
    case SponsorModerationState.blocked:
      return GteShellTheme.negative;
  }
}
