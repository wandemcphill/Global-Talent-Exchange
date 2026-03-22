import 'package:flutter/widgets.dart';

import '../models/player_avatar.dart';
import 'player_avatar_widget.dart';

class PlayerCardAvatar extends StatelessWidget {
  const PlayerCardAvatar({
    super.key,
    required this.avatar,
    this.size = 56,
    this.mode = AvatarMode.card,
  });

  final PlayerAvatar avatar;
  final double size;
  final AvatarMode mode;

  @override
  Widget build(BuildContext context) {
    return PlayerAvatarWidget(
      avatar: avatar,
      size: size,
      mode: mode,
      withShadow: true,
    );
  }
}
