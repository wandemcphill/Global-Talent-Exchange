import 'dart:ui';

import 'package:flutter/material.dart';

import '../../ui_gtex/components/gtex_button.dart';
import '../../ui_gtex/theme/gtex_colors.dart';
import '../../ui_gtex/theme/gtex_spacing.dart';

class GtexPublicLandingScreenV2 extends StatefulWidget {
  const GtexPublicLandingScreenV2({
    super.key,
    this.onSignup,
    this.onLogin,
    this.onCreatorSignup,
    this.onExploreMarket,
  });

  final VoidCallback? onSignup;
  final VoidCallback? onLogin;
  final VoidCallback? onCreatorSignup;
  final VoidCallback? onExploreMarket;

  @override
  State<GtexPublicLandingScreenV2> createState() =>
      _GtexPublicLandingScreenV2State();
}

class _GtexPublicLandingScreenV2State extends State<GtexPublicLandingScreenV2> {
  static const String _posterAsset =
      'assets/media/gtex_landing_single_poster.png';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: GtexColors.black,
      body: Stack(
        children: <Widget>[
          _LandingBackdrop(assetPath: _posterAsset),
          const _SinglePosterLanding(posterAsset: _posterAsset),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(
                GtexSpacing.lg,
                GtexSpacing.md,
                GtexSpacing.lg,
                0,
              ),
              child: _TopBar(onLogin: widget.onLogin),
            ),
          ),
          Align(
            alignment: Alignment.bottomCenter,
            child: _LandingActionDock(
              onSignup: widget.onSignup,
              onCreatorSignup: widget.onCreatorSignup,
              onExploreMarket: widget.onExploreMarket,
            ),
          ),
        ],
      ),
    );
  }
}

class _TopBar extends StatelessWidget {
  const _TopBar({this.onLogin});

  final VoidCallback? onLogin;

  @override
  Widget build(BuildContext context) {
    final bool compact = MediaQuery.sizeOf(context).width < 420;
    return Row(
      children: <Widget>[
        ClipRRect(
          borderRadius: BorderRadius.circular(10),
          child: Image.asset(
            'assets/branding/gtex_icon.png',
            width: 36,
            height: 36,
            fit: BoxFit.cover,
          ),
        ),
        const SizedBox(width: GtexSpacing.sm),
        Expanded(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Text(
                'GTEX',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.w900,
                  height: 1,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                compact
                    ? 'Football marketplace'
                    : 'Global football marketplace',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: GtexColors.textMuted,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  height: 1,
                ),
              ),
            ],
          ),
        ),
        TextButton(
          onPressed: onLogin,
          child: const Text(
            'Login',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800),
          ),
        ),
      ],
    );
  }
}

class _SinglePosterLanding extends StatelessWidget {
  const _SinglePosterLanding({required this.posterAsset});

  final String posterAsset;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool compact = constraints.maxWidth < GtexBreakpoints.mobile;
        final double horizontal = compact ? GtexSpacing.md : GtexSpacing.xl;
        final double topReserve = compact ? 82 : 96;
        final double bottomReserve = compact ? 146 : 126;
        final double maxWidth =
            compact ? constraints.maxWidth - (horizontal * 2) : 460;
        final double maxHeight =
            constraints.maxHeight - topReserve - bottomReserve;

        return SafeArea(
          child: Padding(
            padding: EdgeInsets.fromLTRB(
              horizontal,
              compact ? 64 : 76,
              horizontal,
              compact ? 124 : 106,
            ),
            child: Center(
              child: ConstrainedBox(
                constraints: BoxConstraints(
                  maxWidth: maxWidth,
                  maxHeight: maxHeight.clamp(320.0, 720.0),
                ),
                child: AspectRatio(
                  aspectRatio: 2 / 3,
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(18),
                      boxShadow: const <BoxShadow>[
                        BoxShadow(
                          color: Color(0x99000000),
                          blurRadius: 42,
                          offset: Offset(0, 22),
                        ),
                      ],
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(18),
                      child: Image.asset(
                        posterAsset,
                        fit: BoxFit.contain,
                        filterQuality: FilterQuality.high,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

class _LandingBackdrop extends StatelessWidget {
  const _LandingBackdrop({required this.assetPath});

  final String assetPath;

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: <Widget>[
        ImageFiltered(
          imageFilter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
          child: Transform.scale(
            scale: 1.08,
            child: Image.asset(
              assetPath,
              fit: BoxFit.cover,
              alignment: Alignment.center,
              filterQuality: FilterQuality.high,
            ),
          ),
        ),
        const DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: <Color>[
                Color(0xF7030607),
                Color(0x70030607),
                Color(0xF5030607),
              ],
              stops: <double>[0, 0.48, 1],
            ),
          ),
        ),
        const DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.centerLeft,
              end: Alignment.centerRight,
              colors: <Color>[
                Color(0xBA030607),
                Color(0x2E030607),
                Color(0x8A030607),
              ],
              stops: <double>[0, 0.5, 1],
            ),
          ),
        ),
        const DecoratedBox(
          decoration: BoxDecoration(
            gradient: RadialGradient(
              center: Alignment(0.0, -0.36),
              radius: 0.94,
              colors: <Color>[Color(0x2635FF9C), Color(0x00030607)],
            ),
          ),
        ),
      ],
    );
  }
}

class _LandingActionDock extends StatelessWidget {
  const _LandingActionDock({
    this.onSignup,
    this.onCreatorSignup,
    this.onExploreMarket,
  });

  final VoidCallback? onSignup;
  final VoidCallback? onCreatorSignup;
  final VoidCallback? onExploreMarket;

  @override
  Widget build(BuildContext context) {
    final bool compact =
        MediaQuery.sizeOf(context).width < GtexBreakpoints.mobile;
    return SafeArea(
      top: false,
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          GtexSpacing.lg,
          GtexSpacing.sm,
          GtexSpacing.lg,
          compact ? GtexSpacing.lg : GtexSpacing.xl,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Wrap(
              alignment: WrapAlignment.center,
              spacing: GtexSpacing.sm,
              runSpacing: GtexSpacing.sm,
              children: <Widget>[
                GtexButton(label: 'Create your club', onPressed: onSignup),
                GtexButton(
                  label: 'Explore market',
                  variant: GtexButtonVariant.secondary,
                  onPressed: onExploreMarket,
                ),
                if (!compact)
                  GtexButton(
                    label: 'Become a creator',
                    variant: GtexButtonVariant.ghost,
                    onPressed: onCreatorSignup,
                  ),
              ],
            ),
            if (compact) ...<Widget>[
              const SizedBox(height: GtexSpacing.xs),
              TextButton(
                onPressed: onCreatorSignup,
                child: const Text(
                  'Become a creator',
                  style: TextStyle(
                    color: GtexColors.textSecondary,
                    fontWeight: FontWeight.w800,
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
