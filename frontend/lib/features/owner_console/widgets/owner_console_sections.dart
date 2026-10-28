import 'package:flutter/material.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../../regen_redesign/data/gtex_share_market_api.dart';
import '../../regen_redesign/widgets/gtex_wonderkid_board.dart';
import '../data/owner_console_api.dart';
import '../models/gtex_world_clock_models.dart';
import 'gtex_world_clock_panel.dart';
import 'owner_admin_review_section.dart';

final String _marketPath = const GteNavigationRoute.market().path;
final String _playPath = const GteNavigationRoute.competitions().path;
final String _clubPath = const GteNavigationRoute.club().path;
final String _regensPath = const GteNavigationRoute.regens().path;
const String _nationalPath = '/national-team';

String _gtx(double v) => '${v.toStringAsFixed(v.abs() >= 100 ? 0 : 2)} GTX';

double _numVal(Object? v) =>
    v is num ? v.toDouble() : double.tryParse('${v ?? ''}') ?? 0;

BriefingViewState _briefingStateFromControlCenter(
  OwnerControlCenter d,
  String? clubId,
) {
  final Map<String, dynamic> raw = d.dailyBriefing;
  if (raw.isEmpty) {
    return const BriefingUnavailable();
  }
  final List<BriefingEvent> events = <BriefingEvent>[];
  final Object? sections = raw['sections'];
  if (sections is List) {
    for (int i = 0; i < sections.length; i++) {
      final Object? item = sections[i];
      if (item is Map) {
        final String role = '${item['role'] ?? 'Executive'}';
        final String sender = '${item['sender'] ?? role}';
        final String title = '${item['title'] ?? 'Briefing'}';
        final String summary = '${item['summary'] ?? ''}';
        events.add(
          BriefingEvent(
            eventId: 'sec-$i',
            headline: '$role ($sender): $title',
            occurredAt: '${raw['created_at'] ?? raw['generated_at'] ?? 'Today'}',
            detail: summary,
          ),
        );
      }
    }
  }
  final Object? rawDilemma = raw['boardroom_dilemma'];
  final BoardroomDilemma? dilemma = rawDilemma is Map
      ? BoardroomDilemma.fromJson(Map<String, dynamic>.from(rawDilemma))
      : null;
  return BriefingReady(
    OwnerBriefing(
      briefingId: '${raw['id'] ?? 'daily-briefing'}',
      clubId: '${raw['club_id'] ?? clubId ?? 'club'}',
      worldDate: 'Day ${raw['world_day'] ?? 1}',
      events: events,
      explanation: '${raw['summary'] ?? raw['headline'] ?? ''}',
      boardroomDilemma: dilemma,
    ),
  );
}

/// Where a decision is resolved, by inbox item kind.
String decisionRoute(String kind) {
  final String k = kind.toLowerCase();
  if (k.contains('offer') || k.contains('transfer') || k.contains('bid')) {
    return _marketPath;
  }
  if (k.contains('rental') || k.contains('national')) return _nationalPath;
  if (k.contains('lineup') || k.contains('match') || k.contains('fixture')) {
    return _playPath;
  }
  return _clubPath;
}

/// Decisions this close to their deadline are urgent.
const Duration urgentWindow = Duration(hours: 6);

String countdownLabel(Duration left) {
  if (left <= Duration.zero) return 'Expiring now';
  final int days = left.inDays;
  final int hours = left.inHours % 24;
  final int minutes = left.inMinutes % 60;
  if (days > 0) return '${days}d ${hours}h left';
  if (left.inHours > 0) return '${left.inHours}h ${minutes}m left';
  return '${minutes < 1 ? 1 : minutes}m left';
}

bool isUrgentDecision(OwnerInboxEntry e, DateTime now) =>
    e.respondBy != null && e.respondBy!.difference(now) <= urgentWindow;

int compareByDeadline(OwnerInboxEntry a, OwnerInboxEntry b) {
  final DateTime? x = a.respondBy, y = b.respondBy;
  if (x != null && y != null && x != y) return x.compareTo(y);
  if (x == null && y != null) return 1;
  if (x != null && y == null) return -1;
  return (b.priority == 'high' ? 1 : 0) - (a.priority == 'high' ? 1 : 0);
}

String? decisionDeadlineLine(OwnerInboxEntry entry, DateTime now) {
  if (entry.respondBy == null) return null;
  final bool urgent = isUrgentDecision(entry, now);
  return '${urgent ? 'Respond soon' : 'Respond by'} · ${countdownLabel(entry.respondBy!.difference(now))}';
}

/// Decision actions that spend or move money ask for confirmation first.
bool decisionMovesMoney(String kind, String action) =>
    const <String, String>{
      'transfer_bid': 'accept',
      'facility_request': 'approve',
      'regen_breakthrough': 'new_contract',
      'competition_invite': 'enter',
      'sponsor_opportunity': 'accept',
      'regen_endorsement': 'accept',
    }[kind] ==
    action;

Widget _sectionList(List<Widget> children) => ListView(
  padding: const EdgeInsets.all(GtexSpacing.md),
  children: <Widget>[
    for (final Widget child in children) ...<Widget>[
      child,
      const SizedBox(height: GtexSpacing.md),
    ],
  ],
);

class _CenterLoader extends StatelessWidget {
  const _CenterLoader({
    required this.center,
    required this.onRetry,
    required this.builder,
  });

  final Future<OwnerControlCenter> center;
  final VoidCallback onRetry;
  final Widget Function(OwnerControlCenter data) builder;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<OwnerControlCenter>(
      future: center,
      builder: (BuildContext context, AsyncSnapshot<OwnerControlCenter> snap) {
        if (snap.connectionState != ConnectionState.done) {
          return _sectionList(const <Widget>[
            GtexSkeleton.box(height: 120),
            GtexSkeleton.box(height: 180),
          ]);
        }
        if (snap.hasError || !snap.hasData) {
          return _sectionList(<Widget>[
            GtexBlockedState(
              key: const Key('owner-console-unavailable'),
              title: 'Owner data unavailable',
              reason: '${snap.error ?? 'no response'}',
              severity: GtexBlockedSeverity.warning,
              icon: Icons.cloud_off_rounded,
              ctaLabel: 'Retry',
              ctaAction: onRetry,
            ),
          ]);
        }
        return builder(snap.data!);
      },
    );
  }
}

class _Row extends StatelessWidget {
  const _Row({
    required this.title,
    this.subtitle,
    this.trailing,
    this.onTap,
    this.accent = GtexColors.pitch,
    super.key,
  });

  final String title;
  final String? subtitle;
  final Widget? trailing;
  final VoidCallback? onTap;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        margin: const EdgeInsets.only(bottom: GtexSpacing.xs),
        padding: const EdgeInsets.all(GtexSpacing.sm),
        decoration: BoxDecoration(
          color: GtexColors.panelStrong,
          borderRadius: BorderRadius.circular(8),
          border: Border(left: BorderSide(color: accent, width: 3)),
        ),
        child: Row(
          children: <Widget>[
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    title,
                    style: const TextStyle(
                      color: GtexColors.text,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  if (subtitle != null)
                    Text(
                      subtitle!,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: GtexColors.textSecondary,
                        fontSize: 12,
                      ),
                    ),
                ],
              ),
            ),
            if (trailing != null) trailing!,
            if (onTap != null)
              const Icon(Icons.chevron_right_rounded, color: GtexColors.textMuted),
          ],
        ),
      ),
    );
  }
}

class _Quiet extends StatelessWidget {
  const _Quiet(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) => Row(
    children: <Widget>[
      const Icon(Icons.check_circle_outline, color: GtexColors.pitch, size: 18),
      const SizedBox(width: 6),
      Text(text, style: const TextStyle(color: GtexColors.textSecondary)),
    ],
  );
}

class _Stat extends StatelessWidget {
  const _Stat(this.label, this.value, {super.key, this.warn = false});

  final String label;
  final String value;
  final bool warn;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: 130,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          label.toUpperCase(),
          style: const TextStyle(
            color: GtexColors.textMuted,
            fontSize: 10,
            fontWeight: FontWeight.w800,
          ),
        ),
        Text(
          value,
          style: TextStyle(
            color: warn ? GtexColors.gold : GtexColors.text,
            fontWeight: FontWeight.w900,
            fontSize: 16,
          ),
        ),
      ],
    ),
  );
}

/// A Today's Decisions row with the decision's own inline actions.
class OwnerDecisionRow extends StatefulWidget {
  const OwnerDecisionRow({
    super.key,
    required this.entry,
    required this.reader,
    required this.onTap,
    required this.onResolved,
  });

  final OwnerInboxEntry entry;
  final OwnerConsoleReader reader;
  final VoidCallback onTap;
  final ValueChanged<String> onResolved;

  @override
  State<OwnerDecisionRow> createState() => _OwnerDecisionRowState();
}

class _OwnerDecisionRowState extends State<OwnerDecisionRow> {
  String? _busyKey;
  String? _error;

  Future<void> _act(OwnerDecisionAction a) async {
    final OwnerInboxEntry e = widget.entry;
    if (decisionMovesMoney(e.kind, a.key)) {
      final String? ok = await confirmOwnerAction(context, title: '${a.label}?', message: e.what ?? e.title, confirmLabel: a.label);
      if (ok == null || !mounted) return;
    }
    setState(() {
      _busyKey = a.key;
      _error = null;
    });
    try {
      final OwnerInboxEntry done = await widget.reader.decide(e.id, a.key);
      widget.onResolved(done.outcome ?? '${a.label}: done.');
    } catch (error) {
      if (mounted) {
        setState(() {
          _busyKey = null;
          _error = '$error';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final OwnerInboxEntry e = widget.entry;
    final DateTime now = DateTime.now();
    final bool urgent = isUrgentDecision(e, now);
    final String? deadline = decisionDeadlineLine(e, now);
    final Color accent = urgent || e.priority == 'high' ? GtexColors.red : GtexColors.gold;
    return Container(
      margin: const EdgeInsets.only(bottom: GtexSpacing.xs),
      decoration: BoxDecoration(
        color: GtexColors.panelStrong,
        borderRadius: BorderRadius.circular(8),
        border: Border(left: BorderSide(color: accent, width: 3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          _Row(
            key: Key('owner-decision-${e.id}'),
            title: e.title,
            subtitle: e.why,
            accent: accent,
            trailing: GtexStatusChip(label: e.kind, color: GtexColors.gold, compact: true),
            onTap: widget.onTap,
          ),
          if (deadline != null)
            Padding(
              key: Key('owner-decision-${e.id}-countdown'),
              padding: const EdgeInsets.fromLTRB(GtexSpacing.sm, 0, GtexSpacing.sm, GtexSpacing.xs),
              child: Row(
                children: <Widget>[
                  Icon(
                    urgent ? Icons.alarm_rounded : Icons.timer_outlined,
                    size: 14,
                    color: urgent ? GtexColors.red : GtexColors.textSecondary,
                  ),
                  const SizedBox(width: 4),
                  Flexible(
                    child: Text(
                      deadline,
                      style: TextStyle(
                        color: urgent ? GtexColors.red : GtexColors.textSecondary,
                        fontSize: 12,
                        fontWeight: urgent ? FontWeight.w900 : FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          if (e.actions.isNotEmpty)
            Padding(
              padding: const EdgeInsets.fromLTRB(GtexSpacing.sm, 0, GtexSpacing.sm, GtexSpacing.sm),
              child: Wrap(
                spacing: GtexSpacing.xs,
                runSpacing: GtexSpacing.xs,
                children: <Widget>[
                  for (final OwnerDecisionAction a in e.actions)
                    GtexActionButton(
                      key: Key('owner-decision-${e.id}-action-${a.key}'),
                      label: _busyKey == a.key ? 'Working...' : a.label,
                      compact: true,
                      secondary: !a.isPrimary,
                      onPressed: _busyKey == null ? () => _act(a) : null,
                    ),
                ],
              ),
            ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(GtexSpacing.sm, 0, GtexSpacing.sm, GtexSpacing.sm),
              child: Text(_error!, key: Key('owner-decision-${e.id}-error'), style: const TextStyle(color: GtexColors.red, fontSize: 12)),
            ),
        ],
      ),
    );
  }
}

class ControlCenterSection extends StatelessWidget {
  const ControlCenterSection({
    super.key,
    required this.center,
    required this.clubId,
    required this.onRetry,
    required this.onNavigate,
    required this.onClaim,
    required this.city,
    required this.country,
    required this.reader,
    required this.onResolved,
    this.claiming = false,
    this.claimError,
    this.outcome,
  });

  final Future<OwnerControlCenter> center;
  final String? clubId;
  final VoidCallback onRetry;
  final ValueChanged<String> onNavigate;
  final VoidCallback onClaim;
  final TextEditingController city;
  final TextEditingController country;
  final OwnerConsoleReader reader;
  final ValueChanged<String> onResolved;
  final bool claiming;
  final String? claimError;
  final String? outcome;

  @override
  Widget build(BuildContext context) {
    return _CenterLoader(
      center: center,
      onRetry: onRetry,
      builder: (OwnerControlCenter d) {
        bool mine(String? id) => clubId == null || id == null || id == clubId;
        final DateTime now = DateTime.now();
        final List<OwnerInboxEntry> decisions = d.decisions
            .where((OwnerInboxEntry e) => mine(e.clubId))
            .toList()
          ..sort(compareByDeadline);
        final List<OwnerInboxEntry> inbox =
            d.inbox.where((OwnerInboxEntry e) => mine(e.clubId)).toList();
        final List<OwnerClubHealth> health =
            d.health.where((OwnerClubHealth h) => mine(h.clubId)).toList();
        final List<OwnerFixture> upcoming =
            d.upcoming.where((OwnerFixture f) => f.involves(clubId)).toList();
        final List<OwnerClubCard> clubs = d.clubs;
        final Set<String> myIds = clubs.map((OwnerClubCard c) => c.clubId).toSet();
        final OwnerConsoleReader r = reader;
        return _sectionList(<Widget>[
          if (d.legacy.isNotEmpty)
            GtexPanel(
              key: const Key('owner-legacy-ratings'),
              title: 'Club Legacy',
              subtitle: d.legacy.first.continentName ?? 'Location not set',
              accent: GtexColors.gold,
              child: Wrap(
                spacing: GtexSpacing.sm,
                runSpacing: GtexSpacing.sm,
                children: <Widget>[
                  _Stat('Prestige', '${d.legacy.first.prestige}', key: const Key('owner-legacy-prestige')),
                  _Stat('Development', '${d.legacy.first.development}', key: const Key('owner-legacy-development')),
                  _Stat(
                    'Financial strength',
                    '${d.legacy.first.financialStrength}',
                    key: const Key('owner-legacy-financial'),
                  ),
                ],
              ),
            ),
          if (clubs.isEmpty)
            GtexPanel(
              key: const Key('owner-console-claim-club'),
              title: 'Claim your first club',
              subtitle: 'Starts your squad, staff coach, and the free launch league',
              accent: GtexColors.gold,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  TextField(
                    key: const Key('owner-claim-city'),
                    controller: city,
                    style: const TextStyle(color: GtexColors.text),
                    decoration: const InputDecoration(labelText: 'City'),
                  ),
                  TextField(
                    key: const Key('owner-claim-country'),
                    controller: country,
                    style: const TextStyle(color: GtexColors.text),
                    decoration: const InputDecoration(labelText: 'Country code'),
                  ),
                  const SizedBox(height: GtexSpacing.sm),
                  if (claimError != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
                      child: Text(
                        claimError!,
                        key: const Key('owner-console-claim-error'),
                        style: const TextStyle(color: GtexColors.danger),
                      ),
                    ),
                  GtexActionButton(
                    key: const Key('owner-console-claim-club-button'),
                    label: claiming ? 'Starting your club' : 'Claim a club',
                    icon: Icons.add_business_rounded,
                    onPressed: claiming ? null : onClaim,
                  ),
                ],
              ),
            ),
          GtexPanel(
            key: const Key('owner-console-decisions'),
            title: "Today's Decisions",
            subtitle: '${decisions.length} waiting',
            accent: GtexColors.gold,
            child: Column(
              children: <Widget>[
                if (outcome != null)
                  Container(
                    key: const Key('owner-decision-outcome'),
                    width: double.infinity,
                    margin: const EdgeInsets.only(bottom: GtexSpacing.sm),
                    padding: const EdgeInsets.all(GtexSpacing.sm),
                    decoration: BoxDecoration(
                      color: GtexColors.pitch.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: GtexColors.pitch.withValues(alpha: 0.5)),
                    ),
                    child: Text(outcome!, style: const TextStyle(color: GtexColors.text, fontWeight: FontWeight.w700)),
                  ),
                if (decisions.isEmpty) const _Quiet('All clear - nothing needs you today'),
                for (final OwnerInboxEntry e in decisions)
                  OwnerDecisionRow(
                    key: ValueKey<String>('decision-row-${e.id}'),
                    entry: e,
                    reader: reader,
                    onTap: () => onNavigate(decisionRoute(e.kind)),
                    onResolved: onResolved,
                  ),
              ],
            ),
          ),
          GtexPanel(
            key: const Key('owner-console-board'),
            title: 'Board Table',
            subtitle: 'Your clubs in their current competitions',
            accent: GtexColors.cyan,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                if (d.board.isEmpty) const _Quiet('Not in a competition yet'),
                for (final OwnerBoardTable table in d.board) ...<Widget>[
                  Text(
                    table.competitionName,
                    style: const TextStyle(color: GtexColors.cyan, fontWeight: FontWeight.w900),
                  ),
                  for (int i = 0; i < table.rows.length; i++)
                    if (myIds.contains(table.rows[i].clubId) && mine(table.rows[i].clubId))
                      _Row(
                        key: Key('owner-board-${table.rows[i].clubId}'),
                        title: '#${i + 1} ${table.rows[i].clubName}',
                        subtitle:
                            'P${table.rows[i].played} · W${table.rows[i].won} D${table.rows[i].drawn} L${table.rows[i].lost}',
                        accent: GtexColors.cyan,
                        trailing: Text(
                          '${table.rows[i].points} pts',
                          style: const TextStyle(color: GtexColors.text, fontWeight: FontWeight.w900),
                        ),
                      ),
                ],
                if (upcoming.isNotEmpty)
                  Text(
                    'Next: ${upcoming.first.homeName} vs ${upcoming.first.awayName} · Round ${upcoming.first.round}',
                    key: const Key('owner-board-next-fixture'),
                    style: const TextStyle(color: GtexColors.textSecondary),
                  ),
              ],
            ),
          ),
          GtexPanel(
            key: const Key('owner-console-inbox'),
            title: 'Owner Inbox',
            subtitle: '${d.inboxOpenCount} unread',
            accent: GtexColors.purple,
            onTap: () => onNavigate('/app/inbox'),
            trailing: TextButton.icon(
              key: const Key('owner-inbox-open-queue-btn'),
              onPressed: () => onNavigate('/app/inbox'),
              icon: const Icon(Icons.arrow_forward_rounded, size: 14),
              label: const Text('Open Queue'),
            ),
            child: Column(
              children: <Widget>[
                if (inbox.isEmpty) const _Quiet('Inbox clear'),
                for (final OwnerInboxEntry e in inbox.take(5))
                  _Row(
                    key: Key('owner-inbox-${e.id}'),
                    title: e.title,
                    subtitle: decisionDeadlineLine(e, now) ?? e.sender ?? e.why,
                    accent: GtexColors.purple,
                  ),
              ],
            ),
          ),
          GtexWorldClockPanel(
            load: r is OwnerWorldClockGateway ? (r as OwnerWorldClockGateway).fetchWorldClock : null,
          ),
          GtexOwnerBriefingPanel(
            state: _briefingStateFromControlCenter(d, clubId),
            onNavigate: onNavigate,
            onResolveDilemma: clubs.isNotEmpty
                ? (String choiceId) async {
                    final String targetClubId = clubId ?? clubs.first.clubId;
                    await r.resolveBriefingDilemma(
                      targetClubId,
                      choiceId,
                    );
                    onResolved('Boardroom dilemma ratified ($choiceId).');
                  }
                : null,
          ),
          if (d.ecosystemWaterfall.isNotEmpty)
            GtexPanel(
              key: const Key('owner-console-ecosystem-waterfall'),
              title: 'Ecosystem Revenue & Broadcast Waterfall',
              subtitle: '40% TV Broadcast · 35% Competition Grants · 25% Global Jackpot',
              accent: GtexColors.gold,
              child: Wrap(
                spacing: GtexSpacing.sm,
                runSpacing: GtexSpacing.sm,
                children: <Widget>[
                  _Stat('TV Broadcast Pool', _gtx(_numVal(d.ecosystemWaterfall['tv_broadcast_pool_gtex']))),
                  _Stat('Competition Pool', _gtx(_numVal(d.ecosystemWaterfall['competition_prize_pool_gtex']))),
                  _Stat('Jackpot Pool', _gtx(_numVal(d.ecosystemWaterfall['jackpot_ecosystem_pool_gtex']))),
                  _Stat('Club TV Revenue', _gtx(_numVal(d.ecosystemWaterfall['club_tv_revenue_gtex']))),
                  _Stat('Entry Grants', _gtx(_numVal(d.ecosystemWaterfall['club_competition_grants_gtex']))),
                ],
              ),
            ),
          if (clubs.isNotEmpty)
            GtexPanel(
              key: const Key('owner-console-executive-triumvirate'),
              title: 'Executive Boardroom Triumvirate',
              subtitle: 'Live Staff Agendas, Secret Traits & Alignment',
              accent: GtexColors.purple,
              child: Column(
                children: <Widget>[
                  _Row(
                    key: const Key('owner-exec-manager'),
                    title: 'First-Team Manager · ${clubs.first.managerName ?? 'Tactical Head Coach'}',
                    subtitle: '${clubs.first.managerTrait ?? 'Tactical Purist'} — ${clubs.first.managerAgenda ?? 'Demands marquee reinforcements for continental push.'}',
                    accent: GtexColors.pitch,
                    trailing: GtexStatusChip(
                      label: 'Mood ${clubs.first.managerMood ?? 72}',
                      color: (clubs.first.managerMood ?? 72) < 50 ? GtexColors.red : GtexColors.pitch,
                      compact: true,
                    ),
                    onTap: () => onNavigate(_clubPath),
                  ),
                  _Row(
                    key: const Key('owner-exec-gm'),
                    title: 'General Manager · ${clubs.first.gmName ?? 'Commercial & Sporting Director'}',
                    subtitle: '${clubs.first.gmTrait ?? 'Wage Cap Hawk'} — ${clubs.first.gmAgenda ?? 'Focused on commercial sponsors, stadium ad surfaces & FFP margin.'}',
                    accent: GtexColors.gold,
                    trailing: GtexStatusChip(
                      label: 'Mood ${clubs.first.gmMood ?? 76}',
                      color: (clubs.first.gmMood ?? 76) < 50 ? GtexColors.red : GtexColors.gold,
                      compact: true,
                    ),
                    onTap: () => onNavigate(_marketPath),
                  ),
                  _Row(
                    key: const Key('owner-exec-hoyd'),
                    title: 'Head of Youth Dev · ${clubs.first.hoydName ?? 'Academy & Dynasty Director'}',
                    subtitle: '${clubs.first.hoydTrait ?? 'Bloodline Scout'} — ${clubs.first.hoydAgenda ?? 'Pushing for Build-A-Son dynasty heirs & U19 wonderkid minutes.'}',
                    accent: GtexColors.cyan,
                    trailing: GtexStatusChip(
                      label: 'Mood ${clubs.first.hoydMood ?? 80}',
                      color: (clubs.first.hoydMood ?? 80) < 50 ? GtexColors.red : GtexColors.cyan,
                      compact: true,
                    ),
                    onTap: () => onNavigate(_regensPath),
                  ),
                ],
              ),
            ),
          GtexPanel(
            key: const Key('owner-console-health'),
            title: 'Live Club Health',
            accent: GtexColors.pitch,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                if (health.isEmpty) const _Quiet('No clubs to monitor yet'),
                for (final OwnerClubHealth h in health) ...<Widget>[
                  Text(h.clubName, style: const TextStyle(color: GtexColors.text, fontWeight: FontWeight.w900)),
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: GtexSpacing.sm,
                    runSpacing: GtexSpacing.sm,
                    children: <Widget>[
                      _Stat('Cash', _gtx(h.cash), warn: h.cash <= 0),
                      _Stat('Squad', '${h.squadSize} · ${h.squadDepth}', warn: h.squadDepth == 'thin'),
                      _Stat('Morale', '${h.morale}', warn: h.morale < 45),
                      _Stat('Injuries', '${h.injuries}', warn: h.injuries > 0),
                      _Stat('Fan engagement', '${h.fanEngagement}%'),
                    ],
                  ),
                  const SizedBox(height: GtexSpacing.sm),
                ],
              ],
            ),
          ),
          GtexPanel(
            key: const Key('owner-console-fixtures'),
            title: 'Competition & Fixtures',
            accent: GtexColors.cyan,
            onTap: () => onNavigate(_playPath),
            child: Column(
              children: <Widget>[
                if (upcoming.isEmpty && d.recent.isEmpty) const _Quiet('No fixtures yet - enter a competition'),
                for (final OwnerFixture f in <OwnerFixture>[...upcoming.take(3), ...d.recent.where((OwnerFixture f) => f.involves(clubId)).take(2)])
                  _Row(
                    title: '${f.homeName} vs ${f.awayName}',
                    subtitle: f.status == 'scheduled' ? 'Round ${f.round} · upcoming' : 'Round ${f.round} · ${f.homeGoals ?? 0}-${f.awayGoals ?? 0}',
                    accent: GtexColors.cyan,
                  ),
              ],
            ),
          ),
          GtexPanel(
            key: const Key('owner-console-economy'),
            title: 'Club Economy',
            accent: GtexColors.gold,
            child: Wrap(
              spacing: GtexSpacing.sm,
              runSpacing: GtexSpacing.sm,
              children: <Widget>[
                _Stat('Club cash', _gtx(d.clubCashTotal)),
                _Stat('Withdrawable', _gtx(d.withdrawable)),
                _Stat('Pending payouts', _gtx(d.pendingPayouts)),
                _Stat('Income', _gtx(d.earnings.values.where((double v) => v > 0).fold(0.0, (double a, double b) => a + b))),
                _Stat('Spend', _gtx(-d.earnings.values.where((double v) => v < 0).fold(0.0, (double a, double b) => a + b))),
              ],
            ),
          ),
        ]);
      },
    );
  }
}

class MyClubsSection extends StatelessWidget {
  const MyClubsSection({
    super.key,
    required this.center,
    required this.selectedClubId,
    required this.onRetry,
    required this.onSelectClub,
    required this.onNavigate,
    required this.onClaim,
    this.claiming = false,
  });

  final Future<OwnerControlCenter> center;
  final String? selectedClubId;
  final VoidCallback onRetry;
  final ValueChanged<String> onSelectClub;
  final ValueChanged<String> onNavigate;
  final VoidCallback onClaim;
  final bool claiming;

  @override
  Widget build(BuildContext context) {
    return _CenterLoader(
      center: center,
      onRetry: onRetry,
      builder: (OwnerControlCenter d) => _sectionList(<Widget>[
        if (d.clubs.isEmpty)
          GtexEmptyState(
            title: 'No clubs yet',
            message: 'Claim a club to start running it from here.',
            icon: Icons.shield_outlined,
            accent: GtexColors.gold,
          ),
        if (d.clubs.isEmpty)
          GtexActionButton(
            key: const Key('owner-console-claim-club-cta'),
            label: claiming ? 'Starting your club' : 'Claim a club',
            icon: Icons.add_business_rounded,
            onPressed: claiming ? null : onClaim,
          ),
        for (final OwnerClubCard c in d.clubs)
          GtexPanel(
            key: Key('owner-club-${c.clubId}'),
            title: c.name,
            subtitle: <String?>[c.competitionName ?? 'No active competition', c.countryCode, c.stage].whereType<String>().join(' · '),
            accent: c.clubId == selectedClubId ? GtexColors.pitch : GtexColors.cyan,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Wrap(
                  spacing: GtexSpacing.sm,
                  runSpacing: GtexSpacing.sm,
                  children: <Widget>[
                    _Stat('Club value', _gtx(c.value)),
                    _Stat('Value trend', '${c.valueTrend >= 0 ? '+' : ''}${c.valueTrend.toStringAsFixed(1)}', warn: c.valueTrend < 0),
                    _Stat('Manager', c.managerName ?? '-'),
                    _Stat('Mood', c.managerMood?.toString() ?? '-', warn: (c.managerMood ?? 70) < 45),
                  ],
                ),
                const SizedBox(height: GtexSpacing.sm),
                Wrap(
                  spacing: GtexSpacing.xs,
                  runSpacing: GtexSpacing.xs,
                  children: <Widget>[
                    GtexActionButton(
                      key: Key('owner-club-focus-${c.clubId}'),
                      label: c.clubId == selectedClubId ? 'In focus' : 'Focus Control Center',
                      icon: Icons.center_focus_strong_rounded,
                      compact: true,
                      onPressed: () => onSelectClub(c.clubId),
                    ),
                    GtexActionButton(
                      label: 'Open club',
                      icon: Icons.open_in_new,
                      compact: true,
                      secondary: true,
                      onPressed: () => onNavigate(_clubPath),
                    ),
                  ],
                ),
              ],
            ),
          ),
        if (d.clubs.isNotEmpty && d.clubs.length < d.maxClubs)
          Text('${d.clubs.length}/${d.maxClubs} clubs owned', style: const TextStyle(color: GtexColors.textMuted)),
      ]),
    );
  }
}

class MarketSection extends StatelessWidget {
  const MarketSection({super.key, required this.onNavigate});

  final ValueChanged<String> onNavigate;

  @override
  Widget build(BuildContext context) {
    final List<(String, String, String)> links = <(String, String, String)>[
      ('Transfer Hub', 'Listings, offers, contract negotiations & signing unveilings', _marketPath),
      ('My ownership', 'Shortlist, minority share dividends & club takeover bids', '$_marketPath?mode=ownership'),
      ('Competitions & ELO Matchmaking', 'GTEX/User-hosted cups, global leaderboards & instant quick games', _playPath),
      ('Wallet & Sponsor Desk', 'GTX balance, unified ledger, GM sponsors & stadium ad surfaces', const GteNavigationRoute.wallet().path),
    ];
    return _sectionList(<Widget>[
      GtexPanel(
        key: const Key('owner-console-market'),
        title: 'Market, Transfers & Commercial Hub',
        subtitle: 'Price history, contract negotiations, and club share dividends',
        accent: GtexColors.cyan,
        child: Column(
          children: <Widget>[
            for (final (String title, String sub, String path) in links)
              _Row(key: Key('owner-market-link-${title.toLowerCase().replaceAll(' ', '-')}'), title: title, subtitle: sub, accent: GtexColors.cyan, onTap: () => onNavigate(path)),
          ],
        ),
      ),
    ]);
  }
}

class AcademySection extends StatelessWidget {
  const AcademySection({super.key, required this.shareMarket, required this.onNavigate});

  final GtexShareMarketReader shareMarket;
  final ValueChanged<String> onNavigate;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        Padding(
          padding: const EdgeInsets.fromLTRB(GtexSpacing.md, GtexSpacing.md, GtexSpacing.md, 0),
          child: Column(
            children: <Widget>[
              _Row(
                key: const Key('owner-academy-open-regen-world'),
                title: 'Open Regen World',
                subtitle: 'Prospects, Wonderkids, Rankings, Create-a-Son',
                accent: GtexColors.purple,
                onTap: () => onNavigate(_regensPath),
              ),
              _Row(
                key: const Key('owner-academy-build-a-son-banner'),
                title: 'Build-A-Son Dynasty Legacy & Bloodlines',
                subtitle: 'Induct a second-generation club heir via /regens/request-son with custom position & DNA lineage',
                accent: GtexColors.gold,
                onTap: () => onNavigate(_regensPath),
              ),
            ],
          ),
        ),
        Expanded(child: GtexWonderkidBoard(reader: shareMarket)),
      ],
    );
  }
}

class SquadSection extends StatefulWidget {
  const SquadSection({super.key, required this.reader, required this.isAdmin, required this.onNavigate});

  final OwnerConsoleReader reader;
  final bool isAdmin;
  final ValueChanged<String> onNavigate;

  @override
  State<SquadSection> createState() => _SquadSectionState();
}

class _SquadSectionState extends State<SquadSection> {
  late Future<(List<OwnerNationalCompetition>, List<OwnerNationalEntry>)> _future;
  Future<OwnerNationalSquad>? _squad;
  OwnerAutoBuildPlan? _plan;
  String? _message;
  bool _busy = false;
  final TextEditingController _budget = TextEditingController(text: '500');

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _budget.dispose();
    super.dispose();
  }

  void _load() {
    _future = Future.wait<Object>(<Future<Object>>[
      widget.reader.fetchNationalCompetitions(),
      widget.reader.fetchManagedEntries(),
    ]).then((List<Object> r) {
      final List<OwnerNationalEntry> entries = r[1] as List<OwnerNationalEntry>;
      _squad = entries.isEmpty ? null : widget.reader.fetchSquad(entries.first.id);
      return (r[0] as List<OwnerNationalCompetition>, entries);
    });
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() => _busy = true);
    try {
      await action();
    } catch (error) {
      _message = '$error';
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<(List<OwnerNationalCompetition>, List<OwnerNationalEntry>)>(
      future: _future,
      builder: (BuildContext context, AsyncSnapshot<(List<OwnerNationalCompetition>, List<OwnerNationalEntry>)> snap) {
        if (snap.connectionState != ConnectionState.done) {
          return _sectionList(const <Widget>[GtexSkeleton.box(height: 160)]);
        }
        if (snap.hasError) {
          return _sectionList(<Widget>[
            GtexBlockedState(
              title: 'National squad unavailable',
              reason: '${snap.error}',
              severity: GtexBlockedSeverity.warning,
              icon: Icons.cloud_off_rounded,
              ctaLabel: 'Retry',
              ctaAction: () => setState(_load),
            ),
          ]);
        }
        final (List<OwnerNationalCompetition> comps, List<OwnerNationalEntry> entries) = snap.data!;
        final OwnerNationalEntry? entry = entries.isEmpty ? null : entries.first;
        return _sectionList(<Widget>[
          if (widget.isAdmin)
            GtexActionButton(
              key: const Key('owner-squad-seed-defaults'),
              label: 'Seed default tournaments',
              icon: Icons.add_task_rounded,
              secondary: true,
              onPressed: _busy ? null : () => _run(() async {
                await widget.reader.seedDefaultTournaments();
                _message = 'Default national tournaments seeded';
                _load();
              }),
            ),
          if (_message != null) Text(_message!, key: const Key('owner-squad-message'), style: const TextStyle(color: GtexColors.textSecondary)),
          GtexPanel(
            key: const Key('owner-squad-national'),
            title: 'Your National Squad',
            subtitle: entry == null ? '${comps.length} tournaments open' : entry.countryName,
            accent: GtexColors.pitch,
            child: entry == null
                ? const _Quiet('No national squad yet - enter a tournament from the rental pool')
                : FutureBuilder<OwnerNationalSquad>(
                    future: _squad,
                    builder: (BuildContext context, AsyncSnapshot<OwnerNationalSquad> s) {
                      if (!s.hasData) {
                        return s.hasError ? Text('${s.error}', style: const TextStyle(color: GtexColors.red)) : const GtexSkeleton.box(height: 80);
                      }
                      final OwnerNationalSquad squad = s.data!;
                      return Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text('${squad.members.length}/${squad.minimumSquadSize} minimum', style: const TextStyle(color: GtexColors.textSecondary)),
                          for (final OwnerSquadMember m in squad.members)
                            _Row(title: m.name, subtitle: m.source, trailing: Text('${m.rating}', style: const TextStyle(color: GtexColors.pitch, fontWeight: FontWeight.w900))),
                        ],
                      );
                    },
                  ),
          ),
          GtexPanel(
            key: const Key('owner-squad-rental-pool'),
            title: 'Rental Pool',
            subtitle: 'Rent real players and regens for national tournaments',
            accent: GtexColors.cyan,
            onTap: () => widget.onNavigate(_nationalPath),
            child: const Text('Open the rental pool to browse and rent players.', style: TextStyle(color: GtexColors.textSecondary)),
          ),
          if (entry != null)
            GtexPanel(
              key: const Key('owner-squad-auto-build'),
              title: 'Auto-build a squad',
              subtitle: 'A suggestion to review - nothing is rented or charged here',
              accent: GtexColors.gold,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(
                    children: <Widget>[
                      SizedBox(
                        width: 120,
                        child: TextField(
                          key: const Key('owner-squad-budget'),
                          controller: _budget,
                          keyboardType: TextInputType.number,
                          style: const TextStyle(color: GtexColors.text),
                          decoration: const InputDecoration(labelText: 'Budget (GTX)'),
                        ),
                      ),
                      const SizedBox(width: GtexSpacing.sm),
                      GtexActionButton(
                        key: const Key('owner-squad-suggest'),
                        label: _busy ? 'Scouting...' : 'Suggest squad',
                        icon: Icons.auto_fix_high_rounded,
                        onPressed: _busy ? null : () => _run(() async {
                          _plan = await widget.reader.suggestSquad(
                            competitionId: entry.competitionId,
                            countryCode: entry.countryCode,
                            budgetCoin: double.tryParse(_budget.text) ?? 0,
                          );
                          _message = null;
                        }),
                      ),
                    ],
                  ),
                  if (_plan != null) ...<Widget>[
                    const SizedBox(height: GtexSpacing.sm),
                    Text(
                      '${_plan!.formation} · ${_plan!.selectedCount}/${_plan!.squadSize} picked · cost ${_gtx(_plan!.totalCost)} · left ${_gtx(_plan!.remainingBudget)}',
                      key: const Key('owner-squad-plan-summary'),
                      style: const TextStyle(color: GtexColors.text, fontWeight: FontWeight.w700),
                    ),
                    for (final OwnerSquadMember p in _plan!.players.take(11))
                      _Row(title: p.name, subtitle: p.source, trailing: Text('${p.rating}', style: const TextStyle(color: GtexColors.gold, fontWeight: FontWeight.w900))),
                    GtexActionButton(
                      key: const Key('owner-squad-review-confirm'),
                      label: 'Review & rent in rental pool',
                      icon: Icons.fact_check_rounded,
                      onPressed: () => widget.onNavigate(_nationalPath),
                    ),
                  ],
                ],
              ),
            ),
        ]);
      },
    );
  }
}
