import 'package:flutter/material.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_profile_dto.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_types.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class DynastyProgressTimeline extends StatelessWidget {
  const DynastyProgressTimeline({
    super.key,
    required this.profile,
  });

  final DynastyProfileDto profile;

  @override
  Widget build(BuildContext context) {
    final entries = profile.dynastyTimeline.isNotEmpty
        ? profile.dynastyTimeline.take(5).toList(growable: false)
        : const <DynastySnapshotDto>[];
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Dynasty progression timeline',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            'Era checkpoints that turned form into legacy.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 18),
          if (entries.isEmpty)
            Text(
              'The timeline will populate once the club has enough seasons on record.',
              style: Theme.of(context).textTheme.bodyMedium,
            )
          else
            Column(
              children: entries.map((DynastySnapshotDto snapshot) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: 14),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Column(
                        children: <Widget>[
                          Container(
                            width: 12,
                            height: 12,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: snapshot.activeDynasty
                                  ? GteShellTheme.accentWarm
                                  : GteShellTheme.accent,
                            ),
                          ),
                          if (snapshot != entries.last)
                            Container(
                              width: 2,
                              height: 50,
                              color: GteShellTheme.stroke,
                            ),
                        ],
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(
                              snapshot.metrics.windowEndSeasonLabel,
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                            const SizedBox(height: 4),
                            Text(
                              _labelForEra(snapshot.eraLabel),
                              style: Theme.of(context).textTheme.bodyLarge,
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Dynasty score ${snapshot.dynastyScore}',
                              style: Theme.of(context).textTheme.bodyMedium,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              }).toList(growable: false),
            ),
        ],
      ),
    );
  }
}

String _labelForEra(DynastyEraType value) {
  switch (value) {
    case DynastyEraType.emergingPower:
      return 'Emerging Power';
    case DynastyEraType.dominantEra:
      return 'Dominant Era';
    case DynastyEraType.continentalDynasty:
      return 'Continental Dynasty';
    case DynastyEraType.globalDynasty:
      return 'Global Dynasty';
    case DynastyEraType.fallenGiant:
      return 'Fallen Giant';
    case DynastyEraType.none:
      return 'No Active Dynasty';
  }
}
