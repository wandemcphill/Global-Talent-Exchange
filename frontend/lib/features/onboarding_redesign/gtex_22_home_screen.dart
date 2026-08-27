import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

const _ink = Color(0xFF050709);
const _panel = Color(0xFF0A0F13);
const _line = Color(0xFF1C2830);
const _white = Color(0xFFF4F7F8);
const _muted = Color(0xFF93A0AA);
const _lime = Color(0xFFB9FF3D);
const _green = Color(0xFF36E38A);
const _blue = Color(0xFF00A7FF);
const _gold = Color(0xFFFFC857);
const _violet = Color(0xFF9C6BFF);

class Gtex22HomeScreen extends StatelessWidget {
  const Gtex22HomeScreen({
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
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _ink,
      body: SelectionArea(
        child: CustomScrollView(
          slivers: <Widget>[
            SliverToBoxAdapter(child: _Nav(onLogin: onLogin, onSignup: onSignup)),
            SliverToBoxAdapter(child: _Hero(onSignup: onSignup, onExplore: onExploreMarket)),
            const SliverToBoxAdapter(child: _ClarityStrip()),
            SliverToBoxAdapter(child: _PlatformMap(onSignup: onSignup)),
            const SliverToBoxAdapter(child: _WorldSection()),
            SliverToBoxAdapter(child: _AudienceSection(onSignup: onSignup, onCreatorSignup: onCreatorSignup, onTraderSignup: onTraderSignup)),
            const SliverToBoxAdapter(child: _HowItWorks()),
            SliverToBoxAdapter(child: _FinalCta(onSignup: onSignup)),
            const SliverToBoxAdapter(child: _Footer()),
          ],
        ),
      ),
    );
  }
}

class _Nav extends StatelessWidget {
  const _Nav({this.onLogin, this.onSignup});
  final VoidCallback? onLogin;
  final VoidCallback? onSignup;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 16),
      decoration: const BoxDecoration(
        color: Color(0xF0050709),
        border: Border(bottom: BorderSide(color: _line)),
      ),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: <Widget>[
            Text(
              'GTEX',
              style: const TextStyle(
                color: _white,
                fontSize: 22,
                fontWeight: FontWeight.w900,
                letterSpacing: 2,
              ),
            ),
            const SizedBox(width: 12),
            SvgPicture.asset('assets/branding/gtex_wordmark_22.svg', width: 140, height: 32, semanticsLabel: 'GTEX'),
            const SizedBox(width: 24),
            if (MediaQuery.sizeOf(context).width >= 780) ...const <Widget>[
              _NavLink('Discover'),
              _NavLink('Exchange'),
              _NavLink('Matches'),
              _NavLink('Clubs'),
              _NavLink('Competitions'),
              _NavLink('World'),
              SizedBox(width: 10),
            ],
            TextButton(onPressed: onLogin, child: const Text('Sign in', style: TextStyle(color: _white))),
            const SizedBox(width: 8),
            _GlowButton(label: 'Enter GTEX', onPressed: onSignup),
          ],
        ),
      ),
    );
  }
}

class _NavLink extends StatelessWidget {
  const _NavLink(this.label);
  final String label;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10),
        child: Text(label, style: const TextStyle(color: _muted, fontSize: 13, fontWeight: FontWeight.w600)),
      );
}

class _Hero extends StatelessWidget {
  const _Hero({this.onSignup, this.onExplore});
  final VoidCallback? onSignup;
  final VoidCallback? onExplore;

  @override
  Widget build(BuildContext context) {
    final mobile = MediaQuery.sizeOf(context).width < 760;
    return Container(
      constraints: const BoxConstraints(minHeight: 580),
      child: Stack(
        alignment: Alignment.centerLeft,
        children: <Widget>[
          Positioned.fill(
            child: Image.asset('assets/media/gtex_landing_single_poster.png', fit: BoxFit.cover, alignment: Alignment.centerRight),
          ),
          const Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.centerLeft,
                  end: Alignment.centerRight,
                  colors: <Color>[_ink, Color(0xE8050709), Color(0x75050709), Color(0x15050709)],
                ),
              ),
            ),
          ),
          Padding(
            padding: EdgeInsets.fromLTRB(mobile ? 24 : 120, 48, 24, 48),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 700),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  const _Eyebrow('THE LIVING FOOTBALL ECONOMY'),
                  const SizedBox(height: 14),
                  Text(
                    'GTEX',
                    style: TextStyle(
                      color: _white,
                      fontSize: mobile ? 28 : 36,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 3,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'FOOTBALL,\nREBUILT.',
                    style: TextStyle(color: _white, fontSize: mobile ? 42 : 72, height: .88, fontWeight: FontWeight.w900, letterSpacing: -2),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Discover talent. Build clubs. Trade assets. Play matches. Connect with a football world that never stops moving.',
                    style: TextStyle(color: _muted, fontSize: 16, height: 1.45),
                  ),
                  const SizedBox(height: 22),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: <Widget>[
                      _GlowButton(label: 'Create free account', onPressed: onSignup, large: true),
                      _GhostButton(label: 'Explore the exchange', onPressed: onExplore),
                    ],
                  ),
                  const SizedBox(height: 22),
                  const Wrap(
                    spacing: 9,
                    runSpacing: 9,
                    children: <Widget>[
                      _MicroBadge(icon: Icons.search_rounded, text: 'Scout'),
                      _MicroBadge(icon: Icons.stadium_rounded, text: 'Build'),
                      _MicroBadge(icon: Icons.candlestick_chart_rounded, text: 'Trade'),
                      _MicroBadge(icon: Icons.sports_soccer_rounded, text: 'Compete'),
                      _MicroBadge(icon: Icons.forum_rounded, text: 'Connect'),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const Positioned(right: 24, bottom: 24, child: _LiveSignal()),
        ],
      ),
    );
  }
}

class _Eyebrow extends StatelessWidget {
  const _Eyebrow(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Row(children: <Widget>[
        Container(width: 7, height: 7, decoration: const BoxDecoration(color: _lime, shape: BoxShape.circle)),
        const SizedBox(width: 9),
        Flexible(
          child: Text(text, style: const TextStyle(color: _lime, fontSize: 11, letterSpacing: 1.7, fontWeight: FontWeight.w700)),
        ),
      ]);
}

class _LiveSignal extends StatelessWidget {
  const _LiveSignal();
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(color: const Color(0xDD080E12), borderRadius: BorderRadius.circular(30), border: Border.all(color: _green.withOpacity(.35))),
        child: const Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
          Icon(Icons.circle, color: _green, size: 8),
          SizedBox(width: 7),
          Text('WORLD PULSE  •  LIVE', style: TextStyle(color: _white, fontSize: 10, letterSpacing: 1)),
        ]),
      );
}

class _ClarityStrip extends StatelessWidget {
  const _ClarityStrip();
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
        decoration: const BoxDecoration(color: _panel, border: Border(bottom: BorderSide(color: _line), top: BorderSide(color: _line))),
        child: const Center(child: Wrap(alignment: WrapAlignment.center, spacing: 28, runSpacing: 12, children: <Widget>[
          _Signal('PLAYERS', 'Discover & develop'),
          _Signal('CLUBS', 'Build & manage'),
          _Signal('MARKET', 'Trade & invest'),
          _Signal('MATCHDAY', 'Compete & win'),
          _Signal('COMMUNITY', 'Create & connect'),
        ])),
      );
}

class _Signal extends StatelessWidget {
  const _Signal(this.title, this.body);
  final String title;
  final String body;
  @override
  Widget build(BuildContext context) => Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
        Text(title, style: const TextStyle(color: _white, fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 1)),
        const SizedBox(width: 7),
        Text(body, style: const TextStyle(color: _muted, fontSize: 12)),
      ]);
}

class _PlatformMap extends StatelessWidget {
  const _PlatformMap({this.onSignup});
  final VoidCallback? onSignup;

  @override
  Widget build(BuildContext context) {
    final items = <_Feature>[
      const _Feature(Icons.person_search_rounded, 'Talent Exchange', 'Find players, compare profiles, track value and move talent across the world.', _lime),
      const _Feature(Icons.account_balance_rounded, 'Club Ownership', 'Build a club identity, manage your squad, shape its legacy and compete.', _green),
      const _Feature(Icons.analytics_rounded, 'Football Intelligence', 'Player data, scouting signals, performance, reports and market context.', _blue),
      const _Feature(Icons.emoji_events_rounded, 'Matches & Competitions', 'Live matchday, leagues, tournaments, awards and progression.', _gold),
      const _Feature(Icons.account_balance_wallet_rounded, 'Wallet & Economy', 'Wallet funding, P2P activity, withdrawals and football commerce.', _violet),
      const _Feature(Icons.forum_rounded, 'Social Football', 'Creators, fans, news, Fan Wars, gifting and a living community.', Color(0xFFFF5FA2)),
    ];
    return Container(
      padding: EdgeInsets.symmetric(horizontal: MediaQuery.sizeOf(context).width < 760 ? 24 : 72, vertical: 86),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        const _Eyebrow('ONE PLATFORM. MANY WAYS TO PLAY.'),
        const SizedBox(height: 15),
        const Text('Everything football.\nOne living system.', style: TextStyle(color: _white, fontSize: 56, height: .9, fontWeight: FontWeight.w900)),
        const SizedBox(height: 16),
        const Text('GTEX brings talent, clubs, markets, matches, money and community into one connected football ecosystem.', style: TextStyle(color: _muted, fontSize: 16, height: 1.55)),
        const SizedBox(height: 34),
        _FeatureGrid(items: items),
        const SizedBox(height: 24),
        _GhostButton(label: 'See the football world', onPressed: onSignup),
      ]),
    );
  }
}

class _Feature {
  const _Feature(this.icon, this.title, this.body, this.accent);
  final IconData icon;
  final String title;
  final String body;
  final Color accent;
}

/// Content-height feature grid. A fixed `childAspectRatio` grid sized the
/// cells independently of their copy, so cards clipped their body text at
/// most widths; rows size to their tallest card instead.
class _FeatureGrid extends StatelessWidget {
  const _FeatureGrid({required this.items});
  final List<_Feature> items;

  static const double _gap = 14;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (BuildContext context, BoxConstraints constraints) {
      final int columns = constraints.maxWidth > 1050
          ? 3
          : constraints.maxWidth > 650
              ? 2
              : 1;
      final List<Widget> rows = <Widget>[];
      for (int start = 0; start < items.length; start += columns) {
        if (rows.isNotEmpty) rows.add(const SizedBox(height: _gap));
        final int end = math.min(start + columns, items.length);
        rows.add(IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              for (int column = 0; column < columns; column++) ...<Widget>[
                if (column > 0) const SizedBox(width: _gap),
                Expanded(
                  child: start + column < end
                      ? _FeatureCard(items[start + column])
                      : const SizedBox.shrink(),
                ),
              ],
            ],
          ),
        ));
      }
      return Column(children: rows);
    });
  }
}

class _FeatureCard extends StatelessWidget {
  const _FeatureCard(this.feature);
  final _Feature feature;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(color: _panel, borderRadius: BorderRadius.circular(18), border: Border.all(color: _line)),
        child: Align(
          alignment: Alignment.topLeft,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Container(width: 46, height: 46, decoration: BoxDecoration(color: feature.accent.withOpacity(.10), borderRadius: BorderRadius.circular(13), border: Border.all(color: feature.accent.withOpacity(.25))), child: Icon(feature.icon, color: feature.accent, size: 23)),
              const SizedBox(height: 16),
              Text(feature.title, style: const TextStyle(color: _white, fontSize: 22, fontWeight: FontWeight.w700)),
              const SizedBox(height: 6),
              Text(feature.body, style: const TextStyle(color: _muted, fontSize: 13, height: 1.45)),
            ],
          ),
        ),
      );
}

class _WorldSection extends StatelessWidget {
  const _WorldSection();
  @override
  Widget build(BuildContext context) => Container(
        padding: EdgeInsets.symmetric(horizontal: MediaQuery.sizeOf(context).width < 760 ? 24 : 72, vertical: 80),
        color: _panel,
        child: LayoutBuilder(builder: (BuildContext context, BoxConstraints constraints) {
          final text = Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: const <Widget>[
            _Eyebrow('THE WORLD PULSE'),
            SizedBox(height: 15),
            Text('Football that\nfeels alive.', style: TextStyle(color: _white, fontSize: 58, height: .9, fontWeight: FontWeight.w900)),
            SizedBox(height: 16),
            Text('Markets shift. Players rise. Clubs win. Matches happen. Stories spread. GTEX turns that movement into a living feed you can act on.', style: TextStyle(color: _muted, fontSize: 15, height: 1.55)),
          ]);
          final visual = Container(
            height: 350,
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(24), border: Border.all(color: _line), image: const DecorationImage(image: AssetImage('assets/media/gtex_matchday_wallpaper.png'), fit: BoxFit.cover, opacity: .45)),
            child: const Stack(children: <Widget>[
              _PulseCard(top: 24, left: 24, title: 'LIVE MATCH', value: '2 — 1', detail: '78  •  WORLD CUP'),
              _PulseCard(top: 118, right: 24, title: 'MARKET SIGNAL', value: '+12.8%', detail: 'BREAKOUT PLAYER'),
              _PulseCard(bottom: 24, left: 55, title: 'WORLD PULSE', value: 'LIVE', detail: 'MATCHES • MARKET • NEWS'),
            ]),
          );
          if (constraints.maxWidth < 820) return Column(children: <Widget>[text, const SizedBox(height: 34), visual]);
          return Row(children: <Widget>[Expanded(child: text), const SizedBox(width: 55), Expanded(child: visual)]);
        }),
      );
}

class _PulseCard extends StatelessWidget {
  const _PulseCard({this.top, this.bottom, this.left, this.right, required this.title, required this.value, required this.detail});
  final double? top;
  final double? bottom;
  final double? left;
  final double? right;
  final String title;
  final String value;
  final String detail;
  @override
  Widget build(BuildContext context) => Positioned(
        top: top,
        bottom: bottom,
        left: left,
        right: right,
        child: Container(
          width: 210,
          padding: const EdgeInsets.all(15),
          decoration: BoxDecoration(color: const Color(0xDD080D11), borderRadius: BorderRadius.circular(14), border: Border.all(color: _line)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            Text(title, style: const TextStyle(color: _muted, fontSize: 9, letterSpacing: 1.2)),
            const SizedBox(height: 7),
            Text(value, style: const TextStyle(color: _lime, fontSize: 31, fontWeight: FontWeight.w800)),
            Text(detail, style: const TextStyle(color: _white, fontSize: 10)),
          ]),
        ),
      );
}

class _AudienceSection extends StatelessWidget {
  const _AudienceSection({this.onSignup, this.onCreatorSignup, this.onTraderSignup});
  final VoidCallback? onSignup;
  final VoidCallback? onCreatorSignup;
  final VoidCallback? onTraderSignup;
  @override
  Widget build(BuildContext context) => Container(
        padding: EdgeInsets.symmetric(horizontal: MediaQuery.sizeOf(context).width < 760 ? 24 : 72, vertical: 86),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          const _Eyebrow('YOUR ROLE. YOUR WORLD.'),
          const SizedBox(height: 15),
          const Text('Enter GTEX your way.', style: TextStyle(color: _white, fontSize: 54, fontWeight: FontWeight.w900)),
          const SizedBox(height: 28),
          LayoutBuilder(builder: (BuildContext context, BoxConstraints constraints) {
            final double cardWidth = math.min(320, constraints.maxWidth);
            return Wrap(spacing: 14, runSpacing: 14, children: <Widget>[
              _RoleCard(width: cardWidth, icon: Icons.sports_soccer, title: 'Player / Fan', body: 'Build your identity, follow football and compete.', button: 'Join GTEX', onPressed: onSignup, accent: _lime),
              _RoleCard(width: cardWidth, icon: Icons.stadium, title: 'Creator / Community', body: 'Publish, connect, grow an audience and shape culture.', button: 'Create', onPressed: onCreatorSignup, accent: _blue),
              _RoleCard(width: cardWidth, icon: Icons.candlestick_chart, title: 'Trader / Builder', body: 'Explore talent, markets, clubs and football assets.', button: 'Explore', onPressed: onTraderSignup, accent: _gold),
            ]);
          }),
        ]),
      );
}

class _RoleCard extends StatelessWidget {
  const _RoleCard({required this.width, required this.icon, required this.title, required this.body, required this.button, required this.onPressed, required this.accent});
  final double width;
  final IconData icon;
  final String title;
  final String body;
  final String button;
  final VoidCallback? onPressed;
  final Color accent;
  @override
  Widget build(BuildContext context) => Container(
        width: width,
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(color: _panel, borderRadius: BorderRadius.circular(20), border: Border.all(color: _line)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          Icon(icon, color: accent, size: 32),
          const SizedBox(height: 26),
          Text(title, style: const TextStyle(color: _white, fontSize: 25, fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          Text(body, style: const TextStyle(color: _muted, fontSize: 14, height: 1.45)),
          const SizedBox(height: 22),
          _GhostButton(label: button, onPressed: onPressed),
        ]),
      );
}

class _HowItWorks extends StatelessWidget {
  const _HowItWorks();
  @override
  Widget build(BuildContext context) => Container(
        color: _panel,
        padding: EdgeInsets.symmetric(horizontal: MediaQuery.sizeOf(context).width < 760 ? 24 : 72, vertical: 82),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: const <Widget>[
          _Eyebrow('SIMPLE AT THE SURFACE. DEEP UNDERNEATH.'),
          SizedBox(height: 15),
          Text('One identity. Infinite football.', style: TextStyle(color: _white, fontSize: 52, fontWeight: FontWeight.w900)),
          SizedBox(height: 34),
          _Step(number: '01', title: 'Create your identity', body: 'One account becomes your passport across the GTEX football world.'),
          _Step(number: '02', title: 'Choose your lane', body: 'Scout, build, trade, compete, create or simply follow the action.'),
          _Step(number: '03', title: 'Keep moving', body: 'Your profile, clubs, activity, assets and football story evolve with you.'),
        ]),
      );
}

class _Step extends StatelessWidget {
  const _Step({required this.number, required this.title, required this.body});
  final String number;
  final String title;
  final String body;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 22),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          SizedBox(width: 55, child: Text(number, style: const TextStyle(color: _lime, fontSize: 13, fontWeight: FontWeight.w800))),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            Text(title, style: const TextStyle(color: _white, fontSize: 24, fontWeight: FontWeight.w800)),
            const SizedBox(height: 5),
            Text(body, style: const TextStyle(color: _muted, fontSize: 14, height: 1.45)),
          ])),
        ]),
      );
}

class _FinalCta extends StatelessWidget {
  const _FinalCta({this.onSignup});
  final VoidCallback? onSignup;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 100),
        decoration: const BoxDecoration(gradient: RadialGradient(center: Alignment.center, radius: 1.1, colors: <Color>[Color(0x2036E38A), _ink])),
        child: Center(
          child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
            SvgPicture.asset('assets/branding/gtex_mark_22.svg', width: 76, height: 76, semanticsLabel: 'GTEX'),
            const SizedBox(height: 22),
            const Text('YOUR FOOTBALL WORLD\nSTARTS HERE.', textAlign: TextAlign.center, style: TextStyle(color: _white, fontSize: 58, height: .88, fontWeight: FontWeight.w900)),
            const SizedBox(height: 16),
            const Text('One identity. One world. Infinite football.', style: TextStyle(color: _muted, fontSize: 15)),
            const SizedBox(height: 28),
            _GlowButton(label: 'Enter GTEX', onPressed: onSignup, large: true),
          ]),
        ),
      );
}

class _Footer extends StatelessWidget {
  const _Footer();
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 28),
        decoration: const BoxDecoration(color: _panel, border: Border(top: BorderSide(color: _line))),
        child: const Row(children: <Widget>[
          Text('GTEX', style: TextStyle(color: _white, fontSize: 18, fontWeight: FontWeight.w900, letterSpacing: 2)),
          SizedBox(width: 16),
          Expanded(
            child: Text('GLOBAL TALENT EXCHANGE', textAlign: TextAlign.right, style: TextStyle(color: _muted, fontSize: 10, letterSpacing: 1.3)),
          ),
        ]),
      );
}

class _MicroBadge extends StatelessWidget {
  const _MicroBadge({required this.icon, required this.text});
  final IconData icon;
  final String text;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 8),
        decoration: BoxDecoration(color: const Color(0x77080D11), borderRadius: BorderRadius.circular(20), border: Border.all(color: _line)),
        child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
          Icon(icon, size: 14, color: _white),
          const SizedBox(width: 6),
          Text(text, style: const TextStyle(color: _white, fontSize: 11, fontWeight: FontWeight.w600)),
        ]),
      );
}

class _GlowButton extends StatelessWidget {
  const _GlowButton({required this.label, required this.onPressed, this.large = false});
  final String label;
  final VoidCallback? onPressed;
  final bool large;
  @override
  Widget build(BuildContext context) => ElevatedButton(
        onPressed: onPressed,
        style: ElevatedButton.styleFrom(backgroundColor: _lime, foregroundColor: _ink, elevation: 0, padding: EdgeInsets.symmetric(horizontal: large ? 22 : 16, vertical: large ? 17 : 12), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
        child: Text(label, style: TextStyle(fontSize: large ? 15 : 13, fontWeight: FontWeight.w800)),
      );
}

class _GhostButton extends StatelessWidget {
  const _GhostButton({required this.label, required this.onPressed});
  final String label;
  final VoidCallback? onPressed;
  @override
  Widget build(BuildContext context) => OutlinedButton(
        onPressed: onPressed,
        style: OutlinedButton.styleFrom(foregroundColor: _white, side: const BorderSide(color: _line), padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 13), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
        child: Text(label, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
      );
}
