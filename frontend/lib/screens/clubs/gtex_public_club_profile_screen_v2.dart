import 'dart:async';

import 'package:flutter/material.dart';
import 'package:gte_frontend/data/club_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/club_redesign/club_redesign.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

class GtexPublicClubProfileScreenV2 extends StatefulWidget {
  const GtexPublicClubProfileScreenV2({
    super.key,
    required this.clubId,
    this.clubName,
    this.baseUrl,
    this.backendMode,
    this.accessToken,
    this.snapshotApi,
    this.isAuthenticated = true,
    this.onOpenLogin,
  });

  final String clubId;
  final String? clubName;
  final String? baseUrl;
  final GteBackendMode? backendMode;
  final String? accessToken;
  final ClubApi? snapshotApi;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;

  @override
  State<GtexPublicClubProfileScreenV2> createState() =>
      _GtexPublicClubProfileScreenV2State();
}

class _GtexPublicClubProfileScreenV2State
    extends State<GtexPublicClubProfileScreenV2> {
  ClubApi? _snapshotApi;
  GtexClubWorkspaceSnapshot? _snapshot;
  String? _snapshotError;
  bool _snapshotLoading = false;
  int _snapshotRequestId = 0;

  @override
  void initState() {
    super.initState();
    _createController();
  }

  @override
  void didUpdateWidget(covariant GtexPublicClubProfileScreenV2 oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.clubId != widget.clubId ||
        oldWidget.baseUrl != widget.baseUrl ||
        oldWidget.backendMode != widget.backendMode ||
        oldWidget.accessToken != widget.accessToken ||
        oldWidget.snapshotApi != widget.snapshotApi ||
        oldWidget.clubName != widget.clubName) {
      _resetSnapshotState();
      _createController();
    }
  }

  @override
  void dispose() {
    _snapshotRequestId += 1;
    super.dispose();
  }

  void _resetSnapshotState() {
    _snapshotRequestId += 1;
    _snapshotApi = null;
    _snapshot = null;
    _snapshotError = null;
    _snapshotLoading = false;
  }

  void _createController() {
    final String? baseUrl = widget.baseUrl;
    if (baseUrl == null || baseUrl.trim().isEmpty) {
      _snapshotApi = null;
      return;
    }
    _snapshotApi =
        widget.snapshotApi ??
        ClubApi.standard(
          baseUrl: baseUrl,
          mode: widget.backendMode ?? GteBackendMode.live,
          accessToken: widget.accessToken,
        );
    unawaited(_loadSnapshot(notify: false));
  }

  Future<void> _loadSnapshot({bool notify = true}) {
    final ClubApi? api = _snapshotApi;
    if (api == null) {
      return Future<void>.value();
    }
    final int requestId = ++_snapshotRequestId;
    void update(VoidCallback callback) {
      if (notify && mounted) {
        setState(callback);
      } else {
        callback();
      }
    }

    update(() {
      _snapshotLoading = true;
      _snapshotError = null;
      _snapshot = null;
    });
    return () async {
      try {
        final GtexClubWorkspaceSnapshot snapshot = await api
            .fetchV2WorkspaceSnapshot(
              clubId: widget.clubId,
              clubName: widget.clubName,
            );
        if (!mounted || requestId != _snapshotRequestId) {
          return;
        }
        setState(() {
          _snapshot = snapshot;
          _snapshotError = null;
          _snapshotLoading = false;
        });
      } catch (error) {
        if (!mounted || requestId != _snapshotRequestId) {
          return;
        }
        setState(() {
          _snapshot = null;
          _snapshotError = _snapshotErrorMessage(error);
          _snapshotLoading = false;
        });
      }
    }();
  }

  String _snapshotErrorMessage(Object error) {
    if (error is GteApiException) {
      return error.message;
    }
    return 'GTEX could not load this live Club V2 snapshot. $error';
  }

  @override
  Widget build(BuildContext context) {
    if (_snapshotApi == null) {
      return Padding(
        padding: const EdgeInsets.all(GtexSpacing.lg),
        child: GtexEmptyState(
          title: 'Club profile unavailable',
          message:
              'GTEX needs a live API base URL before this public club profile can load.',
          icon: Icons.shield_outlined,
        ),
      );
    }

    final GtexClubWorkspaceSnapshot? snapshot = _snapshot;
    if (_snapshotLoading && snapshot == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (snapshot == null) {
      return Padding(
        padding: const EdgeInsets.all(GtexSpacing.lg),
        child: GtexEmptyState(
          title: 'Live club profile unavailable',
          message:
              _snapshotError ??
              'GTEX could not load this public Club V2 snapshot from the live backend.',
          icon: Icons.shield_outlined,
          actionLabel: 'Retry club',
          onAction: () => unawaited(_loadSnapshot()),
        ),
      );
    }
    return GtexPublicClubProfileV2(
      clubId: widget.clubId,
      clubName: widget.clubName,
      baseUrl: widget.baseUrl,
      backendMode: widget.backendMode,
      accessToken: widget.accessToken,
      initialSnapshot: snapshot,
      isAuthenticated: widget.isAuthenticated,
      onOpenLogin: widget.onOpenLogin,
    );
  }
}
