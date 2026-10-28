import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/features/owner_console/data/owner_console_api.dart';
import 'package:gte_frontend/features/owner_console/widgets/gtex_owner_inbox_panel.dart';
import 'package:gte_frontend/router/gtex_auth_routes.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

/// Dedicated full screen for the private Owner Decision Inbox.
///
/// Discovered via `/app/inbox` and legacy `/inbox` redirect.
/// Preserves authenticated owner context, active club context, deep links,
/// honest loading/empty/error states, and double-tap protected decision actions.
class GtexOwnerInboxScreen extends StatefulWidget {
  const GtexOwnerInboxScreen({
    super.key,
    required this.dependencies,
    this.api,
    this.clubId,
    this.initialStatus = 'open',
    this.initialCategory = 'all',
    this.initialUnreadOnly = false,
    this.onOpenLogin,
  });

  final GteNavigationDependencies dependencies;
  final GtexOwnerInboxDataSource? api;
  final String? clubId;
  final String initialStatus;
  final String initialCategory;
  final bool initialUnreadOnly;
  final VoidCallback? onOpenLogin;

  @override
  State<GtexOwnerInboxScreen> createState() => _GtexOwnerInboxScreenState();
}

class _GtexOwnerInboxScreenState extends State<GtexOwnerInboxScreen> {
  Key _panelKey = UniqueKey();

  void _refreshInbox() {
    setState(() {
      _panelKey = UniqueKey();
    });
  }

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    final String? effectiveClubId =
        widget.clubId?.trim().isNotEmpty == true
            ? widget.clubId!.trim()
            : widget.dependencies.currentClubId;
    final String? effectiveClubName =
        widget.dependencies.currentClubName ?? effectiveClubId;

    final Widget appBarTitle = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        const Text(
          'Owner Decision Inbox',
          style: TextStyle(
            color: Colors.white,
            fontSize: 16,
            fontWeight: FontWeight.w700,
          ),
        ),
        if (effectiveClubName != null && effectiveClubName.isNotEmpty)
          Text(
            'Club: $effectiveClubName',
            key: const Key('owner-inbox-club-badge'),
            style: TextStyle(
              color: navy.gold500,
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
      ],
    );

    final Widget leadingButton = IconButton(
      key: const Key('owner-inbox-back-button'),
      icon: const Icon(Icons.arrow_back_rounded, color: Colors.white),
      tooltip: 'Back',
      onPressed: () {
        if (Navigator.of(context).canPop()) {
          Navigator.of(context).pop();
        } else {
          context.go('/home');
        }
      },
    );

    if (!widget.dependencies.isAuthenticated) {
      return Scaffold(
        key: const Key('owner-inbox-screen'),
        backgroundColor: navy.bgBase,
        appBar: AppBar(
          backgroundColor: navy.bgBase,
          elevation: 0,
          leading: leadingButton,
          title: appBarTitle,
        ),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(GtexSpacing.lg),
            child: GteStatePanel(
              key: const Key('owner-inbox-unauth-card'),
              title: 'Sign in required',
              message: 'Owner decision inbox requires an authenticated session.',
              icon: Icons.lock_outline_rounded,
              actionLabel: 'Sign in',
              onAction:
                  widget.onOpenLogin ?? () => context.go(gtexLoginRoute),
            ),
          ),
        ),
      );
    }

    final GtexOwnerInboxDataSource inboxApi =
        widget.api ??
        OwnerConsoleApi(
          client: widget.dependencies.createAuthedApi(),
          activeClubId: effectiveClubId,
        );

    return Scaffold(
      key: const Key('owner-inbox-screen'),
      backgroundColor: navy.bgBase,
      appBar: AppBar(
        backgroundColor: navy.bgBase,
        elevation: 0,
        leading: leadingButton,
        title: appBarTitle,
        actions: <Widget>[
          IconButton(
            key: const Key('owner-inbox-refresh-button'),
            icon: const Icon(Icons.refresh_rounded, color: Colors.white70),
            tooltip: 'Refresh inbox',
            onPressed: _refreshInbox,
          ),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(GtexSpacing.md),
          child: GtexOwnerInboxPanel(
            key: _panelKey,
            api: inboxApi,
            clubId: effectiveClubId,
            initialStatus: widget.initialStatus,
            initialCategory: widget.initialCategory,
            initialUnreadOnly: widget.initialUnreadOnly,
            onNavigateRoute: (String route) {
              context.go(route);
            },
          ),
        ),
      ),
    );
  }
}
