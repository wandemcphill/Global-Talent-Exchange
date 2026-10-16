import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/app_spacing.dart';
import '../../core/widgets/gtex_surface_card.dart';
import '../../shared/models/federation.dart';
import '../../shared/providers/regen_provider.dart';
import '../../shared/widgets/section_heading.dart';

class FederationScreen extends ConsumerWidget {
  const FederationScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final List<Federation> federations = ref.watch(federationsProvider);

    return ListView.separated(
      padding: const EdgeInsets.all(spacingMD),
      itemCount: federations.length + 1,
      separatorBuilder: (_, _) => const SizedBox(height: spacingSM),
      itemBuilder: (BuildContext context, int index) {
        if (index == 0) {
          return const SectionHeading(
            title: 'Federation',
            subtitle: 'Governance, regional focus, and competition stewardship.',
          );
        }
        final Federation federation = federations[index - 1];
        return GtexSurfaceCard(
          child: ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(federation.name),
            subtitle: Text(
              '${federation.region} • Rank ${federation.ranking}\n${federation.focus}',
            ),
            trailing: Text('${federation.memberClubs}'),
          ),
        );
      },
    );
  }
}
