import 'package:flutter/material.dart';

import '../models/gtex_creator_social_models.dart';
import 'gtex_creator_social_visuals.dart';

class GtexSocialFeedPanel extends StatelessWidget {
  const GtexSocialFeedPanel({super.key, required this.stories, required this.followedClubs, required this.referral});

  final List<GtexSocialStory> stories;
  final List<GtexFollowedClub> followedClubs;
  final GtexReferralSnapshot referral;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          flex: 3,
          child: Column(
            children: stories.map((story) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _StoryCard(story: story),
            )).toList(),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          flex: 2,
          child: Column(
            children: [
              _FollowedClubsPanel(clubs: followedClubs),
              const SizedBox(height: 12),
              _ReferralPanel(referral: referral),
            ],
          ),
        ),
      ],
    );
  }
}

class _StoryCard extends StatelessWidget {
  const _StoryCard({required this.story});

  final GtexSocialStory story;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              GtexPill(label: story.sourceLabel),
              const Spacer(),
              Text(story.timeLabel, style: const TextStyle(color: gtexCreatorTextSoft, fontSize: 12)),
            ],
          ),
          const SizedBox(height: 12),
          Text(story.title, style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900)),
          const SizedBox(height: 8),
          Text(story.body, style: const TextStyle(color: gtexCreatorTextSoft, height: 1.45)),
          const SizedBox(height: 14),
          Row(
            children: [
              if (story.clubLabel != null) GtexPill(label: story.clubLabel!, color: gtexCreatorGold),
              const Spacer(),
              Text(story.reactionLabel, style: const TextStyle(color: Colors.white70, fontWeight: FontWeight.w700)),
              const SizedBox(width: 8),
              const Icon(Icons.favorite_rounded, color: gtexCreatorGreen, size: 18),
            ],
          ),
        ],
      ),
    );
  }
}

class _FollowedClubsPanel extends StatelessWidget {
  const _FollowedClubsPanel({required this.clubs});

  final List<GtexFollowedClub> clubs;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Followed clubs', style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900)),
          const SizedBox(height: 12),
          ...clubs.map((club) => Container(
                margin: const EdgeInsets.only(bottom: 10),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF101B2C),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(club.name, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900)),
                    const SizedBox(height: 4),
                    Text(club.ownerLabel, style: const TextStyle(color: gtexCreatorTextSoft, fontSize: 12)),
                    const SizedBox(height: 8),
                    Row(children: [
                      Expanded(child: Text(club.valueLabel, style: const TextStyle(color: Colors.white70, fontSize: 12))),
                      Text(club.sharePriceLabel, style: const TextStyle(color: gtexCreatorGold, fontWeight: FontWeight.w900)),
                    ]),
                  ],
                ),
              )),
        ],
      ),
    );
  }
}

class _ReferralPanel extends StatelessWidget {
  const _ReferralPanel({required this.referral});

  final GtexReferralSnapshot referral;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Referral engine', style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900)),
          const SizedBox(height: 12),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: gtexCreatorGreen.withOpacity(.10),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: gtexCreatorGreen.withOpacity(.25)),
            ),
            child: Text(referral.code, style: const TextStyle(color: gtexCreatorGreen, fontWeight: FontWeight.w900, letterSpacing: 1.1)),
          ),
          const SizedBox(height: 12),
          Text(referral.invitesLabel, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800)),
          Text(referral.rewardsLabel, style: const TextStyle(color: gtexCreatorGold, fontWeight: FontWeight.w800)),
          Text(referral.pendingLabel, style: const TextStyle(color: gtexCreatorTextSoft)),
        ],
      ),
    );
  }
}
