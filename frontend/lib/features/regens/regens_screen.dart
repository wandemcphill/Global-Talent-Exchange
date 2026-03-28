import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/app_spacing.dart';
import '../../core/widgets/gtex_surface_card.dart';
import '../../core/widgets/player_card.dart';
import '../../shared/models/competition.dart';
import '../../shared/models/federation.dart';
import '../../shared/models/player.dart';
import '../../shared/providers/regen_provider.dart';
import '../../shared/widgets/section_heading.dart';

class RegensScreen extends ConsumerWidget {
  const RegensScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final List<Player> regens = ref.watch(regenProvider);
    final List<Competition> competitions = ref.watch(competitionsProvider);
    final List<String> history = ref.watch(historyProvider);
    final List<Federation> federations = ref.watch(federationsProvider);

    return DefaultTabController(
      length: 4,
      child: Padding(
        padding: const EdgeInsets.all(spacingMD),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const SectionHeading(
              title: 'World Intel',
              subtitle:
                  'Regens, competitions, federation trends, and long-range history.',
            ),
            const SizedBox(height: spacingMD),
            const TabBar(
              isScrollable: true,
              tabs: <Widget>[
                Tab(text: 'Regens'),
                Tab(text: 'Competitions'),
                Tab(text: 'History'),
                Tab(text: 'Federations'),
              ],
            ),
            const SizedBox(height: spacingMD),
            Expanded(
              child: TabBarView(
                children: <Widget>[
                  LayoutBuilder(
                    builder: (BuildContext context, BoxConstraints constraints) {
                      final int crossAxisCount =
                          constraints.maxWidth >= 1000 ? 4 : 2;
                      return GridView.builder(
                        itemCount: regens.length,
                        gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: crossAxisCount,
                          crossAxisSpacing: 12,
                          mainAxisSpacing: 12,
                          childAspectRatio: 0.88,
                        ),
                        itemBuilder: (BuildContext context, int index) {
                          final Player player = regens[index];
                          return PlayerCard(
                            name: player.name,
                            rating: player.rating,
                            image: player.image,
                            position: player.position,
                            country: player.country,
                            valueInMillions: player.valueInMillions,
                            highlighted: player.isHot,
                          );
                        },
                      );
                    },
                  ),
                  ListView.separated(
                    itemCount: competitions.length,
                    separatorBuilder: (_, _) => const SizedBox(height: spacingSM),
                    itemBuilder: (BuildContext context, int index) {
                      final Competition competition = competitions[index];
                      return GtexSurfaceCard(
                        child: ListTile(
                          contentPadding: EdgeInsets.zero,
                          title: Text(competition.name),
                          subtitle: Text(
                            '${competition.stage} • ${competition.nextFixture}\n${competition.spotlight}',
                          ),
                        ),
                      );
                    },
                  ),
                  ListView.separated(
                    itemCount: history.length,
                    separatorBuilder: (_, _) => const SizedBox(height: spacingSM),
                    itemBuilder: (BuildContext context, int index) {
                      return GtexSurfaceCard(
                        child: Text(history[index]),
                      );
                    },
                  ),
                  ListView.separated(
                    itemCount: federations.length,
                    separatorBuilder: (_, _) => const SizedBox(height: spacingSM),
                    itemBuilder: (BuildContext context, int index) {
                      final Federation federation = federations[index];
                      return GtexSurfaceCard(
                        child: ListTile(
                          contentPadding: EdgeInsets.zero,
                          title: Text(federation.name),
                          subtitle: Text(
                            '${federation.region} • Rank ${federation.ranking}\n${federation.focus}',
                          ),
                          trailing: Text('${federation.memberClubs} clubs'),
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
