import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../data/owner_console_api.dart';

Color _hex(String? value, Color fallback) {
  final String raw = (value ?? '').replaceAll('#', '');
  final int? parsed = raw.length == 6 ? int.tryParse(raw, radix: 16) : null;
  return parsed == null ? fallback : Color(0xFF000000 | parsed);
}

/// Public club card. Supporters open `/showroom/:code` without signing in.
class PublicShowroomScreen extends StatefulWidget {
  const PublicShowroomScreen({super.key, required this.load, this.code});

  final Future<PublicClubCard> Function() load;
  final String? code;

  @override
  State<PublicShowroomScreen> createState() => _PublicShowroomScreenState();
}

class _PublicShowroomScreenState extends State<PublicShowroomScreen> {
  late final Future<PublicClubCard> _card = widget.load();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      key: const Key('public-showroom'),
      backgroundColor: GtexColors.surfaceBase,
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 720),
            child: FutureBuilder<PublicClubCard>(
              future: _card,
              builder: (
                BuildContext context,
                AsyncSnapshot<PublicClubCard> snap,
              ) {
                if (snap.connectionState != ConnectionState.done) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snap.hasError || !snap.hasData) {
                  return const GtexBlockedState(
                    key: Key('public-showroom-missing'),
                    title: 'Showroom not found',
                    reason: 'This club card is not public.',
                    icon: Icons.shield_outlined,
                  );
                }
                return ListView(
                  padding: const EdgeInsets.all(GtexSpacing.md),
                  children: <Widget>[
                    const Text(
                      'GTEX CLUB SHOWROOM',
                      style: TextStyle(
                        color: GtexColors.gold,
                        letterSpacing: 3,
                        fontWeight: FontWeight.w900,
                        fontSize: 12,
                      ),
                    ),
                    const SizedBox(height: GtexSpacing.sm),
                    _PublicCard(card: snap.data!, code: widget.code),
                  ],
                );
              },
            ),
          ),
        ),
      ),
    );
  }
}

class _PublicCard extends StatelessWidget {
  const _PublicCard({required this.card, this.code});

  final PublicClubCard card;
  final String? code;

  @override
  Widget build(BuildContext context) {
    final Color primary = _hex(card.primaryColor, GtexColors.pitch);
    final String place = <String>[
      card.city ?? '',
      card.countryCode ?? '',
      if (card.founded != null) 'est. ${card.founded}',
    ].where((String part) => part.isNotEmpty).join(' · ');
    return Container(
      key: const Key('public-showroom-card'),
      padding: const EdgeInsets.all(GtexSpacing.md),
      decoration: BoxDecoration(
        color: const Color(0xFF0B0F14),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: primary, width: 2),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            card.clubName,
            key: const Key('public-showroom-name'),
            style: TextStyle(
              color: primary,
              fontSize: 28,
              fontWeight: FontWeight.w900,
            ),
          ),
          if (card.shortName != null)
            Text(
              card.shortName!,
              style: const TextStyle(color: GtexColors.textSecondary),
            ),
          if ((code ?? '').isNotEmpty)
            Text(
              code!,
              key: const Key('public-showroom-code'),
              style: const TextStyle(color: GtexColors.textMuted, fontSize: 11),
            ),
          if (place.isNotEmpty)
            Text(
              place,
              key: const Key('public-showroom-place'),
              style: const TextStyle(color: GtexColors.textSecondary),
            ),
          if (card.crestUrl != null)
            Padding(
              padding: const EdgeInsets.only(top: GtexSpacing.sm),
              child: Text(
                card.crestUrl!,
                key: const Key('public-showroom-crest'),
                style: const TextStyle(color: GtexColors.cyan, fontSize: 12),
              ),
            ),
          const SizedBox(height: GtexSpacing.md),
          const Text(
            'TROPHIES',
            style: TextStyle(
              color: GtexColors.gold,
              letterSpacing: 2,
              fontWeight: FontWeight.w900,
              fontSize: 11,
            ),
          ),
          const SizedBox(height: 6),
          if (card.trophies.isEmpty)
            const Text(
              'Space reserved for future glory',
              style: TextStyle(color: GtexColors.textMuted, fontSize: 12),
            )
          else
            for (final PublicTrophy trophy in card.trophies)
              Text(
                '${trophy.position == 1 ? 'Winners' : '#${trophy.position}'} · ${trophy.competition}${trophy.year == null ? '' : ' · ${trophy.year}'}',
                style: const TextStyle(
                  color: GtexColors.text,
                  fontWeight: FontWeight.w700,
                ),
              ),
        ],
      ),
    );
  }
}
