import 'package:flutter/material.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/shared/presentation/gte_feature_forms.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

import '../data/creator_league_admin_models.dart';
import 'creator_league_admin_controller.dart';

enum CreatorLeagueAdminView {
  finance,
  settlements,
}

class CreatorLeagueAdminScreen extends StatefulWidget {
  const CreatorLeagueAdminScreen({
    super.key,
    required this.baseUrl,
    required this.backendMode,
    this.accessToken,
    this.currentUserRole,
    this.onOpenLogin,
    this.seasonId,
    this.initialView = CreatorLeagueAdminView.finance,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final String? currentUserRole;
  final VoidCallback? onOpenLogin;
  final String? seasonId;
  final CreatorLeagueAdminView initialView;

  @override
  State<CreatorLeagueAdminScreen> createState() =>
      _CreatorLeagueAdminScreenState();
}

class _CreatorLeagueAdminScreenState extends State<CreatorLeagueAdminScreen> {
  late final CreatorLeagueAdminController _controller;

  bool get _isAuthenticated => widget.accessToken?.trim().isNotEmpty == true;
  bool get _isAdmin => <String>{'admin', 'super_admin'}
      .contains((widget.currentUserRole ?? '').trim().toLowerCase());

  String get _title => widget.initialView == CreatorLeagueAdminView.settlements
      ? 'Creator league settlements'
      : 'Creator league finance';

  String get _heroCopy => widget.initialView ==
          CreatorLeagueAdminView.settlements
      ? 'Settlement review, approval, and audit visibility stay in the canonical creator-league admin lane.'
      : 'Creator-league financial reporting, live-priority context, and settlement review stay in the canonical admin lane.';

  @override
  void initState() {
    super.initState();
    _controller = CreatorLeagueAdminController.standard(
      baseUrl: widget.baseUrl,
      backendMode: widget.backendMode,
      accessToken: widget.accessToken,
    );
    if (_isAdmin) {
      _load();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    if (!_isAdmin) {
      return;
    }
    await _controller.loadOverview();
    await _controller.loadFinance(
      reportQuery: CreatorLeagueFinancialReportQuery(seasonId: widget.seasonId),
      settlementsQuery:
          CreatorLeagueFinancialSettlementsQuery(seasonId: widget.seasonId),
    );
  }

  Future<void> _run(Future<void> Function() action, String success) async {
    await action();
    if (!mounted) {
      return;
    }
    final String? error = _controller.actionError;
    if (error != null && error.trim().isNotEmpty) {
      AppFeedback.showError(context, error);
    } else {
      AppFeedback.showSuccess(context, success);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_isAuthenticated) {
      return Container(
        decoration: gteBackdropDecoration(),
        child: Scaffold(
          backgroundColor: Colors.transparent,
          appBar: AppBar(title: Text(_title)),
          body: Padding(
            padding: const EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Sign in required',
              message:
                  'Creator-league finance and settlement surfaces require an authenticated admin session.',
              actionLabel: widget.onOpenLogin == null ? null : 'Sign in',
              onAction: widget.onOpenLogin,
              icon: Icons.lock_outline,
            ),
          ),
        ),
      );
    }
    if (!_isAdmin) {
      return Container(
        decoration: gteBackdropDecoration(),
        child: Scaffold(
          backgroundColor: Colors.transparent,
          appBar: AppBar(title: Text(_title)),
          body: const Padding(
            padding: EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Admin permission required',
              message:
                  'League finance, settlements, and approvals are available only to admin roles.',
              icon: Icons.admin_panel_settings_outlined,
            ),
          ),
        ),
      );
    }

    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: Text(_title),
          actions: <Widget>[
            IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
          ],
        ),
        body: AnimatedBuilder(
          animation: _controller,
          builder: (BuildContext context, Widget? child) {
            final CreatorLeagueConfig? overview = _controller.overview;
            final CreatorLeagueFinancialReport? report =
                _controller.financialReport;
            return RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
                children: <Widget>[
                  GteSurfacePanel(
                    accentColor: GteShellTheme.accentAdmin,
                    emphasized: true,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          _title,
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _heroCopy,
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: <Widget>[
                            GteMetricChip(
                              label: 'Settlements',
                              value: _controller.settlements.length.toString(),
                            ),
                            if (overview != null)
                              GteMetricChip(
                                label: 'Divisions',
                                value: overview.divisionCount.toString(),
                              ),
                            if (report != null)
                              GteMetricChip(
                                label: 'Review queue',
                                value: report.settlementsRequiringReview.length
                                    .toString(),
                              ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 12,
                          runSpacing: 12,
                          children: <Widget>[
                            FilledButton.tonalIcon(
                              onPressed: _updateConfig,
                              icon: const Icon(Icons.tune_outlined),
                              label: const Text('Update config'),
                            ),
                            FilledButton.tonalIcon(
                              onPressed: _createSeason,
                              icon: const Icon(Icons.calendar_today_outlined),
                              label: const Text('Create season'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  GteSurfacePanel(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Overview',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 10),
                        if (_controller.isLoadingOverview && overview == null)
                          const GteStatePanel(
                            title: 'Loading overview',
                            message:
                                'League config and live-priority data are syncing.',
                            icon: Icons.leaderboard_outlined,
                            isLoading: true,
                          )
                        else if (_controller.overviewError != null &&
                            overview == null)
                          GteStatePanel(
                            title: 'Overview unavailable',
                            message: _controller.overviewError!,
                            icon: Icons.error_outline,
                          )
                        else if (overview != null)
                          Text(
                            'Enabled: ${overview.enabled}\n'
                            'Format: ${overview.leagueFormat}\n'
                            'Match frequency: ${overview.matchFrequencyDays} days\n'
                            'Settlement review enabled: ${overview.settlementReviewEnabled}',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  GteSurfacePanel(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Financial report',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 10),
                        if (_controller.isLoadingFinance && report == null)
                          const GteStatePanel(
                            title: 'Loading report',
                            message:
                                'Settlement queue and finance controls are syncing.',
                            icon: Icons.receipt_long_outlined,
                            isLoading: true,
                          )
                        else if (_controller.financeError != null &&
                            report == null)
                          GteStatePanel(
                            title: 'Financial report unavailable',
                            message: _controller.financeError!,
                            icon: Icons.error_outline,
                          )
                        else if (report != null)
                          Text(
                            'Settlements needing review: ${report.settlementsRequiringReview.length}\n'
                            'Audit events: ${report.recentAuditEvents.length}\n'
                            'Share-market control keys: ${report.shareMarketControl.keys.join(', ')}',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  GteSurfacePanel(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Settlements',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 10),
                        if (_controller.settlements.isEmpty)
                          const Text('No settlements loaded.')
                        else
                          ..._controller.settlements.take(6).map(
                                (CreatorLeagueSettlement settlement) => Padding(
                                  padding: const EdgeInsets.only(bottom: 12),
                                  child: GteSurfacePanel(
                                    child: Row(
                                      children: <Widget>[
                                        Expanded(
                                          child: Text(
                                            '${settlement.matchId} | ${settlement.reviewStatus}\n'
                                            'Revenue ${settlement.totalRevenueCoin} | Creator ${settlement.totalCreatorShareCoin}',
                                            style: Theme.of(context)
                                                .textTheme
                                                .bodyMedium,
                                          ),
                                        ),
                                        FilledButton.tonal(
                                          onPressed: () =>
                                              _approveSettlement(settlement),
                                          child: const Text('Approve'),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              ),
                      ],
                    ),
                  ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }

  Future<void> _updateConfig() async {
    await showGteFormSheet(
      context,
      title: 'Update league config',
      fields: const <GteFormFieldSpec>[
        GteFormFieldSpec(key: 'clubCount', label: 'Default club count'),
        GteFormFieldSpec(key: 'divisions', label: 'Division count'),
        GteFormFieldSpec(key: 'frequency', label: 'Match frequency days'),
      ],
      onSubmit: (Map<String, String> values) async {
        final int? clubCount = int.tryParse(values['clubCount'] ?? '');
        final int? divisions = int.tryParse(values['divisions'] ?? '');
        final int? frequency = int.tryParse(values['frequency'] ?? '');
        if (clubCount == null || divisions == null || frequency == null) {
          AppFeedback.showError(context, 'Enter valid league config values.');
          return false;
        }
        await _run(
          () => _controller.updateConfig(
            CreatorLeagueConfigUpdateRequest(
              defaultClubCount: clubCount,
              divisionCount: divisions,
              matchFrequencyDays: frequency,
            ),
          ),
          'League config updated.',
        );
        return _controller.actionError == null;
      },
    );
  }

  Future<void> _createSeason() async {
    await showGteFormSheet(
      context,
      title: 'Create season',
      fields: const <GteFormFieldSpec>[
        GteFormFieldSpec(key: 'name', label: 'Season name'),
      ],
      onSubmit: (Map<String, String> values) async {
        if ((values['name'] ?? '').isEmpty) {
          AppFeedback.showError(context, 'Enter a season name.');
          return false;
        }
        await _run(
          () => _controller.createSeason(
            CreatorLeagueSeasonCreateRequest(
              startDate: DateTime.now(),
              assignments: const <CreatorLeagueSeasonTierAssignmentRequest>[],
              name: values['name'],
            ),
          ),
          'Season created.',
        );
        return _controller.actionError == null;
      },
    );
  }

  Future<void> _approveSettlement(CreatorLeagueSettlement settlement) async {
    await _run(
      () => _controller.approveSettlement(
        settlement.id,
        const CreatorLeagueSettlementReviewRequest(),
      ),
      'Settlement approved.',
    );
  }
}
