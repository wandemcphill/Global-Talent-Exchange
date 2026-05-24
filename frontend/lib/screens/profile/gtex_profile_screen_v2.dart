import 'package:flutter/material.dart';

import '../../features/system_profile_redesign/models/gtex_profile_models.dart';
import '../../features/system_profile_redesign/presentation/gtex_profile_controller.dart';
import 'gtex_settings_screen_v2.dart';

class GtexProfileScreenV2 extends StatefulWidget {
  const GtexProfileScreenV2({
    super.key,
    this.controller = const GtexProfileController(),
  });

  final GtexProfileController controller;

  @override
  State<GtexProfileScreenV2> createState() => _GtexProfileScreenV2State();
}

class _GtexProfileScreenV2State extends State<GtexProfileScreenV2> {
  late final Future<GtexProfileSummary> _profile =
      widget.controller.loadProfile();

  static const _bg = Color(0xFF050B08);
  static const _panel = Color(0xFF0E1D15);
  static const _line = Color(0xFF214232);
  static const _green = Color(0xFF39FF88);
  static const _gold = Color(0xFFFFC857);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _bg,
      body: FutureBuilder<GtexProfileSummary>(
        future: _profile,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          final GtexProfileSummary? profile = snapshot.data;
          if (snapshot.hasError || profile == null) {
            return const _ProfileUnavailableState();
          }
          return SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Row(
                children: [
                  SizedBox(
                    width: 280,
                    child: _ProfileLeftPanel(profile: profile),
                  ),
                  const SizedBox(width: 18),
                  Expanded(child: _ProfileWorkspace(profile: profile)),
                  const SizedBox(width: 18),
                  SizedBox(
                    width: 300,
                    child: _ProfileStatusRail(profile: profile),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

class _ProfileUnavailableState extends StatelessWidget {
  const _ProfileUnavailableState();

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: Container(
            margin: const EdgeInsets.all(24),
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: _GtexProfileScreenV2State._panel,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: _GtexProfileScreenV2State._line),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                const Icon(
                  Icons.account_circle_outlined,
                  color: _GtexProfileScreenV2State._green,
                  size: 36,
                ),
                const SizedBox(height: 14),
                Text(
                  'Live profile required',
                  style: Theme.of(
                    context,
                  ).textTheme.titleLarge?.copyWith(color: Colors.white),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Sign in with a live session so GTEX can load the authenticated profile from the backend authority.',
                  style: TextStyle(color: Colors.white70),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ProfileLeftPanel extends StatelessWidget {
  const _ProfileLeftPanel({required this.profile});

  final GtexProfileSummary profile;

  static const _panel = Color(0xFF0E1D15);
  static const _line = Color(0xFF214232);
  static const _green = Color(0xFF39FF88);

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: _panel,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: _line),
      ),
      padding: const EdgeInsets.all(18),
      child: ListView(
        children: [
          const Text(
            'GTEX PROFILE',
            style: TextStyle(
              color: _green,
              fontWeight: FontWeight.w900,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: 18),
          CircleAvatar(
            radius: 38,
            backgroundColor: Colors.black,
            backgroundImage:
                profile.avatarUrl == null
                    ? null
                    : NetworkImage(profile.avatarUrl!),
            child:
                profile.avatarUrl == null
                    ? Text(
                      profile.displayName.characters.first,
                      style: const TextStyle(color: _green, fontSize: 26),
                    )
                    : null,
          ),
          const SizedBox(height: 14),
          Text(
            profile.displayName,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 20,
              fontWeight: FontWeight.w800,
            ),
          ),
          Text(profile.email, style: const TextStyle(color: Colors.white54)),
          const SizedBox(height: 18),
          _NavTile(
            icon: Icons.person_outline,
            label: 'Overview',
            selected: true,
          ),
          _NavTile(icon: Icons.security, label: 'Security'),
          _NavTile(icon: Icons.tune, label: 'Preferences'),
          _NavTile(icon: Icons.notifications_none, label: 'Notifications'),
          _NavTile(
            icon: Icons.account_balance_wallet_outlined,
            label: 'Wallet status',
          ),
          _NavTile(icon: Icons.help_outline, label: 'Support'),
          const SizedBox(height: 18),
          Text(
            'Club: ${profile.clubName}',
            style: const TextStyle(color: Colors.white70),
          ),
          const SizedBox(height: 6),
          Text(
            profile.roleLabel,
            style: const TextStyle(color: _green, fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }
}

class _NavTile extends StatelessWidget {
  const _NavTile({
    required this.icon,
    required this.label,
    this.selected = false,
  });
  final IconData icon;
  final String label;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
      decoration: BoxDecoration(
        color: selected ? const Color(0xFF153B27) : Colors.transparent,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          Icon(
            icon,
            color: selected ? const Color(0xFF39FF88) : Colors.white54,
            size: 20,
          ),
          const SizedBox(width: 10),
          Text(
            label,
            style: TextStyle(
              color: selected ? Colors.white : Colors.white60,
              fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

class _ProfileWorkspace extends StatelessWidget {
  const _ProfileWorkspace({required this.profile});
  final GtexProfileSummary profile;

  static const _panel = Color(0xFF0E1D15);
  static const _line = Color(0xFF214232);
  static const _green = Color(0xFF39FF88);
  static const _gold = Color(0xFFFFC857);

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        Text(
          'Account command profile',
          style: Theme.of(context).textTheme.headlineMedium?.copyWith(
            color: Colors.white,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: 8),
        const Text(
          'Manage your GTEX identity, club owner status, account protection, KYC, and wallet readiness.',
          style: TextStyle(color: Colors.white60),
        ),
        const SizedBox(height: 20),
        Wrap(
          spacing: 14,
          runSpacing: 14,
          children: [
            _MetricCard(
              label: 'Profile completion',
              value: '${profile.profileCompletion}%',
              icon: Icons.account_circle_outlined,
            ),
            _MetricCard(
              label: 'Security score',
              value: '${profile.securityScore}',
              icon: Icons.shield_outlined,
            ),
            _MetricCard(
              label: 'Unread alerts',
              value: '${profile.unreadNotifications}',
              icon: Icons.notifications_active_outlined,
            ),
            _MetricCard(
              label: 'Open disputes',
              value: '${profile.openDisputes}',
              icon: Icons.report_problem_outlined,
            ),
          ],
        ),
        const SizedBox(height: 18),
        Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: _panel,
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: _line),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'GTEX readiness checklist',
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                  fontSize: 18,
                ),
              ),
              const SizedBox(height: 12),
              _ChecklistRow(
                done: true,
                title: 'Account created',
                subtitle: 'Your user profile is active.',
              ),
              _ChecklistRow(
                done: true,
                title: 'Club linked',
                subtitle: profile.clubName,
              ),
              _ChecklistRow(
                done: false,
                title: 'Complete KYC review',
                subtitle: profile.kycStatus,
              ),
              _ChecklistRow(
                done: false,
                title: 'Enable two-factor authentication',
                subtitle: 'Recommended before wallet withdrawals.',
              ),
              _ChecklistRow(
                done: true,
                title: 'Wallet available',
                subtitle: profile.walletStatus,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.label,
    required this.value,
    required this.icon,
  });
  final String label;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 180,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF0E1D15),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: const Color(0xFF214232)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: const Color(0xFF39FF88)),
          const SizedBox(height: 12),
          Text(
            value,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 26,
              fontWeight: FontWeight.w900,
            ),
          ),
          Text(label, style: const TextStyle(color: Colors.white54)),
        ],
      ),
    );
  }
}

class _ChecklistRow extends StatelessWidget {
  const _ChecklistRow({
    required this.done,
    required this.title,
    required this.subtitle,
  });
  final bool done;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(
            done ? Icons.check_circle : Icons.radio_button_unchecked,
            color: done ? const Color(0xFF39FF88) : const Color(0xFFFFC857),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Text(subtitle, style: const TextStyle(color: Colors.white54)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ProfileStatusRail extends StatelessWidget {
  const _ProfileStatusRail({required this.profile});
  final GtexProfileSummary profile;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF0E1D15),
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: const Color(0xFF214232)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Account status',
            style: TextStyle(
              color: Colors.white,
              fontSize: 18,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 14),
          _StatusPill(label: 'KYC', value: profile.kycStatus),
          _StatusPill(label: 'Wallet', value: profile.walletStatus),
          _StatusPill(label: 'Country', value: profile.countryLabel),
          const Spacer(),
          FilledButton.icon(
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xFF39FF88),
              foregroundColor: Colors.black,
              minimumSize: const Size.fromHeight(48),
            ),
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => const GtexSettingsScreenV2(),
                ),
              );
            },
            icon: const Icon(Icons.edit_outlined),
            label: const Text('Edit profile'),
          ),
        ],
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.black26,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF214232)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.white54)),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
