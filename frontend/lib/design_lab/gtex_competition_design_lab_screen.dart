import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/components/gtex_command_center.dart';
import 'package:gte_frontend/ui_gtex/components/gtex_competition_command.dart';
import 'package:gte_frontend/ui_gtex/theme/gtex_colors.dart';
import 'package:gte_frontend/ui_gtex/theme/gtex_spacing.dart';
import 'package:gte_frontend/ui_gtex/theme/gtex_typography.dart';

/// Deliberately unlinked, fixture-only exploration for the Slice 4 hierarchy.
/// These values are not used by the production competition providers.
class GtexCompetitionDesignLabScreen extends StatefulWidget {
  const GtexCompetitionDesignLabScreen({super.key, this.initialDirection});

  final String? initialDirection;

  @override
  State<GtexCompetitionDesignLabScreen> createState() =>
      _GtexCompetitionDesignLabScreenState();
}

class _GtexCompetitionDesignLabScreenState
    extends State<GtexCompetitionDesignLabScreen> {
  _CompetitionLabDirection _direction = _CompetitionLabDirection.atlas;

  @override
  void initState() {
    super.initState();
    _direction = _CompetitionLabDirection.fromQuery(widget.initialDirection);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: GtexColors.surfaceBase,
    body: SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(GtexSpacing.lg),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1200),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'FIXTURE-ONLY DESIGN LAB',
                  style: GtexText.labelSM.copyWith(
                    color: GtexColors.accentAmber,
                    letterSpacing: 1.3,
                  ),
                ),
                const SizedBox(height: GtexSpacing.xs),
                Text(
                  'Competition command compositions',
                  style: GtexText.displayXL.copyWith(
                    color: GtexColors.textPrimary,
                  ),
                ),
                const SizedBox(height: GtexSpacing.sm),
                Text(
                  'Local fixtures only — not a live competition, match, or account state.',
                  style: GtexText.bodyMD.copyWith(
                    color: GtexColors.textSecondary,
                  ),
                ),
                const SizedBox(height: GtexSpacing.lg),
                GtexCompetitionFamilySelector<_CompetitionLabDirection>(
                  value: _direction,
                  onChanged:
                      (_CompetitionLabDirection value) =>
                          setState(() => _direction = value),
                  items: const <
                    GtexCompetitionFamilyItem<_CompetitionLabDirection>
                  >[
                    GtexCompetitionFamilyItem<_CompetitionLabDirection>(
                      value: _CompetitionLabDirection.matchday,
                      label: 'A · Matchday board',
                      accent: GtexColors.accentPrimary,
                    ),
                    GtexCompetitionFamilyItem<_CompetitionLabDirection>(
                      value: _CompetitionLabDirection.atlas,
                      label: 'B · Competition atlas',
                      accent: GtexColors.accentBlue,
                    ),
                    GtexCompetitionFamilyItem<_CompetitionLabDirection>(
                      value: _CompetitionLabDirection.participation,
                      label: 'C · Participation desk',
                      accent: GtexColors.accentAmber,
                    ),
                  ],
                ),
                const SizedBox(height: GtexSpacing.lg),
                _LabComposition(direction: _direction),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}

enum _CompetitionLabDirection {
  matchday,
  atlas,
  participation;

  static _CompetitionLabDirection fromQuery(String? value) {
    return switch (value?.trim().toLowerCase()) {
      'matchday' => _CompetitionLabDirection.matchday,
      'participation' => _CompetitionLabDirection.participation,
      _ => _CompetitionLabDirection.atlas,
    };
  }
}

class _LabComposition extends StatelessWidget {
  const _LabComposition({required this.direction});
  final _CompetitionLabDirection direction;

  @override
  Widget build(BuildContext context) {
    final _LabCopy copy = switch (direction) {
      _CompetitionLabDirection.matchday => const _LabCopy(
        eyebrow: 'A · Matchday board',
        title: 'Next fixture first.',
        summary: 'A high-pressure board where the matchday is the decision.',
        status: 'Fixture sample',
        statusState: GtexCommandStatus.preview,
      ),
      _CompetitionLabDirection.atlas => const _LabCopy(
        eyebrow: 'B · Competition atlas · selected',
        title: 'The competition creates the matchday.',
        summary:
            'Identity, lifecycle, table and fixtures establish football context before the participation decision.',
        status: 'Composition sample',
        statusState: GtexCommandStatus.preview,
      ),
      _CompetitionLabDirection.participation => const _LabCopy(
        eyebrow: 'C · Participation desk',
        title: 'Can this club enter?',
        summary:
            'Eligibility and entry mechanics lead, before the table and matchday context.',
        status: 'Eligibility sample',
        statusState: GtexCommandStatus.preview,
      ),
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        GtexCommandCenterMasthead(
          eyebrow: copy.eyebrow,
          identity: 'Sample GTEX Club',
          identityDetail: 'Fixture-only specimen',
          title: copy.title,
          summary: copy.summary,
          statusLabel: copy.status,
          status: copy.statusState,
          metrics: const <GtexCommandMetric>[
            GtexCommandMetric(
              label: 'Table',
              value: 'Sample',
              detail: 'Not provider data',
              accent: GtexColors.accentBlue,
            ),
            GtexCommandMetric(
              label: 'Fixtures',
              value: 'Sample',
              detail: 'Not provider data',
              accent: GtexColors.accentPrimary,
            ),
            GtexCommandMetric(
              label: 'Entry',
              value: 'Sample',
              detail: 'Not provider data',
              accent: GtexColors.accentAmber,
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.lg),
        if (direction == _CompetitionLabDirection.matchday) ...<Widget>[
          _fixture(),
          const SizedBox(height: GtexSpacing.md),
          _table(),
          const SizedBox(height: GtexSpacing.md),
          _participation(),
        ] else if (direction == _CompetitionLabDirection.atlas) ...<Widget>[
          _table(),
          const SizedBox(height: GtexSpacing.md),
          _fixture(),
          const SizedBox(height: GtexSpacing.md),
          _participation(),
        ] else ...<Widget>[
          _participation(),
          const SizedBox(height: GtexSpacing.md),
          _fixture(),
          const SizedBox(height: GtexSpacing.md),
          _table(),
        ],
      ],
    );
  }

  Widget _fixture() => const _LabPanel(
    title: 'Fixture treatment · sample only',
    child: GtexMatchdayFixtureTile(
      home: 'Northbank FC',
      away: 'Harbour Athletic',
      stateLabel: 'Sample fixture',
      contextLabel: 'No live date or Match Viewer link',
    ),
  );

  Widget _table() => const _LabPanel(
    title: 'Standings treatment · sample only',
    child: Column(
      children: <Widget>[
        GtexCompetitionStandingRow(
          position: '1',
          name: 'Northbank FC',
          played: '0',
          points: '0',
        ),
        GtexCompetitionStandingRow(
          position: '2',
          name: 'Harbour Athletic',
          played: '0',
          points: '0',
        ),
      ],
    ),
  );

  Widget _participation() => const _LabPanel(
    title: 'Participation treatment · sample only',
    child: Text(
      'The production surface replaces this specimen with provider-backed eligibility.',
      style: GtexText.bodyMD,
    ),
  );
}

class _LabPanel extends StatelessWidget {
  const _LabPanel({required this.title, required this.child});
  final String title;
  final Widget child;
  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(GtexSpacing.md),
    decoration: BoxDecoration(
      color: GtexColors.surfaceRaised,
      border: Border.all(color: GtexColors.surfaceBorder),
      borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          title,
          style: GtexText.labelLG.copyWith(color: GtexColors.textPrimary),
        ),
        const SizedBox(height: GtexSpacing.sm),
        child,
      ],
    ),
  );
}

class _LabCopy {
  const _LabCopy({
    required this.eyebrow,
    required this.title,
    required this.summary,
    required this.status,
    required this.statusState,
  });
  final String eyebrow;
  final String title;
  final String summary;
  final String status;
  final GtexCommandStatus statusState;
}
