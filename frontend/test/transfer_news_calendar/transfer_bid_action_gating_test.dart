import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/transfer_news_calendar/data/transfer_news_calendar_models.dart';

void main() {
  test('transfer bid actions are only available for active bid statuses', () {
    expect(isActionableTransferBidStatus('submitted'), isTrue);
    expect(isActionableTransferBidStatus('pending'), isTrue);
    expect(isActionableTransferBidStatus(' Submitted '), isTrue);
    expect(isActionableTransferBidStatus('PENDING'), isTrue);

    for (final String status in <String>[
      'counter',
      'accepted',
      'completed',
      'withdrawn',
      'rejected',
      'cancelled',
      '',
    ]) {
      expect(isActionableTransferBidStatus(status), isFalse);
    }
  });
}
