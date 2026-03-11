import 'package:flutter/material.dart';

import '../providers/gte_mock_api.dart';

class GtePlayerActionRow extends StatelessWidget {
  const GtePlayerActionRow({
    super.key,
    required this.player,
    required this.onFollow,
    required this.onWatchlist,
    required this.onShortlist,
    required this.onTransferRoom,
    required this.onIntensity,
  });

  final PlayerSnapshot player;
  final VoidCallback onFollow;
  final VoidCallback onWatchlist;
  final VoidCallback onShortlist;
  final VoidCallback onTransferRoom;
  final VoidCallback onIntensity;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: <Widget>[
        FilledButton.tonal(
          onPressed: onFollow,
          child: Text(player.isFollowed ? 'Following' : 'Follow'),
        ),
        FilledButton.tonal(
          onPressed: onWatchlist,
          child: Text(player.isWatchlisted ? 'Watchlisted' : 'Watchlist'),
        ),
        FilledButton.tonal(
          onPressed: onShortlist,
          child: Text(player.isShortlisted ? 'Shortlisted' : 'Shortlist'),
        ),
        FilledButton.tonal(
          onPressed: onTransferRoom,
          child: Text(player.inTransferRoom ? 'In Transfer Room' : 'Transfer Room'),
        ),
        OutlinedButton(
          onPressed: onIntensity,
          child: Text(_labelForIntensity(player.notificationIntensity)),
        ),
      ],
    );
  }
}

String _labelForIntensity(NotificationIntensity intensity) {
  switch (intensity) {
    case NotificationIntensity.light:
      return 'Alerts: Light';
    case NotificationIntensity.standard:
      return 'Alerts: Standard';
    case NotificationIntensity.scoutMode:
      return 'Alerts: Scout';
  }
}
