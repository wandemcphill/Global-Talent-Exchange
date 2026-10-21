import 'package:flutter/material.dart';

import 'gtex_home_models.dart';
import 'gtex_home_shared_widgets.dart';

class GtexLivingWorldSection extends StatefulWidget {
  const GtexLivingWorldSection({super.key});

  @override
  State<GtexLivingWorldSection> createState() => _GtexLivingWorldSectionState();
}

class _GtexLivingWorldSectionState extends State<GtexLivingWorldSection> {
  void _inspectArticle(NewsroomArticleItem article) {
    showDialog<void>(
      context: context,
      builder: (BuildContext dialogContext) => _GroundedFactsDialog(article: article),
    );
  }

  @override
  Widget build(BuildContext context) {
    final double width = MediaQuery.sizeOf(context).width;
    final bool isNarrow = width < 760;

    return Container(
      color: kNavyInset,
      padding: EdgeInsets.symmetric(
        horizontal: isNarrow ? 20 : 64,
        vertical: 64,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          // Section Heading
          const GtexSectionHeader(
            eyebrow: 'A Living Football World',
            title: 'Event-Driven Football & Global Broadcasts',
            subtitle: 'The GTEX universe never sleeps. Authenticated platform events, executive purchases, and matchday drama generate grounded football newsrooms and public broadcasts in real-time.',
            accentColor: kSkyBlue,
          ),

          const SizedBox(height: 32),

          // Global Broadcast Ticker Bar
          _GlobalBroadcastTicker(isNarrow: isNarrow),

          const SizedBox(height: 44),

          // Newsroom Header (Adaptive Wrap)
          Wrap(
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: 12,
            runSpacing: 6,
            children: <Widget>[
              Wrap(
                crossAxisAlignment: WrapCrossAlignment.center,
                spacing: 8,
                children: const <Widget>[
                  Icon(Icons.newspaper_rounded, color: kGoldPrimary, size: 20),
                  Text(
                    'AI-GROUNDED EDITORIAL NEWSROOM',
                    style: TextStyle(
                      color: kGoldPrimary,
                      fontSize: 14,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.5,
                      fontFamily: kFontCondensed,
                    ),
                  ),
                ],
              ),
              const Text(
                'FACTS SEPARATED FROM NARRATION',
                style: TextStyle(
                  color: kTextTertiary,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1,
                  fontFamily: kFontCondensed,
                ),
              ),
            ],
          ),

          const SizedBox(height: 16),

          // Editorial Articles Responsive Grid
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final int columns = constraints.maxWidth > 950 ? 3 : (constraints.maxWidth > 600 ? 2 : 1);
              final double cardWidth = (constraints.maxWidth - ((columns - 1) * 16)) / columns;

              return Wrap(
                spacing: 16,
                runSpacing: 16,
                children: kVerifiedArticles.map((NewsroomArticleItem article) {
                  return SizedBox(
                    width: cardWidth,
                    child: _NewsroomCard(
                      article: article,
                      onInspect: () => _inspectArticle(article),
                    ),
                  );
                }).toList(),
              );
            },
          ),
        ],
      ),
    );
  }
}

class _GlobalBroadcastTicker extends StatelessWidget {
  const _GlobalBroadcastTicker({required this.isNarrow});

  final bool isNarrow;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: kNavyRaised,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: kNavyLineStrong),
        boxShadow: const <BoxShadow>[
          BoxShadow(
            color: Color(0x33000000),
            blurRadius: 16,
            offset: Offset(0, 4),
          ),
        ],
      ),
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Wrap(
            spacing: 10,
            runSpacing: 6,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: const <Widget>[
              GtexTagPill(
                label: 'VERIFIED BROADCAST TICKER',
                color: kPitchGreenBright,
                icon: Icons.sensors_rounded,
              ),
              Text(
                'Major platform events trigger public announcements with verified price tags',
                style: TextStyle(
                  color: kTextTertiary,
                  fontSize: 11,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          // Verified platform broadcast events
          Wrap(
            spacing: 12,
            runSpacing: 10,
            children: const <Widget>[
              _TickerItem(
                icon: Icons.flight_takeoff_rounded,
                headline: 'Sovereign 900X Private Jet Commissioned',
                price: '4,800.00 GTX',
                owner: 'Executive Suite',
                time: '24m ago',
              ),
              _TickerItem(
                icon: Icons.stadium_rounded,
                headline: 'Arena Imperiale Expansion Complete (65k Seats)',
                price: '12,500.00 GTX',
                owner: 'Continental Board',
                time: '1h ago',
              ),
              _TickerItem(
                icon: Icons.watch_rounded,
                headline: 'Chronos Tourbillon Gifted to Mateo Alvarez',
                price: '20,000.00 GTX',
                owner: 'Club Owner',
                time: '3h ago',
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _TickerItem extends StatelessWidget {
  const _TickerItem({
    required this.icon,
    required this.headline,
    required this.price,
    required this.owner,
    required this.time,
  });

  final IconData icon;
  final String headline;
  final String price;
  final String owner;
  final String time;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(maxWidth: 380),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: kNavyOverlay,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: kNavyLine),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(icon, size: 16, color: kGoldPrimary),
          const SizedBox(width: 8),
          Flexible(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Text(
                  headline,
                  style: const TextStyle(
                    color: kTextPrimary,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    Text(
                      price,
                      style: const TextStyle(
                        color: kGoldLight,
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                        fontFamily: kFontMono,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Flexible(
                      child: Text(
                        'by $owner • $time',
                        style: const TextStyle(
                          color: kTextTertiary,
                          fontSize: 10,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _NewsroomCard extends StatelessWidget {
  const _NewsroomCard({
    required this.article,
    required this.onInspect,
  });

  final NewsroomArticleItem article;
  final VoidCallback onInspect;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: kNavyRaised,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: kNavyLine),
      ),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Wrap(
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: 8,
            runSpacing: 4,
            children: <Widget>[
              GtexTagPill(
                label: article.category,
                color: kGoldPrimary,
              ),
              Text(
                article.timeAgo,
                style: const TextStyle(
                  color: kTextTertiary,
                  fontSize: 11,
                  fontFamily: kFontMono,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Text(
            article.headline,
            style: const TextStyle(
              color: kTextPrimary,
              fontSize: 18,
              fontWeight: FontWeight.w800,
              height: 1.25,
              fontFamily: kFontCondensed,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            article.subheadline,
            style: const TextStyle(
              color: kTextSecondary,
              fontSize: 13,
              height: 1.45,
            ),
          ),
          const SizedBox(height: 16),
          // Verified Facts Snippet Preview
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: kNavyInset,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: kNavyLine),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: const <Widget>[
                    Icon(Icons.check_circle_outline_rounded, size: 14, color: kPitchGreenBright),
                    SizedBox(width: 6),
                    Text(
                      'ESTABLISHED FACTS',
                      style: TextStyle(
                        color: kPitchGreenBright,
                        fontSize: 10,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 1,
                        fontFamily: kFontCondensed,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  article.establishedFacts.first,
                  style: const TextStyle(
                    color: kTextSecondary,
                    fontSize: 11,
                    fontFamily: kFontMono,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          InkWell(
            onTap: onInspect,
            borderRadius: BorderRadius.circular(8),
            child: Wrap(
              crossAxisAlignment: WrapCrossAlignment.center,
              spacing: 6,
              children: const <Widget>[
                Text(
                  'Inspect Grounded Story & Facts',
                  style: TextStyle(
                    color: kSkyBlue,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Icon(Icons.arrow_forward_rounded, size: 14, color: kSkyBlue),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _GroundedFactsDialog extends StatelessWidget {
  const _GroundedFactsDialog({required this.article});

  final NewsroomArticleItem article;

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: kNavyRaised,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: const BorderSide(color: kNavyLineStrong, width: 1.5),
      ),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 620, maxHeight: 680),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    GtexTagPill(label: article.category, color: kGoldPrimary),
                    const Spacer(),
                    IconButton(
                      icon: const Icon(Icons.close_rounded, color: kTextSecondary),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                Text(
                  article.headline,
                  style: const TextStyle(
                    color: kTextPrimary,
                    fontSize: 22,
                    fontWeight: FontWeight.w900,
                    letterSpacing: -0.5,
                    fontFamily: kFontCondensed,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  article.subheadline,
                  style: const TextStyle(
                    color: kTextSecondary,
                    fontSize: 13,
                    height: 1.4,
                  ),
                ),
                const SizedBox(height: 18),
                const Divider(color: kNavyLine),
                const SizedBox(height: 14),

                // Established Facts Block
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: kNavyInset,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: kPitchGreen.withValues(alpha: 0.3)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Row(
                        children: const <Widget>[
                          Icon(Icons.verified_rounded, size: 16, color: kPitchGreenBright),
                          SizedBox(width: 8),
                          Text(
                            'ESTABLISHED PLATFORM FACTS (READ-ONLY)',
                            style: TextStyle(
                              color: kPitchGreenBright,
                              fontSize: 11,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 1.2,
                              fontFamily: kFontCondensed,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      ...article.establishedFacts.map((String fact) => Padding(
                            padding: const EdgeInsets.symmetric(vertical: 3),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                const Text('• ', style: TextStyle(color: kPitchGreenBright, fontSize: 13)),
                                Expanded(
                                  child: Text(
                                    fact,
                                    style: const TextStyle(
                                      color: kTextPrimary,
                                      fontSize: 12,
                                      fontFamily: kFontMono,
                                      height: 1.4,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          )),
                    ],
                  ),
                ),

                const SizedBox(height: 18),

                // AI Grounded Editorial Narration
                const Text(
                  'EDITORIAL NARRATION',
                  style: TextStyle(
                    color: kGoldPrimary,
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.2,
                    fontFamily: kFontCondensed,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  article.editorialNarration,
                  style: const TextStyle(
                    color: kTextSecondary,
                    fontSize: 13,
                    height: 1.55,
                  ),
                ),

                const SizedBox(height: 20),

                Align(
                  alignment: Alignment.centerRight,
                  child: GtexGhostButton(
                    label: 'Close Inspection',
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
