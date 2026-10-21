import 'package:flutter/material.dart';

import 'gtex_home_models.dart';
import 'gtex_home_shared_widgets.dart';

class GtexRegenEconomySection extends StatefulWidget {
  const GtexRegenEconomySection({super.key});

  @override
  State<GtexRegenEconomySection> createState() => _GtexRegenEconomySectionState();
}

class _GtexRegenEconomySectionState extends State<GtexRegenEconomySection> {
  int _activeStepIndex = 0;
  int _selectedRegenIndex = 0;

  static const List<_RegenJourneyStep> _journeySteps = <_RegenJourneyStep>[
    _RegenJourneyStep(
      stepNumber: '01',
      title: 'Academy Intake & Scout Identification',
      subtitle: 'Raw potential discovered at age 15–16 through regional scout networks.',
      detail: 'Every season, club academies receive new intake batches. Scouts generate comprehensive dossier ratings including hidden potential ceiling, personality traits (e.g. Leadership, Composure), and physical baseline.',
      metricLabel: 'Intake Age',
      metricValue: '15–16 Yrs',
      icon: Icons.person_search_rounded,
      accentColor: kSkyBlue,
    ),
    _RegenJourneyStep(
      stepNumber: '02',
      title: 'Apex Campus & Training Multipliers',
      subtitle: 'Sports science, youth facilities, and mentor coaching accelerate development.',
      detail: 'Training plans combined with Apex Performance Campus facilities apply development multipliers. Regens paired with veteran squad mentors develop secondary positions and boost their composure under pressure.',
      metricLabel: 'Facility Multiplier',
      metricValue: 'Up to 2.4x Speed',
      icon: Icons.fitness_center_rounded,
      accentColor: kPitchGreenBright,
    ),
    _RegenJourneyStep(
      stepNumber: '03',
      title: 'Competitive Squad Progression',
      subtitle: 'From U19 tournaments to first-team matchday bench and continental debuts.',
      detail: 'Match minutes in competitive tournaments (Atlantic Prospect Series, U21 showcases) convert raw potential into actual in-match ability. Decisive performances unlock prestigious GSI (Global Soccer Intelligence) tiers.',
      metricLabel: 'Pathway',
      metricValue: 'U19 → Reserve → First XI',
      icon: Icons.sports_soccer_rounded,
      accentColor: kGoldPrimary,
    ),
    _RegenJourneyStep(
      stepNumber: '04',
      title: 'Valuation & Transfer Marketplace',
      subtitle: 'Value engine recalibrates credit worth. Open market bidding & continental buyouts.',
      detail: 'As regens mature, their market valuation increases exponentially. Owners can sign them to long-term contracts, lease them for national team tournaments, or negotiate record-breaking multi-million GTC transfers.',
      metricLabel: 'Value Engine',
      metricValue: 'Real Credit Liquidity',
      icon: Icons.trending_up_rounded,
      accentColor: Color(0xFFA855F7),
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final double width = MediaQuery.sizeOf(context).width;
    final bool isNarrow = width < 760;
    final _RegenJourneyStep activeStep = _journeySteps[_activeStepIndex];
    final RegenTalentProfile activeRegen = kFeaturedRegens[_selectedRegenIndex];

    return Container(
      color: kNavyBase,
      padding: EdgeInsets.symmetric(
        horizontal: isNarrow ? 20 : 64,
        vertical: 64,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          // Section Masthead
          const GtexSectionHeader(
            eyebrow: 'Player Development & The Regen Economy',
            title: 'Discover the Next Superstar. Build Living Football Value.',
            subtitle: 'Regens in GTEX are one-of-a-kind living assets with unique DNA, evolving ratings, distinct personalities, and genuine transfer market liquidity. Guide an academy intake prospect from raw youth to continental champion.',
            accentColor: kGoldPrimary,
          ),

          const SizedBox(height: 36),

          // Visual Stepper (01 to 04)
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: List<Widget>.generate(_journeySteps.length, (int index) {
                final _RegenJourneyStep step = _journeySteps[index];
                final bool isSelected = index == _activeStepIndex;
                return Padding(
                  padding: const EdgeInsets.only(right: 10),
                  child: InkWell(
                    onTap: () => setState(() => _activeStepIndex = index),
                    borderRadius: BorderRadius.circular(12),
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 200),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      decoration: BoxDecoration(
                        color: isSelected ? kNavyOverlay : kNavyRaised,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: isSelected ? step.accentColor : kNavyLine,
                          width: isSelected ? 2 : 1,
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: <Widget>[
                          Text(
                            step.stepNumber,
                            style: TextStyle(
                              color: isSelected ? step.accentColor : kTextTertiary,
                              fontSize: 15,
                              fontWeight: FontWeight.w900,
                              fontFamily: kFontMono,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisSize: MainAxisSize.min,
                            children: <Widget>[
                              Text(
                                step.title,
                                style: TextStyle(
                                  color: isSelected ? kTextPrimary : kTextSecondary,
                                  fontSize: 12,
                                  fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
                                ),
                              ),
                              Text(
                                step.metricValue,
                                style: TextStyle(
                                  color: isSelected ? step.accentColor : kTextTertiary,
                                  fontSize: 10,
                                  fontFamily: kFontMono,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              }),
            ),
          ),

          const SizedBox(height: 18),

          // Active Step Detail Banner
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: kNavyRaised,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: activeStep.accentColor.withValues(alpha: 0.4)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: activeStep.accentColor.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(activeStep.icon, color: activeStep.accentColor, size: 24),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Wrap(
                        alignment: WrapAlignment.spaceBetween,
                        spacing: 8,
                        runSpacing: 4,
                        children: <Widget>[
                          Text(
                            'STEP ${activeStep.stepNumber} • ${activeStep.title.toUpperCase()}',
                            style: TextStyle(
                              color: activeStep.accentColor,
                              fontSize: 11,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 1.2,
                              fontFamily: kFontCondensed,
                            ),
                          ),
                          Text(
                            '${activeStep.metricLabel}: ${activeStep.metricValue}',
                            style: const TextStyle(
                              color: kTextTertiary,
                              fontSize: 11,
                              fontFamily: kFontMono,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        activeStep.subtitle,
                        style: const TextStyle(
                          color: kTextPrimary,
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        activeStep.detail,
                        style: const TextStyle(
                          color: kTextSecondary,
                          fontSize: 12,
                          height: 1.45,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 40),

          // Featured Regen Profiles Showcase
          Wrap(
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: 10,
            runSpacing: 6,
            children: <Widget>[
              Wrap(
                crossAxisAlignment: WrapCrossAlignment.center,
                spacing: 8,
                children: const <Widget>[
                  Icon(Icons.auto_awesome_rounded, color: kGoldPrimary, size: 20),
                  Text(
                    'FEATURED REGEN TALENT DOSSIERS',
                    style: TextStyle(
                      color: kGoldPrimary,
                      fontSize: 14,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.5,
                      fontFamily: kFontCondensed,
                    ),
                  ),
                ],
              ),
              const Text(
                'REAL ATTRIBUTES & DNA PROFILES',
                style: TextStyle(
                  color: kTextTertiary,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1,
                  fontFamily: kFontCondensed,
                ),
              ),
            ],
          ),

          const SizedBox(height: 14),

          // Regen Switcher Chips
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: List<Widget>.generate(kFeaturedRegens.length, (int index) {
                final RegenTalentProfile regen = kFeaturedRegens[index];
                final bool isSelected = index == _selectedRegenIndex;
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                    label: Text('${regen.name} (${regen.position}, ${regen.age})'),
                    selected: isSelected,
                    onSelected: (_) => setState(() => _selectedRegenIndex = index),
                    selectedColor: kGoldPrimary.withValues(alpha: 0.2),
                    backgroundColor: kNavyRaised,
                    labelStyle: TextStyle(
                      color: isSelected ? kGoldLight : kTextSecondary,
                      fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
                      fontSize: 12,
                    ),
                    side: BorderSide(
                      color: isSelected ? kGoldPrimary : kNavyLine,
                    ),
                  ),
                );
              }),
            ),
          ),

          const SizedBox(height: 18),

          // Selected Regen Deep Card
          Container(
            decoration: BoxDecoration(
              color: kNavyInset,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: kNavyLineStrong),
            ),
            padding: EdgeInsets.all(isNarrow ? 16 : 24),
            child: LayoutBuilder(
              builder: (BuildContext context, BoxConstraints constraints) {
                final bool isWide = constraints.maxWidth > 700;
                return isWide
                    ? Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          // Left column: Identity & Story
                          Expanded(
                            flex: 5,
                            child: _RegenIdentityCol(regen: activeRegen),
                          ),
                          const SizedBox(width: 28),
                          // Right column: Attributes & Traits
                          Expanded(
                            flex: 6,
                            child: _RegenAttributesCol(regen: activeRegen),
                          ),
                        ],
                      )
                    : Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          _RegenIdentityCol(regen: activeRegen),
                          const SizedBox(height: 20),
                          const Divider(color: kNavyLine),
                          const SizedBox(height: 16),
                          _RegenAttributesCol(regen: activeRegen),
                        ],
                      );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _RegenJourneyStep {
  const _RegenJourneyStep({
    required this.stepNumber,
    required this.title,
    required this.subtitle,
    required this.detail,
    required this.metricLabel,
    required this.metricValue,
    required this.icon,
    required this.accentColor,
  });

  final String stepNumber;
  final String title;
  final String subtitle;
  final String detail;
  final String metricLabel;
  final String metricValue;
  final IconData icon;
  final Color accentColor;
}

class _RegenIdentityCol extends StatelessWidget {
  const _RegenIdentityCol({required this.regen});

  final RegenTalentProfile regen;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Wrap(
          spacing: 8,
          runSpacing: 6,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: <Widget>[
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: kGoldPrimary.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: kGoldPrimary),
              ),
              child: Text(
                regen.position,
                style: const TextStyle(
                  color: kGoldPrimary,
                  fontSize: 12,
                  fontWeight: FontWeight.w900,
                  fontFamily: kFontMono,
                ),
              ),
            ),
            GtexTagPill(label: regen.gsiTierLabel, color: kPitchGreenBright),
            Text(
              '${regen.nationality} (${regen.countryCode})',
              style: const TextStyle(color: kTextTertiary, fontSize: 12),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Text(
          regen.name,
          style: const TextStyle(
            color: kTextPrimary,
            fontSize: 26,
            fontWeight: FontWeight.w900,
            fontFamily: kFontCondensed,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          'Archetype: ${regen.archetype} • Age ${regen.age}',
          style: const TextStyle(
            color: kGoldLight,
            fontSize: 13,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 10),
        Text(
          regen.story,
          style: const TextStyle(
            color: kTextSecondary,
            fontSize: 12,
            height: 1.45,
          ),
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: kNavyRaised,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: kNavyLine),
          ),
          child: Wrap(
            alignment: WrapAlignment.spaceAround,
            spacing: 12,
            runSpacing: 8,
            children: <Widget>[
              _StatPill(label: 'CURRENT OVR', value: '${regen.currentRating}'),
              _StatPill(label: 'POTENTIAL CEILING', value: '${regen.potentialRating}', valueColor: kPitchGreenBright),
              _StatPill(label: 'EST. VALUE', value: regen.estimatedValueCredits, valueColor: kGoldLight),
            ],
          ),
        ),
      ],
    );
  }
}

class _RegenAttributesCol extends StatelessWidget {
  const _RegenAttributesCol({required this.regen});

  final RegenTalentProfile regen;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const Text(
          'TECHNICAL & MENTAL ATTRIBUTES',
          style: TextStyle(
            color: kGoldPrimary,
            fontSize: 11,
            fontWeight: FontWeight.w800,
            letterSpacing: 1.2,
            fontFamily: kFontCondensed,
          ),
        ),
        const SizedBox(height: 12),
        _AttributeRow(label: 'Pace & Acceleration', score: regen.pace),
        const SizedBox(height: 8),
        _AttributeRow(label: 'Tactical Vision', score: regen.vision),
        const SizedBox(height: 8),
        _AttributeRow(label: 'Technical Ball Control', score: regen.technique),
        const SizedBox(height: 8),
        _AttributeRow(label: 'Stamina & Work Rate', score: regen.stamina),
        const SizedBox(height: 8),
        _AttributeRow(label: 'Big-Match Mentality', score: regen.mentality),
        const SizedBox(height: 16),
        const Text(
          'UNLOCKED SPECIAL TRAITS',
          style: TextStyle(
            color: kGoldPrimary,
            fontSize: 11,
            fontWeight: FontWeight.w800,
            letterSpacing: 1.2,
            fontFamily: kFontCondensed,
          ),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: regen.traits
              .map((String trait) => Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: kNavyRaised,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: kNavyLine),
                    ),
                    child: Text(
                      trait,
                      style: const TextStyle(
                        color: kTextPrimary,
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ))
              .toList(),
        ),
      ],
    );
  }
}

class _StatPill extends StatelessWidget {
  const _StatPill({
    required this.label,
    required this.value,
    this.valueColor = kTextPrimary,
  });

  final String label;
  final String value;
  final Color valueColor;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Text(
          label,
          style: const TextStyle(
            color: kTextTertiary,
            fontSize: 9,
            fontWeight: FontWeight.w700,
            fontFamily: kFontCondensed,
            letterSpacing: 1,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: TextStyle(
            color: valueColor,
            fontSize: 14,
            fontWeight: FontWeight.w900,
            fontFamily: kFontMono,
          ),
        ),
      ],
    );
  }
}

class _AttributeRow extends StatelessWidget {
  const _AttributeRow({required this.label, required this.score});

  final String label;
  final int score;

  @override
  Widget build(BuildContext context) {
    final double pct = (score / 100).clamp(0.0, 1.0);
    final Color barColor = score >= 90
        ? kPitchGreenBright
        : (score >= 80 ? kGoldPrimary : kSkyBlue);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Text(
              label,
              style: const TextStyle(color: kTextSecondary, fontSize: 11),
            ),
            const Spacer(),
            Text(
              '$score',
              style: TextStyle(
                color: barColor,
                fontSize: 11,
                fontWeight: FontWeight.w800,
                fontFamily: kFontMono,
              ),
            ),
          ],
        ),
        const SizedBox(height: 3),
        ClipRRect(
          borderRadius: BorderRadius.circular(3),
          child: LinearProgressIndicator(
            value: pct,
            minHeight: 5,
            backgroundColor: kNavyRaised,
            valueColor: AlwaysStoppedAnimation<Color>(barColor),
          ),
        ),
      ],
    );
  }
}
