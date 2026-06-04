import 'package:flutter/material.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class GteRegionSelectionScreen extends StatefulWidget {
  const GteRegionSelectionScreen({
    super.key,
    required this.controller,
    this.currentCountry,
  });

  final GteExchangeController controller;
  final String? currentCountry;

  @override
  State<GteRegionSelectionScreen> createState() =>
      _GteRegionSelectionScreenState();
}

class _GteRegionSelectionScreenState extends State<GteRegionSelectionScreen> {
  late String _selectedCountry;
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _selectedCountry = widget.currentCountry?.trim().isNotEmpty == true
        ? widget.currentCountry!
        : 'GLOBAL';
  }

  Future<void> _submit() async {
    if (_submitting) {
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await widget.controller.api.trackAnalyticsEvent(
        'region_selected',
        metadata: <String, Object?>{'country': _selectedCountry},
      );
      await widget.controller.refreshCompliance();
    } catch (error) {
      if (mounted) {
        setState(() => _error = error.toString());
      }
      return;
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
    if (!mounted) {
      return;
    }
    AppFeedback.showSuccess(
      context,
      'Region selection recorded. GTEX will refresh role eligibility if policies changed.',
    );
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Select region'),
        ),
        body: ListView(
          padding: const EdgeInsets.all(20),
          children: <Widget>[
            GteSurfacePanel(
              accentColor: GteShellTheme.accentCommunity,
              emphasized: true,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Region selection',
                      style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 8),
                  Text(
                    'Choose your operating region so GTEX can apply the correct identity, policy, and role-eligibility checks.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            if (_submitting) ...<Widget>[
              const GteStatePanel(
                eyebrow: 'REGION',
                title: 'Saving region selection',
                message:
                    'GTEX is recording the selected region and refreshing account eligibility.',
                isLoading: true,
                icon: Icons.sync_rounded,
                accentColor: GteShellTheme.accentCommunity,
              ),
              const SizedBox(height: 16),
            ],
            if (_error != null) ...<Widget>[
              GteStatePanel(
                eyebrow: 'REGION',
                title: 'Region update blocked',
                message:
                    'GTEX could not confirm this region selection. Review your connection or try again with an eligible account. $_error',
                icon: Icons.warning_amber_outlined,
                actionLabel: 'Retry',
                onAction: _submit,
                accentColor: GteShellTheme.negative,
              ),
              const SizedBox(height: 16),
            ],
            ..._regions.map(
              (_RegionOption option) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: GteSurfacePanel(
                  onTap: () => setState(() => _selectedCountry = option.code),
                  child: Row(
                    children: <Widget>[
                      Radio<String>(
                        value: option.code,
                        groupValue: _selectedCountry,
                        onChanged: (String? value) {
                          if (value != null) {
                            setState(() => _selectedCountry = value);
                          }
                        },
                      ),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(option.label,
                                style: Theme.of(context).textTheme.titleMedium),
                            const SizedBox(height: 4),
                            Text(option.caption,
                                style: Theme.of(context).textTheme.bodySmall),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            GteSurfacePanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Region notes',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  Text(
                    'Region changes may require policy approval and can temporarily restrict account, creator, or trader actions. Contact support if your country is not listed.',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _submitting ? null : _submit,
              icon:
                  _submitting
                      ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                      : const Icon(Icons.public_outlined),
              label: Text(_submitting ? 'Saving region' : 'Confirm region'),
            ),
          ],
        ),
      ),
    );
  }
}

class _RegionOption {
  const _RegionOption(this.code, this.label, this.caption);

  final String code;
  final String label;
  final String caption;
}

const List<_RegionOption> _regions = <_RegionOption>[
  _RegionOption('NG', 'Nigeria', 'Primary launch region with full account review.'),
  _RegionOption('US', 'United States', 'Compliance-reviewed access with role checks.'),
  _RegionOption('GB', 'United Kingdom', 'UK policy stack with standard review.'),
  _RegionOption('BR', 'Brazil', 'Latin America regional controls.'),
  _RegionOption('ES', 'Spain', 'EU policy bucket with account support lanes.'),
  _RegionOption('GLOBAL', 'Global / Other', 'Limited access pending region verification.'),
];
