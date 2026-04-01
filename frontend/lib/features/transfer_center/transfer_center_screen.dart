import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_feedback.dart';
import '../../core/constants/app_spacing.dart';
import '../../navigation/app_destinations.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import '../../shared/widgets/gtex_action_surface.dart';
import '../../shared/widgets/gtex_premium_panels.dart';
import '../../widgets/gte_state_panel.dart';
import '../shared/data/feature_telemetry.dart';
import '../shared/data/gte_feature_support.dart';
import 'live_transfer_center_provider.dart';

class TransferCenterScreen extends ConsumerStatefulWidget {
  const TransferCenterScreen({super.key});

  @override
  ConsumerState<TransferCenterScreen> createState() =>
      _TransferCenterScreenState();
}

class _TransferCenterScreenState extends ConsumerState<TransferCenterScreen> {
  @override
  void initState() {
    super.initState();
    trackFeatureEvent(
      topic: 'transfer_center',
      name: 'transfer_center_viewed',
      dedupeKey: 'transfer-center-view',
    );
  }

  @override
  Widget build(BuildContext context) {
    final AsyncValue<List<TransferCenterListingRecord>> value = ref.watch(
      transferCenterListingsProvider,
    );
    final bool authenticated = ref.watch(isAuthenticatedProvider);
    return AppPageLayout(
      title: 'Transfer Center',
      subtitle:
          'A dedicated transfer route now uses live listings, detail views, bidding, watchlists, and negotiation context.',
      trailing: DataSourceBadge(
        status:
            value.hasError ? DataSourceStatus.blocked : DataSourceStatus.live,
      ),
      children: <Widget>[
        value.when(
          data: (List<TransferCenterListingRecord> listings) {
            final clubContext = ref.watch(clubContextProvider);
            return Column(
              children: <Widget>[
                GtexHeroPanel(
                  eyebrow: 'TRANSFER COMMAND',
                  title: 'Live negotiation board',
                  description:
                      'Premium transfer-center surface for open listings, active bidders, and club-authorized deal flow.',
                  metrics: <Widget>[
                    _MetricChip(
                      label: 'Open listings',
                      value: '${listings.length}',
                      tone: GtexSurfaceTone.live,
                    ),
                    _MetricChip(
                      label: 'Club actions',
                      value:
                          clubContext == null
                              ? (authenticated ? 'Syncing' : 'Login required')
                              : 'Enabled',
                      tone:
                          clubContext == null
                              ? GtexSurfaceTone.danger
                              : GtexSurfaceTone.success,
                    ),
                  ],
                ),
                const SizedBox(height: spacingMD),
                _SectionCard(
                  title: 'Live listings',
                  subtitle:
                      'Each listing opens a live detail route with bidders and negotiation state.',
                  child:
                      listings.isEmpty
                          ? const _EmptyState(
                            message:
                                'No live transfer listings are open right now.',
                          )
                          : Column(
                            children: listings
                                .map(
                                  (
                                    TransferCenterListingRecord listing,
                                  ) => Padding(
                                    padding: const EdgeInsets.only(
                                      bottom: spacingSM,
                                    ),
                                    child: GtexListTile(
                                      title: listing.playerName,
                                      subtitle:
                                          '${listing.status} | bid ${listing.currentHighestBid.toStringAsFixed(0)} | ${listing.bidCount} bids | ${listing.watchlistCount} watchlists',
                                      leadingIcon: Icons.candlestick_chart,
                                      tone: GtexSurfaceTone.live,
                                      trailing: FilledButton(
                                        onPressed:
                                            () => context.push(
                                              AppRoutes.transferCenterDetailLocation(
                                                listing.id,
                                              ),
                                            ),
                                        child: const Text('Open'),
                                      ),
                                    ),
                                  ),
                                )
                                .toList(growable: false),
                          ),
                ),
              ],
            );
          },
          loading:
              () => const GteStatePanel(
                eyebrow: 'TRANSFER CENTER',
                title: 'Loading live listings',
                message:
                    'Syncing the transfer market lane, bidder stack, and club access controls for this route.',
                icon: Icons.candlestick_chart_rounded,
                isLoading: true,
              ),
          error:
              (Object error, StackTrace stackTrace) => _BlockedCard(
                title: 'Transfer center is blocked',
                message: AppFeedback.messageFor(error),
              ),
        ),
      ],
    );
  }
}

class TransferCenterDetailScreen extends ConsumerStatefulWidget {
  const TransferCenterDetailScreen({super.key, required this.listingId});

  final String listingId;

  @override
  ConsumerState<TransferCenterDetailScreen> createState() =>
      _TransferCenterDetailScreenState();
}

class _TransferCenterDetailScreenState
    extends ConsumerState<TransferCenterDetailScreen> {
  @override
  void initState() {
    super.initState();
    trackFeatureEvent(
      topic: 'transfer_center',
      name: 'transfer_listing_viewed',
      payload: <String, Object?>{'listing_id': widget.listingId},
      dedupeKey: 'transfer-listing-${widget.listingId}',
    );
  }

  @override
  Widget build(BuildContext context) {
    final AsyncValue<TransferCenterDetailData> value = ref.watch(
      transferCenterDetailProvider(widget.listingId),
    );
    return AppPageLayout(
      title: value.maybeWhen(
        data: (TransferCenterDetailData data) {
          final JsonMap player = jsonMap(
            data.listing['player'],
            label: 'transfer player',
            fallback: const <String, Object?>{},
          );
          return stringValue(player['full_name'], fallback: 'Transfer listing');
        },
        orElse: () => 'Transfer listing',
      ),
      subtitle:
          'Live auction detail, bidders, and negotiation state for this transfer listing.',
      trailing: DataSourceBadge(
        status:
            value.hasError ? DataSourceStatus.blocked : DataSourceStatus.live,
      ),
      children: <Widget>[
        value.when(
          data: (TransferCenterDetailData detail) {
            final clubContext = ref.watch(clubContextProvider);
            final JsonMap player = jsonMap(
              detail.listing['player'],
              label: 'transfer player',
              fallback: const <String, Object?>{},
            );
            final List<JsonMap> bidders = jsonMapList(
              detail.listing['bidders'],
              label: 'transfer bidders',
            );
            final JsonMap? negotiation = detail.negotiation;
            final JsonMap? playerDecision =
                negotiation == null
                    ? null
                    : jsonMapOrNull(negotiation['player_decision']);
            final JsonMap? coachOpinion =
                negotiation == null
                    ? null
                    : jsonMapOrNull(negotiation['coach_opinion']);
            final JsonMap? agentNegotiation =
                negotiation == null
                    ? null
                    : jsonMapOrNull(negotiation['agent_negotiation']);
            return Column(
              children: <Widget>[
                GtexHeroPanel(
                  eyebrow: 'LISTING DETAIL',
                  title: 'Negotiation cockpit',
                  description:
                      'Pricing, timing, club signal, and deal actions for this live transfer listing.',
                  metrics: <Widget>[
                    _MetricChip(
                      label: 'Status',
                      value: stringValue(
                        detail.listing['status'],
                        fallback: 'open',
                      ),
                      tone: GtexSurfaceTone.live,
                    ),
                    _MetricChip(
                      label: 'Base',
                      value: numberValue(
                        detail.listing['base_price'],
                      ).toStringAsFixed(0),
                      tone: GtexSurfaceTone.info,
                    ),
                    _MetricChip(
                      label: 'Current bid',
                      value: numberValue(
                        detail.listing['current_highest_bid'],
                      ).toStringAsFixed(0),
                      tone: GtexSurfaceTone.warning,
                    ),
                    _MetricChip(
                      label: 'Time remaining',
                      value: _durationLabel(
                        intValue(detail.listing['time_remaining']),
                      ),
                      tone: GtexSurfaceTone.neutral,
                    ),
                    _MetricChip(
                      label: 'Channel',
                      value: stringValue(detail.listing['channel']),
                      tone: GtexSurfaceTone.success,
                    ),
                    GtexPill(
                      label:
                          '${stringValue(player['current_club_name'], fallback: 'Club unavailable')} | ${stringValue(detail.listing['market_signal'], fallback: 'No signal')}',
                      icon: Icons.sync_alt_rounded,
                      tone: GtexSurfaceTone.info,
                    ),
                  ],
                  actions: <Widget>[
                    FilledButton(
                      onPressed:
                          clubContext == null
                              ? null
                              : () => _placeBid(
                                context,
                                clubContext.id,
                                stringValue(player['full_name']),
                              ),
                      child: const Text('Bid'),
                    ),
                    OutlinedButton(
                      onPressed:
                          clubContext == null
                              ? null
                              : () => _watchlist(
                                context,
                                clubContext.id,
                                stringValue(player['full_name']),
                                stringValue(detail.listing['player_id']),
                              ),
                      child: const Text('Watchlist'),
                    ),
                    OutlinedButton(
                      onPressed:
                          clubContext == null || negotiation == null
                              ? null
                              : () =>
                                  _submitContractOffer(context, clubContext.id),
                      child: Text(
                        negotiation == null
                            ? 'Negotiation unavailable'
                            : 'Contract offer',
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: spacingMD),
                _SectionCard(
                  title: 'Bidders',
                  subtitle: 'Live bid stack from the transfer listing detail.',
                  child:
                      bidders.isEmpty
                          ? const _EmptyState(
                            message: 'No bidders have been recorded yet.',
                          )
                          : Column(
                            children: bidders
                                .map(
                                  (JsonMap bidder) => Padding(
                                    padding: const EdgeInsets.only(
                                      bottom: spacingSM,
                                    ),
                                    child: GtexListTile(
                                      title: stringValue(
                                        bidder['club_name'],
                                        fallback: stringValue(
                                          bidder['club_id'],
                                        ),
                                      ),
                                      subtitle:
                                          '${numberValue(bidder['amount']).toStringAsFixed(0)} | ${boolValue(bidder['is_highest']) ? 'Highest' : 'Bid placed'}',
                                      leadingIcon: Icons.account_balance,
                                      tone:
                                          boolValue(bidder['is_highest'])
                                              ? GtexSurfaceTone.success
                                              : GtexSurfaceTone.info,
                                    ),
                                  ),
                                )
                                .toList(growable: false),
                          ),
                ),
                const SizedBox(height: spacingMD),
                _SectionCard(
                  title: 'Negotiation state',
                  subtitle:
                      'When the listing moves into negotiation, player, coach, and agent context appears here.',
                  child:
                      negotiation == null
                          ? const _EmptyState(
                            message:
                                'This listing has not entered negotiation yet.',
                          )
                          : Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Wrap(
                                spacing: spacingSM,
                                runSpacing: spacingSM,
                                children: <Widget>[
                                  _MetricChip(
                                    label: 'Negotiation',
                                    value: stringValue(
                                      negotiation['status'],
                                      fallback: 'unknown',
                                    ),
                                    tone: GtexSurfaceTone.live,
                                  ),
                                  _MetricChip(
                                    label: 'Contract years',
                                    value:
                                        '${intValue(negotiation['contract_years'])}',
                                    tone: GtexSurfaceTone.info,
                                  ),
                                  _MetricChip(
                                    label: 'Wage offer',
                                    value: numberValue(
                                      negotiation['wage_offer_amount'],
                                    ).toStringAsFixed(0),
                                    tone: GtexSurfaceTone.warning,
                                  ),
                                ],
                              ),
                              if (playerDecision != null) ...<Widget>[
                                const SizedBox(height: spacingMD),
                                GtexListTile(
                                  title: 'Player decision',
                                  subtitle:
                                      '${stringValue(playerDecision['action'], fallback: 'pending')} | Score ${numberValue(playerDecision['decision_score']).toStringAsFixed(1)}',
                                  leadingIcon: Icons.person_rounded,
                                  tone: GtexSurfaceTone.success,
                                ),
                              ],
                              if (coachOpinion != null) ...<Widget>[
                                const SizedBox(height: spacingMD),
                                GtexListTile(
                                  title: 'Coach opinion',
                                  subtitle:
                                      '${stringValue(coachOpinion['stance'], fallback: 'neutral')} | ${stringValue(coachOpinion['reason'], fallback: 'No reason supplied.')}',
                                  leadingIcon: Icons.ssid_chart_rounded,
                                  tone: GtexSurfaceTone.info,
                                ),
                              ],
                              if (agentNegotiation != null) ...<Widget>[
                                const SizedBox(height: spacingMD),
                                GtexListTile(
                                  title: 'Agent response',
                                  subtitle:
                                      '${stringValue(agentNegotiation['action'], fallback: 'pending')} | ${stringValue(agentNegotiation['notes'], fallback: 'No notes supplied.')}',
                                  leadingIcon: Icons.support_agent_rounded,
                                  tone: GtexSurfaceTone.warning,
                                ),
                              ],
                            ],
                          ),
                ),
              ],
            );
          },
          loading:
              () => const GteStatePanel(
                eyebrow: 'TRANSFER CENTER',
                title: 'Loading listing detail',
                message:
                    'Resolving the live bidder stack, negotiation state, and club-authorized action lane.',
                icon: Icons.gavel_rounded,
                isLoading: true,
              ),
          error:
              (Object error, StackTrace stackTrace) => _BlockedCard(
                title: 'Transfer listing is blocked',
                message: AppFeedback.messageFor(error),
              ),
        ),
      ],
    );
  }

  Future<void> _watchlist(
    BuildContext context,
    String clubId,
    String playerName,
    String playerId,
  ) async {
    try {
      await ref
          .read(transferCenterApiProvider)
          .addToWatchlist(
            clubId: clubId,
            playerId: playerId,
            listingId: widget.listingId,
          );
      trackFeatureEvent(
        topic: 'transfer_center',
        name: 'transfer_listing_watchlisted',
        payload: <String, Object?>{
          'listing_id': widget.listingId,
          'club_id': clubId,
        },
      );
      ref.invalidate(transferCenterDetailProvider(widget.listingId));
      ref.invalidate(transferCenterListingsProvider);
      if (!mounted) {
        return;
      }
      AppFeedback.showSuccess(this.context, '$playerName added to watchlist.');
    } catch (error) {
      if (!mounted) {
        return;
      }
      AppFeedback.showError(this.context, error);
    }
  }

  Future<void> _placeBid(
    BuildContext context,
    String clubId,
    String playerName,
  ) async {
    final TextEditingController bidController = TextEditingController();
    try {
      final double? amount = await showDialog<double>(
        context: context,
        builder: (BuildContext context) {
          return AnimatedBuilder(
            animation: bidController,
            builder: (BuildContext context, Widget? child) {
              final double? parsedAmount = double.tryParse(
                bidController.text.trim(),
              );
              final bool canSubmit = parsedAmount != null && parsedAmount > 0;
              return GtexActionDialog(
                eyebrow: 'TRANSFER CENTER',
                title: 'Bid for $playerName',
                description:
                    'Submit a live transfer bid from the negotiation board. Invalid amounts stay blocked before the request is sent.',
                leadingIcon: Icons.gavel_rounded,
                content: TextField(
                  controller: bidController,
                  autofocus: true,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'Bid amount',
                    helperText: 'Enter a positive amount in transfer coin.',
                  ),
                ),
                actions: <Widget>[
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Cancel'),
                  ),
                  FilledButton(
                    onPressed:
                        canSubmit
                            ? () => Navigator.of(context).pop(parsedAmount)
                            : null,
                    child: const Text('Submit'),
                  ),
                ],
              );
            },
          );
        },
      );
      if (amount == null || amount <= 0) {
        return;
      }
      await ref
          .read(transferCenterApiProvider)
          .placeBid(
            listingId: widget.listingId,
            clubId: clubId,
            amount: amount,
          );
      trackFeatureEvent(
        topic: 'transfer_center',
        name: 'transfer_bid_submitted',
        payload: <String, Object?>{
          'listing_id': widget.listingId,
          'club_id': clubId,
          'amount': amount,
        },
      );
      ref.invalidate(transferCenterDetailProvider(widget.listingId));
      ref.invalidate(transferCenterListingsProvider);
      if (!mounted) {
        return;
      }
      AppFeedback.showSuccess(this.context, 'Bid submitted for $playerName.');
    } catch (error) {
      if (!mounted) {
        return;
      }
      AppFeedback.showError(this.context, error);
    }
  }

  Future<void> _submitContractOffer(BuildContext context, String clubId) async {
    final TextEditingController wageController = TextEditingController(
      text: '50000',
    );
    final TextEditingController yearsController = TextEditingController(
      text: '3',
    );
    final TextEditingController roleController = TextEditingController(
      text: 'starter',
    );
    final Listenable formListenable = Listenable.merge(<Listenable>[
      wageController,
      yearsController,
      roleController,
    ]);
    try {
      final bool? confirmed = await showDialog<bool>(
        context: context,
        builder: (BuildContext context) {
          return AnimatedBuilder(
            animation: formListenable,
            builder: (BuildContext context, Widget? child) {
              final double? wage = double.tryParse(wageController.text.trim());
              final int? years = int.tryParse(yearsController.text.trim());
              final bool canSubmit =
                  wage != null && wage >= 0 && years != null && years >= 1;
              return GtexActionDialog(
                eyebrow: 'TRANSFER CENTER',
                title: 'Submit contract offer',
                description:
                    'Send live wage, term, and role terms into the current negotiation lane for this listing.',
                leadingIcon: Icons.handshake_rounded,
                content: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    TextField(
                      controller: wageController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Weekly wage',
                        helperText: 'Use a non-negative weekly wage amount.',
                      ),
                    ),
                    const SizedBox(height: spacingSM),
                    TextField(
                      controller: yearsController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Contract years',
                        helperText: 'Minimum term is one year.',
                      ),
                    ),
                    const SizedBox(height: spacingSM),
                    TextField(
                      controller: roleController,
                      decoration: const InputDecoration(
                        labelText: 'Expected role',
                        helperText:
                            'Leave blank to keep the default starter role.',
                      ),
                    ),
                  ],
                ),
                actions: <Widget>[
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(false),
                    child: const Text('Cancel'),
                  ),
                  FilledButton(
                    onPressed:
                        canSubmit
                            ? () => Navigator.of(context).pop(true)
                            : null,
                    child: const Text('Submit'),
                  ),
                ],
              );
            },
          );
        },
      );
      if (confirmed != true) {
        return;
      }
      final double? wage = double.tryParse(wageController.text.trim());
      final int? years = int.tryParse(yearsController.text.trim());
      final String expectedRole =
          roleController.text.trim().isEmpty
              ? 'starter'
              : roleController.text.trim();
      if (wage == null || wage < 0 || years == null || years < 1) {
        if (!mounted) {
          return;
        }
        AppFeedback.showError(
          this.context,
          'Enter a valid wage and contract length before submitting the offer.',
        );
        return;
      }
      await ref
          .read(transferCenterApiProvider)
          .submitContractOffer(
            listingId: widget.listingId,
            clubId: clubId,
            wageOfferAmount: wage,
            contractYears: years,
            expectedRole: expectedRole,
          );
      trackFeatureEvent(
        topic: 'transfer_center',
        name: 'transfer_contract_offer_submitted',
        payload: <String, Object?>{
          'listing_id': widget.listingId,
          'club_id': clubId,
        },
      );
      ref.invalidate(transferCenterDetailProvider(widget.listingId));
      if (!mounted) {
        return;
      }
      AppFeedback.showSuccess(this.context, 'Contract offer submitted.');
    } catch (error) {
      if (!mounted) {
        return;
      }
      AppFeedback.showError(this.context, error);
    }
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.subtitle,
    required this.child,
  });

  final String title;
  final String subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return GtexSectionPanel(title: title, subtitle: subtitle, child: child);
  }
}

class _MetricChip extends StatelessWidget {
  const _MetricChip({
    required this.label,
    required this.value,
    this.tone = GtexSurfaceTone.info,
  });

  final String label;
  final String value;
  final GtexSurfaceTone tone;

  @override
  Widget build(BuildContext context) {
    return GtexStatTile(label: label, value: value, tone: tone);
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return GtexListTile(
      title: 'Nothing live yet',
      subtitle: message,
      leadingIcon: Icons.hourglass_empty_rounded,
      tone: GtexSurfaceTone.neutral,
    );
  }
}

class _BlockedCard extends StatelessWidget {
  const _BlockedCard({required this.title, required this.message});

  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    return GteStatePanel(
      eyebrow: 'TRANSFER CENTER',
      title: title,
      message: message,
      icon: Icons.warning_amber_rounded,
    );
  }
}

String _durationLabel(int seconds) {
  if (seconds <= 0) {
    return '0m';
  }
  final int hours = seconds ~/ 3600;
  final int minutes = (seconds % 3600) ~/ 60;
  if (hours > 0) {
    return '${hours}h ${minutes}m';
  }
  return '${minutes}m';
}
