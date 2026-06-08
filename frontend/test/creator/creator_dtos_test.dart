import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/creator/creator.dart';
import 'package:gte_frontend/features/shell/domain/gtex_surface_state.dart';

void main() {
  test(
    'creator wallet balance is blocked when backend available balance is null',
    () {
      final CreatorWalletDto wallet =
          CreatorWalletDto.fromFinanceJson(const <String, Object?>{
            'currency': 'credits',
            'wallet_available_balance': null,
            'pending_withdrawals': 2,
          });

      expect(wallet.balance, isNull);
      expect(wallet.surfaceState, GtexSurfaceState.blocked);
      expect(wallet.canWithdraw(1), isFalse);
    },
  );

  test(
    'creator wallet parses canonical nested balance and withdrawal flag',
    () {
      final CreatorWalletDto wallet = CreatorWalletDto.fromFinanceJson(
        const <String, Object?>{
          'state': 'confirmed',
          'balance': <String, Object?>{
            'available': '75.50',
            'reserved': '4.25',
            'currency': 'credits',
          },
          'pending_settlements': 2,
          'withdrawal_available': true,
        },
      );

      expect(wallet.balance?.available, 75.5);
      expect(wallet.balance?.reserved, 4.25);
      expect(wallet.pendingSettlements, 2);
      expect(wallet.withdrawalAvailable, isTrue);
      expect(wallet.canWithdraw(25), isTrue);
    },
  );

  test('creator settlements and moderation keep partial backend truth', () {
    final SettlementDto settlement =
        SettlementDto.fromJson(const <String, Object?>{
          'id': 'settlement-1',
          'status': 'pending',
          'currency': 'credits',
          'amount': null,
          'degraded_reason': 'wallet transaction missing',
        });
    final ModerationInboxItemDto moderation =
        ModerationInboxItemDto.fromJson(const <String, Object?>{
          'id': 'clip:clip-1',
          'item_type': 'sponsored_clip',
          'item_id': 'clip-1',
          'status': 'degraded',
          'moderation_status': 'flagged',
          'note': 'Rights proof missing.',
        });

    expect(settlement.amount, isNull);
    expect(settlement.degradedReason, 'wallet transaction missing');
    expect(moderation.status, ClipModerationStatus.flagged);
    expect(moderation.reason, 'Rights proof missing.');
  });

  test('clip moderation states expose creator labels and actions', () {
    final Map<String, List<Object?>> expectations = <String, List<Object?>>{
      'pending': <Object?>[
        ClipModerationStatus.pending,
        'Under review',
        'No creator action available',
        GtexSurfaceState.pending,
      ],
      'approved': <Object?>[
        ClipModerationStatus.approved,
        'Live',
        'View analytics',
        GtexSurfaceState.confirmed,
      ],
      'flagged': <Object?>[
        ClipModerationStatus.flagged,
        'Flagged',
        'Respond',
        GtexSurfaceState.degraded,
      ],
      'rejected': <Object?>[
        ClipModerationStatus.rejected,
        'Rejected',
        'Appeal',
        GtexSurfaceState.blocked,
      ],
    };

    for (final MapEntry<String, List<Object?>> entry in expectations.entries) {
      final SponsoredClipDto clip = SponsoredClipDto.fromJson(<String, Object?>{
        'id': 'clip-${entry.key}',
        'campaign_id': 'campaign-1',
        'title': 'Clip ${entry.key}',
        'status': entry.key,
      });

      expect(clip.status, entry.value[0]);
      expect(clip.status.label, entry.value[1]);
      expect(clip.status.creatorActionLabel, entry.value[2]);
      expect(clip.status.surfaceState, entry.value[3]);
    }
  });

  test('major creator action requests carry audit refs', () {
    const CreateCampaignRequest campaign = CreateCampaignRequest(
      title: 'Launch Cup',
      brief: 'Sponsor the launch cup.',
      auditRef: 'audit-campaign-1',
    );
    const SubmitClipRequest clip = SubmitClipRequest(
      campaignId: 'campaign-1',
      title: 'Opening goal',
      url: 'https://clips.test/opening-goal.mp4',
      auditRef: 'audit-clip-1',
    );
    const CreatorWithdrawalRequest withdrawal = CreatorWithdrawalRequest(
      amount: 25,
      currency: 'credits',
      method: 'bank_transfer',
      auditRef: 'audit-withdrawal-1',
    );

    expect(campaign.toJson()['audit_ref'], 'audit-campaign-1');
    expect(campaign.toJson()['audit_event'], 'creator.campaign.created');
    expect(clip.toJson()['audit_ref'], 'audit-clip-1');
    expect(clip.toJson()['audit_event'], 'creator.clip.submitted');
    expect(withdrawal.toJson()['audit_ref'], 'audit-withdrawal-1');
    expect(withdrawal.toJson()['audit_event'], 'creator.withdrawal.requested');
  });
}
