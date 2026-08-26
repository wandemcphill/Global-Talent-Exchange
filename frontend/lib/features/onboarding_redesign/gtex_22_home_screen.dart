import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

const _ink = Color(0xFF050709);
const _panel = Color(0xFF0A0F13);
const _panel2 = Color(0xFF0E151B);
const _line = Color(0xFF1C2830);
const _white = Color(0xFFF4F7F8);
const _muted = Color(0xFF93A0AA);
const _lime = Color(0xFFB9FF3D);
const _green = Color(0xFF36E38A);
const _blue = Color(0xFF00A7FF);
const _violet = Color(0xFF9C6BFF);
const _gold = Color(0xFFFFC857);

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
      padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 18),
      decoration: const BoxDecoration(
        color: Color(0xD9050709),
        border: Border(bottom: BorderSide(color: _line)),
      ),
      child: Row(
        children: <Widget>[
          SvgPicture.asset('assets/branding/gtex_wordmark_22.svg', width: 178, height: 42),
          const Spacer(),
          if (MediaQuery.sizeOf(context).width >= 760) ...<Widget>[
            const _NavLink('Discover'),
            const _NavLink('Exchange'),
            const _NavLink('Matches'),
            const _NavLink('Clubs'),
            const _NavLink('Competitions'),
            const _NavLink('World'),
            const SizedBox(width: 14),
          ],
          TextButton(onPressed: onLogin, child: const Text('Sign in')),
          const SizedBox(width: 8),
          _GlowButton(label: 'Enter GTEX', onPressed: onSignup),
        ],
      ),
    );
  }
}

class _NavLink extends StatelessWidget {
  const _NavLink(this.label);
  final String label;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 11),
    child: Text(label, style: const TextStyle(color: _muted, fontSize: 13, fontWeight: FontWeight.w600)),
  );
}

class _Hero extends StatelessWidget {
  const _Hero({this.onSignup, this.onExplore});
  final VoidCallback? onSignup;
  final VoidCallback? onExplore;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: MediaQuery.sizeOf(context).width < 760 ? 690 : 620,
      child: Stack(
        fit: StackFit.expand,
        children: <Widget>[
          Image.asset('assets/media/gtex_landing_single_poster.png', fit: BoxFit.cover, alignment: Alignment.centerRight),
          const DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(begin: Alignment.centerLeft, end: Alignment.centerRight, colors: <Color>[_ink, Color(0xE8050709), Color(0x8C050709), Color(0x22050709)]))),
          const DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: <Color>[Color(0x33050709), Color(0x00050709), _ink]))),
          Padding(
            padding: EdgeInsets.fromLTRB(MediaQuery.sizeOf(context).width < 760 ? 24 : 7.5 * 16, 70, 24, 40),
            child: Align(
              alignment: Alignment.centerLeft,
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 680),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const _Eyebrow(text: 'THE LIVING FOOTBALL ECONOMY'),
                    const SizedBox(height: 18),
                    Text('FOOTBALL,\nREBUILT.', style: TextStyle(fontFamily: 'BarlowCondensed', color: _white, fontSize: MediaQuery.sizeOf(context).width < 760 ? 64 : 92, height: .82, fontWeight: FontWeight.w700, letterSpacing: -2)),
                    const SizedBox(height: 18),
                    RichText(text: const TextSpan(style: TextStyle(fontFamily: 'Inter', fontSize: 19, height: 1.45, color: _muted), children: <InlineSpan>[TextSpan(text: 'Discover '), TextSpan(text: 'talent', style: TextStyle(color: _lime, fontWeight: FontWeight.w700)), TextSpan(text: '. Build '), TextSpan(text: 'clubs', style: TextStyle(color: _green, fontWeight: FontWeight.w700)), TextSpan(text: '. Trade '), TextSpan(text: 'assets', style: TextStyle(color: _gold, fontWeight: FontWeight.w700)), TextSpan(text: '. Play '), TextSpan(text: 'matches', style: TextStyle(color: _blue, fontWeight: FontWeight.w700)), TextSpan(text: '. Create your place in a football world that never stops moving.')])) ,
                    const SizedBox(height: 28),
                    Wrap(spacing: 12, runSpacing: 12, children: <Widget>[
                      _GlowButton(label: 'Create your GTEX identity', onPressed: onSignup, large: true),
                      _GhostButton(label: 'Explore the exchange', onPressed: onExplore),
                    ]),
                    const SizedBox(height: 28),
                    const Wrap(spacing: 9, runSpacing: 9, children: <Widget>[
                      _MicroBadge(icon: Icons.search_rounded, text: 'Scout'),
                      _MicroBadge(icon: Icons.stadium_rounded, text: 'Build'),
                      _MicroBadge(icon: Icons.candlestick_chart_rounded, text: 'Trade'),
                      _MicroBadge(icon: Icons.sports_soccer_rounded, text: 'Compete'),
                      _MicroBadge(icon: Icons.forum_rounded, text: 'Connect'),
                    ]),
                  ],
                ),
              ),
            ),
          ),
          const Positioned(right: 26, bottom: 28, child: _LiveSignal()),
        ],
      ),
    );
  }
}

class _Eyebrow extends StatelessWidget {
  const _Eyebrow({required this.text});
  final String text;
  @override
  Widget build(BuildContext context) => Row(children: <Widget>[Container(width: 7, height: 7, decoration: const BoxDecoration(color: _lime, shape: BoxShape.circle)), const SizedBox(width: 9), Text(text, style: const TextStyle(fontFamily: 'DMMono', color: _lime, fontSize: 11, letterSpacing: 1.7, fontWeight: FontWeight.w500))]);
}

class _LiveSignal extends StatelessWidget {
  const _LiveSignal();
  @override
  Widget build(BuildContext context) => Container(padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8), decoration: BoxDecoration(color: const Color(0xCC080E12), borderRadius: BorderRadius.circular(30), border: Border.all(color: _green.withValues(alpha: .35))), child: const Row(mainAxisSize: MainAxisSize.min, children: <Widget>[Icon(Icons.circle, color: _green, size: 8), SizedBox(width: 7), Text('WORLD PULSE  •  LIVE', style: TextStyle(fontFamily: 'DMMono', color: _white, fontSize: 10, letterSpacing: 1))]));
}

class _ClarityStrip extends StatelessWidget {
  const _ClarityStrip();
  @override
  Widget build(BuildContext context) => Container(padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20), decoration: const BoxDecoration(color: _panel, border: Border(bottom: BorderSide(color: _line), top: BorderSide(color: _line))), child: Center(child: Wrap(alignment: WrapAlignment.center, spacing: 28, runSpacing: 12, children: const <Widget>[_Signal('PLAYERS', 'Discover & develop'), _Signal('CLUBS', 'Build & manage'), _Signal('MARKET', 'Trade & invest'), _Signal('MATCHDAY', 'Compete & win'), _Signal('COMMUNITY', 'Create & connect')])));
}

class _Signal extends StatelessWidget {
  const _Signal(this.title, this.body);
  final String title;
  final String body;
  @override
  Widget build(BuildContext context) => Row(mainAxisSize: MainAxisSize.min, children: <Widget>[Text(title, style: const TextStyle(fontFamily: 'DMMono', color: _white, fontSize: 11, fontWeight: FontWeight.w500, letterSpacing: 1)), const SizedBox(width: 7), Text(body, style: const TextStyle(color: _muted, fontSize: 12))]);
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
      const _Feature(Icons.emoji_events_rounded, 'Matches & Competitions', 'Live matchday, leagues, tournaments, predictions, awards and progression.', _gold),
      const _Feature(Icons.account_balance_wallet_rounded, 'Wallet & Economy', 'Protected wallet flows, P2P activity, funding, withdrawals and football commerce.', _violet),
      const _Feature(Icons.forum_rounded, 'Social Football', 'Creators, fans, news, Fan Wars, gifting and a living football community.', Color(0xFFFF5FA2)),
    ];
    return Container(padding: EdgeInsets.symmetric(horizontal: MediaQuery.sizeOf(context).width < 760 ? 24 : 72, vertical: 86), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
      const _Eyebrow(text: 'ONE PLATFORM. MANY WAYS TO PLAY.'),
      const SizedBox(height: 15),
      const Text('Everything football.\nOne living system.', style: TextStyle(fontFamily: 'BarlowCondensed', color: _white, fontSize: 56, height: .9, fontWeight: FontWeight.w700)),
      const SizedBox(height: 16),
      const Text('GTEX brings the football ecosystem into one place: talent, clubs, markets, matches, money and community. No hunting through six different products to understand what is happening.', style: TextStyle(color: _muted, fontSize: 16, height: 1.55)),
      const SizedBox(height: 34),
      LayoutBuilder(builder: (context, c) {
        final columns = c.maxWidth > 1050 ? 3 : c.maxWidth > 650 ? 2 : 1;
        return GridView.builder(shrinkWrap: true, physics: const NeverScrollableScrollPhysics(), itemCount: items.length, gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: columns, crossAxisSpacing: 14, mainAxisSpacing: 14, childAspectRatio: columns == 1 ? 2.6 : 1.45), itemBuilder: (_, i) => _FeatureCard(items[i]));
      }),
      const SizedBox(height: 24),
      _GhostButton(label: 'See the football world', onPressed: onSignup),
    ]));
  }
}

class _Feature {
  const _Feature(this.icon, this.title, this.body, this.accent);
  final IconData icon; final String title; final String body; final Color accent;
}

class _FeatureCard extends StatelessWidget {
  const _FeatureCard(this.feature);
  final _Feature feature;
  @override
  Widget build(BuildContext context) => Container(padding: const EdgeInsets.all(22), decoration: BoxDecoration(color: _panel, borderRadius: BorderRadius.circular(18), border: Border.all(color: _line)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[Container(width: 46, height: 46, decoration: BoxDecoration(color: feature.accent.withValues(alpha: .10), borderRadius: BorderRadius.circular(13), border: Border.all(color: feature.accent.withValues(alpha: .25))), child: Icon(feature.icon, color: feature.accent, size: 23)), const Spacer(), Text(feature.title, style: const TextStyle(fontFamily: 'BarlowCondensed', color: _white, fontSize: 24, fontWeight: FontWeight.w600)), const SizedBox(height: 6), Text(feature.body, style: const TextStyle(color: _muted, fontSize: 13, height: 1.45))]));
}

class _WorldSection extends StatelessWidget {
  const _WorldSection();
  @override
  Widget build(BuildContext context) => Container(padding: EdgeInsets.symmetric(horizontal: MediaQuery.sizeOf(context).width < 760 ? 24 : 72, vertical: 80), color: _panel, child: LayoutBuilder(builder: (context, c) {
    final text = Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: const <Widget>[_Eyebrow(text: 'THE WORLD PULSE'), SizedBox(height: 15), Text('Football that\nfeels alive.', style: TextStyle(fontFamily: 'BarlowCondensed', color: _white, fontSize: 58, height: .9, fontWeight: FontWeight.w700)), SizedBox(height: 16), Text('The world keeps moving after you close the app. Markets shift. Players rise. Clubs win. Matches happen. Stories spread. GTEX turns that movement into a living feed you can act on.', style: TextStyle(color: _muted, fontSize: 15, height: 1.55))]);
    final visual = Container(height: 350, decoration: BoxDecoration(borderRadius: BorderRadius.circular(24), border: Border.all(color: _line), image: const DecorationImage(image: AssetImage('assets/media/gtex_matchday_wallpaper.png'), fit: BoxFit.cover, opacity: .45)), child: Stack(children: const <Widget>[_PulseCard(top: 24, left: 24, title: 'LIVE MATCH', value: '2 — 1', detail: '78\'  •  WORLD CUP'), _PulseCard(top: 118, right: 24, title: 'MARKET SIGNAL', value: '+12.8%', detail: 'BREAKOUT PLAYER'), _PulseCard(bottom: 24, left: 55, title: 'WORLD PULSE', value: 'LIVE', detail: 'MATCHES • MARKET • NEWS')]));
    if (c.maxWidth < 820) return Column(children: <Widget>[text, const SizedBox(height: 34), visual]);
    return Row(children: <Widget>[Expanded(child: text), const SizedBox(width: 55), Expanded(child: visual)]);
  }));
}

class _PulseCard extends StatelessWidget {
  const _PulseCard({this.top, this.bottom, this.left, this.right, required this.title, required this.value, required this.detail});
  final double? top, bottom, left, right; final String title, value, detail;
  @override
  Widget build(BuildContext context) => Positioned(top: top, bottom: bottom, left: left, right: right, child: Container(width: 210, padding: const EdgeInsets.all(15), decoration: BoxDecoration(color: const Color(0xDD080D11), borderRadius: BorderRadius.circular(14), border: Border.all(color: _line)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[Text(title, style: const TextStyle(fontFamily: 'DMMono', color: _muted, fontSize: 9, letterSpacing: 1.2)), const SizedBox(height: 7), Text(value, style: const TextStyle(fontFamily: 'BarlowCondensed', color: _lime, fontSize: 31, fontWeight: FontWeight.w700)), Text(detail, style: const TextStyle(color: _white, fontSize: 10))]));
}

class _AudienceSection extends StatelessWidget {
  const _AudienceSection({this.onSignup, this.onCreatorSignup, this.onTraderSignup});
  final VoidCallback? onSignup, onCreatorSignup, onTraderSignup;
  @override
  Widget build(BuildContext context) => Container(padding: EdgeInsets.fromLTRB(MediaQuery.sizeOf(context).width < 760 ? 24 : 72, 84, MediaQuery.sizeOf(context).width < 760 ? 24 : 72, 84), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[const _Eyebrow(text: 'YOUR ROLE. YOUR GTEX.'), const SizedBox(height: 15), const Text('Come for the football.\nStay for the world.', style: TextStyle(fontFamily: 'BarlowCondensed', color: _white, fontSize: 56, height: .9, fontWeight: FontWeight.w700)), const SizedBox(height: 32), LayoutBuilder(builder: (_, c) { final narrow = c.maxWidth < 820; final cards = <Widget>[_RoleCard('PLAYERS', 'Get discovered. Build your profile. Grow your career.', Icons.directions_run_rounded, _lime, onSignup), _RoleCard('CLUBS & SCOUTS', 'Find talent. Build squads. Recruit with intelligence.', Icons.stadium_rounded, _green, onSignup), _RoleCard('CREATORS & FANS', 'Tell stories. Build communities. Battle for your side.', Icons.campaign_rounded, Color(0xFFFF5FA2), onCreatorSignup), _RoleCard('TRADERS & OWNERS', 'Participate in the football economy with dedicated tools.', Icons.candlestick_chart_rounded, _gold, onTraderSignup)]; return narrow ? Column(children: cards.map((e) => Padding(padding: const EdgeInsets.only(bottom: 12), child: e)).toList()) : GridView.count(shrinkWrap: true, physics: const NeverScrollableScrollPhysics(), crossAxisCount: 2, crossAxisSpacing: 12, mainAxisSpacing: 12, childAspectRatio: 2.4, children: cards); })]));
}

class _RoleCard extends StatelessWidget {
  const _RoleCard(this.title, this.body, this.icon, this.accent, this.onTap);
  final String title, body; final IconData icon; final Color accent; final VoidCallback? onTap;
  @override
  Widget build(BuildContext context) => InkWell(onTap: onTap, borderRadius: BorderRadius.circular(18), child: Container(padding: const EdgeInsets.all(20), decoration: BoxDecoration(color: _panel, borderRadius: BorderRadius.circular(18), border: Border.all(color: _line)), child: Row(children: <Widget>[Container(width: 48, height: 48, decoration: BoxDecoration(color: accent.withValues(alpha: .1), borderRadius: BorderRadius.circular(14)), child: Icon(icon, color: accent)), const SizedBox(width: 16), Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: <Widget>[Text(title, style: TextStyle(fontFamily: 'DMMono', color: accent, fontSize: 10, letterSpacing: 1.2)), const SizedBox(height: 5), Text(body, style: const TextStyle(color: _white, fontSize: 13, height: 1.35))])), const Icon(Icons.arrow_forward_rounded, color: _muted, size: 19)]));
}

class _HowItWorks extends StatelessWidget {
  const _HowItWorks();
  @override
  Widget build(BuildContext context) => Container(padding: EdgeInsets.symmetric(horizontal: MediaQuery.sizeOf(context).width < 760 ? 24 : 72, vertical: 80), color: _panel, child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[const _Eyebrow(text: 'THE GTEX LOOP'), SizedBox(height: 15), Text('DISCOVER → DECIDE → ACT → WIN', style: TextStyle(fontFamily: 'BarlowCondensed', color: _white, fontSize: 48, fontWeight: FontWeight.w700)), SizedBox(height: 34), Wrap(spacing: 10, runSpacing: 10, children: const <Widget>[_Loop(n: '01', t: 'DISCOVER', b: 'Find talent, clubs, matches and stories.', c: _lime), _Loop(n: '02', t: 'EVALUATE', b: 'Use profiles, data, reports and market signals.', c: _blue), _Loop(n: '03', t: 'ACT', b: 'Scout, trade, build, compete, create or connect.', c: _green), _Loop(n: '04', t: 'PROGRESS', b: 'Win, grow value, build reputation and unlock more.', c: _gold)] )]));
}

class _Loop extends StatelessWidget {
  const _Loop({required this.n, required this.t, required this.b, required this.c});
  final String n, t, b; final Color c;
  @override
  Widget build(BuildContext context) => Container(width: 270, padding: const EdgeInsets.all(20), decoration: BoxDecoration(color: _ink, borderRadius: BorderRadius.circular(16), border: Border.all(color: _line)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[Text(n, style: TextStyle(fontFamily: 'DMMono', color: c, fontSize: 11)), const SizedBox(height: 22), Text(t, style: const TextStyle(fontFamily: 'BarlowCondensed', color: _white, fontSize: 27, fontWeight: FontWeight.w700)), const SizedBox(height: 6), Text(b, style: const TextStyle(color: _muted, fontSize: 12, height: 1.4))]);
}

class _FinalCta extends StatelessWidget {
  const _FinalCta({this.onSignup});
  final VoidCallback? onSignup;
  @override
  Widget build(BuildContext context) => Container(padding: EdgeInsets.symmetric(horizontal: 24, vertical: 100), decoration: const BoxDecoration(gradient: RadialGradient(center: Alignment.center, radius: 1.1, colors: <Color>[Color(0x2036E38A), _ink])), child: Center(child: Column(children: <Widget>[SvgPicture.asset('assets/branding/gtex_mark_22.svg', width: 76, height: 76), const SizedBox(height: 22), const Text('YOUR FOOTBALL WORLD\nSTARTS HERE.', textAlign: TextAlign.center, style: TextStyle(fontFamily: 'BarlowCondensed', color: _white, fontSize: 58, height: .88, fontWeight: FontWeight.w700)), const SizedBox(height: 16), const Text('One identity. One world. Infinite football.', style: TextStyle(color: _muted, fontSize: 15)), const SizedBox(height: 28), _GlowButton(label: 'Enter GTEX', onPressed: onSignup, large: true)]));
}

class _Footer extends StatelessWidget {
  const _Footer();
  @override
  Widget build(BuildContext context) => const Padding(padding: EdgeInsets.all(28), child: Row(children: <Widget>[Text('GTEX', style: TextStyle(fontFamily: 'BarlowCondensed', color: _white, fontSize: 20, fontWeight: FontWeight.w700)), Spacer(), Text('GLOBAL TALENT EXCHANGE  •  THE LIVING FOOTBALL ECONOMY', style: TextStyle(fontFamily: 'DMMono', color: _muted, fontSize: 9, letterSpacing: 1))]));
}

class _MicroBadge extends StatelessWidget {
  const _MicroBadge({required this.icon, required this.text});
  final IconData icon; final String text;
  @override
  Widget build(BuildContext context) => Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7), decoration: BoxDecoration(color: const Color(0xAA080D11), borderRadius: BorderRadius.circular(30), border: Border.all(color: _line)), child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[Icon(icon, color: _muted, size: 13), const SizedBox(width: 6), Text(text, style: const TextStyle(color: _white, fontSize: 11, fontWeight: FontWeight.w600))]));
}

class _GlowButton extends StatelessWidget {
  const _GlowButton({required this.label, required this.onPressed, this.large = false});
  final String label; final VoidCallback? onPressed; final bool large;
  @override
  Widget build(BuildContext context) => FilledButton(onPressed: onPressed, style: FilledButton.styleFrom(backgroundColor: _lime, foregroundColor: const Color(0xFF08100A), padding: EdgeInsets.symmetric(horizontal: large ? 22 : 16, vertical: large ? 17 : 12), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)), elevation: 0), child: Text(label, style: TextStyle(fontWeight: FontWeight.w800, fontSize: large ? 13 : 12, letterSpacing: .2)));
}

class _GhostButton extends StatelessWidget {
  const _GhostButton({required this.label, required this.onPressed});
  final String label; final VoidCallback? onPressed;
  @override
  Widget build(BuildContext context) => OutlinedButton(onPressed: onPressed, style: OutlinedButton.styleFrom(foregroundColor: _white, side: const BorderSide(color: _line), padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))), child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[Text(label, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12)), const SizedBox(width: 8), const Icon(Icons.arrow_forward_rounded, size: 16)]));
}
