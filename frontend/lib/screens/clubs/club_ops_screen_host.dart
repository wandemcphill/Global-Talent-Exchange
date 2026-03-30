import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/widgets/gte_route_integrity_screen.dart';

typedef ClubOpsViewBuilder =
    Widget Function(BuildContext context, ClubOpsController controller);

class ClubOpsScreenHost extends StatelessWidget {
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
  Widget build(BuildContext context) {
    return const GteRouteIntegrityScreen.blocked(
      title: 'Club operations unavailable',
      message:
          'Academy, finance, sponsorship, scouting, youth pipeline, and club operations admin routes are blocked until the club backend can run without fixture fallback.',
      icon: Icons.dashboard_customize_outlined,
    );
  }
}
