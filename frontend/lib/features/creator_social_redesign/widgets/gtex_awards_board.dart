import 'package:flutter/material.dart';

import '../models/gtex_creator_social_models.dart';
import 'gtex_creator_social_visuals.dart';

class GtexAwardsBoard extends StatelessWidget {
  const GtexAwardsBoard({
    super.key,
    required this.seasons,
    required this.nominees,
  });

  final List<GtexAwardSeason> seasons;
  final List<GtexAwardNominee> nominees;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        GtexPanel(
          child: Row(
            children: [
              Container(
                height: 76,
                width: 76,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    colors: [
                      gtexCreatorGold,
                      gtexCreatorGreen.withOpacity(.85),
                    ],
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: gtexCreatorGold.withOpacity(.26),
                      blurRadius: 32,
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.workspace_premium_rounded,
                  color: Colors.black,
                  size: 40,
                ),
              ),
              const SizedBox(width: 18),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'GTEX Awards',
                      style: TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.w900,
                        color: Colors.white,
                      ),
                    ),
                    SizedBox(height: 6),
                    Text(
                      'Recognize players, regens, clubs, creators, and national-team moments across the living GTEX football universe.',
                      style: TextStyle(color: gtexCreatorTextSoft),
                    ),
                  ],
                ),
              ),
              const GtexPill(label: 'Voting open', color: gtexCreatorGold),
            ],
          ),
        ),
        const SizedBox(height: 14),
        ...seasons.map(
          (season) => Padding(
            padding: const EdgeInsets.only(bottom: 14),
            child: GtexPanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          season.title,
                          style: const TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.w900,
                            color: Colors.white,
                          ),
                        ),
                      ),
                      GtexPill(label: season.status),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    season.periodLabel,
                    style: const TextStyle(color: gtexCreatorTextSoft),
                  ),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(height: 4),
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
            maxCrossAxisExtent: 340,
            mainAxisExtent: 226,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
          ),
          itemCount: nominees.length,
          itemBuilder:
              (context, index) => _NomineeCard(nominee: nominees[index]),
        ),
      ],
    );
  }
}

class _NomineeCard extends StatelessWidget {
  const _NomineeCard({required this.nominee});

  final GtexAwardNominee nominee;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              CircleAvatar(
                radius: 26,
                backgroundColor: gtexCreatorGreen.withOpacity(.15),
                child: const Icon(
                  Icons.person_rounded,
                  color: gtexCreatorGreen,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      nominee.name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    Text(
                      nominee.badgeLabel ?? 'Nominee',
                      style: const TextStyle(
                        color: gtexCreatorGold,
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ],
                ),
              ),
              Text(
                nominee.scoreLabel,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 22,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Text(
            nominee.subtitle,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(color: gtexCreatorTextSoft),
          ),
          const Spacer(),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text(
                          '${nominee.name} vote capture requires the live awards ballot endpoint.',
                        ),
                      ),
                    );
                  },
                  icon: const Icon(Icons.how_to_vote_rounded, size: 16),
                  label: const Text('Vote'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: gtexCreatorGreen,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              IconButton(
                onPressed: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(
                        '${nominee.name} detail opens once the awards route publishes a nominee id.',
                      ),
                    ),
                  );
                },
                icon: const Icon(
                  Icons.open_in_new_rounded,
                  color: Colors.white70,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
