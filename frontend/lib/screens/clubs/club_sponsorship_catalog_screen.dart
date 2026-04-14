import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/sponsorship_models.dart';
import 'package:gte_frontend/screens/clubs/club_ops_screen_host.dart';
import 'package:gte_frontend/widgets/clubs/sponsorship_package_card.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

class ClubSponsorshipCatalogScreen extends StatefulWidget {
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
  State<ClubSponsorshipCatalogScreen> createState() =>
      _ClubSponsorshipCatalogScreenState();
}

class _ClubSponsorshipCatalogScreenState
    extends State<ClubSponsorshipCatalogScreen> {
  @override
  Widget build(BuildContext context) {
    return ClubOpsScreenHost(
      title: 'Sponsorship catalog',
      subtitle: 'Transparent package value, duration, and asset inventory.',
      clubId: widget.clubId,
      clubName: widget.clubName,
      baseUrl: widget.baseUrl,
      mode: widget.mode,
      api: widget.api,
      controller: widget.controller,
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
        if (packages.isEmpty) {
          return const Padding(
            padding: EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'No sponsorship packages available',
              message:
                  'The live backend did not return any sponsorship inventory for this club.',
              icon: Icons.store_mall_directory_outlined,
            ),
          );
        }
        return ListView.separated(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          itemBuilder: (BuildContext context, int index) {
            final SponsorshipPackage package = packages[index];
            return SponsorshipPackageCard(
              package: package,
              primaryActionLabel:
                  controller.isSubmittingSponsorshipApplication
                      ? 'Submitting...'
                      : 'Apply',
              onPrimaryAction:
                  controller.isSubmittingSponsorshipApplication
                      ? null
                      : () => _openApplicationSheet(controller, package),
            );
          },
          separatorBuilder: (_, __) => const SizedBox(height: 12),
          itemCount: packages.length,
        );
      },
    );
  }

  Future<void> _openApplicationSheet(
    ClubOpsController controller,
    SponsorshipPackage package,
  ) async {
    final GlobalKey<FormState> formKey = GlobalKey<FormState>();
    final TextEditingController sponsorNameController = TextEditingController();
    final TextEditingController durationController = TextEditingController(
      text: package.durationMonths.toString(),
    );
    final TextEditingController customCopyController = TextEditingController();
    final TextEditingController logoUrlController = TextEditingController();
    String? inlineError;
    bool submitting = false;

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext sheetContext) {
        return StatefulBuilder(
          builder: (
            BuildContext context,
            void Function(void Function()) setState,
          ) {
            final double bottomInset = MediaQuery.of(context).viewInsets.bottom;
            return Padding(
              padding: EdgeInsets.fromLTRB(20, 20, 20, bottomInset + 20),
              child: Form(
                key: formKey,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Apply for ${package.name}',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Submit a live sponsorship contract for this package.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      if (inlineError != null) ...<Widget>[
                        const SizedBox(height: 16),
                        Text(
                          inlineError!,
                          style: Theme.of(
                            context,
                          ).textTheme.bodyMedium?.copyWith(
                            color: Theme.of(context).colorScheme.error,
                          ),
                        ),
                      ],
                      const SizedBox(height: 16),
                      TextFormField(
                        controller: sponsorNameController,
                        decoration: const InputDecoration(
                          labelText: 'Sponsor name',
                        ),
                        validator: (String? value) {
                          final String trimmed = value?.trim() ?? '';
                          if (trimmed.length < 2) {
                            return 'Enter the sponsor name.';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: durationController,
                        decoration: const InputDecoration(
                          labelText: 'Duration (months)',
                        ),
                        keyboardType: TextInputType.number,
                        validator: (String? value) {
                          final int? parsed = int.tryParse(value?.trim() ?? '');
                          if (parsed == null || parsed < 1 || parsed > 36) {
                            return 'Enter a duration between 1 and 36 months.';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: customCopyController,
                        decoration: const InputDecoration(
                          labelText: 'Custom copy (optional)',
                        ),
                        maxLength: 80,
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: logoUrlController,
                        decoration: const InputDecoration(
                          labelText: 'Logo URL (optional)',
                        ),
                      ),
                      const SizedBox(height: 20),
                      Row(
                        children: <Widget>[
                          Expanded(
                            child: OutlinedButton(
                              onPressed:
                                  submitting
                                      ? null
                                      : () => Navigator.of(sheetContext).pop(),
                              child: const Text('Cancel'),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: FilledButton(
                              onPressed:
                                  submitting
                                      ? null
                                      : () async {
                                        if (!formKey.currentState!.validate()) {
                                          return;
                                        }
                                        setState(() {
                                          submitting = true;
                                          inlineError = null;
                                        });
                                        try {
                                          final SponsorshipContract contract =
                                              await controller.applySponsorship(
                                                draft:
                                                    SponsorshipApplicationDraft(
                                                      packageCode: package.code,
                                                      sponsorName:
                                                          sponsorNameController
                                                              .text
                                                              .trim(),
                                                      durationMonths: int.parse(
                                                        durationController.text
                                                            .trim(),
                                                      ),
                                                      currency:
                                                          package.currency,
                                                      customCopy:
                                                          _nullableTrimmed(
                                                            customCopyController
                                                                .text,
                                                          ),
                                                      customLogoUrl:
                                                          _nullableTrimmed(
                                                            logoUrlController
                                                                .text,
                                                          ),
                                                    ),
                                              );
                                          if (sheetContext.mounted) {
                                            Navigator.of(sheetContext).pop();
                                          }
                                          if (!mounted) {
                                            return;
                                          }
                                          AppFeedback.showSuccess(
                                            this.context,
                                            contract.status ==
                                                    SponsorshipContractStatus
                                                        .pendingApproval
                                                ? '${package.name} submitted for approval.'
                                                : '${package.name} activated for ${contract.sponsorName}.',
                                          );
                                        } catch (error) {
                                          setState(() {
                                            inlineError =
                                                AppFeedback.messageFor(error);
                                          });
                                        } finally {
                                          if (sheetContext.mounted) {
                                            setState(() {
                                              submitting = false;
                                            });
                                          }
                                        }
                                      },
                              child: const Text('Submit'),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }
}

String? _nullableTrimmed(String value) {
  final String trimmed = value.trim();
  return trimmed.isEmpty ? null : trimmed;
}
