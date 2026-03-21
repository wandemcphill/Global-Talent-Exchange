import 'package:flutter/material.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
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

  @override
  void initState() {
    super.initState();
    _selectedCountry = widget.currentCountry?.trim().isNotEmpty == true
        ? widget.currentCountry!
        : 'GLOBAL';
  }

  Future<void> _submit() async {
    await widget.controller.api.trackAnalyticsEvent(
      'region_selected',
      metadata: <String, Object?>{'country': _selectedCountry},
    );
    await widget.controller.refreshCompliance();
    if (!mounted) {
      return;
    }
    AppFeedback.showSuccess(
      context,
      'Region selection recorded. Compliance will refresh if policies changed.',
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
                    'Choose your operating region to load the correct policy, deposits, and withdrawal rules.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
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
                    'Region changes may require policy approval and could temporarily restrict withdrawals or rewards. Contact support if your country is not listed.',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _submit,
              icon: const Icon(Icons.public_outlined),
              label: const Text('Confirm region'),
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
  _RegionOption('NG', 'Nigeria', 'Primary launch region with full market lanes.'),
  _RegionOption('US', 'United States', 'Regulated trading access with compliance checks.'),
  _RegionOption('GB', 'United Kingdom', 'EU/UK policy stack with standard review.'),
  _RegionOption('BR', 'Brazil', 'Latin America regional controls.'),
  _RegionOption('ES', 'Spain', 'EU policy bucket with fan support lanes.'),
  _RegionOption('GLOBAL', 'Global / Other', 'Limited access pending region verification.'),
];
