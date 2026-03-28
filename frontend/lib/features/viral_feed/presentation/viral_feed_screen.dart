import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../data/viral_feed_models.dart';
import '../data/viral_feed_repository.dart';

class ViralFeedScreen extends StatefulWidget {
  const ViralFeedScreen({super.key, ViralFeedRepository? repository})
    : _repository = repository;

  final ViralFeedRepository? _repository;

  @override
  State<ViralFeedScreen> createState() => _ViralFeedScreenState();
}

class _ViralFeedScreenState extends State<ViralFeedScreen> {
  late final ViralFeedRepository _repository;
  late Future<ViralFeedDeck> _deckFuture;
  int _pageIndex = 0;

  @override
  void initState() {
    super.initState();
    _repository = widget._repository ?? ViralFeedApiRepository.standard();
    _deckFuture = _repository.fetchDeck();
  }

  void _reload() {
    setState(() {
      _deckFuture = _repository.fetchDeck();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: FutureBuilder<ViralFeedDeck>(
        future: _deckFuture,
        builder: (BuildContext context, AsyncSnapshot<ViralFeedDeck> snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const _LoadingState();
          }
          if (!snapshot.hasData || snapshot.data!.clips.isEmpty) {
            return _EmptyState(onRetry: _reload);
          }
          final ViralFeedDeck deck = snapshot.data!;
          return PageView.builder(
            key: const Key('viral-feed-page-view'),
            scrollDirection: Axis.vertical,
            itemCount: deck.clips.length,
            onPageChanged: (int index) {
              setState(() {
                _pageIndex = index;
              });
            },
            itemBuilder: (BuildContext context, int index) {
              final ViralClip clip = deck.clips[index];
              return _ViralClipPage(
                clip: clip,
                debate: deck.debatesByMatch[clip.matchId],
                index: index,
                total: deck.clips.length,
                isActive: index == _pageIndex,
              );
            },
          );
        },
      ),
    );
  }
}

class _ViralClipPage extends StatelessWidget {
  const _ViralClipPage({
    required this.clip,
    required this.index,
    required this.total,
    required this.isActive,
    this.debate,
  });

  final ViralClip clip;
  final PunditDebate? debate;
  final int index;
  final int total;
  final bool isActive;

  @override
  Widget build(BuildContext context) {
    final List<Color> palette = _paletteFor(clip.eventType);
    final ThemeData theme = Theme.of(context);
    final List<PunditDebateLine> visibleLines =
        debate?.lines.take(2).toList(growable: false) ??
        const <PunditDebateLine>[];
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: palette,
        ),
      ),
      child: Stack(
        fit: StackFit.expand,
        children: <Widget>[
          const _BackdropTexture(),
          SafeArea(
            child: LayoutBuilder(
              builder: (BuildContext context, BoxConstraints constraints) {
                return SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
                  child: ConstrainedBox(
                    constraints: BoxConstraints(
                      minHeight: constraints.maxHeight,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Row(
                          children: <Widget>[
                            IconButton(
                              onPressed: () => Navigator.of(context).maybePop(),
                              icon: const Icon(
                                Icons.arrow_back_ios_new_rounded,
                              ),
                              color: AppColors.textPrimary,
                            ),
                            const SizedBox(width: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 12,
                                vertical: 8,
                              ),
                              decoration: BoxDecoration(
                                color: Colors.black.withValues(alpha: 0.28),
                                borderRadius: BorderRadius.circular(999),
                                border: Border.all(
                                  color: Colors.white.withValues(alpha: 0.12),
                                ),
                              ),
                              child: Text(
                                'FOR YOU',
                                style: theme.textTheme.bodySmall?.copyWith(
                                  color: AppColors.primary,
                                  fontWeight: FontWeight.w800,
                                  letterSpacing: 1.4,
                                ),
                              ),
                            ),
                            const Spacer(),
                            Text(
                              '${index + 1}/$total',
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: AppColors.textPrimary,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: <Widget>[
                            _MetaChip(label: "${clip.minute}'"),
                            if (clip.teamName != null)
                              _MetaChip(label: clip.teamName!.toUpperCase()),
                            if (clip.scorelineLabel != null)
                              _MetaChip(label: clip.scorelineLabel!),
                          ],
                        ),
                        const SizedBox(height: 24),
                        Text(
                          clip.caption.hook,
                          key: Key('viral-hook-${clip.highlightId}'),
                          style: theme.textTheme.headlineLarge?.copyWith(
                            fontSize: 34,
                            fontWeight: FontWeight.w900,
                            height: 0.98,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          clip.title,
                          style: theme.textTheme.titleLarge?.copyWith(
                            color: Colors.white.withValues(alpha: 0.9),
                          ),
                        ),
                        const SizedBox(height: 24),
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: <Widget>[
                                  _StageCard(
                                    clip: clip,
                                    debate: debate,
                                    visibleLines: visibleLines,
                                  ),
                                  const SizedBox(height: 18),
                                  Text(
                                    clip.caption.caption,
                                    style: theme.textTheme.bodyLarge,
                                  ),
                                  const SizedBox(height: 10),
                                  Wrap(
                                    spacing: 8,
                                    runSpacing: 8,
                                    children: clip.caption.hashtags
                                        .map(
                                          (String hashtag) => Text(
                                            hashtag,
                                            style: theme.textTheme.bodySmall
                                                ?.copyWith(
                                                  color: AppColors.primary,
                                                  fontWeight: FontWeight.w700,
                                                ),
                                          ),
                                        )
                                        .toList(growable: false),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: 18),
                            _ActionRail(clip: clip, isActive: isActive),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _StageCard extends StatelessWidget {
  const _StageCard({
    required this.clip,
    required this.visibleLines,
    this.debate,
  });

  final ViralClip clip;
  final PunditDebate? debate;
  final List<PunditDebateLine> visibleLines;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Container(
      constraints: const BoxConstraints(minHeight: 320),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        color: Colors.black.withValues(alpha: 0.24),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.24),
            blurRadius: 32,
            offset: const Offset(0, 18),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              children: <Widget>[
                Container(
                  width: 54,
                  height: 54,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: AppColors.primary.withValues(alpha: 0.18),
                  ),
                  child: Icon(
                    _iconFor(clip.eventType),
                    color: AppColors.primary,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Text(
                    clip.playerName == null
                        ? clip.title
                        : '${clip.playerName} • ${clip.title}',
                    style: theme.textTheme.titleLarge,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 18),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Row(
                children: <Widget>[
                  const Icon(Icons.play_circle_fill_rounded, size: 20),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      clip.videoUrl == null
                          ? 'Vertical render ready. Playback source attaches when the clip CDN is available.'
                          : 'Playback source connected. This card can hand off to the actual video player next.',
                      style: theme.textTheme.bodyMedium,
                    ),
                  ),
                ],
              ),
            ),
            if (debate != null) ...<Widget>[
              const SizedBox(height: 18),
              Text(
                debate!.headline,
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
            if (visibleLines.isNotEmpty) ...<Widget>[
              const SizedBox(height: 12),
              ...visibleLines.map(
                (PunditDebateLine line) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: RichText(
                    text: TextSpan(
                      style: theme.textTheme.bodyMedium,
                      children: <InlineSpan>[
                        TextSpan(
                          text: '${line.speaker}: ',
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color: AppColors.gold,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        TextSpan(text: line.line),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ActionRail extends StatelessWidget {
  const _ActionRail({required this.clip, required this.isActive});

  final ViralClip clip;
  final bool isActive;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return SizedBox(
      width: 96,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.end,
        children: <Widget>[
          _ActionBubble(
            icon: Icons.local_fire_department_rounded,
            label: '${clip.viralScore}',
            active: isActive,
          ),
          const SizedBox(height: 16),
          _ActionBubble(
            icon: Icons.share_rounded,
            label: clip.caption.cta,
            active: true,
          ),
          const SizedBox(height: 16),
          const _ActionBubble(
            icon: Icons.stadium_rounded,
            label: 'Debate',
            active: false,
          ),
          const SizedBox(height: 20),
          Text(
            clip.shareChannel.toUpperCase(),
            style: theme.textTheme.bodySmall?.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.0,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

class _ActionBubble extends StatelessWidget {
  const _ActionBubble({
    required this.icon,
    required this.label,
    required this.active,
  });

  final IconData icon;
  final String label;
  final bool active;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Column(
      children: <Widget>[
        Container(
          width: 60,
          height: 60,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color:
                active
                    ? AppColors.primary.withValues(alpha: 0.2)
                    : Colors.white.withValues(alpha: 0.08),
            border: Border.all(
              color:
                  active
                      ? AppColors.primary.withValues(alpha: 0.34)
                      : Colors.white.withValues(alpha: 0.12),
            ),
          ),
          child: Icon(
            icon,
            color: active ? AppColors.primary : AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          label,
          style: theme.textTheme.bodySmall?.copyWith(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w700,
          ),
          textAlign: TextAlign.center,
        ),
      ],
    );
  }
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.24),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
          color: AppColors.textPrimary,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.8,
        ),
      ),
    );
  }
}

class _BackdropTexture extends StatelessWidget {
  const _BackdropTexture();

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(child: CustomPaint(painter: _BackdropPainter()));
  }
}

class _BackdropPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final Paint glowPaint = Paint()..style = PaintingStyle.fill;
    final List<Offset> centers = <Offset>[
      Offset(size.width * 0.18, size.height * 0.22),
      Offset(size.width * 0.84, size.height * 0.34),
      Offset(size.width * 0.42, size.height * 0.82),
    ];
    final List<Color> colors = <Color>[
      AppColors.primary.withValues(alpha: 0.08),
      AppColors.gold.withValues(alpha: 0.08),
      Colors.white.withValues(alpha: 0.04),
    ];
    for (int i = 0; i < centers.length; i += 1) {
      glowPaint.color = colors[i];
      canvas.drawCircle(
        centers[i],
        size.shortestSide * (0.22 + (i * 0.03)),
        glowPaint,
      );
    }

    final Paint linePaint =
        Paint()
          ..color = Colors.white.withValues(alpha: 0.04)
          ..strokeWidth = 1;
    for (double y = 0; y < size.height; y += 56) {
      final Path path = Path()..moveTo(0, y);
      for (double x = 0; x <= size.width; x += 28) {
        path.lineTo(x, y + math.sin((x + y) / 80) * 4);
      }
      canvas.drawPath(path, linePaint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _LoadingState extends StatelessWidget {
  const _LoadingState();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: CircularProgressIndicator(color: AppColors.primary),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            const Icon(
              Icons.video_collection_outlined,
              color: AppColors.textSecondary,
              size: 48,
            ),
            const SizedBox(height: 12),
            Text(
              'No clips ready yet',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              'The viral engine will surface ranked highlights here as soon as the backend has replay payloads to work with.',
              style: Theme.of(context).textTheme.bodyMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            FilledButton(onPressed: onRetry, child: const Text('Retry')),
          ],
        ),
      ),
    );
  }
}

List<Color> _paletteFor(String eventType) {
  switch (eventType.toLowerCase()) {
    case 'goal':
    case 'penalty_scored':
      return const <Color>[
        Color(0xFF170C1F),
        Color(0xFF5C162E),
        Color(0xFFF59E0B),
      ];
    case 'double_save':
    case 'goalkeeper_save':
      return const <Color>[
        Color(0xFF071A22),
        Color(0xFF0A495B),
        Color(0xFF2DD4BF),
      ];
    default:
      return const <Color>[
        Color(0xFF0B1020),
        Color(0xFF1B2440),
        Color(0xFF5B6CB8),
      ];
  }
}

IconData _iconFor(String eventType) {
  switch (eventType.toLowerCase()) {
    case 'goal':
    case 'penalty_scored':
      return Icons.sports_soccer_rounded;
    case 'double_save':
    case 'goalkeeper_save':
      return Icons.pan_tool_alt_rounded;
    default:
      return Icons.bolt_rounded;
  }
}
