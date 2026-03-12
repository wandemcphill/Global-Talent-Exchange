import 'package:flutter/material.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/season_honors_dto.dart';
import 'package:gte_frontend/features/club_identity/trophies/widgets/season_honors_group.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class HonorsTimelineCard extends StatefulWidget {
  const HonorsTimelineCard({
    super.key,
    required this.seasonLabel,
    required this.records,
    this.initiallyExpanded = false,
  });

  final String seasonLabel;
  final List<SeasonHonorsRecordDto> records;
  final bool initiallyExpanded;

  @override
  State<HonorsTimelineCard> createState() => _HonorsTimelineCardState();
}

class _HonorsTimelineCardState extends State<HonorsTimelineCard> {
  late bool _expanded;

  @override
  void initState() {
    super.initState();
    _expanded = widget.initiallyExpanded;
  }

  @override
  Widget build(BuildContext context) {
    final int totalHonors = widget.records.fold<int>(
      0,
      (int sum, SeasonHonorsRecordDto record) => sum + record.totalHonorsCount,
    );
    final int majorHonors = widget.records.fold<int>(
      0,
      (int sum, SeasonHonorsRecordDto record) => sum + record.majorHonorsCount,
    );
    return GteSurfacePanel(
      emphasized: widget.initiallyExpanded,
      onTap: () {
        setState(() {
          _expanded = !_expanded;
        });
      },
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      widget.seasonLabel,
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      '$totalHonors honors archived • $majorHonors major',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              Icon(
                _expanded ? Icons.expand_less : Icons.expand_more,
              ),
            ],
          ),
          AnimatedCrossFade(
            duration: const Duration(milliseconds: 220),
            crossFadeState: _expanded
                ? CrossFadeState.showSecond
                : CrossFadeState.showFirst,
            firstChild: const SizedBox(height: 0),
            secondChild: Padding(
              padding: const EdgeInsets.only(top: 18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: widget.records.map((SeasonHonorsRecordDto record) {
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 18),
                    child: SeasonHonorsGroup(record: record),
                  );
                }).toList(growable: false),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
