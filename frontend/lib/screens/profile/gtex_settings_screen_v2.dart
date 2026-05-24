import 'package:flutter/material.dart';

import '../../features/system_profile_redesign/models/gtex_profile_models.dart';
import '../../features/system_profile_redesign/presentation/gtex_profile_controller.dart';

class GtexSettingsScreenV2 extends StatefulWidget {
  const GtexSettingsScreenV2({
    super.key,
    this.controller = const GtexProfileController(),
  });

  final GtexProfileController controller;

  @override
  State<GtexSettingsScreenV2> createState() => _GtexSettingsScreenV2State();
}

class _GtexSettingsScreenV2State extends State<GtexSettingsScreenV2> {
  late String _selected = widget.controller.settingSections().first.id;

  @override
  Widget build(BuildContext context) {
    final sections = widget.controller.settingSections();
    final selected = sections.firstWhere((section) => section.id == _selected);
    return Scaffold(
      backgroundColor: const Color(0xFF050B08),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Row(
            children: [
              SizedBox(
                width: 300,
                child: _SettingsList(
                  sections: sections,
                  selectedId: _selected,
                  onSelected: (id) => setState(() => _selected = id),
                ),
              ),
              const SizedBox(width: 18),
              Expanded(child: _SettingsWorkspace(section: selected)),
            ],
          ),
        ),
      ),
    );
  }
}

class _SettingsList extends StatelessWidget {
  const _SettingsList({
    required this.sections,
    required this.selectedId,
    required this.onSelected,
  });
  final List<GtexSettingSection> sections;
  final String selectedId;
  final ValueChanged<String> onSelected;

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
            'SETTINGS',
            style: TextStyle(
              color: Color(0xFF39FF88),
              fontWeight: FontWeight.w900,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: 18),
          for (final section in sections)
            InkWell(
              onTap: () => onSelected(section.id),
              borderRadius: BorderRadius.circular(16),
              child: Container(
                width: double.infinity,
                margin: const EdgeInsets.only(bottom: 10),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color:
                      selectedId == section.id
                          ? const Color(0xFF153B27)
                          : Colors.transparent,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      section.title,
                      style: TextStyle(
                        color:
                            selectedId == section.id
                                ? Colors.white
                                : Colors.white70,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      section.subtitle,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Colors.white38,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _SettingsWorkspace extends StatelessWidget {
  const _SettingsWorkspace({required this.section});
  final GtexSettingSection section;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        Text(
          section.title,
          style: Theme.of(context).textTheme.headlineMedium?.copyWith(
            color: Colors.white,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: 8),
        Text(section.subtitle, style: const TextStyle(color: Colors.white60)),
        const SizedBox(height: 18),
        for (final item in section.items) _SettingItemCard(item: item),
      ],
    );
  }
}

class _SettingItemCard extends StatelessWidget {
  const _SettingItemCard({required this.item});
  final GtexSettingItem item;

  @override
  Widget build(BuildContext context) {
    final accent = item.isDanger ? Colors.redAccent : const Color(0xFF39FF88);
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF0E1D15),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: const Color(0xFF214232)),
      ),
      child: Row(
        children: [
          Icon(
            item.isDanger ? Icons.warning_amber_rounded : Icons.tune,
            color: accent,
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                    fontSize: 16,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  item.description,
                  style: const TextStyle(color: Colors.white60),
                ),
              ],
            ),
          ),
          const SizedBox(width: 14),
          Chip(
            label: Text(item.status),
            backgroundColor: Colors.black26,
            labelStyle: TextStyle(color: accent),
          ),
          const SizedBox(width: 8),
          Tooltip(
            message: 'Detailed settings are not mounted in this shell yet.',
            child: IconButton(
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(
                      '${item.title} is tracked here; detailed controls are handled by the live preferences APIs.',
                    ),
                  ),
                );
              },
              icon: const Icon(Icons.chevron_right, color: Colors.white54),
            ),
          ),
        ],
      ),
    );
  }
}
