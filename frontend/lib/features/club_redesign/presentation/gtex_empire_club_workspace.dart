import 'dart:async';

import 'package:flutter/material.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../widgets/gtex_empire_club_switcher.dart';
import '../widgets/gtex_empire_group_panel.dart';

/// Loads owned clubs + ownership groups, then hosts the active club desk.
///
/// Phase B3: Exposes `onClubsLoaded` and `onClubActivated` so the shell top bar
/// and club-scoped surfaces stay synchronized with `/api/clubs/owned/{id}/activate`.
class GtexEmpireClubWorkspace extends StatefulWidget {
  const GtexEmpireClubWorkspace({
    super.key,
    required this.controller,
    required this.activeClubId,
    required this.activeClubName,
    required this.child,
    this.authedApi,
    this.onClubsLoaded,
    this.onClubActivated,
  });

  final GteExchangeController controller;
  final String activeClubId;
  final String? activeClubName;
  final Widget child;
  final GteAuthedApi? authedApi;
  final ValueChanged<List<GtexOwnedClubOption>>? onClubsLoaded;
  final ValueChanged<GtexOwnedClubOption>? onClubActivated;

  /// Shared helper to activate a club via `/api/clubs/owned/{id}/activate`
  /// and bind it to [GteExchangeController].
  static Future<void> activateClub({
    required GteAuthedApi api,
    required GteExchangeController controller,
    required GtexOwnedClubOption club,
  }) async {
    await api.post('/api/clubs/owned/${club.id}/activate');
    controller.bindCurrentClub(
      clubId: club.id,
      clubName: club.name,
      clubSlug: club.slug,
    );
  }

  @override
  State<GtexEmpireClubWorkspace> createState() =>
      _GtexEmpireClubWorkspaceState();
}

class _GtexEmpireClubWorkspaceState extends State<GtexEmpireClubWorkspace> {
  List<GtexOwnedClubOption> _clubs = const <GtexOwnedClubOption>[];
  List<GtexEmpireGroupSummary> _groups = const <GtexEmpireGroupSummary>[];
  bool _loading = false;
  bool _switching = false;
  String? _error;
  String? _groupError;

  @override
  void initState() {
    super.initState();
    unawaited(_load());
  }

  @override
  void didUpdateWidget(covariant GtexEmpireClubWorkspace oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.activeClubId != widget.activeClubId ||
        oldWidget.authedApi != widget.authedApi) {
      unawaited(_load());
    }
  }

  Future<void> _load() async {
    final GteAuthedApi? api = widget.authedApi;
    if (api == null || !widget.controller.isAuthenticated) {
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
      _groupError = null;
    });
    try {
      final List<dynamic> clubPayload = await api.getList('/api/clubs/owned');
      final List<GtexOwnedClubOption> clubs =
          clubPayload
              .map(GtexOwnedClubOption.fromJson)
              .where((GtexOwnedClubOption club) => club.id.isNotEmpty)
              .toList(growable: false);
      List<GtexEmpireGroupSummary> groups = const <GtexEmpireGroupSummary>[];
      String? groupError;
      try {
        final List<dynamic> groupPayload = await api.getList(
          '/api/ownership-groups',
        );
        groups =
            groupPayload
                .map(GtexEmpireGroupSummary.fromJson)
                .where((GtexEmpireGroupSummary group) => group.id.isNotEmpty)
                .toList(growable: false);
      } catch (error) {
        debugPrint('Could not load ownership groups: $error');
        groupError = 'Ownership groups could not be loaded right now.';
      }
      if (!mounted) {
        return;
      }
      setState(() {
        _clubs = clubs;
        _groups = groups;
        _groupError = groupError;
        _loading = false;
      });
      widget.onClubsLoaded?.call(clubs);
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _loading = false;
        _error = 'Could not load empire clubs: $error';
      });
    }
  }

  Future<void> _activate(GtexOwnedClubOption club) async {
    final GteAuthedApi? api = widget.authedApi;
    if (api == null || _switching) {
      return;
    }
    setState(() {
      _switching = true;
      _error = null;
    });
    try {
      await GtexEmpireClubWorkspace.activateClub(
        api: api,
        controller: widget.controller,
        club: club,
      );
      if (!mounted) {
        return;
      }
      setState(() => _switching = false);
      widget.onClubActivated?.call(club);
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _switching = false;
        _error = 'Could not switch club: $error';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final double childHeight =
            !constraints.hasBoundedHeight
                ? 720
                : constraints.maxHeight > 560
                ? constraints.maxHeight
                : 560;
        return SingleChildScrollView(
          child: Column(
            children: <Widget>[
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  GtexSpacing.md,
                  GtexSpacing.md,
                  GtexSpacing.md,
                  0,
                ),
                child: Column(
                  children: <Widget>[
                    GtexEmpireClubSwitcher(
                      clubs: _clubs,
                      activeClubId: widget.activeClubId,
                      busy: _switching || _loading,
                      errorMessage: _error,
                      onActivate: (GtexOwnedClubOption club) {
                        unawaited(_activate(club));
                      },
                    ),
                    const SizedBox(height: GtexSpacing.sm),
                    GtexEmpireGroupPanel(
                      groups: _groups,
                      isLoading: _loading,
                      errorMessage: _groupError,
                      onRetry: () => unawaited(_load()),
                    ),
                  ],
                ),
              ),
              SizedBox(height: childHeight, child: widget.child),
            ],
          ),
        );
      },
    );
  }
}
