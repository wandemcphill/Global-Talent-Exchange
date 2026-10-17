import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../data/owner_ops_api.dart';
import '../widgets/owner_admin_review_section.dart';

const Map<String, String> _modeLabels = <String, String>{'owner_only': 'Owner only', 'approval': 'Needs approval', 'auto': 'Auto within budget'};

/// GM / HoYD hiring, per-task delegation policies and the staff action log.
class StaffDelegationPanel extends StatelessWidget {
  const StaffDelegationPanel({super.key, required this.client, required this.clubId, required this.onChanged});

  final OwnerOpsClient client;
  final String clubId;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) => OpsLoader(
    key: ValueKey<String>('owner-staff-$clubId'),
    label: 'Staff',
    load: () => client.get('/owner/clubs/$clubId/staff'),
    builder: (BuildContext context, Map<String, dynamic> d, VoidCallback reload) {
      void changed() {
        reload();
        onChanged();
      }

      final List<Map<String, dynamic>> staff = opsMaps(d['staff']);
      final Map<String, dynamic> candidates = opsMap(d['candidates']);
      return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
        for (final (String role, String label) in const <(String, String)>[('gm', 'General Manager'), ('hoyd', 'Head of Youth Development')])
          Padding(
            padding: const EdgeInsets.only(bottom: GtexSpacing.md),
            child: GtexPanel(
              key: Key('owner-staff-role-$role'),
              title: label,
              subtitle: role == 'gm' ? 'Transfers, bids and squad budget' : 'Academy intakes and contract renewals',
              accent: role == 'gm' ? GtexColors.cyan : GtexColors.pitch,
              child: Column(children: <Widget>[
                for (final Map<String, dynamic> s in staff.where((Map<String, dynamic> s) => s['role'] == role))
                  OpsLine(
                    key: Key('owner-staff-${s['id']}'),
                    title: '${opsStr(s['name'])} · quality ${s['quality']}/20',
                    subtitle: '${opsMap(s['attributes']).entries.map((MapEntry<String, dynamic> e) => '${opsLabel(e.key)} ${e.value}').join(' · ')} · ${opsLabel(opsMap(s['personality'])['risk_appetite'])} · ${opsGtx(s['salary_per_cycle'])} per cycle',
                    trailing: GtexActionButton(
                      key: Key('owner-staff-release-${s['id']}'),
                      label: 'Release',
                      compact: true,
                      secondary: true,
                      accent: GtexColors.red,
                      onPressed: () async {
                        if (await confirmOwnerAction(context, title: 'Release ${opsStr(s['name'])}?', message: 'They stop acting for the club immediately.', confirmLabel: 'Release') == null || !context.mounted) return;
                        if (await runOwnerAction(context, () => client.post('/owner/clubs/$clubId/staff/${s['id']}/release'), success: (_) => '${opsStr(s['name'])} released') != null) changed();
                      },
                    ),
                  ),
                for (final Map<String, dynamic> c in opsMaps(candidates[role]))
                  OpsLine(
                    key: Key('owner-candidate-${c['candidate_id']}'),
                    title: '${opsStr(c['name'])} · quality ${c['quality']}/20',
                    subtitle: '${opsMap(c['attributes']).entries.map((MapEntry<String, dynamic> e) => '${opsLabel(e.key)} ${e.value}').join(' · ')} · ${opsLabel(opsMap(c['personality'])['risk_appetite'])}',
                    accent: GtexColors.textMuted,
                    trailing: GtexActionButton(
                      key: Key('owner-hire-staff-${c['candidate_id']}'),
                      label: 'Hire · ${opsGtx(c['salary_per_cycle'])}/cycle',
                      compact: true,
                      onPressed: () async {
                        if (await confirmOwnerAction(context, title: 'Hire ${opsStr(c['name'])}?', message: 'Salary ${opsGtx(c['salary_per_cycle'])} per world-day cycle, paid from club cash.', confirmLabel: 'Hire') == null || !context.mounted) return;
                        if (await runOwnerAction(context, () => client.post('/owner/clubs/$clubId/staff/hire', body: <String, Object?>{'candidate_id': c['candidate_id']}), success: (_) => '${opsStr(c['name'])} hired') != null) changed();
                      },
                    ),
                  ),
              ]),
            ),
          ),
        GtexPanel(
          key: const Key('owner-delegation-policies'),
          title: 'Delegation rules',
          subtitle: 'What your staff may do without you',
          accent: GtexColors.gold,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            for (final Map<String, dynamic> p in opsMaps(d['policies'])) _PolicyRow(client: client, clubId: clubId, policy: p, onSaved: changed),
            const SizedBox(height: GtexSpacing.sm),
            const Text('Always yours', style: TextStyle(color: GtexColors.textSecondary, fontSize: 12, fontWeight: FontWeight.w700)),
            Wrap(spacing: GtexSpacing.xs, children: <Widget>[
              for (final Map<String, dynamic> r in opsMaps(d['reserved'])) GtexStatusChip(label: opsStr(r['label']), icon: Icons.lock_outline_rounded, color: GtexColors.textSecondary, compact: true),
            ]),
          ]),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          key: const Key('owner-staff-actions'),
          title: 'Staff actions',
          subtitle: 'Every action traces to a policy version',
          accent: GtexColors.cyan,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            GtexActionButton(
              key: const Key('owner-staff-run'),
              label: 'Let staff review now',
              compact: true,
              secondary: true,
              onPressed: () async {
                if (await runOwnerAction(context, () => client.post('/owner/clubs/$clubId/staff/run'), success: (Map<String, dynamic> r) => '${r['executed'] ?? 0} handled · ${r['recommended'] ?? 0} recommended') != null) changed();
              },
            ),
            if (opsMaps(d['actions']).isEmpty) const OpsNote('No staff actions yet.'),
            for (final Map<String, dynamic> a in opsMaps(d['actions']))
              OpsLine(
                title: '${opsLabel(a['task'])}: ${opsLabel(a['recommendation'])} · ${opsStr(a['status'])}',
                subtitle: '${opsStr(a['reason'], '')} ${opsStr(a['outcome'], '')} · ${a['confidence']}% · policy v${a['policy_version']} (${_modeLabels[a['mode']] ?? a['mode']})',
                accent: a['status'] == 'executed' ? GtexColors.pitch : GtexColors.gold,
              ),
          ]),
        ),
      ]);
    },
  );
}

class _PolicyRow extends StatefulWidget {
  const _PolicyRow({required this.client, required this.clubId, required this.policy, required this.onSaved});

  final OwnerOpsClient client;
  final String clubId;
  final Map<String, dynamic> policy;
  final VoidCallback onSaved;

  @override
  State<_PolicyRow> createState() => _PolicyRowState();
}

class _PolicyRowState extends State<_PolicyRow> {
  late String _mode = '${widget.policy['mode']}';
  late final TextEditingController _cap = TextEditingController(text: opsFmt(widget.policy['budget_cap']).replaceAll(',', ''));

  @override
  void dispose() {
    _cap.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final String task = '${widget.policy['task']}';
    return Container(
      key: Key('owner-policy-$task'),
      margin: const EdgeInsets.only(bottom: GtexSpacing.sm),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        Text('${opsStr(widget.policy['label'])} · ${widget.policy['role'] == 'gm' ? 'GM' : 'HoYD'} · v${widget.policy['version']}', style: const TextStyle(color: GtexColors.text, fontWeight: FontWeight.w700)),
        const SizedBox(height: 4),
        Wrap(spacing: GtexSpacing.xs, runSpacing: GtexSpacing.xs, crossAxisAlignment: WrapCrossAlignment.center, children: <Widget>[
          for (final MapEntry<String, String> m in _modeLabels.entries)
            GtexActionButton(key: Key('owner-policy-$task-${m.key}'), label: m.value, compact: true, secondary: _mode != m.key, onPressed: () => setState(() => _mode = m.key)),
          OpsField(key: Key('owner-policy-$task-cap'), controller: _cap, label: 'Budget cap (GTX)', number: true, width: 150),
          GtexActionButton(
            key: Key('owner-policy-$task-save'),
            label: 'Save',
            compact: true,
            onPressed: () async {
              if (await runOwnerAction(context, () => widget.client.put('/owner/clubs/${widget.clubId}/delegation/$task', body: <String, Object?>{'mode': _mode, 'budget_cap': opsNum(_cap.text)}), success: (Map<String, dynamic> r) => 'Rule saved (v${r['version']})') != null) widget.onSaved();
            },
          ),
        ]),
      ]),
    );
  }
}
