import 'package:flutter/material.dart';

import '../../data/personal_manager_api.dart';
import '../../ui_gtex/ui_gtex.dart';

/// Club-owner personal manager office: load / create / appoint against live
/// `/api/clubs/personal-manager` contracts.
class GtexPersonalManagerOfficePanel extends StatefulWidget {
  const GtexPersonalManagerOfficePanel({
    super.key,
    required this.api,
    this.clubId,
  });

  final PersonalManagerApi api;
  final String? clubId;

  @override
  State<GtexPersonalManagerOfficePanel> createState() =>
      _GtexPersonalManagerOfficePanelState();
}

class _GtexPersonalManagerOfficePanelState
    extends State<GtexPersonalManagerOfficePanel> {
  late Future<PersonalManagerProfile?> _future;
  bool _busy = false;
  String? _error;
  String? _message;
  final TextEditingController _nameController = TextEditingController(
    text: 'My Personal Manager',
  );

  @override
  void initState() {
    super.initState();
    _future = widget.api.fetchMe();
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  void _reload() {
    setState(() {
      _error = null;
      _message = null;
      _future = widget.api.fetchMe();
    });
  }

  Future<void> _create() async {
    if (_busy) {
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
      _message = null;
    });
    try {
      final PersonalManagerProfile created = await widget.api.create(
        displayName: _nameController.text.trim().isEmpty
            ? 'My Personal Manager'
            : _nameController.text.trim(),
        qualityBand: 3,
        fanCoinPrice: 25000,
        tacticalIdentity: const <String, Object?>{
          'identity': 'balanced_control',
        },
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _message = 'Created ${created.displayName}.';
        _future = Future<PersonalManagerProfile?>.value(created);
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() => _error = error.toString());
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  Future<void> _appoint(PersonalManagerProfile profile) async {
    final String? clubId = widget.clubId?.trim();
    if (_busy || clubId == null || clubId.isEmpty) {
      setState(
        () =>
            _error =
                'Appoint requires an owned club id on this desk.',
      );
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
      _message = null;
    });
    try {
      await widget.api.appointToClub(clubId);
      if (!mounted) {
        return;
      }
      setState(
        () => _message =
            '${profile.displayName} appointed to club $clubId.',
      );
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() => _error = error.toString());
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<PersonalManagerProfile?>(
      future: _future,
      builder: (
        BuildContext context,
        AsyncSnapshot<PersonalManagerProfile?> snapshot,
      ) {
        if (snapshot.hasError) {
          return GtexPanel(
            title: 'Personal manager office',
            subtitle: snapshot.error.toString(),
            accent: GtexColors.orange,
            child: GtexActionButton(
              label: 'Retry office',
              icon: Icons.refresh,
              onPressed: _reload,
              accent: GtexColors.orange,
              secondary: true,
            ),
          );
        }
        if (!snapshot.hasData &&
            snapshot.connectionState != ConnectionState.done) {
          return const GtexPanel(
            title: 'Personal manager office',
            subtitle: 'Loading your profile-bound manager…',
            accent: GtexColors.orange,
            child: LinearProgressIndicator(),
          );
        }
        final PersonalManagerProfile? profile = snapshot.data;
        return GtexPanel(
          title: 'Personal manager office',
          subtitle:
              profile == null
                  ? 'Create a permanent, non-transferable personal manager bound to your account, then appoint them to a club you operate.'
                  : 'Live personal manager from /api/clubs/personal-manager/me.',
          accent: GtexColors.orange,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              if (_error != null) ...<Widget>[
                Text(
                  _error!,
                  style: const TextStyle(color: GtexColors.red, height: 1.4),
                ),
                const SizedBox(height: GtexSpacing.sm),
              ],
              if (_message != null) ...<Widget>[
                Text(
                  _message!,
                  style: const TextStyle(color: GtexColors.pitch, height: 1.4),
                ),
                const SizedBox(height: GtexSpacing.sm),
              ],
              if (profile == null) ...<Widget>[
                TextField(
                  controller: _nameController,
                  decoration: const InputDecoration(
                    labelText: 'Display name',
                  ),
                ),
                const SizedBox(height: GtexSpacing.sm),
                GtexActionButton(
                  label: _busy ? 'Creating…' : 'Create personal manager',
                  icon: Icons.person_add_alt_1_outlined,
                  onPressed: _busy ? null : _create,
                  accent: GtexColors.orange,
                ),
              ] else ...<Widget>[
                Text(
                  profile.displayName,
                  style: const TextStyle(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                    fontSize: 18,
                  ),
                ),
                const SizedBox(height: GtexSpacing.xs),
                Text(
                  'Band ${profile.qualityBand} • GSI ${profile.gsiRating} (${profile.gsiMin}-${profile.gsiMax}) • ${profile.fanCoinPrice} coin',
                  style: const TextStyle(color: GtexColors.textSecondary),
                ),
                const SizedBox(height: GtexSpacing.sm),
                Wrap(
                  spacing: GtexSpacing.xs,
                  runSpacing: GtexSpacing.xs,
                  children: <Widget>[
                    GtexStatusChip(
                      label: profile.permanent ? 'PERMANENT' : 'TEMPORARY',
                      color: GtexColors.gold,
                    ),
                    GtexStatusChip(
                      label:
                          profile.transferable
                              ? 'TRANSFERABLE'
                              : 'NON-TRANSFERABLE',
                      color: GtexColors.cyan,
                    ),
                    GtexStatusChip(
                      label:
                          profile.salaryBearing
                              ? 'SALARY'
                              : 'NO CLUB SALARY',
                      color: GtexColors.pitch,
                    ),
                  ],
                ),
                const SizedBox(height: GtexSpacing.md),
                GtexActionButton(
                  label: _busy ? 'Appointing…' : 'Appoint to my club',
                  icon: Icons.how_to_reg_outlined,
                  onPressed:
                      _busy || (widget.clubId ?? '').trim().isEmpty
                          ? null
                          : () => _appoint(profile),
                  accent: GtexColors.pitch,
                ),
                if ((widget.clubId ?? '').trim().isEmpty) ...<Widget>[
                  const SizedBox(height: GtexSpacing.xs),
                  const Text(
                    'Appoint unlocks when this desk knows which club you operate.',
                    style: TextStyle(color: GtexColors.textMuted),
                  ),
                ],
              ],
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                label: 'Refresh office',
                icon: Icons.refresh,
                onPressed: _busy ? null : _reload,
                accent: GtexColors.orange,
                secondary: true,
              ),
            ],
          ),
        );
      },
    );
  }
}
