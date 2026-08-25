import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';

class Gtex22AuthGateway extends StatelessWidget {
  const Gtex22AuthGateway({super.key, this.onLogin});
  final VoidCallback? onLogin;

  @override
  Widget build(BuildContext context) {
    final narrow = MediaQuery.sizeOf(context).width < 820;
    final roles = <_Role>[
      const _Role('PLAYER / CLUB', 'Build your football identity, discover talent, manage squads and compete.', Icons.sports_soccer_rounded, Color(0xFFB9FF3D), '/auth/signup/user'),
      const _Role('CREATOR', 'Publish football stories, grow a following and build your community.', Icons.campaign_rounded, Color(0xFFFF5FA2), '/auth/signup/creator'),
      const _Role('TRADER', 'Access the GTEX economy with dedicated trading and wallet security.', Icons.candlestick_chart_rounded, Color(0xFFFFC857), '/auth/signup/trader'),
    ];
    return Scaffold(
      backgroundColor: const Color(0xFF050709),
      body: SafeArea(child: Center(child: SingleChildScrollView(padding: EdgeInsets.all(narrow ? 20 : 42), child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 1160), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        Row(children: <Widget>[SvgPicture.asset('assets/branding/gtex_wordmark_22.svg', width: 170, height: 40), const Spacer(), TextButton.icon(onPressed: onLogin, icon: const Icon(Icons.login_rounded, size: 17), label: const Text('Already have an account? Sign in'))]),
        const SizedBox(height: 55),
        const Text('ENTER THE\nFOOTBALL WORLD.', style: TextStyle(fontFamily: 'BarlowCondensed', color: Color(0xFFF4F7F8), fontSize: 68, height: .84, fontWeight: FontWeight.w700, letterSpacing: -1.5)),
        const SizedBox(height: 16),
        const SizedBox(width: 660, child: Text('One account opens a living football ecosystem of talent, clubs, markets, matches and community. Pick the way you want to play.', style: TextStyle(color: Color(0xFF93A0AA), fontSize: 16, height: 1.55))),
        const SizedBox(height: 34),
        LayoutBuilder(builder: (_, c) { final columns = c.maxWidth > 920 ? 3 : c.maxWidth > 580 ? 2 : 1; return GridView.builder(shrinkWrap: true, physics: const NeverScrollableScrollPhysics(), itemCount: roles.length, gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: columns, crossAxisSpacing: 14, mainAxisSpacing: 14, childAspectRatio: columns == 1 ? 2.5 : 1.2), itemBuilder: (_, i) => _RoleCard(role: roles[i])); }),
        const SizedBox(height: 30),
        Container(padding: const EdgeInsets.all(18), decoration: BoxDecoration(color: const Color(0xFF0A0F13), borderRadius: BorderRadius.circular(16), border: Border.all(color: const Color(0xFF1C2830))), child: const Row(children: <Widget>[Icon(Icons.verified_user_rounded, color: Color(0xFF36E38A), size: 20), SizedBox(width: 12), Expanded(child: Text('Secure identity, protected account sessions and role-aware onboarding. KYC is requested where the platform actually needs it.', style: TextStyle(color: Color(0xFF93A0AA), fontSize: 12, height: 1.45)))])),
      ]))))),
    );
  }
}

class _Role { const _Role(this.title, this.body, this.icon, this.accent, this.route); final String title, body, route; final IconData icon; final Color accent; }
class _RoleCard extends StatelessWidget { const _RoleCard({required this.role}); final _Role role; @override Widget build(BuildContext context) => InkWell(onTap: () => context.go(role.route), borderRadius: BorderRadius.circular(20), child: Container(padding: const EdgeInsets.all(22), decoration: BoxDecoration(color: const Color(0xFF0A0F13), borderRadius: BorderRadius.circular(20), border: Border.all(color: role.accent.withValues(alpha: .28))), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[Container(width: 48, height: 48, decoration: BoxDecoration(color: role.accent.withValues(alpha: .1), borderRadius: BorderRadius.circular(14)), child: Icon(role.icon, color: role.accent)), const Spacer(), Text(role.title, style: TextStyle(fontFamily: 'DMMono', color: role.accent, fontSize: 10, letterSpacing: 1.2)), const SizedBox(height: 7), Text(role.body, style: const TextStyle(color: Color(0xFFF4F7F8), fontSize: 13, height: 1.4)), const SizedBox(height: 15), const Row(children: <Widget>[Text('CONTINUE', style: TextStyle(color: Color(0xFF93A0AA), fontFamily: 'DMMono', fontSize: 9, letterSpacing: 1)), Spacer(), Icon(Icons.arrow_forward_rounded, color: Color(0xFF93A0AA), size: 17)])])); }

class Gtex22LoginScreen extends StatefulWidget {
  const Gtex22LoginScreen({super.key, required this.controller, this.onSignup});
  final GteExchangeController controller;
  final VoidCallback? onSignup;
  @override State<Gtex22LoginScreen> createState() => _Gtex22LoginScreenState();
}

class _Gtex22LoginScreenState extends State<Gtex22LoginScreen> {
  final _email = TextEditingController(); final _password = TextEditingController(); bool _busy = false; String? _error; bool _obscure = true;
  @override void dispose() { _email.dispose(); _password.dispose(); super.dispose(); }
  Future<void> _submit() async { setState(() { _busy = true; _error = null; }); try { await widget.controller.signIn(email: _email.text.trim(), password: _password.text); if (mounted && widget.controller.isAuthenticated) context.go('/app/home'); } catch (e) { if (mounted) setState(() => _error = e.toString()); } finally { if (mounted) setState(() => _busy = false); } }
  @override Widget build(BuildContext context) => Scaffold(backgroundColor: const Color(0xFF050709), body: SafeArea(child: Center(child: SingleChildScrollView(padding: const EdgeInsets.all(24), child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 1040), child: LayoutBuilder(builder: (_, c) { final narrow = c.maxWidth < 780; final form = _form(context); final story = Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: const <Widget>[_Eyebrow(text: 'WELCOME BACK TO GTEX'), SizedBox(height: 18), Text('THE WORLD\nIS STILL MOVING.', style: TextStyle(fontFamily: 'BarlowCondensed', color: Color(0xFFF4F7F8), fontSize: 62, height: .84, fontWeight: FontWeight.w700)), SizedBox(height: 16), Text('Pick up where you left off. Your club, talent watchlist, market activity, matches and community are waiting.', style: TextStyle(color: Color(0xFF93A0AA), fontSize: 15, height: 1.5)), SizedBox(height: 28), _TinyStat('LIVE WORLD', 'MATCHES • MARKET • NEWS'), _TinyStat('YOUR IDENTITY', 'CLUB • PLAYER • CREATOR • TRADER')]); return narrow ? Column(children: <Widget>[story, const SizedBox(height: 34), form]) : Row(crossAxisAlignment: CrossAxisAlignment.center, children: <Widget>[Expanded(child: story), const SizedBox(width: 70), SizedBox(width: 390, child: form)]); }))))));
  Widget _form(BuildContext context) => Container(padding: const EdgeInsets.all(26), decoration: BoxDecoration(color: const Color(0xFF0A0F13), borderRadius: BorderRadius.circular(22), border: Border.all(color: const Color(0xFF1C2830))), child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[SvgPicture.asset('assets/branding/gtex_mark_22.svg', width: 48, height: 48, alignment: Alignment.centerLeft), const SizedBox(height: 20), const Text('Sign in', style: TextStyle(fontFamily: 'BarlowCondensed', color: Color(0xFFF4F7F8), fontSize: 34, fontWeight: FontWeight.w700)), const SizedBox(height: 5), const Text('Continue your football world.', style: TextStyle(color: Color(0xFF93A0AA), fontSize: 12)), const SizedBox(height: 22), _field(_email, 'Email', Icons.mail_outline_rounded), const SizedBox(height: 11), _passwordField(), if (_error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(_error!, style: const TextStyle(color: Color(0xFFFF6B7A), fontSize: 11)),), const SizedBox(height: 18), FilledButton(onPressed: _busy ? null : _submit, style: FilledButton.styleFrom(backgroundColor: const Color(0xFFB9FF3D), foregroundColor: const Color(0xFF08100A), padding: const EdgeInsets.symmetric(vertical: 16), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))), child: _busy ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Text('ENTER GTEX', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12, letterSpacing: .8))), const SizedBox(height: 16), Row(children: const <Widget>[Expanded(child: Divider(color: Color(0xFF1C2830))), Padding(padding: EdgeInsets.symmetric(horizontal: 10), child: Text('OR', style: TextStyle(color: Color(0xFF66737D), fontFamily: 'DMMono', fontSize: 9))), Expanded(child: Divider(color: Color(0xFF1C2830)))]), const SizedBox(height: 14), OutlinedButton(onPressed: widget.onSignup ?? () => context.go('/auth'), style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFFF4F7F8), side: const BorderSide(color: Color(0xFF1C2830)), padding: const EdgeInsets.symmetric(vertical: 14)), child: const Text('CREATE A GTEX ID', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 11))) ]);
  Widget _field(TextEditingController c, String label, IconData icon) => TextField(controller: c, keyboardType: TextInputType.emailAddress, style: const TextStyle(color: Color(0xFFF4F7F8), fontSize: 13), decoration: _decoration(label, icon));
  Widget _passwordField() => TextField(controller: _password, obscureText: _obscure, style: const TextStyle(color: Color(0xFFF4F7F8), fontSize: 13), decoration: _decoration('Password', Icons.lock_outline_rounded).copyWith(suffixIcon: IconButton(onPressed: () => setState(() => _obscure = !_obscure), icon: Icon(_obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined, color: const Color(0xFF66737D), size: 18))));
  InputDecoration _decoration(String label, IconData icon) => InputDecoration(labelText: label, labelStyle: const TextStyle(color: Color(0xFF66737D), fontSize: 12), prefixIcon: Icon(icon, color: const Color(0xFF66737D), size: 18), filled: true, fillColor: const Color(0xFF070B0F), border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1C2830))), enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1C2830))), focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF36E38A))));
}

class _Eyebrow extends StatelessWidget { const _Eyebrow({required this.text}); final String text; @override Widget build(BuildContext context) => Row(children: <Widget>[Container(width: 6, height: 6, decoration: const BoxDecoration(color: Color(0xFFB9FF3D), shape: BoxShape.circle)), const SizedBox(width: 8), Text(text, style: const TextStyle(fontFamily: 'DMMono', color: Color(0xFFB9FF3D), fontSize: 10, letterSpacing: 1.6))]); }
class _TinyStat extends StatelessWidget { const _TinyStat(this.a, this.b); final String a, b; @override Widget build(BuildContext context) => Padding(padding: const EdgeInsets.only(bottom: 9), child: Row(children: <Widget>[Text(a, style: const TextStyle(fontFamily: 'DMMono', color: Color(0xFFF4F7F8), fontSize: 9, letterSpacing: 1)), const SizedBox(width: 10), Text(b, style: const TextStyle(color: Color(0xFF66737D), fontSize: 11))])); }
