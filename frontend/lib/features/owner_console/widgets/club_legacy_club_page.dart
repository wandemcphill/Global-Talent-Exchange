import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

class ClubLegacyClubPageData {
  const ClubLegacyClubPageData({
    required this.locationLines,
    required this.history,
    required this.roster,
    required this.honours,
    required this.staff,
    required this.facilities,
    required this.commercial,
    this.ownershipLabels = const <String>[],
    this.modelFailed = false,
  });

  factory ClubLegacyClubPageData.fromJson(Map<String, dynamic> json) {
    final Map<String, dynamic> sections =
        json['sections'] is Map ? Map<String, dynamic>.from(json['sections'] as Map) : <String, dynamic>{};
    final Map<String, dynamic> location =
        sections['location'] is Map
            ? Map<String, dynamic>.from(sections['location'] as Map)
            : <String, dynamic>{};
    final Map<String, dynamic> showroom =
        json['showroom'] is Map ? Map<String, dynamic>.from(json['showroom'] as Map) : <String, dynamic>{};
    final List<Map<String, dynamic>> exhibits = _rows(showroom['exhibits']);
    return ClubLegacyClubPageData(
      locationLines: <String>[
        for (final String key in <String>['city', 'country_code', 'continent_name'])
          if ('${location[key] ?? ''}'.trim().isNotEmpty) '${location[key]}',
      ],
      history: _labels(sections['history']),
      roster: _labels(sections['roster'], fallback: 'name'),
      honours: _labels(sections['honours']),
      staff: _labels(sections['staff']),
      facilities: _labels(sections['facilities']),
      commercial: _labels(sections['commercial']),
      ownershipLabels: <String>[
        for (final Map<String, dynamic> row in exhibits)
          if ('${row['ownership_label'] ?? ''}'.trim().isNotEmpty) '${row['ownership_label']}',
      ],
      modelFailed: showroom['model_error'] != null || showroom['mode'] == 'static-fallback',
    );
  }

  final List<String> locationLines;
  final List<String> history;
  final List<String> roster;
  final List<String> honours;
  final List<String> staff;
  final List<String> facilities;
  final List<String> commercial;
  final List<String> ownershipLabels;
  final bool modelFailed;
}

List<Map<String, dynamic>> _rows(Object? value) =>
    (value is List ? value : const <dynamic>[])
        .whereType<Map>()
        .map((Map row) => Map<String, dynamic>.from(row))
        .toList();

List<String> _labels(Object? value, {String fallback = 'label'}) {
  final List<String> lines = <String>[];
  for (final Map<String, dynamic> row in _rows(value)) {
    final String name = '${row['name'] ?? row[fallback] ?? row['label'] ?? ''}'.trim();
    if (name.isEmpty) {
      continue;
    }
    final String extra = '${row['role'] ?? row['position'] ?? row['level'] ?? ''}'.trim();
    lines.add(extra.isEmpty ? name : '$name · $extra');
  }
  return lines;
}

class _ClubTab {
  const _ClubTab(this.keyName, this.title, this.lines);

  final String keyName;
  final String title;
  final List<String> lines;
}

/// Club page sections from real records. An empty honour list stays empty.
class ClubLegacyClubPage extends StatelessWidget {
  const ClubLegacyClubPage({super.key, required this.data});

  final ClubLegacyClubPageData data;

  @override
  Widget build(BuildContext context) {
    final List<_ClubTab> tabs = <_ClubTab>[
      _ClubTab('location', 'Location', data.locationLines),
      _ClubTab('history', 'History', data.history),
      _ClubTab('roster', 'Roster', data.roster),
      _ClubTab('honours', 'Honours', data.honours),
      _ClubTab('staff', 'Staff', data.staff),
      _ClubTab('facilities', 'Facilities', data.facilities),
      _ClubTab('commercial', 'Commercial', data.commercial),
    ];
    return Column(
      key: const Key('club-page'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        if (data.modelFailed)
          const Padding(
            padding: EdgeInsets.fromLTRB(12, 12, 12, 0),
            child: Text(
              'Static card',
              key: Key('club-page-static-fallback'),
              style: TextStyle(color: GtexColors.text, fontWeight: FontWeight.w800),
            ),
          ),
        if (data.ownershipLabels.isNotEmpty)
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
            child: Wrap(
              spacing: 8,
              runSpacing: 4,
              children: <Widget>[
                for (final String label in data.ownershipLabels)
                  Text(
                    label,
                    key: Key('club-page-ownership-${_slug(label)}'),
                    style: const TextStyle(color: GtexColors.textSecondary, fontSize: 12),
                  ),
              ],
            ),
          ),
        Expanded(
          child: DefaultTabController(
            length: tabs.length,
            child: Column(
              children: <Widget>[
                TabBar(
                  isScrollable: true,
                  tabAlignment: TabAlignment.start,
                  tabs: <Widget>[
                    for (final _ClubTab tab in tabs)
                      Tab(key: Key('club-page-tab-${tab.keyName}'), text: tab.title),
                  ],
                ),
                Expanded(
                  child: TabBarView(
                    children: <Widget>[for (final _ClubTab tab in tabs) _pane(tab)],
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _pane(_ClubTab tab) {
    final bool empty = tab.lines.isEmpty;
    final String emptyMessage = tab.keyName == 'honours' ? 'No honours yet' : 'Nothing here yet';
    return ListView(
      key: Key('club-page-${tab.keyName}'),
      padding: const EdgeInsets.all(12),
      children: <Widget>[
        if (empty)
          Text(
            emptyMessage,
            key: Key('club-page-${tab.keyName}-empty'),
            style: const TextStyle(color: GtexColors.textSecondary),
          ),
        for (final String line in tab.lines)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Text(line, style: const TextStyle(color: GtexColors.text)),
          ),
      ],
    );
  }
}

String _slug(String label) => label.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), '-');
