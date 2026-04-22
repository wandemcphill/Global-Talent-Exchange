import 'package:flutter/material.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

import '../data/club_identity_repository.dart';
import 'club_identity_controller.dart';
import 'identity_preview_screen.dart';

class ClubIdentityScreen extends StatefulWidget {
  const ClubIdentityScreen({
    super.key,
    required this.clubId,
    this.initialClubName,
    this.apiBaseUrl,
    this.backendMode,
    this.controller,
    this.repository,
  });

  final String clubId;
  final String? initialClubName;
  final String? apiBaseUrl;
  final GteBackendMode? backendMode;
  final ClubIdentityController? controller;
  final ClubIdentityRepository? repository;

  @override
  State<ClubIdentityScreen> createState() => _ClubIdentityScreenState();
}

class _ClubIdentityScreenState extends State<ClubIdentityScreen> {
  late final ClubIdentityController _controller;
  late final bool _ownsController;

  @override
  void initState() {
    super.initState();
    _ownsController = widget.controller == null;
    _controller =
        widget.controller ??
        ClubIdentityController(
          clubId: widget.clubId,
          initialClubName: widget.initialClubName,
          repository:
              widget.repository ??
              ClubIdentityApiRepository.standard(
                baseUrl: widget.apiBaseUrl ?? 'http://127.0.0.1:8000',
                mode: widget.backendMode ?? GteBackendMode.live,
              ),
        );
    if (!_controller.isLoading && !_controller.hasIdentity) {
      _controller.load();
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
    return AnimatedBuilder(
      animation: _controller,
      builder: (BuildContext context, _) {
        if (_controller.isLoading && !_controller.hasIdentity) {
          return Container(
            decoration: gteBackdropDecoration(),
            child: const Scaffold(
              backgroundColor: Colors.transparent,
              body: Center(child: CircularProgressIndicator()),
            ),
          );
        }
        if (_controller.errorMessage != null && !_controller.hasIdentity) {
          return Container(
            decoration: gteBackdropDecoration(),
            child: Scaffold(
              backgroundColor: Colors.transparent,
              body: Center(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: GteStatePanel(
                    title: 'Club identity unavailable',
                    message: _controller.errorMessage!,
                    actionLabel: 'Retry',
                    onAction: _controller.load,
                    icon: Icons.shield_outlined,
                    accentColor: GteShellTheme.accentClub,
                  ),
                ),
              ),
            ),
          );
        }
        return IdentityPreviewScreen(controller: _controller);
      },
    );
  }
}
