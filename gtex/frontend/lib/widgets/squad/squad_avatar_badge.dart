import 'package:flutter/widgets.dart';

import '../../models/player_avatar.dart';
import '../player_card_avatar.dart';

class SquadAvatarBadge extends StatelessWidget {
  const SquadAvatarBadge({
    super.key,
    required this.avatar,
    this.size = 42,
    this.mode = AvatarMode.lineup,
  });

  final PlayerAvatar avatar;
  final double size;
  final AvatarMode mode;

  @override
  Widget build(BuildContext context) {
    return PlayerCardAvatar(avatar: avatar, size: size, mode: mode);
  }
}
