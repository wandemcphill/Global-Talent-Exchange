import 'package:flutter/material.dart';
import 'package:gte_frontend/features/player_detail/gtex_player_navigator.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../data/gtex_share_market_api.dart';

const int _spotlightSize = 5;

/// Regens aged 21 or under ranked by potential, optionally for one nation,
/// from `GET /players/markets?sort=wonderkid`.
class GtexWonderkidBoard extends StatefulWidget {
  const GtexWonderkidBoard({super.key, required this.reader});

  final GtexShareMarketReader reader;

  @override
  State<GtexWonderkidBoard> createState() => _GtexWonderkidBoardState();
}

class _GtexWonderkidBoardState extends State<GtexWonderkidBoard> {
  String? _nation;
  late Future<List<GtexShareNation>> _nations;
  late Future<List<GtexWonderkid>> _kids;

  @override
  void initState() {
    super.initState();
    _nations = widget.reader.fetchRegenNations();
    _loadKids();
  }

  void _loadKids() {
    _kids = widget.reader.fetchWonderkids(nation: _nation);
  }

  void _pickNation(String? nation) {
    setState(() {
      _nation = nation;
      _loadKids();
    });
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      key: const Key('gtex-wonderkid-board'),
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        GtexPanel(
          title: 'Wonderkid spotlight',
          subtitle: 'Regens aged 21 or under, ranked by potential',
          accent: GtexColors.gold,
          child: FutureBuilder<List<GtexShareNation>>(
            future: _nations,
            builder: (
              BuildContext context,
              AsyncSnapshot<List<GtexShareNation>> snapshot,
            ) {
              final List<GtexShareNation> nations =
                  snapshot.data ?? const <GtexShareNation>[];
              return DropdownButton<String?>(
                key: const Key('gtex-wonderkid-nation-picker'),
                value: _nation,
                isExpanded: true,
                dropdownColor: GtexColors.panelStrong,
                style: const TextStyle(
                  color: GtexColors.text,
                  fontWeight: FontWeight.w700,
                ),
                onChanged: _pickNation,
                items: <DropdownMenuItem<String?>>[
                  const DropdownMenuItem<String?>(
                    value: null,
                    child: Text('All nations'),
                  ),
                  ...nations.map(
                    (GtexShareNation n) => DropdownMenuItem<String?>(
                      value: n.name,
                      child: Text('${n.name} (${n.count})'),
                    ),
                  ),
                ],
              );
            },
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        FutureBuilder<List<GtexWonderkid>>(
          future: _kids,
          builder: (
            BuildContext context,
            AsyncSnapshot<List<GtexWonderkid>> snapshot,
          ) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: <Widget>[
                  GtexSkeleton.box(height: 72),
                  SizedBox(height: GtexSpacing.sm),
                  GtexSkeleton.box(height: 72),
                ],
              );
            }
            if (snapshot.hasError) {
              return GtexBlockedState(
                title: 'Could not load wonderkids',
                reason: '${snapshot.error}',
                severity: GtexBlockedSeverity.warning,
                icon: Icons.cloud_off_rounded,
                ctaLabel: 'Retry',
                ctaAction: () => setState(_loadKids),
              );
            }
            final List<GtexWonderkid> kids =
                snapshot.data ?? const <GtexWonderkid>[];
            if (kids.isEmpty) {
              return const GtexEmptyState(
                title: 'No wonderkids listed',
                message: 'No regen aged 21 or under is listed for this nation.',
                icon: Icons.star_border_rounded,
                accent: GtexColors.gold,
              );
            }
            return Column(
              children: <Widget>[
                for (int i = 0; i < kids.length; i++)
                  _WonderkidRow(rank: i + 1, kid: kids[i]),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _WonderkidRow extends StatelessWidget {
  const _WonderkidRow({required this.rank, required this.kid});

  final int rank;
  final GtexWonderkid kid;

  @override
  Widget build(BuildContext context) {
    final bool spotlight = rank <= _spotlightSize;
    final Color accent = spotlight ? GtexColors.gold : GtexColors.purple;
    final VoidCallback? open = GtexPlayerNavigator.tapToOpen(
      context,
      kid.playerId,
    );
    final int? headroom = kid.growthHeadroom;
    return Padding(
      padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
      child: GtexPanel(
        key: Key('gtex-wonderkid-row-${kid.playerId}'),
        padding: const EdgeInsets.all(GtexSpacing.sm),
        accent: accent,
        onTap: open,
        child: Row(
          children: <Widget>[
            SizedBox(
              width: 36,
              child: Text(
                '#$rank',
                style: TextStyle(color: accent, fontWeight: FontWeight.w900),
              ),
            ),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    kid.name,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: GtexColors.text,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  Text(
                    <String>[
                      if (kid.nationality != null) kid.nationality!,
                      if (kid.position != null) kid.position!,
                      if (kid.age != null) '${kid.age}y',
                      '${kid.sharePriceCoin.toStringAsFixed(4)} GTX',
                    ].join(' · '),
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: GtexColors.textSecondary,
                      fontWeight: FontWeight.w600,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
            Wrap(
              spacing: 6,
              runSpacing: 4,
              children: <Widget>[
                GtexStatusChip(
                  label: '${kid.rating ?? '-'} → ${kid.potential ?? '-'}',
                  color: accent,
                  compact: true,
                ),
                if (headroom != null && headroom > 0)
                  GtexStatusChip(
                    label: '+$headroom',
                    color: GtexColors.pitch,
                    compact: true,
                  ),
              ],
            ),
            if (open != null)
              const Icon(
                Icons.chevron_right_rounded,
                color: GtexColors.textMuted,
              ),
          ],
        ),
      ),
    );
  }
}
