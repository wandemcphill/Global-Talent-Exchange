import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

/// Empire club switcher — up to three controlling clubs, one active desk.
class GtexEmpireClubSwitcher extends StatelessWidget {
  const GtexEmpireClubSwitcher({
    super.key,
    required this.clubs,
    required this.activeClubId,
    required this.onActivate,
    this.busy = false,
    this.errorMessage,
    this.maxClubs = 3,
  });

  final List<GtexOwnedClubOption> clubs;
  final String activeClubId;
  final ValueChanged<GtexOwnedClubOption> onActivate;
  final bool busy;
  final String? errorMessage;
  final int maxClubs;

  @override
  Widget build(BuildContext context) {
    if (clubs.isEmpty) {
      return const SizedBox.shrink();
    }
    return GtexPanel(
      title: 'Empire clubs',
      subtitle: 'Controlling ownership cap $maxClubs. Switch the active desk.',
      accent: GtexColors.pitch,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          if (errorMessage != null) ...<Widget>[
            GtexErrorBanner(message: errorMessage!),
            const SizedBox(height: GtexSpacing.sm),
          ],
          Wrap(
            spacing: GtexSpacing.sm,
            runSpacing: GtexSpacing.sm,
            children:
                clubs.map((GtexOwnedClubOption club) {
                  final bool active = club.id == activeClubId;
                  return GtexActionButton(
                    label: club.name,
                    icon:
                        active
                            ? Icons.check_circle_outline
                            : Icons.shield_outlined,
                    accent: active ? GtexColors.mint : GtexColors.pitch,
                    secondary: !active,
                    onPressed:
                        busy || active ? null : () => onActivate(club),
                  );
                }).toList(growable: false),
          ),
          const SizedBox(height: GtexSpacing.xs),
          Text(
            '${clubs.length} / $maxClubs clubs under your control',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: GtexColors.textMuted,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class GtexOwnedClubOption {
  const GtexOwnedClubOption({
    required this.id,
    required this.name,
    this.slug,
  });

  final String id;
  final String name;
  final String? slug;

  factory GtexOwnedClubOption.fromJson(Object? value) {
    final Map<String, Object?> root =
        value is Map<String, Object?>
            ? value
            : value is Map
            ? Map<String, Object?>.from(value)
            : const <String, Object?>{};
    final Object? profileRaw = root['profile'] ?? root;
    final Map<String, Object?> profile =
        profileRaw is Map
            ? Map<String, Object?>.from(profileRaw)
            : const <String, Object?>{};
    final String id =
        (profile['id'] ?? profile['club_id'] ?? profile['clubId'] ?? '')
            .toString()
            .trim();
    final String name =
        (profile['club_name'] ??
                profile['clubName'] ??
                profile['name'] ??
                id)
            .toString()
            .trim();
    final String? slug =
        (profile['slug'] ?? profile['club_slug'] ?? profile['clubSlug'])
            ?.toString()
            .trim();
    return GtexOwnedClubOption(
      id: id,
      name: name.isEmpty ? id : name,
      slug: (slug == null || slug.isEmpty) ? null : slug,
    );
  }
}
