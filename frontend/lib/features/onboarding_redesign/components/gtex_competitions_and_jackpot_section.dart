import 'dart:async';
import 'package:flutter/material.dart';

import 'gtex_home_models.dart';
import 'gtex_home_shared_widgets.dart';

class GtexCompetitionsAndJackpotSection extends StatefulWidget {
  const GtexCompetitionsAndJackpotSection({
    super.key,
    this.initialJackpotBalance,
    this.initialFailsafeAt,
  });

  final String? initialJackpotBalance;
  final DateTime? initialFailsafeAt;

  @override
  State<GtexCompetitionsAndJackpotSection> createState() => _GtexCompetitionsAndJackpotSectionState();
}

class _GtexCompetitionsAndJackpotSectionState extends State<GtexCompetitionsAndJackpotSection> {
  Timer? _countdownTimer;
  Duration _remaining = Duration.zero;
  DateTime? _targetAt;

  @override
  void initState() {
    super.initState();
    _syncCountdown();
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        final DateTime now = DateTime.now().toUtc();
        if (_targetAt == null || !_targetAt!.isAfter(now)) {
          _targetAt = _nextScheduledDrop(now);
        }
        _remaining = _targetAt!.difference(now);
      });
    });
  }

  @override
  void didUpdateWidget(covariant GtexCompetitionsAndJackpotSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.initialFailsafeAt != oldWidget.initialFailsafeAt) {
      _syncCountdown();
    }
  }

  void _syncCountdown() {
    final DateTime now = DateTime.now().toUtc();
    final DateTime? serverTarget = widget.initialFailsafeAt?.toUtc();
    _targetAt = serverTarget != null && serverTarget.isAfter(now)
        ? serverTarget
        : _nextScheduledDrop(now);
    _remaining = _targetAt!.difference(now);
  }

  DateTime _nextScheduledDrop(DateTime now) {
    final int nextDropHour = ((now.hour ~/ 6) + 1) * 6;
    if (nextDropHour >= 24) {
      return DateTime.utc(now.year, now.month, now.day + 1);
    }
    return DateTime.utc(now.year, now.month, now.day, nextDropHour);
  }

  @override
  void dispose() {
    _countdownTimer?.cancel();
    super.dispose();
  }

  String _formatDuration(Duration d) {
    final String hh = d.inHours.toString().padLeft(2, '0');
    final String mm = (d.inMinutes % 60).toString().padLeft(2, '0');
    final String ss = (d.inSeconds % 60).toString().padLeft(2, '0');
    return '$hh:$mm:$ss';
  }

  @override
  Widget build(BuildContext context) {
    final double width = MediaQuery.sizeOf(context).width;
    final bool isNarrow = width < 760;

    return Container(
      color: kNavyInset,
      padding: EdgeInsets.symmetric(
        horizontal: isNarrow ? 20 : 64,
        vertical: 64,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          // Section Masthead
          const GtexSectionHeader(
            eyebrow: 'Competitions & Prize Drops',
            title: 'Continental Glory & 4 Scheduled Daily Jackpots',
            subtitle: 'Enter league circuits, knockout tournaments and user-hosted cups. Published event rules define eligibility and prize pools, alongside the four scheduled daily jackpot drops.',
            accentColor: kGoldPrimary,
          ),

          const SizedBox(height: 32),

          // The 4 Daily Jackpot Drops Flagship Card
          Container(
            decoration: BoxDecoration(
              color: kNavyRaised,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: kGoldPrimary.withValues(alpha: 0.5), width: 1.5),
              boxShadow: <BoxShadow>[
                BoxShadow(
                  color: kGoldPrimary.withValues(alpha: 0.12),
                  blurRadius: 28,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            padding: EdgeInsets.all(isNarrow ? 18 : 32),
            child: LayoutBuilder(
              builder: (BuildContext context, BoxConstraints constraints) {
                final bool wide = constraints.maxWidth > 720;
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Wrap(
                      alignment: WrapAlignment.spaceBetween,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      spacing: 10,
                      runSpacing: 6,
                      children: <Widget>[
                        const GtexTagPill(
                          label: '4 SCHEDULED DAILY DROPS • 6-HR CYCLE',
                          color: kGoldPrimary,
                          icon: Icons.access_time_filled_rounded,
                        ),
                        const GtexTagPill(
                          label: 'UTC SCHEDULE',
                          color: kSkyBlue,
                          icon: Icons.schedule_rounded,
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),
                    if (wide)
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.center,
                        children: <Widget>[
                          Expanded(
                            flex: 6,
                            child: _JackpotCountdownBlock(
                              countdownStr: _formatDuration(_remaining),
                              balanceStr: widget.initialJackpotBalance ?? 'Pool unavailable',
                            ),
                          ),
                          const SizedBox(width: 28),
                          const Expanded(
                            flex: 6,
                            child: _JackpotMechanicsBlock(),
                          ),
                        ],
                      )
                    else
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          _JackpotCountdownBlock(
                            countdownStr: _formatDuration(_remaining),
                            balanceStr: widget.initialJackpotBalance ?? 'Pool unavailable',
                          ),
                          const SizedBox(height: 20),
                          const Divider(color: kNavyLine),
                          const SizedBox(height: 14),
                          const _JackpotMechanicsBlock(),
                        ],
                      ),
                  ],
                );
              },
            ),
          ),

          const SizedBox(height: 40),

          // Active Tournaments Showcase
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
                  Icon(Icons.emoji_events_rounded, color: kGoldPrimary, size: 20),
                  Text(
                    'FEATURED COMPETITION FORMATS',
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
                'ILLUSTRATIVE • NOT LIVE FIXTURES',
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

          const SizedBox(height: 16),

          // Tournament Cards Grid
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final int columns = constraints.maxWidth > 950 ? 3 : (constraints.maxWidth > 600 ? 2 : 1);
              final double cardWidth = (constraints.maxWidth - ((columns - 1) * 16)) / columns;

              return Wrap(
                spacing: 16,
                runSpacing: 16,
                children: kCompetitionFormatPreviews.map((ActiveCompetitionItem comp) {
                  return SizedBox(
                    width: cardWidth,
                    child: _TournamentCard(comp: comp),
                  );
                }).toList(),
              );
            },
          ),
        ],
      ),
    );
  }
}

class _JackpotCountdownBlock extends StatelessWidget {
  const _JackpotCountdownBlock({
    required this.countdownStr,
    required this.balanceStr,
  });

  final String countdownStr;
  final String balanceStr;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const Text(
          'CURRENT JACKPOT ROUND POOL',
          style: TextStyle(
            color: kTextTertiary,
            fontSize: 11,
            fontWeight: FontWeight.w800,
            letterSpacing: 1.5,
            fontFamily: kFontCondensed,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          balanceStr,
          style: const TextStyle(
            color: kGoldLight,
            fontSize: 32,
            fontWeight: FontWeight.w900,
            letterSpacing: -1,
            fontFamily: kFontMono,
          ),
        ),
        const SizedBox(height: 14),
        const Text(
          'TIME TO NEXT SCHEDULED DROP',
          style: TextStyle(
            color: kPitchGreenBright,
            fontSize: 11,
            fontWeight: FontWeight.w800,
            letterSpacing: 1.2,
            fontFamily: kFontCondensed,
          ),
        ),
        const SizedBox(height: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          decoration: BoxDecoration(
            color: kNavyInset,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: kNavyLine),
          ),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                const Icon(Icons.timer_rounded, size: 18, color: kPitchGreenBright),
                const SizedBox(width: 8),
                Text(
                  countdownStr,
                  style: const TextStyle(
                    color: kTextPrimary,
                    fontSize: 22,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 2,
                    fontFamily: kFontMono,
                  ),
                ),
                const SizedBox(width: 8),
                const Text(
                  'UTC',
                  style: TextStyle(
                    color: kTextTertiary,
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _JackpotMechanicsBlock extends StatelessWidget {
  const _JackpotMechanicsBlock();

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: const <Widget>[
        Text(
          'THREE VERIFIED TRIGGER MECHANISMS',
          style: TextStyle(
            color: kGoldPrimary,
            fontSize: 11,
            fontWeight: FontWeight.w800,
            letterSpacing: 1.2,
            fontFamily: kFontCondensed,
          ),
        ),
        SizedBox(height: 8),
        _TriggerRow(
          title: '1. Threshold Trigger (500.00 GTC)',
          description: 'Automatically triggers payout the moment pool hits the verified threshold balance.',
          icon: Icons.trending_up_rounded,
        ),
        SizedBox(height: 6),
        _TriggerRow(
          title: '2. Probability Roll (Scales to 50% Cap)',
          description: 'Every match contribution rolls dynamic win chance capped at 50% maximum limit.',
          icon: Icons.casino_rounded,
        ),
        SizedBox(height: 6),
        _TriggerRow(
          title: '3. 6-Hour Failsafe (Guaranteed 4x Daily)',
          description: 'If neither threshold nor roll occurs, round triggers automatically every 6 hours.',
          icon: Icons.alarm_on_rounded,
        ),
      ],
    );
  }
}

class _TriggerRow extends StatelessWidget {
  const _TriggerRow({
    required this.title,
    required this.description,
    required this.icon,
  });

  final String title;
  final String description;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Icon(icon, size: 14, color: kGoldPrimary),
        const SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                title,
                style: const TextStyle(
                  color: kTextPrimary,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                ),
              ),
              Text(
                description,
                style: const TextStyle(
                  color: kTextTertiary,
                  fontSize: 11,
                  height: 1.3,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _TournamentCard extends StatelessWidget {
  const _TournamentCard({required this.comp});

  final ActiveCompetitionItem comp;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: kNavyRaised,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: kNavyLine),
      ),
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              GtexTagPill(label: comp.type, color: comp.accentColor),
              const Spacer(),
              GtexTagPill(
                label: comp.status,
                color: comp.accentColor,
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            comp.name,
            style: const TextStyle(
              color: kTextPrimary,
              fontSize: 17,
              fontWeight: FontWeight.w800,
              fontFamily: kFontCondensed,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            comp.format,
            style: const TextStyle(
              color: kTextSecondary,
              fontSize: 12,
            ),
          ),
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: kNavyInset,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: kNavyLine),
            ),
            child: const Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Icon(Icons.info_outline_rounded, size: 16, color: kGoldPrimary),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Format preview. Live entry status, prize pools and broadcast availability must come from the published event data.',
                    style: TextStyle(
                      color: kTextSecondary,
                      fontSize: 11,
                      height: 1.4,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
