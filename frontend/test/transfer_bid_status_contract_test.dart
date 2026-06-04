import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_exchange_models.dart';

void main() {
  test(
    'transfer status preserves canonical bid statuses without remapping',
    () {
      const List<String> statuses = <String>[
        'submitted',
        'pending',
        'counter',
        'accepted',
        'completed',
        'withdrawn',
        'rejected',
      ];

      for (final String status in statuses) {
        final GteTransferStatusView transferStatus =
            GteTransferStatusView.fromJson(<String, Object?>{
              'window_open': true,
              'eligible': true,
              'last_bid_status': status,
            });

        expect(transferStatus.lastBidStatus, status);
      }
    },
  );
}
