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
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(spacingLG),
                    child: Wrap(
                      spacing: spacingSM,
                      runSpacing: spacingSM,
                      children: <Widget>[
                        _MetricChip(
                          label: 'Open listings',
                          value: '${listings.length}',
                        ),
                        _MetricChip(
                          label: 'Club actions',
                          value: clubContext == null ? 'Blocked' : 'Enabled',
                        ),
                      ],
                    ),
                  ),
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
                                  ) => ListTile(
                                    contentPadding: EdgeInsets.zero,
                                    title: Text(listing.playerName),
                                    subtitle: Text(
                                      '${listing.status} | bid ${listing.currentHighestBid.toStringAsFixed(0)} | ${listing.bidCount} bids | ${listing.watchlistCount} watchlists',
                                    ),
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
                                )
                                .toList(growable: false),
                          ),
                ),
              ],
            );
          },
          loading:
              () => const Center(
                child: Padding(
                  padding: EdgeInsets.all(spacingLG),
                  child: CircularProgressIndicator(),
                ),
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
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(spacingLG),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Wrap(
                          spacing: spacingSM,
                          runSpacing: spacingSM,
                          children: <Widget>[
                            _MetricChip(
                              label: 'Status',
                              value: stringValue(
                                detail.listing['status'],
                                fallback: 'open',
                              ),
                            ),
                            _MetricChip(
                              label: 'Base',
                              value: numberValue(
                                detail.listing['base_price'],
                              ).toStringAsFixed(0),
                            ),
                            _MetricChip(
                              label: 'Current bid',
                              value: numberValue(
                                detail.listing['current_highest_bid'],
                              ).toStringAsFixed(0),
                            ),
                            _MetricChip(
                              label: 'Time remaining',
                              value: _durationLabel(
                                intValue(detail.listing['time_remaining']),
                              ),
                            ),
                            _MetricChip(
                              label: 'Channel',
                              value: stringValue(detail.listing['channel']),
                            ),
                          ],
                        ),
                        const SizedBox(height: spacingMD),
                        Text(
                          '${stringValue(player['current_club_name'], fallback: 'Club unavailable')} | ${stringValue(detail.listing['market_signal'], fallback: 'No signal')}',
                        ),
                        const SizedBox(height: spacingMD),
                        Wrap(
                          spacing: spacingSM,
                          runSpacing: spacingSM,
                          children: <Widget>[
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
                                        stringValue(
                                          detail.listing['player_id'],
                                        ),
                                      ),
                              child: const Text('Watchlist'),
                            ),
                            OutlinedButton(
                              onPressed:
                                  clubContext == null || negotiation == null
                                      ? null
                                      : () => _submitContractOffer(
                                        context,
                                        clubContext.id,
                                      ),
                              child: Text(
                                negotiation == null
                                    ? 'Negotiation unavailable'
                                    : 'Contract offer',
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
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
                                  (JsonMap bidder) => ListTile(
                                    contentPadding: EdgeInsets.zero,
                                    title: Text(
                                      stringValue(
                                        bidder['club_name'],
                                        fallback: stringValue(
                                          bidder['club_id'],
                                        ),
                                      ),
                                    ),
                                    subtitle: Text(
                                      '${numberValue(bidder['amount']).toStringAsFixed(0)} | ${boolValue(bidder['is_highest']) ? 'Highest' : 'Bid placed'}',
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
                                  ),
                                  _MetricChip(
                                    label: 'Contract years',
                                    value:
                                        '${intValue(negotiation['contract_years'])}',
                                  ),
                                  _MetricChip(
                                    label: 'Wage offer',
                                    value: numberValue(
                                      negotiation['wage_offer_amount'],
                                    ).toStringAsFixed(0),
                                  ),
                                ],
                              ),
                              if (playerDecision != null) ...<Widget>[
                                const SizedBox(height: spacingMD),
                                Text(
                                  'Player decision',
                                  style:
                                      Theme.of(context).textTheme.titleMedium,
                                ),
                                const SizedBox(height: spacingSM),
                                Text(
                                  '${stringValue(playerDecision['action'], fallback: 'pending')} | Score ${numberValue(playerDecision['decision_score']).toStringAsFixed(1)}',
                                ),
                              ],
                              if (coachOpinion != null) ...<Widget>[
                                const SizedBox(height: spacingMD),
                                Text(
                                  'Coach opinion',
                                  style:
                                      Theme.of(context).textTheme.titleMedium,
                                ),
                                const SizedBox(height: spacingSM),
                                Text(
                                  '${stringValue(coachOpinion['stance'], fallback: 'neutral')} | ${stringValue(coachOpinion['reason'], fallback: 'No reason supplied.')}',
                                ),
                              ],
                              if (agentNegotiation != null) ...<Widget>[
                                const SizedBox(height: spacingMD),
                                Text(
                                  'Agent response',
                                  style:
                                      Theme.of(context).textTheme.titleMedium,
                                ),
                                const SizedBox(height: spacingSM),
                                Text(
                                  '${stringValue(agentNegotiation['action'], fallback: 'pending')} | ${stringValue(agentNegotiation['notes'], fallback: 'No notes supplied.')}',
                                ),
                              ],
                            ],
                          ),
                ),
              ],
            );
          },
          loading:
              () => const Center(
                child: Padding(
                  padding: EdgeInsets.all(spacingLG),
                  child: CircularProgressIndicator(),
                ),
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
    final double? amount = await showDialog<double>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: Text('Bid for $playerName'),
          content: TextField(
            controller: bidController,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'Bid amount'),
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed:
                  () => Navigator.of(
                    context,
                  ).pop(double.tryParse(bidController.text.trim())),
              child: const Text('Submit'),
            ),
          ],
        );
      },
    );
    if (amount == null || amount <= 0) {
      return;
    }
    try {
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

  Future<void> _submitContractOffer(
    BuildContext context,
    String clubId,
  ) async {
    final TextEditingController wageController = TextEditingController(
      text: '50000',
    );
    final TextEditingController yearsController = TextEditingController(
      text: '3',
    );
    final TextEditingController roleController = TextEditingController(
      text: 'starter',
    );
    final bool? confirmed = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Submit contract offer'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              TextField(
                controller: wageController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Weekly wage'),
              ),
              const SizedBox(height: spacingSM),
              TextField(
                controller: yearsController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Contract years'),
              ),
              const SizedBox(height: spacingSM),
              TextField(
                controller: roleController,
                decoration: const InputDecoration(labelText: 'Expected role'),
              ),
            ],
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Submit'),
            ),
          ],
        );
      },
    );
    if (confirmed != true) {
      return;
    }
    final double? wage = double.tryParse(wageController.text.trim());
    final int? years = int.tryParse(yearsController.text.trim());
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
    try {
      await ref
          .read(transferCenterApiProvider)
          .submitContractOffer(
            listingId: widget.listingId,
            clubId: clubId,
            wageOfferAmount: wage,
            contractYears: years,
            expectedRole: roleController.text,
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
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(spacingLG),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: spacingXS),
            Text(subtitle),
            const SizedBox(height: spacingMD),
            child,
          ],
        ),
      ),
    );
  }
}

class _MetricChip extends StatelessWidget {
  const _MetricChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Chip(label: Text('$label: $value'));
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Text(message);
  }
}

class _BlockedCard extends StatelessWidget {
  const _BlockedCard({required this.title, required this.message});

  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(spacingLG),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: spacingSM),
            Text(message),
          ],
        ),
      ),
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
