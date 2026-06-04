import 'package:flutter/widgets.dart';
import 'package:gte_frontend/models/player_avatar.dart';
import 'package:gte_frontend/widgets/player_card_avatar.dart';

class MatchHudAvatar extends StatelessWidget {
  const MatchHudAvatar({super.key, required this.avatar, this.size = 34});

  final PlayerAvatar avatar;
  final double size;

  @override
  Widget build(BuildContext context) {
    return PlayerCardAvatar(
      avatar: avatar,
      size: size,
      mode: AvatarMode.hudMinimal,
    );
  }
}
