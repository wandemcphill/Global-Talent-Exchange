import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/creator_club_follow_controller.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/community_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class CreatorClubFollowPanel extends StatefulWidget {
  const CreatorClubFollowPanel({
    super.key,
    required this.baseUrl,
    required this.backendMode,
    required this.clubId,
    this.clubName,
    this.accessToken,
    this.isAuthenticated = false,
    this.onOpenLogin,
    this.api,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String clubId;
  final String? clubName;
  final String? accessToken;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;
  final CommunityApi? api;

  @override
  State<CreatorClubFollowPanel> createState() => _CreatorClubFollowPanelState();
}

class _CreatorClubFollowPanelState extends State<CreatorClubFollowPanel> {
  late CreatorClubFollowController _controller;

  @override
  void initState() {
    super.initState();
    _controller = _buildController();
    _controller.load();
  }

  @override
  void didUpdateWidget(covariant CreatorClubFollowPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.baseUrl != widget.baseUrl ||
        oldWidget.backendMode != widget.backendMode ||
        oldWidget.accessToken != widget.accessToken ||
        oldWidget.clubId != widget.clubId ||
        oldWidget.isAuthenticated != widget.isAuthenticated ||
        oldWidget.api != widget.api) {
      _controller.dispose();
      _controller = _buildController();
      _controller.load();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  CreatorClubFollowController _buildController() {
    return CreatorClubFollowController(
      api:
          widget.api ??
          CommunityApi.standard(
            baseUrl: widget.baseUrl,
            accessToken: widget.accessToken,
            mode: widget.backendMode,
          ),
      clubId: widget.clubId,
      isAuthenticated: widget.isAuthenticated,
    );
  }

  Future<void> _toggleFollow() async {
    final bool? nextValue = await _controller.toggleFollow();
    if (!mounted) {
      return;
    }
    final String? errorMessage = _controller.errorMessage;
    if (errorMessage != null && errorMessage.trim().isNotEmpty) {
      AppFeedback.showError(context, errorMessage);
      return;
    }
    AppFeedback.showSuccess(
      context,
      nextValue == true ? 'Club follow enabled.' : 'Club follow removed.',
    );
  }

  @override
  Widget build(BuildContext context) {
    final String clubId = widget.clubId.trim();
    if (clubId.isEmpty) {
      return const GteSurfacePanel(
        child: Text(
          'Community follow needs a live club context before it can become actionable.',
        ),
      );
    }
    final bool hasAuthedApi =
        widget.isAuthenticated &&
        (widget.api != null || !(widget.accessToken?.trim().isEmpty ?? true));
    if (!hasAuthedApi) {
      return GteSurfacePanel(
        child: Row(
          children: <Widget>[
            const Icon(Icons.lock_outline),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                'Club follow is read-only until the shell has an authenticated session.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ),
            if (widget.onOpenLogin != null) ...<Widget>[
              const SizedBox(width: 12),
              FilledButton.tonal(
                onPressed: widget.onOpenLogin,
                child: const Text('Sign in'),
              ),
            ],
          ],
        ),
      );
    }
    return AnimatedBuilder(
      animation: _controller,
      builder: (BuildContext context, Widget? child) {
        if (_controller.isLoading && _controller.isFollowing == null) {
          return const GteStatePanel(
            title: 'Loading follow state',
            message:
                'Community follow state is syncing from the live fan graph.',
            icon: Icons.groups_outlined,
            isLoading: true,
          );
        }
        if (_controller.errorMessage != null &&
            _controller.isFollowing == null) {
          return GteStatePanel(
            title: 'Community follow unavailable',
            message: _controller.errorMessage!,
            icon: Icons.error_outline,
            actionLabel: 'Retry',
            onAction: _controller.load,
          );
        }
        final bool isFollowing = _controller.isFollowing ?? false;
        final String clubName =
            widget.clubName?.trim().isNotEmpty == true
                ? widget.clubName!.trim()
                : widget.clubId.trim();
        return GteSurfacePanel(
          accentColor: GteShellTheme.accentCommunity,
          child: Row(
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Community follow',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      isFollowing
                          ? 'You are following $clubName through the live creator-club graph.'
                          : 'Follow $clubName to expose the real creator-club follow mutation on this shell.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              FilledButton.tonal(
                onPressed: _controller.isUpdating ? null : _toggleFollow,
                child: Text(
                  _controller.isUpdating
                      ? 'Updating...'
                      : isFollowing
                      ? 'Unfollow'
                      : 'Follow',
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
