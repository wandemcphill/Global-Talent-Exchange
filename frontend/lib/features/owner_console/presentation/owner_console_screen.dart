import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../../regen_redesign/data/gtex_share_market_api.dart';
import '../data/owner_console_api.dart';
import '../widgets/club_legacy_desk.dart';
import '../widgets/club_legacy_showroom.dart';
import '../widgets/owner_admin_review_section.dart';
import '../widgets/owner_console_sections.dart';

enum OwnerConsoleSection { control, clubs, showroom, desk, market, squad, academy, admin }

const Map<OwnerConsoleSection, (String, IconData)> _sectionMeta =
    <OwnerConsoleSection, (String, IconData)>{
      OwnerConsoleSection.control: ('Today', Icons.bolt_rounded),
      OwnerConsoleSection.clubs: ('My Clubs', Icons.shield_rounded),
      OwnerConsoleSection.showroom: ('Showroom', Icons.museum_rounded),
      OwnerConsoleSection.desk: ('Club desk', Icons.account_balance_rounded),
      OwnerConsoleSection.market: ('Transfers', Icons.storefront_rounded),
      OwnerConsoleSection.squad: ('Squad', Icons.groups_rounded),
      OwnerConsoleSection.academy: ('Academy', Icons.auto_awesome_rounded),
      OwnerConsoleSection.admin: ('Trust desk', Icons.admin_panel_settings_rounded),
    };

/// The signed-in owner's home: Control Center plus My Clubs, Market,
/// Manager & Squad and Academy sections over the existing GTEX backend.
class OwnerConsoleScreen extends StatefulWidget {
  const OwnerConsoleScreen({
    super.key,
    required this.reader,
    required this.shareMarket,
    required this.role,
    required this.signedInAs,
    required this.onNavigate,
    this.walletBalance,
  });

  final OwnerConsoleReader reader;
  final GtexShareMarketReader shareMarket;
  final String role;
  final String signedInAs;
  final double? walletBalance;
  final ValueChanged<String> onNavigate;

  bool get isAdmin => <String>{
    'admin',
    'super_admin',
  }.contains(role.trim().toLowerCase());

  @override
  State<OwnerConsoleScreen> createState() => _OwnerConsoleScreenState();
}

class _OwnerConsoleScreenState extends State<OwnerConsoleScreen> {
  OwnerConsoleSection _section = OwnerConsoleSection.control;
  String? _clubId;
  late Future<OwnerControlCenter> _center;
  double? _wallet;
  String? _outcome;
  bool _claiming = false;
  String? _claimError;
  final TextEditingController _city = TextEditingController(text: 'Lagos');
  final TextEditingController _country = TextEditingController(text: 'NG');

  @override
  void initState() {
    super.initState();
    _center = widget.reader.fetchControlCenter();
    _wallet = widget.walletBalance;
    if (_wallet == null) {
      widget.reader.fetchWalletBalance().then((double v) {
        if (mounted) setState(() => _wallet = v);
      }, onError: (Object _) {});
    }
  }

  @override
  void dispose() {
    _city.dispose();
    _country.dispose();
    super.dispose();
  }

  void _reload() => setState(() => _center = widget.reader.fetchControlCenter());

  Future<void> _claimClub() async {
    if (_claiming) {
      return;
    }
    setState(() {
      _claiming = true;
      _claimError = null;
    });
    try {
      await widget.reader.claimClub(city: _city.text, country: _country.text);
      if (!mounted) {
        return;
      }
      setState(() {
        _claiming = false;
        _center = widget.reader.fetchControlCenter();
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _claiming = false;
        _claimError = '$error';
      });
    }
  }

  void _resolved(String outcome) => setState(() {
    _outcome = outcome;
    _center = widget.reader.fetchControlCenter();
  });

  void _pickClub(String clubId) => setState(() {
    _clubId = clubId;
    _section = OwnerConsoleSection.control;
  });

  Widget _body() {
    switch (_section) {
      case OwnerConsoleSection.control:
        return ControlCenterSection(
          center: _center,
          clubId: _clubId,
          onRetry: _reload,
          onNavigate: widget.onNavigate,
          onClaim: _claimClub,
          city: _city,
          country: _country,
          claiming: _claiming,
          claimError: _claimError,
          reader: widget.reader,
          onResolved: _resolved,
          outcome: _outcome,
        );
      case OwnerConsoleSection.clubs:
        return MyClubsSection(
          center: _center,
          selectedClubId: _clubId,
          onRetry: _reload,
          onSelectClub: _pickClub,
          onNavigate: widget.onNavigate,
          onClaim: _claimClub,
          claiming: _claiming,
        );
      case OwnerConsoleSection.showroom:
        return ShowroomSection(load: widget.reader.fetchShowroom);
      case OwnerConsoleSection.desk:
        return _DeskLoader(load: widget.reader.fetchDesk, act: widget.reader.performDesk);
      case OwnerConsoleSection.market:
        return MarketSection(onNavigate: widget.onNavigate);
      case OwnerConsoleSection.squad:
        return SquadSection(
          reader: widget.reader,
          isAdmin: widget.isAdmin,
          onNavigate: widget.onNavigate,
        );
      case OwnerConsoleSection.academy:
        return AcademySection(
          shareMarket: widget.shareMarket,
          onNavigate: widget.onNavigate,
        );
      case OwnerConsoleSection.admin:
        if (!widget.isAdmin) {
          return const Padding(
            padding: EdgeInsets.all(GtexSpacing.md),
            child: GtexBlockedState(
              key: Key('owner-admin-only'),
              title: 'Admins only',
              reason: 'The Trust & Payouts desk is for admin roles.',
              severity: GtexBlockedSeverity.warning,
              icon: Icons.lock_outline_rounded,
            ),
          );
        }
        return AdminReviewSection(reader: widget.reader);
    }
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool wide = constraints.maxWidth >= 900;
        final Widget menu = _SectionMenu(
          wide: wide,
          sections: OwnerConsoleSection.values
              .where((OwnerConsoleSection s) => s != OwnerConsoleSection.admin || widget.isAdmin)
              .toList(),
          selected: _section,
          onSelected: (OwnerConsoleSection s) => setState(() => _section = s),
        );
        return Container(
          key: const Key('owner-console'),
          color: Colors.transparent,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              _OwnershipHeader(
                center: _center,
                role: widget.role,
                walletBalance: widget.walletBalance ?? _wallet,
              ),
              if (!wide) menu,
              Expanded(
                child:
                    wide
                        ? Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            SizedBox(width: 230, child: menu),
                            Expanded(child: _body()),
                          ],
                        )
                        : _body(),
              ),
              _Footer(signedInAs: widget.signedInAs, role: widget.role),
            ],
          ),
        );
      },
    );
  }
}

class _DeskLoader extends StatefulWidget {
  const _DeskLoader({required this.load, required this.act});

  final Future<ClubLegacyDeskData> Function() load;
  final Future<void> Function(String action, [Map<String, Object?> payload]) act;

  @override
  State<_DeskLoader> createState() => _DeskLoaderState();
}

class _DeskLoaderState extends State<_DeskLoader> {
  late Future<ClubLegacyDeskData> _desk;

  @override
  void initState() {
    super.initState();
    _desk = widget.load();
  }

  Future<void> _run(String action, [Map<String, Object?> payload = const <String, Object?>{}]) async {
    await widget.act(action, payload);
    setState(() => _desk = widget.load());
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<ClubLegacyDeskData>(
      future: _desk,
      builder: (BuildContext context, AsyncSnapshot<ClubLegacyDeskData> snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Padding(padding: EdgeInsets.all(GtexSpacing.md), child: GtexSkeleton.box(height: 180));
        }
        final ClubLegacyDeskData data = snap.data ??
            const ClubLegacyDeskData(staff: [], policies: [], clubValuation: '0', equity: '0', preseason: [], sponsors: [], offers: [], cases: []);
        return ClubLegacyDesk(
          data: data,
          onAction: (String action, Map<String, Object?> payload) => _run(action, payload),
        );
      },
    );
  }
}

class _OwnershipHeader extends StatelessWidget {
  const _OwnershipHeader({
    required this.center,
    required this.role,
    this.walletBalance,
  });

  final Future<OwnerControlCenter> center;
  final String role;
  final double? walletBalance;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        GtexSpacing.md,
        GtexSpacing.md,
        GtexSpacing.md,
        GtexSpacing.sm,
      ),
      child: FutureBuilder<OwnerControlCenter>(
        future: center,
        builder: (BuildContext context, AsyncSnapshot<OwnerControlCenter> snap) {
          final OwnerControlCenter? data = snap.data;
          final OwnerClubCard? club =
              data == null || data.clubs.isEmpty ? null : data.clubs.first;
          final int decisions = data?.decisions.length ?? 0;
          final String walletLabel =
              walletBalance == null
                  ? '—'
                  : walletBalance!.toStringAsFixed(
                    walletBalance! % 1 == 0 ? 0 : 2,
                  );
          final String title = club == null ? 'Claim your club' : club.name;
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              GtexShellLaneHero.compactStrip(
                key: const Key('owner-console-hero'),
                eyebrow: 'Club ownership',
                title: title,
                summary:
                    club == null
                        ? 'Start ownership with a club identity and today\'s decisions.'
                        : 'Decisions, next fixture, and club capital.',
              ),
              const SizedBox(height: GtexSpacing.sm),
              Wrap(
                spacing: GtexSpacing.xs,
                runSpacing: GtexSpacing.xs,
                children: <Widget>[
                  GtexStatusChip(
                    key: const Key('owner-console-wallet-chip'),
                    label: '$walletLabel GTX',
                    color: GtexFloodlit.pitch,
                    icon: Icons.account_balance_wallet_outlined,
                  ),
                  GtexStatusChip(
                    key: const Key('owner-console-role-chip'),
                    label: role.toUpperCase(),
                    color: GtexFloodlit.gold,
                  ),
                  GtexStatusChip(
                    label: '$decisions due',
                    color:
                        decisions == 0
                            ? GtexFloodlit.pitch
                            : GtexFloodlit.scoreboard,
                    icon: Icons.bolt_rounded,
                  ),
                ],
              ),
            ],
          );
        },
      ),
    );
  }
}

class _SectionMenu extends StatelessWidget {
  const _SectionMenu({
    required this.wide,
    required this.sections,
    required this.selected,
    required this.onSelected,
  });

  final bool wide;
  final List<OwnerConsoleSection> sections;
  final OwnerConsoleSection selected;
  final ValueChanged<OwnerConsoleSection> onSelected;

  @override
  Widget build(BuildContext context) {
    final List<Widget> items = sections.map((
      OwnerConsoleSection s,
    ) {
      final (String label, IconData icon) = _sectionMeta[s]!;
      final bool active = s == selected;
      return Padding(
        padding: EdgeInsets.only(
          bottom: wide ? GtexSpacing.xs : 0,
          right: wide ? 0 : GtexSpacing.xs,
        ),
        child: InkWell(
          key: Key('owner-console-section-${s.name}'),
          borderRadius: BorderRadius.circular(10),
          onTap: () => onSelected(s),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 160),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color:
                  active
                      ? GtexFloodlit.pitch.withValues(alpha: 0.16)
                      : GtexFloodlit.card.withValues(alpha: 0.72),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: active ? GtexFloodlit.pitch : GtexFloodlit.line,
              ),
            ),
            child: Row(
              mainAxisSize: wide ? MainAxisSize.max : MainAxisSize.min,
              children: <Widget>[
                Icon(
                  icon,
                  size: 18,
                  color:
                      active ? GtexFloodlit.pitch : GtexFloodlit.chalkMuted,
                ),
                const SizedBox(width: 8),
                Flexible(
                  child: Text(
                    label,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color:
                          active ? GtexFloodlit.chalk : GtexFloodlit.chalkMuted,
                      fontWeight: FontWeight.w800,
                      fontFamily: GtexFloodlit.display,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }).toList();
    if (wide) {
      return ListView(
        padding: const EdgeInsets.all(GtexSpacing.md),
        children: items,
      );
    }
    return SizedBox(
      height: 52,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: GtexSpacing.md),
        child: Row(children: items),
      ),
    );
  }
}

class _Footer extends StatelessWidget {
  const _Footer({required this.signedInAs, required this.role});

  final String signedInAs;
  final String role;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const Key('owner-console-footer'),
      padding: const EdgeInsets.symmetric(
        horizontal: GtexSpacing.md,
        vertical: GtexSpacing.sm,
      ),
      decoration: const BoxDecoration(
        border: Border(top: BorderSide(color: GtexColors.line)),
      ),
      child: Text(
        'Signed in as $signedInAs · ${role.replaceAll('_', ' ')} access',
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(
          color: GtexColors.textMuted,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
