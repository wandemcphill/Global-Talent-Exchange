import 'package:flutter/material.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/features/club_redesign/models/gtex_club_redesign_models.dart';

import '../live_transfer_center_provider.dart';
import 'gtex_transfers_hub_panel.dart';

/// Loads the sporting transfer board for one club and lets the owner list a player.
class GtexLiveTransferRoom extends StatefulWidget {
  const GtexLiveTransferRoom({
    super.key,
    required this.clubId,
    required this.squad,
    required this.baseUrl,
    required this.backendMode,
    this.accessToken,
    this.api,
    this.onOpenFinancialMarket,
  });

  final String clubId;
  final List<GtexClubMember> squad;
  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final TransferCenterApi? api;
  final VoidCallback? onOpenFinancialMarket;

  @override
  State<GtexLiveTransferRoom> createState() => _GtexLiveTransferRoomState();
}

class _GtexLiveTransferRoomState extends State<GtexLiveTransferRoom> {
  late final TransferCenterApi _api;
  final TextEditingController _nameQuery = TextEditingController();
  final TextEditingController _minGsi = TextEditingController();
  final TextEditingController _maxGsi = TextEditingController();
  List<TransferCenterListingRecord> _listings = const <TransferCenterListingRecord>[];
  List<TransferHubOfferRecord> _offers = const <TransferHubOfferRecord>[];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _api = widget.api ??
        TransferCenterApi(
          client: GteAuthedApi(
            config: GteRepositoryConfig(baseUrl: widget.baseUrl, mode: widget.backendMode),
            transport: GteHttpTransport(),
            accessToken: widget.accessToken,
            mode: widget.backendMode,
          ),
        );
    _load();
  }

  @override
  void dispose() {
    _nameQuery.dispose();
    _minGsi.dispose();
    _maxGsi.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final int? minGsi = int.tryParse(_minGsi.text.trim());
      final int? maxGsi = int.tryParse(_maxGsi.text.trim());
      final String query = _nameQuery.text.trim();
      final List<TransferCenterListingRecord> publicListings = await _api.listListings(
        status: 'open',
        query: query.isEmpty ? null : query,
        minGsi: minGsi,
        maxGsi: maxGsi,
        publicBoard: true,
      );
      List<TransferCenterListingRecord> ownListings = const <TransferCenterListingRecord>[];
      List<TransferHubOfferRecord> offers = const <TransferHubOfferRecord>[];
      if ((widget.accessToken ?? '').trim().isNotEmpty) {
        ownListings = await _api.listListings(
          status: 'open',
          clubId: widget.clubId,
          query: query.isEmpty ? null : query,
          minGsi: minGsi,
          maxGsi: maxGsi,
        );
        offers = await _api.listOffers(clubId: widget.clubId);
      }
      final Map<String, TransferCenterListingRecord> merged = <String, TransferCenterListingRecord>{
        for (final TransferCenterListingRecord item in publicListings) item.id: item,
        for (final TransferCenterListingRecord item in ownListings) item.id: item,
      };
      if (!mounted) {
        return;
      }
      setState(() {
        _listings = merged.values.toList(growable: false);
        _offers = offers;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = 'Transfer listings could not be loaded.';
        _loading = false;
      });
    }
  }

  Future<void> _listPlayer() async {
    if (widget.squad.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('This squad has no player to list.')),
      );
      return;
    }
    final _ListedPlayer? listed = await showDialog<_ListedPlayer>(
      context: context,
      builder: (BuildContext dialogContext) {
        return _ListPlayerDialog(squad: widget.squad, initialPlayerId: widget.squad.first.id);
      },
    );
    if (listed == null) {
      return;
    }
    try {
      await _api.createListing(
        playerId: listed.playerId,
        sellingClubId: widget.clubId,
        basePrice: listed.asking,
        expiresAt: DateTime.now().toUtc().add(const Duration(days: 14)),
        visibility: listed.visibility,
        salaryAmount: listed.salary,
        contractYears: listed.salary == null ? null : 3,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Player listed. Other clubs can find the listing and make an offer.')),
        );
      }
      await _load();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('The player could not be listed.')),
        );
      }
    }
  }

  Future<void> _makeOffer(TransferCenterListingRecord listing) async {
    final TextEditingController amount = TextEditingController(
      text: listing.basePrice.toStringAsFixed(0),
    );
    final bool? submit = await showDialog<bool>(
      context: context,
      builder: (BuildContext dialogContext) {
        return AlertDialog(
          title: Text('Offer for ${listing.playerName}'),
          content: TextField(
            controller: amount,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'Cash offer'),
          ),
          actions: <Widget>[
            TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('Cancel')),
            FilledButton(onPressed: () => Navigator.pop(dialogContext, true), child: const Text('Send offer')),
          ],
        );
      },
    );
    final double? cash = double.tryParse(amount.text.trim());
    amount.dispose();
    if (submit != true || cash == null) {
      return;
    }
    try {
      await _api.createOffer(
        listingId: listing.id,
        bidderClubId: widget.clubId,
        cashAmount: cash,
        message: 'Offer from the transfer room.',
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Offer sent. The selling club can accept, reject, or counter.')),
        );
      }
      await _load();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('The offer could not be sent.')),
        );
      }
    }
  }

  Future<void> _accept(TransferHubOfferRecord offer) async {
    try {
      final TransferHubOfferRecord accepted = await _api.acceptOffer(offer.id);
      if (!mounted) {
        return;
      }
      if (accepted.settlement == 'contract_needed') {
        final double? wageAmount = await showDialog<double>(
          context: context,
          builder: (BuildContext dialogContext) => const _ContractWageDialog(),
        );
        if (wageAmount != null) {
          await _api.submitContractOffer(
            listingId: accepted.listingId,
            bidderClubId: accepted.bidderClubId,
            wageOfferAmount: wageAmount,
          );
        }
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              accepted.settlement == 'completed' ||
                      accepted.settlement == 'loan_active' ||
                      accepted.settlement == 'swapped'
                  ? 'The move is complete.'
                  : 'Offer accepted.',
            ),
          ),
        );
      }
      await _load();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('The offer could not be accepted.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        Wrap(
          spacing: 8,
          runSpacing: 8,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: <Widget>[
            SizedBox(
              width: 220,
              child: TextField(
                key: const Key('gtex-transfer-name-search'),
                controller: _nameQuery,
                decoration: const InputDecoration(
                  hintText: 'Player name',
                  isDense: true,
                  border: OutlineInputBorder(),
                ),
                onSubmitted: (_) => _load(),
              ),
            ),
            SizedBox(
              width: 90,
              child: TextField(
                key: const Key('gtex-transfer-min-gsi'),
                controller: _minGsi,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  hintText: 'Min GSI',
                  isDense: true,
                  border: OutlineInputBorder(),
                ),
              ),
            ),
            SizedBox(
              width: 90,
              child: TextField(
                controller: _maxGsi,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  hintText: 'Max GSI',
                  isDense: true,
                  border: OutlineInputBorder(),
                ),
              ),
            ),
            FilledButton(onPressed: _loading ? null : _load, child: const Text('Search')),
            OutlinedButton.icon(
              key: const Key('gtex-list-for-sale'),
              onPressed: _listPlayer,
              icon: const Icon(Icons.sell_outlined),
              label: const Text('List for sale'),
            ),
          ],
        ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(_error!),
          ),
        const SizedBox(height: 12),
        GtexTransfersHubPanel(
          activeClubId: widget.clubId,
          listings: _listings,
          offers: _offers,
          onMakeOfferForListing: _makeOffer,
          onAcceptOffer: _accept,
          onRejectOffer: (TransferHubOfferRecord offer) async {
            await _api.rejectOffer(offer.id);
            await _load();
          },
          onCancelOffer: (TransferHubOfferRecord offer) async {
            await _api.cancelOffer(offer.id);
            await _load();
          },
          onOpenFinancialMarket: widget.onOpenFinancialMarket,
        ),
      ],
    );
  }
}

class _ListedPlayer {
  const _ListedPlayer({
    required this.playerId,
    required this.asking,
    required this.salary,
    required this.visibility,
  });

  final String playerId;
  final double asking;
  final double? salary;
  final String visibility;
}

class _ListPlayerDialog extends StatefulWidget {
  const _ListPlayerDialog({required this.squad, required this.initialPlayerId});

  final List<GtexClubMember> squad;
  final String initialPlayerId;

  @override
  State<_ListPlayerDialog> createState() => _ListPlayerDialogState();
}

class _ListPlayerDialogState extends State<_ListPlayerDialog> {
  late String _playerId = widget.initialPlayerId;
  final TextEditingController _price = TextEditingController();
  final TextEditingController _wage = TextEditingController();
  String _visibility = 'public';

  @override
  void dispose() {
    _price.dispose();
    _wage.dispose();
    super.dispose();
  }

  void _submit() {
    final double? asking = double.tryParse(_price.text.trim());
    if (asking == null) {
      return;
    }
    final String wageText = _wage.text.trim();
    Navigator.pop(
      context,
      _ListedPlayer(
        playerId: _playerId,
        asking: asking,
        salary: wageText.isEmpty ? null : double.tryParse(wageText),
        visibility: _visibility,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('List a player for sale'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          DropdownButton<String>(
            key: const Key('gtex-list-player-picker'),
            isExpanded: true,
            value: _playerId,
            items: widget.squad
                .map(
                  (GtexClubMember player) => DropdownMenuItem<String>(
                    value: player.id,
                    child: Text('${player.name} · ${player.position}'),
                  ),
                )
                .toList(growable: false),
            onChanged: (String? value) {
              if (value != null) {
                setState(() => _playerId = value);
              }
            },
          ),
          TextField(
            key: const Key('gtex-list-player-price'),
            controller: _price,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'Asking price'),
          ),
          TextField(
            controller: _wage,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'Weekly wage'),
          ),
          DropdownButton<String>(
            isExpanded: true,
            value: _visibility,
            items: const <DropdownMenuItem<String>>[
              DropdownMenuItem(value: 'public', child: Text('Public')),
              DropdownMenuItem(value: 'private', child: Text('Private')),
              DropdownMenuItem(value: 'invite_only', child: Text('Invite only')),
            ],
            onChanged: (String? value) {
              if (value != null) {
                setState(() => _visibility = value);
              }
            },
          ),
        ],
      ),
      actions: <Widget>[
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
        FilledButton(
          key: const Key('gtex-list-player-submit'),
          onPressed: _submit,
          child: const Text('List for sale'),
        ),
      ],
    );
  }
}

class _ContractWageDialog extends StatefulWidget {
  const _ContractWageDialog();

  @override
  State<_ContractWageDialog> createState() => _ContractWageDialogState();
}

class _ContractWageDialogState extends State<_ContractWageDialog> {
  final TextEditingController _wage = TextEditingController();

  @override
  void dispose() {
    _wage.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Agree the contract'),
      content: TextField(
        controller: _wage,
        keyboardType: TextInputType.number,
        decoration: const InputDecoration(labelText: 'Weekly wage'),
      ),
      actions: <Widget>[
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Later')),
        FilledButton(
          onPressed: () {
            final double? amount = double.tryParse(_wage.text.trim());
            if (amount == null) {
              return;
            }
            Navigator.pop(context, amount);
          },
          child: const Text('Submit contract'),
        ),
      ],
    );
  }
}
