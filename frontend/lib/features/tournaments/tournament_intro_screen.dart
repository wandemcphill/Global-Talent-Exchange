import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

import '../../core/constants/app_spacing.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/models/competition.dart';
import '../../shared/models/player.dart';
import 'tournament_models.dart';
import 'tournament_screen.dart';

class TournamentIntroScreen extends StatefulWidget {
  const TournamentIntroScreen({
    super.key,
    required this.competition,
    this.videoAssetPath,
    this.fixtures,
    this.standings,
    this.squad,
    this.onEnterTournament,
  });

  final Competition competition;
  final String? videoAssetPath;
  final List<TournamentFixture>? fixtures;
  final List<TournamentStanding>? standings;
  final List<Player>? squad;
  final VoidCallback? onEnterTournament;

  @override
  State<TournamentIntroScreen> createState() => _TournamentIntroScreenState();
}

class _TournamentIntroScreenState extends State<TournamentIntroScreen> {
  VideoPlayerController? _controller;
  bool _entered = false;
  bool _videoReady = false;

  @override
  void initState() {
    super.initState();
    _initializeVideo();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        setState(() => _entered = true);
      }
    });
  }

  Future<void> _initializeVideo() async {
    final String? videoAssetPath = widget.videoAssetPath;
    if (videoAssetPath == null || videoAssetPath.isEmpty) {
      return;
    }

    final VideoPlayerController controller = VideoPlayerController.asset(
      videoAssetPath,
    );

    try {
      await controller.initialize();
      await controller.setLooping(true);
      await controller.setVolume(0);
      await controller.play();

      if (!mounted) {
        controller.dispose();
        return;
      }

      setState(() {
        _controller = controller;
        _videoReady = true;
      });
    } catch (_) {
      await controller.dispose();
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  void _enterTournament() {
    if (widget.onEnterTournament != null) {
      widget.onEnterTournament!.call();
      return;
    }

    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (BuildContext context) {
          return TournamentScreen(
            competition: widget.competition,
            fixtures: widget.fixtures,
            standings: widget.standings,
            squad: widget.squad,
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final Competition competition = widget.competition;

    return Scaffold(
      body: Stack(
        fit: StackFit.expand,
        children: <Widget>[
          if (_videoReady && _controller != null)
            FittedBox(
              fit: BoxFit.cover,
              child: SizedBox(
                width: _controller!.value.size.width,
                height: _controller!.value.size.height,
                child: VideoPlayer(_controller!),
              ),
            )
          else
            const _TournamentPosterBackground(),
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: <Color>[
                    Colors.black.withValues(alpha: 0.18),
                    Colors.black.withValues(alpha: 0.3),
                    Colors.black.withValues(alpha: 0.74),
                  ],
                ),
              ),
            ),
          ),
          Positioned.fill(
            child: IgnorePointer(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: RadialGradient(
                    center: const Alignment(0, -0.35),
                    radius: 1.1,
                    colors: <Color>[
                      AppColors.primary.withValues(alpha: 0.08),
                      Colors.transparent,
                    ],
                  ),
                ),
              ),
            ),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(spacingLG),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Container(
                    width: 54,
                    height: 54,
                    padding: const EdgeInsets.all(spacingSM),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(18),
                      color: AppColors.card.withValues(alpha: 0.72),
                      border: Border.all(color: AppColors.divider),
                    ),
                    child: Image.asset('assets/branding/gtex_logo.png'),
                  ),
                  const Spacer(),
                  AnimatedSlide(
                    duration: const Duration(milliseconds: 420),
                    curve: Curves.easeOutCubic,
                    offset: _entered ? Offset.zero : const Offset(0, 0.08),
                    child: AnimatedOpacity(
                      duration: const Duration(milliseconds: 360),
                      opacity: _entered ? 1 : 0,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Wrap(
                            spacing: spacingSM,
                            runSpacing: spacingSM,
                            children: <Widget>[
                              _IntroPill(
                                label: competition.region.toUpperCase(),
                                highlight: false,
                              ),
                              _IntroPill(
                                label: competition.stage.toUpperCase(),
                                highlight: true,
                              ),
                            ],
                          ),
                          const SizedBox(height: spacingLG),
                          Text(
                            competition.name.toUpperCase(),
                            style: Theme.of(
                              context,
                            ).textTheme.headlineLarge?.copyWith(
                              fontSize: 42,
                              color: AppColors.textPrimary,
                              letterSpacing: 1.8,
                              height: 0.98,
                            ),
                          ),
                          const SizedBox(height: spacingMD),
                          Text(
                            competition.spotlight,
                            style: Theme.of(
                              context,
                            ).textTheme.bodyLarge?.copyWith(
                              color: AppColors.textPrimary.withValues(
                                alpha: 0.88,
                              ),
                            ),
                          ),
                          const SizedBox(height: spacingLG),
                          Text(
                            competition.nextFixture,
                            style: Theme.of(context).textTheme.titleLarge
                                ?.copyWith(color: AppColors.gold),
                          ),
                          const SizedBox(height: spacingLG),
                          FilledButton.icon(
                            key: const Key('tournament-enter-button'),
                            onPressed: _enterTournament,
                            icon: const Icon(Icons.play_arrow_rounded),
                            label: const Text('Enter Tournament'),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _TournamentPosterBackground extends StatelessWidget {
  const _TournamentPosterBackground();

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: <Widget>[
        const DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[
                Color(0xFF05111D),
                Color(0xFF10263F),
                Color(0xFF0B0F1A),
              ],
            ),
          ),
        ),
        Positioned(
          top: -80,
          right: -60,
          child: Container(
            width: 260,
            height: 260,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.primary.withValues(alpha: 0.18),
            ),
          ),
        ),
        Positioned(
          bottom: -90,
          left: -40,
          child: Container(
            width: 220,
            height: 220,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.gold.withValues(alpha: 0.12),
            ),
          ),
        ),
        Center(
          child: Opacity(
            opacity: 0.18,
            child: Padding(
              padding: const EdgeInsets.all(64),
              child: Image.asset('assets/branding/gtex_logo.png'),
            ),
          ),
        ),
      ],
    );
  }
}

class _IntroPill extends StatelessWidget {
  const _IntroPill({required this.label, required this.highlight});

  final String label;
  final bool highlight;

  @override
  Widget build(BuildContext context) {
    final Color color = highlight ? AppColors.gold : AppColors.primary;

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: spacingSM,
        vertical: spacingXS,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.34)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
          color: color,
          fontWeight: FontWeight.w700,
          letterSpacing: 1,
        ),
      ),
    );
  }
}
