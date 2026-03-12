import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_scaffold.dart';

typedef ClubOpsViewBuilder = Widget Function(
  BuildContext context,
  ClubOpsController controller,
);

class ClubOpsScreenHost extends StatefulWidget {
  const ClubOpsScreenHost({
    super.key,
    required this.title,
    required this.builder,
    this.subtitle,
    this.clubId = 'royal-lagos-fc',
    this.clubName,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.mode = GteBackendMode.liveThenFixture,
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
  late final ClubOpsController _controller;
  late final bool _ownsController;

  @override
  void initState() {
    super.initState();
    _ownsController = widget.controller == null;
    _controller = widget.controller ??
        ClubOpsController(
          api: widget.api ??
              ClubOpsApi.standard(
                baseUrl: widget.baseUrl,
                mode: widget.mode,
              ),
          clubId: widget.clubId,
          clubName: widget.clubName,
        );
    if (widget.adminData) {
      _controller.loadAdminData();
    } else {
      _controller.loadClubData();
    }
  }

  @override
  void dispose() {
    if (_ownsController) {
      _controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ClubOpsScaffold(
      title: widget.title,
      subtitle: widget.subtitle,
      actions: widget.actions,
      body: AnimatedBuilder(
        animation: _controller,
        builder: (BuildContext context, Widget? child) {
          return widget.builder(context, _controller);
        },
      ),
    );
  }
}
