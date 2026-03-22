import 'package:flutter/widgets.dart';

import '../../models/player_avatar.dart';
import '../player_avatar_widget.dart';

class MatchHudAvatar extends StatelessWidget {
  const MatchHudAvatar({
    super.key,
    required this.avatar,
    this.size = 34,
  });

  final PlayerAvatar avatar;
  final double size;

  @override
  Widget build(BuildContext context) {
    return PlayerAvatarWidget(
      avatar: avatar,
      size: size,
      mode: AvatarMode.hudMinimal,
    );
  }
}
