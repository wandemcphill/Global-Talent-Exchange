import 'package:flutter/material.dart';

import '../../data/gte_api_repository.dart';
import '../../data/gte_exchange_api_client.dart';
import '../../data/gte_exchange_models.dart';

const Color _bg = Color(0xFF0E1217);
const Color _panel = Color(0xFF141A21);
const Color _border = Color(0xFF283039);
const Color _text = Color(0xFFF4F6F8);
const Color _textSecondary = Color(0xFF9AA7B4);
const Color _textMuted = Color(0xFF7F8C99);
const Color _green = Color(0xFF5FD17A);
const Color _amber = Color(0xFFE3B23C);
const Color _orange = Color(0xFFE08A3C);
const Color _red = Color(0xFFC7543A);
const Color _blue = Color(0xFF85B7EB);

const String _condensed = 'BarlowCondensed';

/// Football-Manager-style full player profile: identity + bio (height/foot/
/// positions) + the six colour-coded stats + GSI/OVR/POT + a market panel.
class GtexFmPlayerProfileScreen extends StatefulWidget {
  const GtexFmPlayerProfileScreen({
    super.key,
    required this.playerId,
    required this.baseUrl,
    this.backendMode = GteBackendMode.live,
  });

  final String playerId;
  final String baseUrl;
  final GteBackendMode backendMode;

  @override
  State<GtexFmPlayerProfileScreen> createState() =>
      _GtexFmPlayerProfileScreenState();
}

class _GtexFmPlayerProfileScreenState extends State<GtexFmPlayerProfileScreen> {
  late Future<GteMarketPlayerDetailView> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<GteMarketPlayerDetailView> _load() {
    final GteExchangeApiClient client = GteExchangeApiClient.standard(
      baseUrl: widget.baseUrl,
      mode: widget.backendMode,
    );
    return client.fetchPlayerDetail(widget.playerId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        backgroundColor: _bg,
        foregroundColor: _text,
        elevation: 0,
        title: const Text('Player profile'),
      ),
      body: FutureBuilder<GteMarketPlayerDetailView>(
        future: _future,
        builder: (BuildContext context, AsyncSnapshot<GteMarketPlayerDetailView> snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError || snap.data == null) {
            return _ErrorState(onRetry: () => setState(() => _future = _load()));
          }
          return _ProfileBody(detail: snap.data!);
        },
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          const Icon(Icons.refresh_rounded, color: _textMuted, size: 40),
          const SizedBox(height: 12),
          const Text(
            "We couldn't load this player",
            style: TextStyle(color: _text, fontSize: 16),
          ),
          const SizedBox(height: 12),
          OutlinedButton(onPressed: onRetry, child: const Text('Retry')),
        ],
      ),
    );
  }
}

class _ProfileBody extends StatelessWidget {
  const _ProfileBody({required this.detail});

  final GteMarketPlayerDetailView detail;

  @override
  Widget build(BuildContext context) {
    final GteMarketPlayerIdentity id = detail.identity;
    final GteMarketPlayerAttributes attr = detail.attributes;
    final int gsi = detail.trend.globalScoutingIndex.round().clamp(0, 99);
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          _HeaderCard(identity: id, gsi: gsi, attr: attr),
          const SizedBox(height: 14),
          _BioCard(identity: id),
          const SizedBox(height: 14),
          _SectionLabel('ATTRIBUTES'),
          const SizedBox(height: 8),
          _AttributesCard(attr: attr),
          const SizedBox(height: 14),
          _SectionLabel('MARKET'),
          const SizedBox(height: 8),
          _MarketCard(detail: detail),
        ],
      ),
    );
  }
}

class _HeaderCard extends StatelessWidget {
  const _HeaderCard({required this.identity, required this.gsi, required this.attr});

  final GteMarketPlayerIdentity identity;
  final int gsi;
  final GteMarketPlayerAttributes attr;

  @override
  Widget build(BuildContext context) {
    final String position = identity.normalizedPosition ?? identity.position ?? '—';
    final String club = identity.currentClubName ?? '—';
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _panel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _border),
      ),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  identity.playerName,
                  style: const TextStyle(
                    fontFamily: _condensed,
                    color: _text,
                    fontSize: 24,
                    fontWeight: FontWeight.w800,
                    height: 1.05,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  '$club · ${identity.age}y · $position',
                  style: const TextStyle(color: _textSecondary, fontSize: 12.5),
                ),
                if ((identity.nationality ?? '').isNotEmpty) ...<Widget>[
                  const SizedBox(height: 2),
                  Text(
                    identity.nationality!,
                    style: const TextStyle(color: _blue, fontSize: 12),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: 10),
          _RatingBox(label: 'GSI', value: gsi, color: _green),
          const SizedBox(width: 8),
          _RatingBox(label: 'POT', value: attr.potential, color: _blue),
        ],
      ),
    );
  }
}

class _RatingBox extends StatelessWidget {
  const _RatingBox({required this.label, required this.value, required this.color});

  final String label;
  final int value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: _bg,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.5)),
      ),
      child: Column(
        children: <Widget>[
          Text(
            '$value',
            style: TextStyle(
              color: color,
              fontSize: 22,
              fontWeight: FontWeight.w800,
              height: 1,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: const TextStyle(color: _textMuted, fontSize: 10, letterSpacing: 0.5),
          ),
        ],
      ),
    );
  }
}

class _BioCard extends StatelessWidget {
  const _BioCard({required this.identity});

  final GteMarketPlayerIdentity identity;

  @override
  Widget build(BuildContext context) {
    final String primary = identity.normalizedPosition ?? identity.position ?? '—';
    final String height = identity.heightCm == null ? '—' : '${identity.heightCm} cm';
    final String foot = _foot(identity.preferredFoot);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _panel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Text('POSITIONS', style: TextStyle(color: _textMuted, fontSize: 10, letterSpacing: 0.6)),
          const SizedBox(height: 6),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: <Widget>[
              _PosChip(label: primary, natural: true),
              ...identity.secondaryPositions
                  .take(4)
                  .map((String p) => _PosChip(label: p, natural: false)),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: <Widget>[
              _BioStat(label: 'Height', value: height),
              _BioStat(label: 'Foot', value: foot),
              _BioStat(label: 'Age', value: '${identity.age}'),
            ],
          ),
        ],
      ),
    );
  }

  String _foot(String? foot) {
    final String? f = foot?.trim();
    if (f == null || f.isEmpty) {
      return '—';
    }
    return f[0].toUpperCase() + f.substring(1).toLowerCase();
  }
}

class _PosChip extends StatelessWidget {
  const _PosChip({required this.label, required this.natural});

  final String label;
  final bool natural;

  @override
  Widget build(BuildContext context) {
    final Color color = natural ? _green : _textSecondary;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: natural ? color.withValues(alpha: 0.5) : _border),
      ),
      child: Text(
        label.toUpperCase(),
        style: TextStyle(
          color: color,
          fontFamily: _condensed,
          fontSize: 13,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.4,
        ),
      ),
    );
  }
}

class _BioStat extends StatelessWidget {
  const _BioStat({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label.toUpperCase(), style: const TextStyle(color: _textMuted, fontSize: 10, letterSpacing: 0.5)),
          const SizedBox(height: 2),
          Text(value, style: const TextStyle(color: _text, fontSize: 14, fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }
}

class _AttributesCard extends StatelessWidget {
  const _AttributesCard({required this.attr});

  final GteMarketPlayerAttributes attr;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 6),
      decoration: BoxDecoration(
        color: _panel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _border),
      ),
      child: Column(
        children: attr.sixStats
            .map((MapEntry<String, int> stat) => _StatBar(label: stat.key, value: stat.value))
            .toList(growable: false),
      ),
    );
  }
}

class _StatBar extends StatelessWidget {
  const _StatBar({required this.label, required this.value});

  final String label;
  final int value;

  Color get _color {
    if (value >= 80) return _green;
    if (value >= 65) return _amber;
    if (value >= 50) return _orange;
    return _red;
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: <Widget>[
          SizedBox(
            width: 80,
            child: Text(label, style: const TextStyle(color: _textSecondary, fontSize: 13)),
          ),
          SizedBox(
            width: 24,
            child: Text(
              '$value',
              style: TextStyle(color: _color, fontSize: 14, fontWeight: FontWeight.w800),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(3),
              child: LinearProgressIndicator(
                value: (value / 99).clamp(0.0, 1.0),
                minHeight: 6,
                backgroundColor: const Color(0xFF1E252E),
                valueColor: AlwaysStoppedAnimation<Color>(_color),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _MarketCard extends StatelessWidget {
  const _MarketCard({required this.detail});

  final GteMarketPlayerDetailView detail;

  @override
  Widget build(BuildContext context) {
    final GteMarketPlayerMarketProfile mp = detail.marketProfile;
    final double? movement = detail.value.movementPct;
    final String value = _value(mp);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _panel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Text('VALUE', style: TextStyle(color: _textMuted, fontSize: 10, letterSpacing: 0.6)),
          const SizedBox(height: 2),
          Text(value, style: const TextStyle(color: _text, fontSize: 22, fontWeight: FontWeight.w800)),
          if (movement != null) ...<Widget>[
            const SizedBox(height: 2),
            Text(
              '${movement >= 0 ? '+' : ''}${movement.toStringAsFixed(1)}% recent',
              style: TextStyle(color: movement >= 0 ? _green : _red, fontSize: 12),
            ),
          ],
          const SizedBox(height: 10),
          Row(
            children: <Widget>[
              _MarketStat(
                label: 'Tradable',
                value: mp.isTradable ? 'Yes' : 'No',
                color: mp.isTradable ? _green : _textMuted,
              ),
              _MarketStat(
                label: 'Holders',
                value: mp.holderCount == null ? '—' : '${mp.holderCount}',
                color: _blue,
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _value(GteMarketPlayerMarketProfile mp) {
    if (mp.marketValueEur != null && mp.marketValueEur! > 0) {
      return '€${_compact(mp.marketValueEur!)}';
    }
    final double? credits = mp.quotedMarketPriceCredits ?? mp.snapshotMarketPriceCredits;
    if (credits != null && credits > 0) {
      return '${_compact(credits)} GTC';
    }
    return 'Unpriced';
  }

  String _compact(double v) {
    if (v >= 1000000) return '${(v / 1000000).toStringAsFixed(1)}M';
    if (v >= 1000) return '${(v / 1000).toStringAsFixed(1)}K';
    return v.toStringAsFixed(0);
  }
}

class _MarketStat extends StatelessWidget {
  const _MarketStat({required this.label, required this.value, required this.color});

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label.toUpperCase(), style: const TextStyle(color: _textMuted, fontSize: 10, letterSpacing: 0.5)),
          const SizedBox(height: 2),
          Text(value, style: TextStyle(color: color, fontSize: 14, fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.label);

  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        Text(
          label,
          style: const TextStyle(
            fontFamily: _condensed,
            color: _textMuted,
            fontSize: 13,
            fontWeight: FontWeight.w800,
            letterSpacing: 1.5,
          ),
        ),
        const SizedBox(width: 10),
        const Expanded(child: Divider(color: _border, height: 1)),
      ],
    );
  }
}
