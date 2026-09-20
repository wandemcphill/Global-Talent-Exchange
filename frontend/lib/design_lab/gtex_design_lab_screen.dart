import 'package:flutter/material.dart';

import '../ui_gtex/ui_gtex.dart';

/// Isolated visual exploration only. The fixtures below are never read by a
/// production route or provider; `/design-lab` is intentionally unlinked from
/// the GTEX shell and exists for design review and visual regression capture.
class GtexDesignLabScreen extends StatefulWidget {
  const GtexDesignLabScreen({super.key, this.initialDirection});

  final String? initialDirection;

  @override
  State<GtexDesignLabScreen> createState() => _GtexDesignLabScreenState();
}

class _GtexDesignLabScreenState extends State<GtexDesignLabScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs = TabController(
    length: 3,
    vsync: this,
    initialIndex: _initialDirectionIndex(),
  );

  /// Enables deterministic visual-regression captures without linking the lab
  /// into production navigation. Widget interaction remains the normal review
  /// path; this only selects the opening specimen on Flutter Web.
  int _initialDirectionIndex() {
    final Uri baseUri = Uri.base;
    final String fragment = baseUri.fragment;
    final int fragmentQueryStart = fragment.indexOf('?');
    final String? requestedDirection =
        widget.initialDirection ??
        baseUri.queryParameters['direction'] ??
        (fragmentQueryStart < 0
            ? null
            : Uri.splitQueryString(
              fragment.substring(fragmentQueryStart + 1),
            )['direction']);
    switch (requestedDirection) {
      case 'club':
        return 1;
      case 'ownership':
        return 2;
      case 'matchday':
      default:
        return 0;
    }
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: GtexColors.surfaceBase,
      appBar: AppBar(
        backgroundColor: GtexColors.surfaceBase,
        foregroundColor: GtexColors.textPrimary,
        title: const Text('GTEX Design Lab'),
        bottom: TabBar(
          controller: _tabs,
          isScrollable: true,
          tabs: const <Widget>[
            Tab(text: 'A · Matchday Pulse'),
            Tab(text: 'B · Club Atlas'),
            Tab(text: 'C · Ownership Ledger'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabs,
        children: const <Widget>[
          _DesignLabDirection(direction: _DesignDirection.matchday),
          _DesignLabDirection(direction: _DesignDirection.club),
          _DesignLabDirection(direction: _DesignDirection.ownership),
        ],
      ),
    );
  }
}

enum _DesignDirection { matchday, club, ownership }

class _DesignLabDirection extends StatelessWidget {
  const _DesignLabDirection({required this.direction});
  final _DesignDirection direction;

  @override
  Widget build(BuildContext context) {
    final _LabDirectionData data = _LabDirectionData.forDirection(direction);
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 20, 16, 60),
      children: <Widget>[
        Semantics(
          label: 'Design Lab fixtures only',
          child: Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: GtexCommandTokens.pending.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
              border: Border.all(
                color: GtexCommandTokens.pending.withValues(alpha: 0.4),
              ),
            ),
            child: Text(
              'ISOLATED FIXTURE MODE · No live GTEX data is rendered here.',
              style: GtexText.labelSM.copyWith(
                color: GtexCommandTokens.pending,
              ),
            ),
          ),
        ),
        const SizedBox(height: 16),
        GtexCommandCenterMasthead(
          eyebrow: 'Direction ${data.letter} · ${data.name}',
          identity: data.identity,
          identityDetail: data.identityDetail,
          title: data.title,
          summary: data.summary,
          statusLabel: data.status,
          status: data.statusState,
          metrics: data.metrics,
          primaryAction: GtexCommandAction(
            label: data.primaryAction,
            icon: data.primaryIcon,
            onPressed: () {},
          ),
          secondaryAction: GtexCommandAction(
            label: 'Explore direction',
            icon: Icons.auto_awesome_outlined,
            onPressed: () {},
            secondary: true,
            accent: data.accent,
          ),
        ),
        const SizedBox(height: 20),
        _DirectionBoard(data: data),
        const SizedBox(height: 28),
        const _LabSectionTitle(
          eyebrow: 'PRIMITIVE LIBRARY',
          title: 'Shared GTEX components and state treatments',
          detail:
              'Every specimen is controlled local fixture data. Production Home uses the command-center primitives, not these fixture values.',
        ),
        const SizedBox(height: 14),
        const _PrimitiveLibrary(),
      ],
    );
  }
}

class _DirectionBoard extends StatelessWidget {
  const _DirectionBoard({required this.data});
  final _LabDirectionData data;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (BuildContext context, BoxConstraints constraints) {
      final bool wide = constraints.maxWidth >= 920;
      final List<Widget> focus = data.focus
          .map(
            (_LabFocus item) => GtexCommandFocusTile(
              kicker: item.kicker,
              title: item.title,
              detail: item.detail,
              icon: item.icon,
              accent: item.accent,
              onTap: () {},
            ),
          )
          .toList(growable: false);
      final Widget story = _StorySurface(data: data);
      if (!wide) {
        return Column(
          children: <Widget>[
            story,
            const SizedBox(height: 12),
            ...focus.map(
              (Widget item) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: item,
              ),
            ),
          ],
        );
      }
      return Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Expanded(flex: 5, child: story),
          const SizedBox(width: 16),
          Expanded(
            flex: 4,
            child: Column(
              children: focus
                  .map(
                    (Widget item) => Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: item,
                    ),
                  )
                  .toList(growable: false),
            ),
          ),
        ],
      );
    },
  );
}

class _StorySurface extends StatelessWidget {
  const _StorySurface({required this.data});
  final _LabDirectionData data;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(GtexSpacing.lg),
    decoration: BoxDecoration(
      color: GtexColors.surfaceRaised,
      borderRadius: BorderRadius.circular(GtexCommandTokens.panelRadius),
      border: Border.all(color: data.accent.withValues(alpha: 0.4)),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Icon(data.storyIcon, color: data.accent, size: 24),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                data.storyKicker.toUpperCase(),
                style: GtexText.labelSM.copyWith(color: data.accent),
              ),
            ),
            const _MiniStateBadge(
              label: 'FIXTURE',
              color: GtexCommandTokens.settled,
            ),
          ],
        ),
        const SizedBox(height: 18),
        Text(
          data.storyTitle,
          style: GtexText.displayLG.copyWith(color: GtexColors.textPrimary),
        ),
        const SizedBox(height: 8),
        Text(
          data.storyDetail,
          style: GtexText.bodyMD.copyWith(color: GtexColors.textSecondary),
        ),
        const SizedBox(height: 20),
        if (data.direction == _DesignDirection.matchday)
          const _MiniPitch()
        else if (data.direction == _DesignDirection.club)
          const _ClubIdentitySpecimen()
        else
          const _OwnershipSpecimen(),
      ],
    ),
  );
}

class _PrimitiveLibrary extends StatelessWidget {
  const _PrimitiveLibrary();
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: <Widget>[
      const _LibraryGroup(
        title: 'Actions and status',
        child: _ActionSpecimens(),
      ),
      const SizedBox(height: 16),
      const _LibraryGroup(
        title: 'Identity, player, rank, and reward',
        child: _IdentitySpecimens(),
      ),
      const SizedBox(height: 16),
      const _LibraryGroup(
        title: 'Truthful state treatments',
        child: _StateSpecimens(),
      ),
    ],
  );
}

class _LibraryGroup extends StatelessWidget {
  const _LibraryGroup({required this.title, required this.child});
  final String title;
  final Widget child;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(GtexSpacing.md),
    decoration: BoxDecoration(
      color: GtexColors.surfaceRaised,
      borderRadius: BorderRadius.circular(GtexCommandTokens.panelRadius),
      border: Border.all(color: GtexColors.surfaceBorder),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          title,
          style: GtexText.displaySM.copyWith(color: GtexColors.textPrimary),
        ),
        const SizedBox(height: 14),
        child,
      ],
    ),
  );
}

class _ActionSpecimens extends StatelessWidget {
  const _ActionSpecimens();
  @override
  Widget build(BuildContext context) => Wrap(
    spacing: 10,
    runSpacing: 10,
    children: <Widget>[
      GtexCommandAction(
        label: 'Enter matchday',
        icon: Icons.sports_soccer_rounded,
        onPressed: () {},
      ),
      GtexCommandAction(
        label: 'Scout market',
        icon: Icons.radar_rounded,
        onPressed: () {},
        accent: GtexCommandTokens.coin,
        secondary: true,
      ),
      const _MiniStateBadge(label: 'LIVE', color: GtexCommandTokens.live),
      const _MiniStateBadge(label: 'PENDING', color: GtexCommandTokens.pending),
      const _MiniStateBadge(label: 'SETTLED', color: GtexCommandTokens.settled),
    ],
  );
}

class _IdentitySpecimens extends StatelessWidget {
  const _IdentitySpecimens();
  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (BuildContext context, BoxConstraints constraints) {
      final double column =
          constraints.maxWidth >= 760
              ? (constraints.maxWidth - 24) / 3
              : constraints.maxWidth;
      return Wrap(
        spacing: 12,
        runSpacing: 12,
        children: <Widget>[
          SizedBox(width: column, child: const _ClubIdentitySpecimen()),
          SizedBox(width: column, child: _RankRewardSpecimen()),
          SizedBox(
            width: column,
            child: const GtexPlayerCard(
              name: 'Ayo Mensah',
              position: 'CM',
              clubName: 'Lagos Comets',
              nationality: 'GHA',
              priceLabel: 'GTC 18.4K',
              isOwned: true,
              ownershipLabel: '12 shares owned',
              scale: GtexPlayerCardScale.compact,
            ),
          ),
        ],
      );
    },
  );
}

class _RankRewardSpecimen extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: GtexColors.surfaceOverlay,
      borderRadius: BorderRadius.circular(12),
      border: Border.all(
        color: GtexCommandTokens.prestige.withValues(alpha: 0.45),
      ),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          'RANK INDICATOR',
          style: GtexText.labelSM.copyWith(color: GtexCommandTokens.prestige),
        ),
        const SizedBox(height: 8),
        Text(
          '#18',
          style: GtexText.monoXL.copyWith(color: GtexColors.textPrimary),
        ),
        Text(
          'West Africa club standing',
          style: GtexText.bodySM.copyWith(color: GtexColors.textSecondary),
        ),
        const Divider(height: 24),
        Row(
          children: <Widget>[
            const Icon(
              Icons.workspace_premium_rounded,
              color: GtexCommandTokens.reward,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'MATCHDAY REWARD',
                    style: GtexText.labelSM.copyWith(
                      color: GtexCommandTokens.reward,
                    ),
                  ),
                  Text(
                    'Claim 240 Fan Coin',
                    style: GtexText.labelMD.copyWith(
                      color: GtexColors.textPrimary,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ],
    ),
  );
}

class _StateSpecimens extends StatelessWidget {
  const _StateSpecimens();
  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (BuildContext context, BoxConstraints constraints) {
      final double width =
          constraints.maxWidth >= 760
              ? (constraints.maxWidth - 24) / 3
              : constraints.maxWidth;
      return Wrap(
        spacing: 12,
        runSpacing: 12,
        children: <Widget>[
          SizedBox(
            width: width,
            child: const _StateCard(
              icon: Icons.hourglass_top_rounded,
              title: 'Loading matchday',
              detail: 'Authoritative match data is being checked.',
              accent: GtexCommandTokens.competition,
            ),
          ),
          SizedBox(
            width: width,
            child: const _StateCard(
              icon: Icons.shield_outlined,
              title: 'No club yet',
              detail: 'Create or acquire a club to unlock club decisions.',
              accent: GtexCommandTokens.ownership,
            ),
          ),
          SizedBox(
            width: width,
            child: const _StateCard(
              icon: Icons.inbox_outlined,
              title: 'Quiet market',
              detail: 'No owned-player movement has been reported today.',
              accent: GtexCommandTokens.settled,
            ),
          ),
        ],
      );
    },
  );
}

class _StateCard extends StatelessWidget {
  const _StateCard({
    required this.icon,
    required this.title,
    required this.detail,
    required this.accent,
  });
  final IconData icon;
  final String title;
  final String detail;
  final Color accent;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: GtexColors.surfaceOverlay,
      borderRadius: BorderRadius.circular(12),
      border: Border.all(color: accent.withValues(alpha: 0.35)),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Icon(icon, color: accent),
        const SizedBox(height: 12),
        Text(
          title,
          style: GtexText.labelLG.copyWith(color: GtexColors.textPrimary),
        ),
        const SizedBox(height: 4),
        Text(
          detail,
          style: GtexText.bodySM.copyWith(color: GtexColors.textSecondary),
        ),
      ],
    ),
  );
}

class _MiniPitch extends StatelessWidget {
  const _MiniPitch();
  @override
  Widget build(BuildContext context) => AspectRatio(
    aspectRatio: 1.7,
    child: CustomPaint(
      painter: _MiniPitchPainter(),
      child: const Center(
        child: _MiniStateBadge(
          label: 'MATCHDAY COMMAND',
          color: GtexCommandTokens.pitch,
        ),
      ),
    ),
  );
}

class _MiniPitchPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final Rect rect = Offset.zero & size;
    final RRect rounded = RRect.fromRectAndRadius(
      rect,
      const Radius.circular(12),
    );
    canvas.drawRRect(rounded, Paint()..color = const Color(0xFF103826));
    final Paint line =
        Paint()
          ..color = GtexCommandTokens.pitch.withValues(alpha: .52)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.5;
    canvas.drawRRect(rounded, line);
    canvas.drawLine(
      Offset(size.width / 2, 0),
      Offset(size.width / 2, size.height),
      line,
    );
    canvas.drawCircle(
      Offset(size.width / 2, size.height / 2),
      size.height * .18,
      line,
    );
    canvas.drawRect(
      Rect.fromLTWH(0, size.height * .25, size.width * .12, size.height * .5),
      line,
    );
    canvas.drawRect(
      Rect.fromLTWH(
        size.width * .88,
        size.height * .25,
        size.width * .12,
        size.height * .5,
      ),
      line,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _ClubIdentitySpecimen extends StatelessWidget {
  const _ClubIdentitySpecimen();
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: GtexColors.surfaceOverlay,
      borderRadius: BorderRadius.circular(12),
      border: Border.all(
        color: GtexCommandTokens.ownership.withValues(alpha: 0.45),
      ),
    ),
    child: Row(
      children: <Widget>[
        Container(
          width: 52,
          height: 52,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: GtexCommandTokens.ownership.withValues(alpha: .16),
            border: Border.all(color: GtexCommandTokens.ownership, width: 2),
          ),
          child: const Icon(
            Icons.shield_rounded,
            color: GtexCommandTokens.ownership,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'LAGOS COMETS',
                style: GtexText.labelLG.copyWith(color: GtexColors.textPrimary),
              ),
              const SizedBox(height: 3),
              Text(
                'Club identity · Owned',
                style: GtexText.bodySM.copyWith(
                  color: GtexColors.textSecondary,
                ),
              ),
              const SizedBox(height: 6),
              const _MiniStateBadge(
                label: 'FOUNDED 2026',
                color: GtexCommandTokens.ownership,
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

class _OwnershipSpecimen extends StatelessWidget {
  const _OwnershipSpecimen();
  @override
  Widget build(BuildContext context) => Column(
    children: const <Widget>[
      _OwnershipLine(
        label: 'Owned player positions',
        value: '04',
        color: GtexCommandTokens.ownership,
      ),
      SizedBox(height: 10),
      _OwnershipLine(
        label: 'Value moved today',
        value: '+3.8%',
        color: GtexCommandTokens.coin,
      ),
      SizedBox(height: 10),
      _OwnershipLine(
        label: 'Open market actions',
        value: '02',
        color: GtexCommandTokens.competition,
      ),
    ],
  );
}

class _OwnershipLine extends StatelessWidget {
  const _OwnershipLine({
    required this.label,
    required this.value,
    required this.color,
  });
  final String label;
  final String value;
  final Color color;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
    decoration: BoxDecoration(
      color: color.withValues(alpha: .08),
      borderRadius: BorderRadius.circular(8),
    ),
    child: Row(
      children: <Widget>[
        Expanded(
          child: Text(
            label,
            style: GtexText.bodyMD.copyWith(color: GtexColors.textSecondary),
          ),
        ),
        Text(value, style: GtexText.monoLG.copyWith(color: color)),
      ],
    ),
  );
}

class _MiniStateBadge extends StatelessWidget {
  const _MiniStateBadge({required this.label, required this.color});
  final String label;
  final Color color;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
    decoration: BoxDecoration(
      color: color.withValues(alpha: .12),
      borderRadius: BorderRadius.circular(999),
      border: Border.all(color: color.withValues(alpha: .45)),
    ),
    child: Text(label, style: GtexText.labelSM.copyWith(color: color)),
  );
}

class _LabSectionTitle extends StatelessWidget {
  const _LabSectionTitle({
    required this.eyebrow,
    required this.title,
    required this.detail,
  });
  final String eyebrow;
  final String title;
  final String detail;
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: <Widget>[
      Text(
        eyebrow,
        style: GtexText.labelSM.copyWith(
          color: GtexCommandTokens.fan,
          letterSpacing: 1.2,
        ),
      ),
      const SizedBox(height: 5),
      Text(
        title,
        style: GtexText.displayMD.copyWith(color: GtexColors.textPrimary),
      ),
      const SizedBox(height: 5),
      Text(
        detail,
        style: GtexText.bodyMD.copyWith(color: GtexColors.textSecondary),
      ),
    ],
  );
}

class _LabFocus {
  const _LabFocus(this.kicker, this.title, this.detail, this.icon, this.accent);
  final String kicker;
  final String title;
  final String detail;
  final IconData icon;
  final Color accent;
}

class _LabDirectionData {
  const _LabDirectionData({
    required this.direction,
    required this.letter,
    required this.name,
    required this.identity,
    required this.identityDetail,
    required this.title,
    required this.summary,
    required this.status,
    required this.statusState,
    required this.primaryAction,
    required this.primaryIcon,
    required this.metrics,
    required this.storyKicker,
    required this.storyTitle,
    required this.storyDetail,
    required this.storyIcon,
    required this.accent,
    required this.focus,
  });
  final _DesignDirection direction;
  final String letter;
  final String name;
  final String identity;
  final String identityDetail;
  final String title;
  final String summary;
  final String status;
  final GtexCommandStatus statusState;
  final String primaryAction;
  final IconData primaryIcon;
  final List<GtexCommandMetric> metrics;
  final String storyKicker;
  final String storyTitle;
  final String storyDetail;
  final IconData storyIcon;
  final Color accent;
  final List<_LabFocus> focus;
  factory _LabDirectionData.forDirection(
    _DesignDirection direction,
  ) => switch (direction) {
    _DesignDirection.matchday => _LabDirectionData(
      direction: direction,
      letter: 'A',
      name: 'Matchday Pulse',
      identity: 'Lagos Comets',
      identityDetail: 'Manager: Amara · Club owner',
      title: 'The next football moment is the command.',
      summary:
          'Event-led hierarchy puts the most immediate competition decision above everything else.',
      status: 'Matchday live',
      statusState: GtexCommandStatus.live,
      primaryAction: 'Open matchday',
      primaryIcon: Icons.sports_soccer_rounded,
      metrics: const <GtexCommandMetric>[
        GtexCommandMetric(
          label: 'Kickoff',
          value: '18:30',
          detail: 'Tonight · League',
          accent: GtexCommandTokens.pitch,
          icon: Icons.timer_outlined,
        ),
        GtexCommandMetric(
          label: 'Standing',
          value: '#04',
          detail: 'Regional table',
          accent: GtexCommandTokens.competition,
          icon: Icons.leaderboard_outlined,
        ),
        GtexCommandMetric(
          label: 'Form',
          value: 'W-D-W',
          detail: 'Last 3 matches',
          accent: GtexCommandTokens.prestige,
          icon: Icons.show_chart_rounded,
        ),
        GtexCommandMetric(
          label: 'Squad',
          value: '2',
          detail: 'Decisions waiting',
          accent: GtexCommandTokens.pending,
          icon: Icons.groups_outlined,
        ),
      ],
      storyKicker: 'Match narrative',
      storyTitle: 'Comets v Atlas is the moment that matters.',
      storyDetail:
          'The layout uses a single event spine: fixture, readiness, and the two decision paths that alter the next match.',
      storyIcon: Icons.stadium_outlined,
      accent: GtexCommandTokens.pitch,
      focus: const <_LabFocus>[
        _LabFocus(
          'Readiness',
          'Set the final XI',
          'Two squad choices are still open.',
          Icons.tune_rounded,
          GtexCommandTokens.pending,
        ),
        _LabFocus(
          'Competition',
          'Table pressure',
          'A win moves the club into the top three.',
          Icons.emoji_events_outlined,
          GtexCommandTokens.competition,
        ),
        _LabFocus(
          'Reward',
          'Matchday pool',
          'A settled result unlocks the reward surface.',
          Icons.workspace_premium_rounded,
          GtexCommandTokens.reward,
        ),
      ],
    ),
    _DesignDirection.club => _LabDirectionData(
      direction: direction,
      letter: 'B',
      name: 'Club Atlas',
      identity: 'Lagos Comets',
      identityDetail: 'Founder-owned club · Est. 2026',
      title: 'Your club is the world you are building.',
      summary:
          'Identity and long-term progression lead, with the current football decision kept present but secondary.',
      status: 'Club active',
      statusState: GtexCommandStatus.active,
      primaryAction: 'Open club HQ',
      primaryIcon: Icons.shield_outlined,
      metrics: const <GtexCommandMetric>[
        GtexCommandMetric(
          label: 'Prestige',
          value: 'VIII',
          detail: 'Rising dynasty',
          accent: GtexCommandTokens.prestige,
          icon: Icons.workspace_premium_outlined,
        ),
        GtexCommandMetric(
          label: 'Academy',
          value: '03',
          detail: 'Prospects tracked',
          accent: GtexCommandTokens.ownership,
          icon: Icons.school_outlined,
        ),
        GtexCommandMetric(
          label: 'Honors',
          value: '01',
          detail: 'Cabinet pieces',
          accent: GtexCommandTokens.reward,
          icon: Icons.military_tech_outlined,
        ),
        GtexCommandMetric(
          label: 'Support',
          value: '2.4K',
          detail: 'Club following',
          accent: GtexCommandTokens.fan,
          icon: Icons.favorite_outline_rounded,
        ),
      ],
      storyKicker: 'Club identity',
      storyTitle: 'The crest, squad, and legacy share one narrative.',
      storyDetail:
          'This direction makes ownership and progression legible first. It is strong for club builders but softer for urgent match moments.',
      storyIcon: Icons.shield_outlined,
      accent: GtexCommandTokens.ownership,
      focus: const <_LabFocus>[
        _LabFocus(
          'Dynasty',
          'Build the next era',
          'Progression and reputation are the center.',
          Icons.auto_graph_rounded,
          GtexCommandTokens.prestige,
        ),
        _LabFocus(
          'Academy',
          'One prospect is rising',
          'A real player-development lane.',
          Icons.school_outlined,
          GtexCommandTokens.ownership,
        ),
        _LabFocus(
          'Matchday',
          'Fixture at 18:30',
          'Competition remains visible, not dominant.',
          Icons.sports_soccer_rounded,
          GtexCommandTokens.competition,
        ),
      ],
    ),
    _DesignDirection.ownership => _LabDirectionData(
      direction: direction,
      letter: 'C',
      name: 'Ownership Ledger',
      identity: 'Amara',
      identityDetail: 'Collector · Club owner · Market participant',
      title: 'Make your football ownership visible.',
      summary:
          'Value, player positions, and market movement become the primary navigation model for returning collectors.',
      status: 'Market open',
      statusState: GtexCommandStatus.open,
      primaryAction: 'Review positions',
      primaryIcon: Icons.pie_chart_outline_rounded,
      metrics: const <GtexCommandMetric>[
        GtexCommandMetric(
          label: 'Positions',
          value: '12',
          detail: 'Players and clubs',
          accent: GtexCommandTokens.ownership,
          icon: Icons.account_balance_wallet_outlined,
        ),
        GtexCommandMetric(
          label: 'Day move',
          value: '+3.8%',
          detail: 'Owned assets',
          accent: GtexCommandTokens.coin,
          icon: Icons.trending_up_rounded,
        ),
        GtexCommandMetric(
          label: 'Open bids',
          value: '02',
          detail: 'Transfer market',
          accent: GtexCommandTokens.pending,
          icon: Icons.gavel_outlined,
        ),
        GtexCommandMetric(
          label: 'Rank',
          value: '#18',
          detail: 'Regional owner',
          accent: GtexCommandTokens.prestige,
          icon: Icons.leaderboard_outlined,
        ),
      ],
      storyKicker: 'Ownership intelligence',
      storyTitle: 'A football portfolio should still feel like football.',
      storyDetail:
          'The ledger direction gives rich market context but risks making GTEX feel transactional when a user arrives for their club or match.',
      storyIcon: Icons.insights_outlined,
      accent: GtexCommandTokens.coin,
      focus: const <_LabFocus>[
        _LabFocus(
          'Market',
          'Three player values moved',
          'Your owned positions are prioritized.',
          Icons.show_chart_rounded,
          GtexCommandTokens.coin,
        ),
        _LabFocus(
          'Collecting',
          'Prospect rank improved',
          'Prestige is tied to real ownership.',
          Icons.workspace_premium_rounded,
          GtexCommandTokens.prestige,
        ),
        _LabFocus(
          'Action',
          'Two bids need review',
          'A concrete route into the transfer surface.',
          Icons.gavel_outlined,
          GtexCommandTokens.pending,
        ),
      ],
    ),
  };
}
