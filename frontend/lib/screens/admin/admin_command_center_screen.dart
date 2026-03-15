import 'package:flutter/material.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/admin_engine_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/policy_admin_api.dart';
import 'package:gte_frontend/models/admin_engine_models.dart';
import 'package:gte_frontend/models/policy_admin_models.dart';
import 'package:gte_frontend/screens/admin/god_mode_admin_screen.dart';
import 'package:gte_frontend/screens/admin/treasury_ops_screen.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';
import 'package:gte_frontend/widgets/gtex_branding.dart';

class AdminCommandCenterScreen extends StatefulWidget {
  const AdminCommandCenterScreen({
    super.key,
    required this.baseUrl,
    required this.accessToken,
    required this.backendMode,
  });

  final String baseUrl;
  final String accessToken;
  final GteBackendMode backendMode;

  @override
  State<AdminCommandCenterScreen> createState() =>
      _AdminCommandCenterScreenState();
}

class _AdminCommandCenterScreenState extends State<AdminCommandCenterScreen> {
  late final AdminEngineApi _engineApi;
  late final PolicyAdminApi _policyApi;
  late Future<_AdminCommandBundle> _bundleFuture;
  final TextEditingController _currentPassword = TextEditingController();
  final TextEditingController _newPassword = TextEditingController();
  final TextEditingController _confirmPassword = TextEditingController();
  bool _savingPassword = false;

  @override
  void initState() {
    super.initState();
    _engineApi = AdminEngineApi.standard(
      baseUrl: widget.baseUrl,
      accessToken: widget.accessToken,
      mode: widget.backendMode,
    );
    _policyApi = PolicyAdminApi.standard(
      baseUrl: widget.baseUrl,
      accessToken: widget.accessToken,
      mode: widget.backendMode,
    );
    _bundleFuture = _loadBundle();
  }

  @override
  void dispose() {
    _currentPassword.dispose();
    _newPassword.dispose();
    _confirmPassword.dispose();
    super.dispose();
  }

  Future<_AdminCommandBundle> _loadBundle() async {
    final List<dynamic> payload = await Future.wait<dynamic>(<Future<dynamic>>[
      _engineApi.listRewardRules(),
      _engineApi.listFeatureFlags(),
      _policyApi.listCountryPolicies(),
    ]);
    return _AdminCommandBundle(
      rewardRules: payload[0] as List<AdminRewardRule>,
      featureFlags: payload[1] as List<AdminFeatureFlag>,
      policies: payload[2] as List<CountryFeaturePolicy>,
    );
  }

  Future<void> _refresh() async {
    setState(() {
      _bundleFuture = _loadBundle();
    });
  }

  Future<void> _changePassword() async {
    if (_currentPassword.text.trim().isEmpty ||
        _newPassword.text.trim().isEmpty ||
        _confirmPassword.text.trim().isEmpty) {
      AppFeedback.showError(
        context,
        'Enter current, new, and confirmation passwords.',
      );
      return;
    }
    setState(() => _savingPassword = true);
    try {
      final GodModeAdminApi api = GodModeAdminApi(
        baseUrl: widget.baseUrl,
        accessToken: widget.accessToken,
        mode: widget.backendMode,
      );
      await api.changePassword(
        currentPassword: _currentPassword.text.trim(),
        newPassword: _newPassword.text.trim(),
        confirmNewPassword: _confirmPassword.text.trim(),
      );
      _currentPassword.clear();
      _newPassword.clear();
      _confirmPassword.clear();
      AppFeedback.showSuccess(context, 'Admin password updated.');
    } catch (error) {
      AppFeedback.showError(context, 'Unable to change password.');
    } finally {
      if (mounted) {
        setState(() => _savingPassword = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Admin command center'),
          actions: <Widget>[
            IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh)),
          ],
        ),
        body: FutureBuilder<_AdminCommandBundle>(
          future: _bundleFuture,
          builder: (BuildContext context,
              AsyncSnapshot<_AdminCommandBundle> snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (!snapshot.hasData) {
              return const Center(
                child: GteStatePanel(
                  title: 'Admin command center unavailable',
                  message: 'Unable to load admin configuration right now.',
                  icon: Icons.admin_panel_settings_outlined,
                ),
              );
            }
            final _AdminCommandBundle bundle = snapshot.data!;
            final List<AdminRewardRule> rewardRules = bundle.rewardRules;
            final List<CountryFeaturePolicy> policies = bundle.policies;
            final List<AdminFeatureFlag> flags = bundle.featureFlags;
            final List<AdminFeatureFlag> sponsorshipFlags = flags
                .where((AdminFeatureFlag flag) =>
                    flag.featureKey.toLowerCase().contains('sponsor'))
                .toList(growable: false);
            return RefreshIndicator(
              onRefresh: _refresh,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
                children: <Widget>[
                  GteSurfacePanel(
                    accentColor: GteShellTheme.accentAdmin,
                    emphasized: true,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text('GTEX command center',
                            style: Theme.of(context).textTheme.headlineSmall),
                        const SizedBox(height: 8),
                        Text(
                          'Admin controls are organized for fast policy changes, reward tuning, and compliance guardrails.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: <Widget>[
                            GteMetricChip(
                                label: 'Reward rules',
                                value: rewardRules.length.toString()),
                            GteMetricChip(
                                label: 'Region policies',
                                value: policies.length.toString()),
                            GteMetricChip(
                                label: 'Feature flags',
                                value: flags.length.toString()),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  const GtexSectionHeader(
                    eyebrow: 'FEES + REWARD POOLS',
                    title: 'Tune fees, reward pools, and payout policies.',
                    description:
                        'Adjust trading fees, withdrawal policy, and competition platform fees from a single admin lane.',
                    accent: GteShellTheme.accentAdmin,
                  ),
                  const SizedBox(height: 12),
                  ...rewardRules.map(
                    (AdminRewardRule rule) => _RewardRuleCard(
                      rule: rule,
                      onEdit: () => _editRewardRule(rule),
                    ),
                  ),
                  const SizedBox(height: 18),
                  const GtexSectionHeader(
                    eyebrow: 'REGION POLICIES',
                    title: 'Region policy management',
                    description:
                        'Toggle deposits, market trading, and reward withdrawals by country.',
                    accent: GteShellTheme.accentAdmin,
                  ),
                  const SizedBox(height: 12),
                  ...policies.map(
                    (CountryFeaturePolicy policy) => _PolicyCard(
                      policy: policy,
                      onEdit: () => _editPolicy(policy),
                    ),
                  ),
                  const SizedBox(height: 18),
                  const GtexSectionHeader(
                    eyebrow: 'SPONSORSHIP HOOKS',
                    title: 'Sponsorship placement hooks',
                    description:
                        'Enable or disable sponsor placements across match and highlight surfaces.',
                    accent: GteShellTheme.accentAdmin,
                  ),
                  const SizedBox(height: 12),
                  if (sponsorshipFlags.isEmpty)
                    const GteStatePanel(
                      title: 'No sponsorship hooks found',
                      message:
                          'Create a feature flag with a sponsorship key to enable placements.',
                      icon: Icons.campaign_outlined,
                    )
                  else
                    ...sponsorshipFlags.map(
                      (AdminFeatureFlag flag) => _FeatureFlagTile(
                        flag: flag,
                        onToggle: (bool value) => _toggleFlag(flag, value),
                      ),
                    ),
                  const SizedBox(height: 18),
                  GteSurfacePanel(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text('Payment rails + withdrawals',
                            style: Theme.of(context).textTheme.titleMedium),
                        const SizedBox(height: 8),
                        Text(
                          'Payment rail toggles and withdrawal controls live in God Mode and Treasury Ops.',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 12,
                          runSpacing: 12,
                          children: <Widget>[
                            FilledButton.tonalIcon(
                              onPressed: () => _openGodMode(),
                              icon: const Icon(Icons.admin_panel_settings_outlined),
                              label: const Text('Open God Mode'),
                            ),
                            OutlinedButton.icon(
                              onPressed: () => _openTreasuryOps(),
                              icon: const Icon(Icons.account_balance_outlined),
                              label: const Text('Treasury ops'),
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
                        Text('Policy documents',
                            style: Theme.of(context).textTheme.titleMedium),
                        const SizedBox(height: 8),
                        Text(
                          'Document publishing and versioning require the admin policy endpoint to be wired.',
                          style: Theme.of(context).textTheme.bodySmall),
                        const SizedBox(height: 12),
                        FilledButton.tonalIcon(
                          onPressed: null,
                          icon: const Icon(Icons.library_books_outlined),
                          label: const Text('Publish new policy version'),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  GteSurfacePanel(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text('Highlight archive controls',
                            style: Theme.of(context).textTheme.titleMedium),
                        const SizedBox(height: 8),
                        Text(
                          'Archive and retention controls require a highlight admin endpoint.',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        const SizedBox(height: 12),
                        ..._highlightArchiveFixtures.map(
                          (_ArchiveFixture item) => Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: Row(
                              children: <Widget>[
                                const Icon(Icons.movie_outlined),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Text(item.label),
                                ),
                                OutlinedButton(
                                  onPressed: null,
                                  child: Text(item.actionLabel),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  GteSurfacePanel(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text('Audit trail',
                            style: Theme.of(context).textTheme.titleMedium),
                        const SizedBox(height: 8),
                        Text(
                          'Audit trail feed requires /admin/audit-trail to be wired.',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  GteSurfacePanel(
                    accentColor: GteShellTheme.accentAdmin,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text('Admin password',
                            style: Theme.of(context).textTheme.titleMedium),
                        const SizedBox(height: 8),
                        Text(
                          'Change the bootstrap admin password immediately after first login.',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        const SizedBox(height: 12),
                        TextField(
                          controller: _currentPassword,
                          obscureText: true,
                          decoration: const InputDecoration(
                            labelText: 'Current password',
                          ),
                        ),
                        const SizedBox(height: 10),
                        TextField(
                          controller: _newPassword,
                          obscureText: true,
                          decoration: const InputDecoration(
                            labelText: 'New password',
                          ),
                        ),
                        const SizedBox(height: 10),
                        TextField(
                          controller: _confirmPassword,
                          obscureText: true,
                          decoration: const InputDecoration(
                            labelText: 'Confirm new password',
                          ),
                        ),
                        const SizedBox(height: 12),
                        FilledButton.icon(
                          onPressed: _savingPassword ? null : _changePassword,
                          icon: const Icon(Icons.password_outlined),
                          label: const Text('Change admin password'),
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

  Future<void> _editRewardRule(AdminRewardRule rule) async {
    final TextEditingController trading =
        TextEditingController(text: rule.tradingFeeBps.toString());
    final TextEditingController withdrawal =
        TextEditingController(text: rule.withdrawalFeeBps.toString());
    final TextEditingController competition =
        TextEditingController(text: rule.competitionPlatformFeeBps.toString());
    final TextEditingController gift =
        TextEditingController(text: rule.giftPlatformRakeBps.toString());
    final TextEditingController minFee = TextEditingController(
        text: rule.minimumWithdrawalFeeCredits.toStringAsFixed(0));

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext context) {
        return Padding(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(context).viewInsets.bottom,
            left: 20,
            right: 20,
            top: 20,
          ),
          child: ListView(
            shrinkWrap: true,
            children: <Widget>[
              Text('Edit reward rule', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 12),
              TextField(
                controller: trading,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Trading fee (bps)'),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: gift,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Gift platform rake (bps)'),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: withdrawal,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Withdrawal fee (bps)'),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: minFee,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Min withdrawal fee'),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: competition,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Competition fee (bps)'),
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: () async {
                  Navigator.of(context).pop();
                  await _engineApi.upsertRewardRule(
                    ruleKey: rule.ruleKey,
                    title: rule.title,
                    description: rule.description,
                    tradingFeeBps: int.tryParse(trading.text) ?? rule.tradingFeeBps,
                    giftPlatformRakeBps:
                        int.tryParse(gift.text) ?? rule.giftPlatformRakeBps,
                    withdrawalFeeBps:
                        int.tryParse(withdrawal.text) ?? rule.withdrawalFeeBps,
                    minimumWithdrawalFeeCredits:
                        double.tryParse(minFee.text) ?? rule.minimumWithdrawalFeeCredits,
                    competitionPlatformFeeBps:
                        int.tryParse(competition.text) ?? rule.competitionPlatformFeeBps,
                    active: rule.active,
                  );
                  await _refresh();
                },
                child: const Text('Save reward rule'),
              ),
              const SizedBox(height: 12),
            ],
          ),
        );
      },
    );
  }

  Future<void> _editPolicy(CountryFeaturePolicy policy) async {
    bool deposits = policy.depositsEnabled;
    bool trading = policy.marketTradingEnabled;
    bool rewardWithdrawals = policy.platformRewardWithdrawalsEnabled;
    bool giftWithdrawals = policy.userHostedGiftWithdrawalsEnabled;
    bool gtexGifts = policy.gtexCompetitionGiftWithdrawalsEnabled;
    bool nationalRewards = policy.nationalRewardWithdrawalsEnabled;
    bool active = policy.active;
    final TextEditingController bucket =
        TextEditingController(text: policy.bucketType);
    final TextEditingController regionDays = TextEditingController(
        text: policy.oneTimeRegionChangeAfterDays.toString());

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext context) {
        return Padding(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(context).viewInsets.bottom,
            left: 20,
            right: 20,
            top: 20,
          ),
          child: StatefulBuilder(
            builder: (BuildContext context, StateSetter setModalState) {
              return ListView(
                shrinkWrap: true,
                children: <Widget>[
                  Text('Edit ${policy.countryCode} policy',
                      style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 12),
                  TextField(
                    controller: bucket,
                    decoration:
                        const InputDecoration(labelText: 'Policy bucket'),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: regionDays,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                        labelText: 'Region change cooldown (days)'),
                  ),
                  const SizedBox(height: 10),
                  SwitchListTile(
                    value: active,
                    onChanged: (bool value) =>
                        setModalState(() => active = value),
                    title: const Text('Active'),
                  ),
                  SwitchListTile(
                    value: deposits,
                    onChanged: (bool value) =>
                        setModalState(() => deposits = value),
                    title: const Text('Deposits enabled'),
                  ),
                  SwitchListTile(
                    value: trading,
                    onChanged: (bool value) =>
                        setModalState(() => trading = value),
                    title: const Text('Market trading enabled'),
                  ),
                  SwitchListTile(
                    value: rewardWithdrawals,
                    onChanged: (bool value) =>
                        setModalState(() => rewardWithdrawals = value),
                    title: const Text('Platform reward withdrawals'),
                  ),
                  SwitchListTile(
                    value: giftWithdrawals,
                    onChanged: (bool value) =>
                        setModalState(() => giftWithdrawals = value),
                    title: const Text('User-hosted gift withdrawals'),
                  ),
                  SwitchListTile(
                    value: gtexGifts,
                    onChanged: (bool value) =>
                        setModalState(() => gtexGifts = value),
                    title: const Text('GTEX gift withdrawals'),
                  ),
                  SwitchListTile(
                    value: nationalRewards,
                    onChanged: (bool value) =>
                        setModalState(() => nationalRewards = value),
                    title: const Text('National reward withdrawals'),
                  ),
                  const SizedBox(height: 12),
                  FilledButton(
                    onPressed: () async {
                      Navigator.of(context).pop();
                      await _policyApi.upsertCountryPolicy(
                        countryCode: policy.countryCode,
                        bucketType: bucket.text.trim().isEmpty
                            ? policy.bucketType
                            : bucket.text.trim(),
                        depositsEnabled: deposits,
                        marketTradingEnabled: trading,
                        platformRewardWithdrawalsEnabled: rewardWithdrawals,
                        userHostedGiftWithdrawalsEnabled: giftWithdrawals,
                        gtexCompetitionGiftWithdrawalsEnabled: gtexGifts,
                        nationalRewardWithdrawalsEnabled: nationalRewards,
                        oneTimeRegionChangeAfterDays:
                            int.tryParse(regionDays.text) ??
                                policy.oneTimeRegionChangeAfterDays,
                        active: active,
                      );
                      await _refresh();
                    },
                    child: const Text('Save policy'),
                  ),
                  const SizedBox(height: 12),
                ],
              );
            },
          ),
        );
      },
    );
  }

  Future<void> _toggleFlag(AdminFeatureFlag flag, bool value) async {
    await _engineApi.upsertFeatureFlag(
      featureKey: flag.featureKey,
      title: flag.title,
      description: flag.description,
      enabled: value,
      audience: flag.audience,
    );
    await _refresh();
  }

  Future<void> _openGodMode() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => GodModeAdminScreen(
          baseUrl: widget.baseUrl,
          accessToken: widget.accessToken,
          backendMode: widget.backendMode,
        ),
      ),
    );
  }

  Future<void> _openTreasuryOps() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => GteTreasuryOpsScreen(
          baseUrl: widget.baseUrl,
          accessToken: widget.accessToken,
          backendMode: widget.backendMode,
        ),
      ),
    );
  }
}

class _AdminCommandBundle {
  const _AdminCommandBundle({
    required this.rewardRules,
    required this.featureFlags,
    required this.policies,
  });

  final List<AdminRewardRule> rewardRules;
  final List<AdminFeatureFlag> featureFlags;
  final List<CountryFeaturePolicy> policies;
}

class _RewardRuleCard extends StatelessWidget {
  const _RewardRuleCard({
    required this.rule,
    required this.onEdit,
  });

  final AdminRewardRule rule;
  final VoidCallback onEdit;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: GteSurfacePanel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              children: <Widget>[
                Expanded(
                  child: Text(rule.title,
                      style: Theme.of(context).textTheme.titleMedium),
                ),
                OutlinedButton(onPressed: onEdit, child: const Text('Edit')),
              ],
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: <Widget>[
                GteMetricChip(
                    label: 'Trading fee', value: '${rule.tradingFeeBps} bps'),
                GteMetricChip(
                    label: 'Withdraw fee', value: '${rule.withdrawalFeeBps} bps'),
                GteMetricChip(
                    label: 'Competition fee',
                    value: '${rule.competitionPlatformFeeBps} bps'),
                GteMetricChip(
                    label: 'Gift rake', value: '${rule.giftPlatformRakeBps} bps'),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _PolicyCard extends StatelessWidget {
  const _PolicyCard({
    required this.policy,
    required this.onEdit,
  });

  final CountryFeaturePolicy policy;
  final VoidCallback onEdit;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: GteSurfacePanel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              children: <Widget>[
                Expanded(
                  child: Text(
                    '${policy.countryCode} • ${policy.bucketType}',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                OutlinedButton(onPressed: onEdit, child: const Text('Edit')),
              ],
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: <Widget>[
                GteMetricChip(
                    label: 'Deposits',
                    value: policy.depositsEnabled ? 'On' : 'Off'),
                GteMetricChip(
                    label: 'Trading',
                    value: policy.marketTradingEnabled ? 'On' : 'Off'),
                GteMetricChip(
                    label: 'Rewards',
                    value:
                        policy.platformRewardWithdrawalsEnabled ? 'On' : 'Off'),
                GteMetricChip(
                    label: 'Active',
                    value: policy.active ? 'Yes' : 'No'),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _FeatureFlagTile extends StatelessWidget {
  const _FeatureFlagTile({
    required this.flag,
    required this.onToggle,
  });

  final AdminFeatureFlag flag;
  final ValueChanged<bool> onToggle;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: GteSurfacePanel(
        child: SwitchListTile(
          value: flag.enabled,
          onChanged: onToggle,
          title: Text(flag.title),
          subtitle: Text(flag.description ?? flag.featureKey),
        ),
      ),
    );
  }
}

class _ArchiveFixture {
  const _ArchiveFixture(this.label, this.actionLabel);

  final String label;
  final String actionLabel;
}

const List<_ArchiveFixture> _highlightArchiveFixtures = <_ArchiveFixture>[
  _ArchiveFixture('Matchday 24 highlight reel', 'Archive'),
  _ArchiveFixture('Creator finals montage', 'Restore'),
  _ArchiveFixture('Rookie cup recap', 'Archive'),
];
