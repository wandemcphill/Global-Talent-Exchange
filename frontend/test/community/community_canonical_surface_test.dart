import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/community/community.dart';
import 'package:gte_frontend/models/community_models.dart';

void main() {
  testWidgets('community surface renders backend-backed scaffolds only', (
    WidgetTester tester,
  ) async {
    final DateTime now = DateTime.utc(2026, 6);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: CommunityCanonicalSurface(
            isAuthenticated: true,
            hasLiveToken: true,
            isLoading: false,
            isMutating: false,
            digest: const CommunityDigest(
              watchlistCount: 1,
              liveThreadCount: 1,
              privateThreadCount: 1,
              unreadHintCount: 3,
            ),
            watchlist: <CommunityWatchlistItem>[
              CommunityWatchlistItem(
                id: 'watch-1',
                competitionKey: 'cup-1',
                competitionTitle: 'Sunday Cup',
                competitionType: 'knockout',
                notifyOnStory: true,
                notifyOnLaunch: true,
                metadata: const <String, Object?>{},
                createdAt: now,
                updatedAt: now,
              ),
            ],
            liveThreads: <LiveThread>[
              LiveThread(
                id: 'thread-1',
                threadKey: 'cup-1:live',
                competitionKey: 'cup-1',
                title: 'Sunday Cup',
                createdByUserId: 'user-1',
                status: 'open',
                pinned: false,
                lastMessageAt: now,
                metadata: const <String, Object?>{},
                createdAt: now,
                updatedAt: now,
              ),
            ],
            privateThreads: <PrivateMessageThread>[
              PrivateMessageThread(
                id: 'private-1',
                threadKey: 'dm-1',
                createdByUserId: 'user-1',
                status: 'open',
                subject: 'Scout chat',
                lastMessageAt: now,
                metadata: const <String, Object?>{},
                createdAt: now,
                updatedAt: now,
                participants: const <PrivateMessageParticipant>[],
              ),
            ],
            currentClubId: 'club-1',
            currentClubName: 'Lagos Royals',
          ),
        ),
      ),
    );

    expect(find.text('Community canonical surface'), findsOneWidget);
    expect(find.text('Discussions'), findsOneWidget);
    expect(find.textContaining('cup-1:live'), findsOneWidget);
    expect(find.text('Chat'), findsOneWidget);
    expect(find.textContaining('Scout chat'), findsOneWidget);
    expect(find.text('Gifting'), findsOneWidget);
    expect(
      find.text(
        'BLOCKED: gift actions require backend gift ledger target and catalog payloads before settlement.',
      ),
      findsOneWidget,
    );
    expect(find.textContaining('No gift ledger payload'), findsOneWidget);
  });

  testWidgets('community gifting locks for public readers', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: CommunityCanonicalSurface(
            isAuthenticated: false,
            hasLiveToken: false,
            isLoading: false,
            isMutating: false,
            watchlist: <CommunityWatchlistItem>[],
            liveThreads: <LiveThread>[],
            privateThreads: <PrivateMessageThread>[],
          ),
        ),
      ),
    );

    expect(find.text('Role: '), findsOneWidget);
    expect(find.text('Public reader'), findsOneWidget);
    expect(
      find.text('BLOCKED: gift actions are locked for public readers.'),
      findsOneWidget,
    );
    expect(find.textContaining('community.gifting'), findsOneWidget);
  });
}
