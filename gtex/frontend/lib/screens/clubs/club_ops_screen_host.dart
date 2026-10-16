import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_scaffold.dart';

typedef ClubOpsViewBuilder =
    Widget Function(BuildContext context, ClubOpsController controller);

class ClubOpsScreenHost extends StatefulWidget {
  const ClubOpsScreenHost({
    super.key,
    required this.title,
    required this.builder,
    this.subtitle,
    this.clubId = 'royal-lagos-fc',
    this.clubName,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.mode = GteBackendMode.live,
    this.api,
    this.controller,
    this.actions = const <Widget>[],
    this.adminData = false,
  });

  final String title;
  final String? subtitle;
  final String clubId;
  final String? clubName;
  final String baseUrl;
  final GteBackendMode mode;
  final ClubOpsApi? api;
  final ClubOpsController? controller;
  final List<Widget> actions;
  final bool adminData;
  final ClubOpsViewBuilder builder;

  @override
  State<ClubOpsScreenHost> createState() => _ClubOpsScreenHostState();
}

class _ClubOpsScreenHostState extends State<ClubOpsScreenHost> {
  ClubOpsController? _ownedController;

  ClubOpsController get _controller => widget.controller ?? _ownedController!;

  @override
  void initState() {
    super.initState();
    _syncController();
    _load();
  }

  @override
  void didUpdateWidget(covariant ClubOpsScreenHost oldWidget) {
    super.didUpdateWidget(oldWidget);
    final bool needsControllerRefresh =
        oldWidget.controller != widget.controller ||
        oldWidget.api != widget.api ||
        oldWidget.baseUrl != widget.baseUrl ||
        oldWidget.mode != widget.mode ||
        oldWidget.clubId != widget.clubId ||
        oldWidget.clubName != widget.clubName;
    final bool needsReload =
        needsControllerRefresh || oldWidget.adminData != widget.adminData;
    if (!needsControllerRefresh && !needsReload) {
      return;
    }
    _syncController();
    _load(force: needsReload);
  }

  @override
  void dispose() {
    _ownedController?.dispose();
    super.dispose();
  }

  void _syncController() {
    if (widget.controller != null) {
      _ownedController?.dispose();
      _ownedController = null;
      return;
    }

    if (_ownedController != null &&
        _ownedController!.clubId == widget.clubId &&
        _ownedController!.clubName == widget.clubName) {
      return;
    }

    _ownedController?.dispose();
    _ownedController = ClubOpsController(
      api:
          widget.api ??
          ClubOpsApi.standard(baseUrl: widget.baseUrl, mode: widget.mode),
      clubId: widget.clubId,
      clubName: widget.clubName,
    );
  }

  void _load({bool force = false}) {
    final ClubOpsController controller = _controller;
    if (widget.adminData) {
      controller.loadAdminData(force: force);
      return;
    }
    controller.loadClubData(force: force);
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (BuildContext context, Widget? child) {
        return ClubOpsScaffold(
          title: widget.title,
          subtitle: widget.subtitle,
          actions: widget.actions,
          body: widget.builder(context, _controller),
        );
      },
    );
  }
}
