import 'package:flutter/material.dart';

import 'gtex_home_shared_widgets.dart';

class GtexWiderUniverseSection extends StatelessWidget {
  const GtexWiderUniverseSection({super.key});

  @override
  Widget build(BuildContext context) {
    final double width = MediaQuery.sizeOf(context).width;
    final bool isNarrow = width < 760;

    return Container(
      color: kNavyBase,
      padding: EdgeInsets.symmetric(
        horizontal: isNarrow ? 20 : 64,
        vertical: 72,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          // Section Masthead
          const GtexSectionHeader(
            eyebrow: 'The Wider Football Universe',
            title: 'National Federation Rentals, Tacticians & Living Culture',
            subtitle: 'The GTEX football universe is alive 24/7 even when you are away from the dugout. Lease your star regens to national teams for international glory, appoint renowned tacticians, and join fervent fan tribes.',
            accentColor: kSkyBlue,
          ),

          const SizedBox(height: 36),

          // 3 Feature Cards Layout (Rentals, Managers, Fan Culture)
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool wide = constraints.maxWidth > 900;
              final double cardWidth = wide ? (constraints.maxWidth - 32) / 3 : constraints.maxWidth;

              return wide
                  ? Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        SizedBox(width: cardWidth, child: _RentalCard()),
                        const SizedBox(width: 16),
                        SizedBox(width: cardWidth, child: _ManagerMarketCard()),
                        const SizedBox(width: 16),
                        SizedBox(width: cardWidth, child: _FanCultureCard()),
                      ],
                    )
                  : Column(
                      children: const <Widget>[
                        _RentalCard(),
                        SizedBox(height: 16),
                        _ManagerMarketCard(),
                        SizedBox(height: 16),
                        _FanCultureCard(),
                      ],
                    );
            },
          ),
        ],
      ),
    );
  }
}

class _RentalCard extends StatelessWidget {
  const _RentalCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: kNavyRaised,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: kNavyLine),
      ),
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const GtexTagPill(
            label: 'NATIONAL TEAM RENTALS',
            color: kSkyBlue,
            icon: Icons.flag_rounded,
          ),
          const SizedBox(height: 16),
          const Text(
            'International Tournament Call-Ups',
            style: TextStyle(
              color: kTextPrimary,
              fontSize: 20,
              fontWeight: FontWeight.w800,
              fontFamily: kFontCondensed,
            ),
          ),
          const SizedBox(height: 10),
          const Text(
            'National federations rent eligible domestic and regen superstars for international tournament campaigns. Owners collect verified rental fees while their players earn caps, prestige, and tournament medals.',
            style: TextStyle(
              color: kTextSecondary,
              fontSize: 13,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 20),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: kNavyInset,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: kNavyLine),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const <Widget>[
                _KeyBenefitRow(icon: Icons.monetization_on_rounded, text: 'Direct rental fee credited to owner ledger'),
                SizedBox(height: 6),
                _KeyBenefitRow(icon: Icons.military_tech_rounded, text: '+15% Big-Match Composure on return'),
                SizedBox(height: 6),
                _KeyBenefitRow(icon: Icons.public_rounded, text: 'Player global valuation rises with international caps'),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ManagerMarketCard extends StatelessWidget {
  const _ManagerMarketCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: kNavyRaised,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: kNavyLine),
      ),
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const GtexTagPill(
            label: 'TACTICAL PHILOSOPHIES',
            color: kGoldPrimary,
            icon: Icons.psychology_rounded,
          ),
          const SizedBox(height: 16),
          const Text(
            'Elite Manager Marketplace',
            style: TextStyle(
              color: kTextPrimary,
              fontSize: 20,
              fontWeight: FontWeight.w800,
              fontFamily: kFontCondensed,
            ),
          ),
          const SizedBox(height: 10),
          const Text(
            'Appoint tacticians with distinct doctrines: Gegenpress, Tiki-taka, Low-Block Counter, and Direct Possession. Tactical styles govern spatial simulation behaviors and unlock customized set-piece variants.',
            style: TextStyle(
              color: kTextSecondary,
              fontSize: 13,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 20),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: kNavyInset,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: kNavyLine),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const <Widget>[
                _KeyBenefitRow(icon: Icons.auto_graph_rounded, text: 'Gegenpress: +12% high-turnover recoveries'),
                SizedBox(height: 6),
                _KeyBenefitRow(icon: Icons.swap_horiz_rounded, text: 'Tiki-taka: +18% central passing retention'),
                SizedBox(height: 6),
                _KeyBenefitRow(icon: Icons.shield_rounded, text: 'Low-Block: +22% box duel success rate'),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _FanCultureCard extends StatelessWidget {
  const _FanCultureCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: kNavyRaised,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: kNavyLine),
      ),
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const GtexTagPill(
            label: 'COMMUNITY & TRIBES',
            color: kPitchGreenBright,
            icon: Icons.groups_rounded,
          ),
          const SizedBox(height: 16),
          const Text(
            'Fan Warfare & Social Matchday',
            style: TextStyle(
              color: kTextPrimary,
              fontSize: 20,
              fontWeight: FontWeight.w800,
              fontFamily: kFontCondensed,
            ),
          ),
          const SizedBox(height: 10),
          const Text(
            'Supporters join club fan tribes, wage Fan Wars during derby weeks, send live match reactions, and participate in award ceremony voting for the global Ballon d\'Or equivalent.',
            style: TextStyle(
              color: kTextSecondary,
              fontSize: 13,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 20),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: kNavyInset,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: kNavyLine),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const <Widget>[
                _KeyBenefitRow(icon: Icons.local_fire_department_rounded, text: 'Fan tribe derby multipliers on matchday'),
                SizedBox(height: 6),
                _KeyBenefitRow(icon: Icons.how_to_vote_rounded, text: 'Annual regen awards and ceremony balloting'),
                SizedBox(height: 6),
                _KeyBenefitRow(icon: Icons.forum_rounded, text: 'Realtime spectator chat with tactical emotes'),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _KeyBenefitRow extends StatelessWidget {
  const _KeyBenefitRow({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        Icon(icon, size: 14, color: kGoldPrimary),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            text,
            style: const TextStyle(
              color: kTextPrimary,
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ],
    );
  }
}
