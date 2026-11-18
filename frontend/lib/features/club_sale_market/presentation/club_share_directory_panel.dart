import 'package:flutter/material.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';

class ClubShareListing {
  const ClubShareListing({
    required this.clubId,
    required this.clubName,
    required this.marketKind,
    required this.unitPrice,
    required this.available,
    required this.totalSupply,
  });

  final String clubId;
  final String clubName;
  final String marketKind;
  final double unitPrice;
  final int available;
  final int totalSupply;

  factory ClubShareListing.fromJson(Map<String, dynamic> json) {
    return ClubShareListing(
      clubId: (json['club_id'] ?? '').toString(),
      clubName: (json['club_name'] ?? 'Club').toString(),
      marketKind: (json['market_kind'] ?? 'token').toString(),
      unitPrice: double.tryParse('${json['unit_price']}') ?? 0,
      available: int.tryParse('${json['available']}') ?? 0,
      totalSupply: int.tryParse('${json['total_supply']}') ?? 0,
    );
  }
}

class ClubShareDirectoryPanel extends StatefulWidget {
  const ClubShareDirectoryPanel({
    super.key,
    required this.baseUrl,
    required this.backendMode,
    this.accessToken,
    this.searchShares,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final Future<List<ClubShareListing>> Function(String query)? searchShares;

  @override
  State<ClubShareDirectoryPanel> createState() => _ClubShareDirectoryPanelState();
}

class _ClubShareDirectoryPanelState extends State<ClubShareDirectoryPanel> {
  final TextEditingController _query = TextEditingController();
  final TextEditingController _quantity = TextEditingController(text: '1');
  List<ClubShareListing> _items = const <ClubShareListing>[];
  bool _loading = false;
  String? _message;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _query.dispose();
    _quantity.dispose();
    super.dispose();
  }

  GteAuthedApi get _client => GteAuthedApi(
    config: GteRepositoryConfig(baseUrl: widget.baseUrl, mode: widget.backendMode),
    transport: GteHttpTransport(),
    accessToken: widget.accessToken,
    mode: widget.backendMode,
  );

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _message = null;
    });
    try {
      final Future<List<ClubShareListing>> Function(String query)? injected = widget.searchShares;
      final List<ClubShareListing> items;
      if (injected != null) {
        items = await injected(_query.text);
      } else {
        final Map<String, dynamic> payload = await _client.getMap(
          '/api/clubs/ownership-market',
          auth: false,
          query: <String, Object?>{
            if (_query.text.trim().isNotEmpty) 'q': _query.text.trim(),
          },
        );
        final List<dynamic> rows = payload['items'] as List<dynamic>? ?? <dynamic>[];
        items = rows
            .whereType<Map>()
            .map((Map row) => ClubShareListing.fromJson(Map<String, dynamic>.from(row)))
            .toList(growable: false);
      }
      if (!mounted) {
        return;
      }
      setState(() {
        _items = items;
        _loading = false;
      });
    } catch (_) {
      if (mounted) {
        setState(() {
          _loading = false;
          _message = 'Club shares could not be loaded.';
        });
      }
    }
  }

  Future<void> _trade(ClubShareListing item, {required bool buy}) async {
    final int quantity = int.tryParse(_quantity.text.trim()) ?? 0;
    if (quantity <= 0) {
      setState(() => _message = 'Enter a quantity above zero.');
      return;
    }
    if ((widget.accessToken ?? '').trim().isEmpty) {
      setState(() => _message = 'Sign in to buy or sell club shares.');
      return;
    }
    final String path = item.marketKind == 'fan_share'
        ? '/api/creator/clubs/${item.clubId}/fan-share-market/purchase'
        : '/api/clubs/${item.clubId}/${buy ? 'buy-tokens' : 'sell-tokens'}';
    try {
      await _client.request(
        'POST',
        path,
        body: item.marketKind == 'fan_share'
            ? <String, Object?>{'share_count': quantity}
            : <String, Object?>{'quantity': quantity},
      );
      if (!mounted) {
        return;
      }
      setState(() => _message = buy ? 'Shares purchased.' : 'Shares sold.');
      await _load();
    } catch (_) {
      if (mounted) {
        setState(() => _message = 'The share trade could not be completed.');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      key: const Key('gtex-club-share-directory'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        Text('Club shares', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 4),
        const Text('Search a club and buy a slice of it. Whole-club sales stay on the board above.'),
        const SizedBox(height: 8),
        TextField(
          key: const Key('gtex-club-share-search'),
          controller: _query,
          decoration: const InputDecoration(
            hintText: 'Search clubs by name',
            border: OutlineInputBorder(),
          ),
          onSubmitted: (_) => _load(),
        ),
        const SizedBox(height: 8),
        TextField(
          controller: _quantity,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(
            labelText: 'Quantity',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton(
            onPressed: _loading ? null : _load,
            child: Text(_loading ? 'Searching' : 'Search shares'),
          ),
        ),
        if (_message != null)
          Padding(padding: const EdgeInsets.only(top: 8), child: Text(_message!)),
        for (final ClubShareListing item in _items)
          ListTile(
            key: Key('gtex-club-share-${item.clubId}-${item.marketKind}'),
            title: Text(item.clubName),
            subtitle: Text(
              '${item.marketKind == 'fan_share' ? 'Fan shares' : 'Club tokens'} · ${item.unitPrice.toStringAsFixed(2)} · ${item.available} available',
            ),
            trailing: Wrap(
              spacing: 8,
              children: <Widget>[
                TextButton(onPressed: () => _trade(item, buy: true), child: const Text('Buy')),
                if (item.marketKind != 'fan_share')
                  TextButton(onPressed: () => _trade(item, buy: false), child: const Text('Sell')),
              ],
            ),
          ),
      ],
    );
  }
}
