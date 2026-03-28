import 'package:flutter/material.dart';

import '../../core/constants/app_spacing.dart';
import '../../core/widgets/gtex_surface_card.dart';
import '../../shared/widgets/section_heading.dart';

class SocialScreen extends StatelessWidget {
  const SocialScreen({super.key});

  @override
  Widget build(BuildContext context) {
    const List<(String, String)> feed = <(String, String)>[
      (
        'Fans react to the new academy drop',
        'Engagement is up 18% after the teaser post and matchday tunnel clip.',
      ),
      (
        'Creator League highlights are trending',
        'Three creators crossed the one-million replay mark in the last 24 hours.',
      ),
      (
        'Club challenge issued',
        'Rival clubs are calling for a regen showdown before the transfer window closes.',
      ),
    ];

    return ListView.separated(
      padding: const EdgeInsets.all(spacingMD),
      itemCount: feed.length + 1,
      separatorBuilder: (_, _) => const SizedBox(height: spacingSM),
      itemBuilder: (BuildContext context, int index) {
        if (index == 0) {
          return const SectionHeading(
            title: 'Social',
            subtitle: 'Momentum loops, creator traction, and fan sentiment.',
          );
        }
        final (String, String) item = feed[index - 1];
        return GtexSurfaceCard(
          child: ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(item.$1),
            subtitle: Text(item.$2),
          ),
        );
      },
    );
  }
}
