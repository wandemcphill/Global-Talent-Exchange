import 'package:flutter/material.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

class CompetitionVisibilityChip extends StatelessWidget {
  const CompetitionVisibilityChip({
    super.key,
    required this.visibility,
  });

  final CompetitionVisibility visibility;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: Chip(
        avatar: Icon(
          _iconFor(visibility),
          size: 18,
          color: GteShellTheme.textPrimary,
        ),
        label: Text(_labelFor(visibility)),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      ),
    );
  }

  IconData _iconFor(CompetitionVisibility value) {
    switch (value) {
      case CompetitionVisibility.private:
        return Icons.lock_outline;
      case CompetitionVisibility.inviteOnly:
        return Icons.key_outlined;
      case CompetitionVisibility.public:
        return Icons.public;
    }
  }

  String _labelFor(CompetitionVisibility value) {
    switch (value) {
      case CompetitionVisibility.private:
        return 'Private';
      case CompetitionVisibility.inviteOnly:
        return 'Invite only';
      case CompetitionVisibility.public:
        return 'Public';
    }
  }
}
