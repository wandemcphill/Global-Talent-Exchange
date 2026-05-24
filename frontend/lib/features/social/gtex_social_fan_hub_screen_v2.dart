import 'package:flutter/material.dart';

import '../creator_social_redesign/models/gtex_creator_social_models.dart';
import '../creator_social_redesign/presentation/gtex_creator_social_controller.dart';
import '../creator_social_redesign/widgets/gtex_creator_social_visuals.dart';
import '../creator_social_redesign/widgets/gtex_social_feed_panel.dart';

class GtexSocialFanHubScreenV2 extends StatefulWidget {
  const GtexSocialFanHubScreenV2({
    super.key,
    this.snapshot,
    this.allowFixtureData = false,
  });

  final GtexCreatorSocialSnapshot? snapshot;
  final bool allowFixtureData;

  @override
  State<GtexSocialFanHubScreenV2> createState() =>
      _GtexSocialFanHubScreenV2State();
}

class _GtexSocialFanHubScreenV2State extends State<GtexSocialFanHubScreenV2> {
  late final GtexCreatorSocialController controller;

  @override
  void initState() {
    super.initState();
    controller = GtexCreatorSocialController(
      snapshot: widget.snapshot,
      allowFixtureData: widget.allowFixtureData,
    );
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder:
          (context, _) => Scaffold(
            backgroundColor: gtexCreatorBg,
            body: SafeArea(
              child:
                  controller.hasLiveSnapshot
                      ? LayoutBuilder(
                        builder: (context, constraints) {
                          final isWide = constraints.maxWidth >= 1040;
                          return Row(
                            children: [
                              if (isWide)
                                SizedBox(
                                  width: 320,
                                  child: _SocialLeftPanel(
                                    controller: controller,
                                  ),
                                ),
                              Expanded(
                                child: SingleChildScrollView(
                                  padding: const EdgeInsets.all(22),
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      const Text(
                                        'GTEX Fan Hub',
                                        style: TextStyle(
                                          color: Colors.white,
                                          fontSize: 34,
                                          fontWeight: FontWeight.w900,
                                        ),
                                      ),
                                      const SizedBox(height: 6),
                                      const Text(
                                        'Follow clubs, react to AI football stories, join fan wars, track shares, and invite new managers.',
                                        style: TextStyle(
                                          color: gtexCreatorTextSoft,
                                        ),
                                      ),
                                      const SizedBox(height: 18),
                                      GtexSocialFeedPanel(
                                        stories: controller.stories,
                                        followedClubs:
                                            controller.snapshot.followedClubs,
                                        referral: controller.snapshot.referral,
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ],
                          );
                        },
                      )
                      : const _FanHubBlockedState(),
            ),
          ),
    );
  }
}

class _FanHubBlockedState extends StatelessWidget {
  const _FanHubBlockedState();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Padding(
        padding: EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.forum_outlined, color: gtexCreatorGreen, size: 44),
            SizedBox(height: 14),
            Text(
              'Live fan hub unavailable',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white,
                fontSize: 24,
                fontWeight: FontWeight.w900,
              ),
            ),
            SizedBox(height: 8),
            Text(
              'Fan stories, followed clubs, referrals, and reactions require the live community backend.',
              textAlign: TextAlign.center,
              style: TextStyle(color: gtexCreatorTextSoft),
            ),
          ],
        ),
      ),
    );
  }
}

class _SocialLeftPanel extends StatelessWidget {
  const _SocialLeftPanel({required this.controller});

  final GtexCreatorSocialController controller;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF090F19),
        border: Border(right: BorderSide(color: Colors.white.withOpacity(.07))),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Community',
            style: TextStyle(
              color: Colors.white,
              fontSize: 25,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            onChanged: controller.updateSearch,
            style: const TextStyle(color: Colors.white),
            decoration: InputDecoration(
              hintText: 'Search clubs, stories...',
              hintStyle: const TextStyle(color: Colors.white38),
              prefixIcon: const Icon(
                Icons.search_rounded,
                color: Colors.white54,
              ),
              filled: true,
              fillColor: const Color(0xFF101B2C),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(18),
                borderSide: BorderSide.none,
              ),
            ),
          ),
          const SizedBox(height: 14),
          ...GtexSocialModule.values.map((module) {
            final label = switch (module) {
              GtexSocialModule.feed => 'Live feed',
              GtexSocialModule.followedClubs => 'Followed clubs',
              GtexSocialModule.fanWars => 'Fan wars',
              GtexSocialModule.referrals => 'Referrals',
              GtexSocialModule.shares => 'Shares',
              GtexSocialModule.community => 'Community',
            };
            final selected = controller.socialModule == module;
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: ListTile(
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
                selected: selected,
                selectedTileColor: gtexCreatorGreen.withOpacity(.11),
                onTap: () => controller.selectSocialModule(module),
                title: Text(
                  label,
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                trailing: Icon(
                  Icons.chevron_right_rounded,
                  color: selected ? gtexCreatorGreen : Colors.white38,
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}
