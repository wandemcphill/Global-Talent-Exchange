import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../data/owner_console_api.dart';
import '../data/owner_ops_api.dart';
import '../widgets/owner_console_sections.dart';

/// Full owner inbox with open / resolved / all filters and inline decisions.
class OwnerInboxSection extends StatefulWidget {
  const OwnerInboxSection({super.key, required this.client, required this.reader, required this.onNavigate, required this.onChanged});

  final OwnerOpsClient client;
  final OwnerConsoleReader reader;
  final ValueChanged<String> onNavigate;
  final VoidCallback onChanged;

  @override
  State<OwnerInboxSection> createState() => _OwnerInboxSectionState();
}

class _OwnerInboxSectionState extends State<OwnerInboxSection> {
  String _status = 'open';
  String? _outcome;
  int _version = 0;

  @override
  Widget build(BuildContext context) {
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
      Padding(
        padding: const EdgeInsets.fromLTRB(GtexSpacing.md, GtexSpacing.md, GtexSpacing.md, 0),
        child: Wrap(spacing: GtexSpacing.xs, children: <Widget>[
          for (final String s in <String>['open', 'resolved', 'all'])
            GtexActionButton(key: Key('owner-inbox-filter-$s'), label: s, compact: true, secondary: _status != s, onPressed: () => setState(() => _status = s)),
        ]),
      ),
      if (_outcome != null)
        Padding(
          padding: const EdgeInsets.fromLTRB(GtexSpacing.md, GtexSpacing.sm, GtexSpacing.md, 0),
          child: Text(_outcome!, key: const Key('owner-inbox-outcome'), style: const TextStyle(color: GtexColors.pitch, fontWeight: FontWeight.w700)),
        ),
      Expanded(
        child: OpsLoader(
          key: ValueKey<String>('owner-inbox-$_status-$_version'),
          label: 'Inbox',
          load: () => widget.client.get('/owner/inbox', query: <String, Object?>{'status': _status}),
          builder: (BuildContext context, Map<String, dynamic> d, _) {
            final List<OwnerInboxEntry> items = opsMaps(d['items']).map(OwnerInboxEntry.fromJson).toList();
            return opsList(<Widget>[
              if (items.isEmpty) const GtexEmptyState(key: Key('owner-inbox-empty'), title: 'Nothing here', message: 'Advance the world day from the Academy to generate new events.', icon: Icons.inbox_outlined),
              for (final OwnerInboxEntry e in items)
                e.isDecision && e.status == 'open'
                    ? OwnerDecisionRow(
                        key: ValueKey<String>('inbox-decision-${e.id}'),
                        entry: e,
                        reader: widget.reader,
                        onTap: () => widget.onNavigate(decisionRoute(e.kind)),
                        onResolved: (String outcome) {
                          setState(() {
                            _outcome = outcome;
                            _version++;
                          });
                          widget.onChanged();
                        },
                      )
                    : OpsLine(
                        key: Key('owner-inbox-item-${e.id}'),
                        title: e.title,
                        subtitle: <String?>[e.what ?? e.why, e.outcome, e.sender].whereType<String>().join(' · '),
                        accent: inboxAccent(e),
                        trailing: e.status == null ? null : GtexStatusChip(label: e.status!, color: GtexColors.textSecondary, compact: true),
                      ),
            ]);
          },
        ),
      ),
    ]);
  }
}
