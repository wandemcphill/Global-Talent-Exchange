import 'package:flutter/material.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_item_dto.dart';
import 'package:gte_frontend/features/club_identity/trophies/widgets/major_honor_badge.dart';
import 'package:gte_frontend/widgets/gte_formatters.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

class TrophyTile extends StatelessWidget {
  const TrophyTile({
    super.key,
    required this.trophy,
    this.compact = false,
  });

  final TrophyItemDto trophy;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final bool highlight = trophy.isEliteHonor || trophy.isMajorHonor;
    return Container(
      width: compact ? 220 : null,
      padding: EdgeInsets.all(compact ? 14 : 18),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: trophy.isEliteHonor
              ? GteShellTheme.accentWarm.withValues(alpha: 0.65)
              : highlight
                  ? GteShellTheme.accent.withValues(alpha: 0.5)
                  : GteShellTheme.stroke,
        ),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            trophy.isEliteHonor
                ? const Color(0x26FFC76B)
                : highlight
                    ? const Color(0x167DE2D1)
                    : GteShellTheme.panelStrong.withValues(alpha: 0.88),
            GteShellTheme.panel.withValues(alpha: 0.92),
          ],
        ),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.2),
            blurRadius: 22,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              _TrophyEmblem(
                isEliteHonor: trophy.isEliteHonor,
                isMajorHonor: trophy.isMajorHonor,
                isAcademy: trophy.isAcademy,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      trophy.trophyName,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${trophy.competitionRegion} • ${_formatTier(trophy.competitionTier)}',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              if (trophy.isEliteHonor)
                const MajorHonorBadge(
                  label: 'Elite Honor',
                  style: MajorHonorBadgeStyle.elite,
                )
              else if (trophy.isMajorHonor)
                const MajorHonorBadge(label: 'Major Honor'),
              if (trophy.isAcademy)
                const MajorHonorBadge(
                  label: 'Academy',
                  style: MajorHonorBadgeStyle.academy,
                ),
              _MetaPill(label: trophy.seasonLabel),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            trophy.finalResultSummary,
            style: Theme.of(context).textTheme.bodyLarge,
          ),
          const SizedBox(height: 12),
          Text(
            gteFormatDateTime(trophy.earnedAt),
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          if (!compact &&
              (trophy.captainName != null ||
                  trophy.topPerformerName != null)) ...<Widget>[
            const SizedBox(height: 12),
            Wrap(
              spacing: 10,
              runSpacing: 8,
              children: <Widget>[
                if (trophy.captainName != null)
                  _MetaPill(label: 'Captain: ${trophy.captainName}'),
                if (trophy.topPerformerName != null)
                  _MetaPill(label: 'Top performer: ${trophy.topPerformerName}'),
              ],
            ),
          ],
        ],
      ),
    );
  }

  String _formatTier(String rawTier) {
    return rawTier.replaceAll('_', ' ').split(' ').map((String segment) {
      if (segment.isEmpty) {
        return segment;
      }
      return '${segment[0].toUpperCase()}${segment.substring(1)}';
    }).join(' ');
  }
}

class _TrophyEmblem extends StatelessWidget {
  const _TrophyEmblem({
    required this.isEliteHonor,
    required this.isMajorHonor,
    required this.isAcademy,
  });

  final bool isEliteHonor;
  final bool isMajorHonor;
  final bool isAcademy;

  @override
  Widget build(BuildContext context) {
    final Color tone = isEliteHonor
        ? GteShellTheme.accentWarm
        : isAcademy
            ? GteShellTheme.positive
            : isMajorHonor
                ? GteShellTheme.accent
                : GteShellTheme.textMuted;
    return Container(
      width: 48,
      height: 48,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: tone.withValues(alpha: 0.12),
        border: Border.all(color: tone.withValues(alpha: 0.5)),
      ),
      child: Icon(
        isEliteHonor
            ? Icons.workspace_premium
            : isAcademy
                ? Icons.school
                : Icons.emoji_events_outlined,
        color: tone,
      ),
    );
  }
}

class _MetaPill extends StatelessWidget {
  const _MetaPill({
    required this.label,
  });

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: GteShellTheme.panelStrong.withValues(alpha: 0.92),
        border: Border.all(color: GteShellTheme.stroke),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: GteShellTheme.textPrimary,
            ),
      ),
    );
  }
}
