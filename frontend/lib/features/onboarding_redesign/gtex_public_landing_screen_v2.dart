import 'dart:async';

import 'package:flutter/material.dart';

const Color _bg = Color(0xFF090C10);
const Color _card = Color(0xFF12171D);
const Color _border = Color(0xFF232B34);
const Color _green = Color(0xFF21C77A);
const Color _greenBright = Color(0xFF2BE08A);
const Color _gold = Color(0xFFE6B450);
const Color _blue = Color(0xFF5AA2F0);
const Color _violet = Color(0xFFB07CF0);
const Color _text = Color(0xFFF4F7FA);
const Color _textSecondary = Color(0xFFAEB9C4);
const Color _textMuted = Color(0xFF7E8B98);

const String _condensed = 'BarlowCondensed';

/// World-class post-install landing: trophy hero, an auto-playing "how you play"
/// showcase, a live results ticker, and a one-glance account chooser.
class GtexPublicLandingScreenV2 extends StatefulWidget {
  const GtexPublicLandingScreenV2({
    super.key,
    this.onSignup,
    this.onLogin,
    this.onCreatorSignup,
    this.onTraderSignup,
    this.onExploreMarket,
  });

  final VoidCallback? onSignup;
  final VoidCallback? onLogin;
  final VoidCallback? onCreatorSignup;
  final VoidCallback? onTraderSignup;
  final VoidCallback? onExploreMarket;

  @override
  State<GtexPublicLandingScreenV2> createState() =>
      _GtexPublicLandingScreenV2State();
}

class _ShowcaseStep {
  const _ShowcaseStep({
    required this.index,
    required this.title,
    required this.body,
    required this.icon,
    required this.color,
    this.image,
  });

  final String index;
  final String title;
  final String body;
  final IconData icon;
  final Color color;
  final String? image;
}

const List<_ShowcaseStep> _steps = <_ShowcaseStep>[
  _ShowcaseStep(
    index: '1',
    title: 'Scout & sign',
    body: 'Search 17K+ real players and regens. Make an offer, win the deal.',
    icon: Icons.person_search_rounded,
    color: _blue,
  ),
  _ShowcaseStep(
    index: '2',
    title: 'Pick your XI',
    body: 'Set your formation and tactics, or let your coach auto-pick.',
    icon: Icons.dashboard_customize_rounded,
    color: _gold,
  ),
  _ShowcaseStep(
    index: '3',
    title: 'Play live',
    body: 'Watch your match play out live in 2D — goals, cards, drama.',
    icon: Icons.sports_soccer_rounded,
    color: _greenBright,
    image: 'assets/media/gtex_match_live.webp',
  ),
  _ShowcaseStep(
    index: '4',
    title: 'Lift trophies',
    body: 'Win cups and the GTEX World Cup. Climb the global leaderboard.',
    icon: Icons.emoji_events_rounded,
    color: _gold,
  ),
  _ShowcaseStep(
    index: '5',
    title: 'Regens rise',
    body: 'Grow one-of-a-kind regens into legends with their own awards.',
    icon: Icons.auto_awesome_rounded,
    color: _violet,
  ),
];

class _GtexPublicLandingScreenV2State extends State<GtexPublicLandingScreenV2> {
  final PageController _pageController = PageController();
  Timer? _timer;
  int _index = 0;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(milliseconds: 2800), (_) {
      if (!mounted || !_pageController.hasClients) {
        return;
      }
      _index = (_index + 1) % _steps.length;
      _pageController.animateToPage(
        _index,
        duration: const Duration(milliseconds: 520),
        curve: Curves.easeInOutCubic,
      );
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _bg,
      body: SafeArea(
        bottom: false,
        child: SingleChildScrollView(
          physics: const ClampingScrollPhysics(),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              _Hero(onLogin: widget.onLogin),
              const SizedBox(height: 20),
              _SectionLabel(label: 'HOW YOU PLAY'),
              const SizedBox(height: 12),
              _Showcase(controller: _pageController, onChanged: (int i) => _index = i),
              const SizedBox(height: 18),
              const _ResultsTicker(),
              const SizedBox(height: 20),
              _SectionLabel(label: 'CHOOSE YOUR PATH'),
              const SizedBox(height: 12),
              _AccountChooser(
                onSignup: widget.onSignup,
                onTraderSignup: widget.onTraderSignup ?? widget.onExploreMarket,
                onCreatorSignup: widget.onCreatorSignup,
              ),
              const SizedBox(height: 18),
              const _TrustStrip(),
              const Padding(
                padding: EdgeInsets.fromLTRB(20, 14, 20, 26),
                child: Text(
                  'Admin access is invite-only.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Color(0xFF5B6772), fontSize: 12),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Hero extends StatelessWidget {
  const _Hero({this.onLogin});

  final VoidCallback? onLogin;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 330,
      child: Stack(
        fit: StackFit.expand,
        children: <Widget>[
          Image.asset(
            'assets/media/gtex_hero_trophy.webp',
            fit: BoxFit.cover,
            alignment: Alignment.topCenter,
            errorBuilder: (_, __, ___) => const ColoredBox(color: Color(0xFF0C2A1E)),
          ),
          const DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: <Color>[
                  Color(0x33090C10),
                  Color(0x00090C10),
                  Color(0xCC090C10),
                  Color(0xFF090C10),
                ],
                stops: <double>[0, 0.32, 0.78, 1],
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 10, 20, 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: <Widget>[
                    Row(
                      children: <Widget>[
                        Container(
                          width: 30,
                          height: 30,
                          decoration: BoxDecoration(
                            color: _green,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          alignment: Alignment.center,
                          child: const Text(
                            'GT',
                            style: TextStyle(
                              color: Color(0xFF06140C),
                              fontWeight: FontWeight.w800,
                              fontSize: 14,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        const Text(
                          'GTEX',
                          style: TextStyle(
                            fontFamily: _condensed,
                            color: _text,
                            fontWeight: FontWeight.w800,
                            fontSize: 20,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ],
                    ),
                    TextButton(
                      onPressed: onLogin,
                      child: const Text(
                        'Sign in',
                        style: TextStyle(color: Color(0xFFC4CDD6), fontSize: 13),
                      ),
                    ),
                  ],
                ),
                const Spacer(),
                Row(
                  children: const <Widget>[
                    _HeroPill(
                      label: 'Jackpot 02:14:08',
                      icon: Icons.card_giftcard_rounded,
                      color: _gold,
                    ),
                    SizedBox(width: 7),
                    _HeroPill(
                      label: '1,204 live',
                      icon: Icons.circle,
                      color: Color(0xFFFF6B6B),
                      dot: true,
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                const Text(
                  'OWN A CLUB.\nSIGN THE STARS.',
                  style: TextStyle(
                    fontFamily: _condensed,
                    color: _text,
                    fontSize: 38,
                    height: 0.92,
                    fontWeight: FontWeight.w900,
                    letterSpacing: -0.5,
                  ),
                ),
                const Text(
                  'WIN IT ALL.',
                  style: TextStyle(
                    fontFamily: _condensed,
                    color: _greenBright,
                    fontSize: 38,
                    height: 0.95,
                    fontWeight: FontWeight.w900,
                    letterSpacing: -0.5,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _HeroPill extends StatelessWidget {
  const _HeroPill({
    required this.label,
    required this.icon,
    required this.color,
    this.dot = false,
  });

  final String label;
  final IconData icon;
  final Color color;
  final bool dot;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.34)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(icon, size: dot ? 8 : 12, color: color),
          const SizedBox(width: 5),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 11,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Row(
        children: <Widget>[
          Text(
            label,
            style: const TextStyle(
              fontFamily: _condensed,
              color: _textMuted,
              fontSize: 13,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.5,
            ),
          ),
          const SizedBox(width: 10),
          const Expanded(child: Divider(color: Color(0xFF20262E), height: 1)),
        ],
      ),
    );
  }
}

class _Showcase extends StatelessWidget {
  const _Showcase({required this.controller, required this.onChanged});

  final PageController controller;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Container(
        decoration: BoxDecoration(
          color: const Color(0xFF0E1318),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: _border),
        ),
        child: Column(
          children: <Widget>[
            SizedBox(
              height: 104,
              child: PageView.builder(
                controller: controller,
                onPageChanged: onChanged,
                itemCount: _steps.length,
                itemBuilder: (BuildContext context, int i) => _StepCard(step: _steps[i]),
              ),
            ),
            const SizedBox(height: 12),
            _Dots(controller: controller),
            const SizedBox(height: 12),
          ],
        ),
      ),
    );
  }
}

class _StepCard extends StatelessWidget {
  const _StepCard({required this.step});

  final _ShowcaseStep step;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(14),
      child: Row(
        children: <Widget>[
          if (step.image != null)
            ClipRRect(
              borderRadius: BorderRadius.circular(11),
              child: Image.asset(
                step.image!,
                width: 76,
                height: 76,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => _StepIcon(step: step),
              ),
            )
          else
            _StepIcon(step: step),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: <Widget>[
                Text(
                  '${step.index} · ${step.title}',
                  style: TextStyle(
                    fontFamily: _condensed,
                    color: step.color,
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  step.body,
                  style: const TextStyle(
                    color: _textSecondary,
                    fontSize: 13,
                    height: 1.3,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _StepIcon extends StatelessWidget {
  const _StepIcon({required this.step});

  final _ShowcaseStep step;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 76,
      height: 76,
      decoration: BoxDecoration(
        color: step.color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(11),
      ),
      child: Icon(step.icon, color: step.color, size: 34),
    );
  }
}

class _Dots extends StatelessWidget {
  const _Dots({required this.controller});

  final PageController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (BuildContext context, _) {
        double page = 0;
        if (controller.hasClients && controller.page != null) {
          page = controller.page!;
        }
        final int active = page.round();
        return Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: List<Widget>.generate(_steps.length, (int i) {
            final bool on = i == active;
            return AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              margin: const EdgeInsets.symmetric(horizontal: 2.5),
              height: 6,
              width: on ? 18 : 6,
              decoration: BoxDecoration(
                color: _green.withValues(alpha: on ? 1 : 0.3),
                borderRadius: BorderRadius.circular(3),
              ),
            );
          }),
        );
      },
    );
  }
}

class _ResultsTicker extends StatefulWidget {
  const _ResultsTicker();

  @override
  State<_ResultsTicker> createState() => _ResultsTickerState();
}

class _ResultsTickerState extends State<_ResultsTicker>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 22),
  )..repeat();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    const List<Widget> items = <Widget>[
      _TickerItem(text: 'Marlow FC signed J. Okafor', color: _greenBright),
      _TickerItem(text: 'Lagos Cup won by Vista United', color: _gold),
      _TickerItem(text: 'Rivas (regen) hits 92 GSI', color: _violet),
      _TickerItem(text: '+1,420 GTC top transfer', color: _blue),
    ];
    return Container(
      height: 34,
      decoration: const BoxDecoration(
        border: Border(
          top: BorderSide(color: Color(0xFF1B2128)),
          bottom: BorderSide(color: Color(0xFF1B2128)),
        ),
      ),
      child: ClipRect(
        child: LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            return AnimatedBuilder(
              animation: _controller,
              builder: (BuildContext context, Widget? child) {
                final double w = constraints.maxWidth;
                final double dx = -_controller.value * w;
                return Stack(
                  children: <Widget>[
                    Transform.translate(
                      offset: Offset(dx, 0),
                      child: child,
                    ),
                    Transform.translate(
                      offset: Offset(dx + w, 0),
                      child: child,
                    ),
                  ],
                );
              },
              child: SizedBox(
                width: constraints.maxWidth,
                child: const Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: items,
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

class _TickerItem extends StatelessWidget {
  const _TickerItem({required this.text, required this.color});

  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Icon(Icons.circle, size: 6, color: color),
        const SizedBox(width: 6),
        Text(
          text,
          style: const TextStyle(color: _textSecondary, fontSize: 12),
        ),
      ],
    );
  }
}

class _AccountChooser extends StatelessWidget {
  const _AccountChooser({
    this.onSignup,
    this.onTraderSignup,
    this.onCreatorSignup,
  });

  final VoidCallback? onSignup;
  final VoidCallback? onTraderSignup;
  final VoidCallback? onCreatorSignup;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        children: <Widget>[
          _PrimaryPathCard(onTap: onSignup),
          const SizedBox(height: 10),
          _PathRow(
            icon: Icons.swap_horiz_rounded,
            color: _blue,
            title: 'Coin trader',
            body: 'Buy and sell GTEX and Fan Coin.',
            onTap: onTraderSignup,
          ),
          const SizedBox(height: 10),
          _PathRow(
            icon: Icons.mic_external_on_rounded,
            color: _violet,
            title: 'Creator',
            body: 'Cover the game, grow an audience.',
            onTap: onCreatorSignup,
          ),
        ],
      ),
    );
  }
}

class _PrimaryPathCard extends StatelessWidget {
  const _PrimaryPathCard({this.onTap});

  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(15),
      decoration: BoxDecoration(
        color: const Color(0xFF113323).withValues(alpha: 0.38),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: _green, width: 2),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Row(
            children: <Widget>[
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: _green.withValues(alpha: 0.16),
                  borderRadius: BorderRadius.circular(11),
                ),
                child: const Icon(Icons.shield_rounded, color: _green, size: 23),
              ),
              const SizedBox(width: 11),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Player & club owner',
                      style: TextStyle(
                        fontFamily: _condensed,
                        color: _text,
                        fontSize: 21,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    Text(
                      'Start free. Buy players to open your club.',
                      style: TextStyle(color: _textSecondary, fontSize: 12.5),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: _green,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Text(
                  'FREE · INSTANT',
                  style: TextStyle(
                    color: Color(0xFF06140C),
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 13),
          FilledButton(
            onPressed: onTap,
            style: FilledButton.styleFrom(
              backgroundColor: _green,
              foregroundColor: const Color(0xFF06140C),
              padding: const EdgeInsets.symmetric(vertical: 13),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(11),
              ),
            ),
            child: const Text(
              'Create free account',
              style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800),
            ),
          ),
          const SizedBox(height: 9),
          Row(
            children: const <Widget>[
              Icon(Icons.lock_outline_rounded, size: 13, color: _textMuted),
              SizedBox(width: 6),
              Expanded(
                child: Text(
                  'Verify ID (KYC) only when you withdraw.',
                  style: TextStyle(color: _textMuted, fontSize: 11.5),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _PathRow extends StatelessWidget {
  const _PathRow({
    required this.icon,
    required this.color,
    required this.title,
    required this.body,
    this.onTap,
  });

  final IconData icon;
  final Color color;
  final String title;
  final String body;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(13),
          decoration: BoxDecoration(
            color: _card,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: _border),
          ),
          child: Row(
            children: <Widget>[
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(icon, color: color, size: 21),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      title,
                      style: const TextStyle(
                        fontFamily: _condensed,
                        color: _text,
                        fontSize: 18,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    Text(
                      body,
                      style: const TextStyle(color: _textSecondary, fontSize: 12),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: <Widget>[
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                    decoration: BoxDecoration(
                      color: color.withValues(alpha: 0.14),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: color.withValues(alpha: 0.3)),
                    ),
                    child: Text(
                      'APPLY · VERIFIED',
                      style: TextStyle(
                        color: color,
                        fontSize: 9.5,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                  const SizedBox(height: 7),
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      Text(
                        'Apply',
                        style: TextStyle(
                          color: color,
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      Icon(Icons.arrow_forward_rounded, size: 13, color: color),
                    ],
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _TrustStrip extends StatelessWidget {
  const _TrustStrip();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Container(
        padding: const EdgeInsets.only(top: 14),
        decoration: const BoxDecoration(
          border: Border(top: BorderSide(color: Color(0xFF1B2128))),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: const <Widget>[
            _TrustItem(icon: Icons.verified_user_rounded, label: 'KYC payouts', color: _green),
            _TrustItem(icon: Icons.groups_rounded, label: '17K+ players', color: _blue),
            _TrustItem(icon: Icons.sports_soccer_rounded, label: 'Live 2D', color: _gold),
          ],
        ),
      ),
    );
  }
}

class _TrustItem extends StatelessWidget {
  const _TrustItem({required this.icon, required this.label, required this.color});

  final IconData icon;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        Icon(icon, size: 14, color: color),
        const SizedBox(width: 4),
        Text(label, style: const TextStyle(color: _textMuted, fontSize: 11)),
      ],
    );
  }
}
