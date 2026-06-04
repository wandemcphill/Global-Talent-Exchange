import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/screens/admin/admin_command_center_screen.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  late http.Client Function() previousClientFactory;

  setUp(() {
    previousClientFactory = GteHttpTransport.clientFactory;
  });

  tearDown(() {
    GteHttpTransport.clientFactory = previousClientFactory;
  });

  testWidgets(
    'admin command center renders canonical live queue rows and blocked states',
    (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1800, 5200);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      _installAdminCommandCenterMockClient();
      await _pumpAdminCommandCenter(tester);

      expect(find.text('Command queues'), findsOneWidget);
      expect(find.text('Payment Review Queue'), findsOneWidget);
      expect(find.text('Pending (2)'), findsOneWidget);
      expect(find.text('Approved (1)'), findsOneWidget);
      expect(find.text('Rejected (1)'), findsOneWidget);
      expect(find.text('Bids (1)'), findsOneWidget);
      expect(find.text('Payment proofs'), findsWidgets);
      expect(find.text('Manual bank-transfer proof'), findsWidgets);
      expect(find.textContaining('Actor: Ada Finance'), findsWidgets);
      expect(find.textContaining('Severity: High'), findsWidgets);
      expect(find.textContaining('Severity: Critical'), findsWidgets);
      expect(find.text('Audit trail'), findsWidgets);
      expect(find.text('Notes'), findsWidgets);
      expect(find.text('Dispute review required'), findsWidgets);
      expect(find.text('Approve'), findsWidgets);
      expect(find.text('Reject'), findsWidgets);
      expect(find.text('Export visible'), findsOneWidget);
      expect(find.text('Lock selected'), findsOneWidget);
      expect(find.text('Open settlements'), findsOneWidget);
      expect(find.text('3 open fraud cases'), findsOneWidget);
      _expectNoForbiddenAdminPaymentText();

      final Finder pendingDepositRow =
          find
              .ancestor(
                of: find.textContaining('Ref DEP-001'),
                matching: find.byType(GteSurfacePanel),
              )
              .first;
      final Finder disputedDepositRow =
          find
              .ancestor(
                of: find.textContaining('Ref DEP-DISPUTED'),
                matching: find.byType(GteSurfacePanel),
              )
              .first;
      expect(
        find.descendant(
          of: disputedDepositRow,
          matching: find.text('Dispute review required'),
        ),
        findsOneWidget,
      );
      expect(
        find.descendant(
          of: disputedDepositRow,
          matching: find.widgetWithText(FilledButton, 'Approve'),
        ),
        findsNothing,
      );
      expect(
        find.descendant(
          of: disputedDepositRow,
          matching: find.widgetWithText(OutlinedButton, 'Reject'),
        ),
        findsNothing,
      );
      expect(
        find.descendant(
          of: pendingDepositRow,
          matching: find.text('Severity: High'),
        ),
        findsOneWidget,
      );
      expect(
        find.descendant(
          of: pendingDepositRow,
          matching: find.text('Escalation: Watching'),
        ),
        findsOneWidget,
      );
      expect(
        find.descendant(
          of: pendingDepositRow,
          matching: find.text('Audit reference: deposit:dep-1'),
        ),
        findsWidgets,
      );
      expect(
        find.descendant(of: pendingDepositRow, matching: find.text('Notes')),
        findsOneWidget,
      );

      await tester.tap(
        find.descendant(
          of: pendingDepositRow,
          matching: find.widgetWithText(FilledButton, 'Approve'),
        ),
      );
      await tester.pumpAndSettle();
      await _expectRequiredNotesGate(
        tester,
        dialogTitle: 'Confirm deposit payment',
        confirmLabel: 'Confirm payment',
      );

      await tester.tap(
        find.descendant(
          of: pendingDepositRow,
          matching: find.widgetWithText(OutlinedButton, 'Reject'),
        ),
      );
      await tester.pumpAndSettle();
      await _expectRequiredNotesGate(
        tester,
        dialogTitle: 'Reject deposit',
        confirmLabel: 'Reject deposit',
      );

      await tester.tap(find.text('Approved (1)'));
      await tester.pumpAndSettle();
      expect(find.textContaining('DEP-APPROVED'), findsWidgets);
      expect(find.text('Confirmed'), findsWidgets);

      await tester.tap(find.text('Rejected (1)'));
      await tester.pumpAndSettle();
      expect(find.textContaining('DEP-REJECTED'), findsWidgets);
      expect(find.text('Reinstate'), findsOneWidget);
      await tester.tap(find.text('Reinstate'));
      await tester.pumpAndSettle();
      await _expectRequiredNotesGate(
        tester,
        dialogTitle: 'Reinstate rejected deposit',
        confirmLabel: 'Reinstate',
      );
    },
  );

  testWidgets('admin command center renders backend transfer bid reservations', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1800, 3200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final List<http.Request> bidActionRequests = <http.Request>[];
    _installAdminCommandCenterMockClient(recordedRequests: bidActionRequests);
    await _pumpAdminCommandCenter(tester);

    expect(find.text('Bids (1)'), findsOneWidget);
    await tester.tap(find.text('Bids (1)'));
    await _pumpUntilFound(tester, find.textContaining('Transfer bid bid-1'));

    expect(find.textContaining('Transfer bid bid-1'), findsOneWidget);
    expect(find.text('Reserved 500000 GTEX Coin'), findsOneWidget);
    expect(
      find.textContaining('Reservation reference: bid-reservation-1'),
      findsOneWidget,
    );
    expect(find.text('Audit-only bid actions'), findsOneWidget);
    expect(find.text('Audit approve'), findsOneWidget);
    expect(find.text('Audit reject'), findsOneWidget);
    expect(find.text('Audit counter'), findsOneWidget);
    expect(find.text('No bid audit actions exposed'), findsNothing);
    _expectNoForbiddenAdminPaymentText();

    final Finder bidRow =
        find
            .ancestor(
              of: find.textContaining('Transfer bid bid-1'),
              matching: find.byType(GteSurfacePanel),
            )
            .first;
    expect(
      find.descendant(of: bidRow, matching: find.text('Severity: Medium')),
      findsOneWidget,
    );
    expect(
      find.descendant(of: bidRow, matching: find.text('Escalation: Watching')),
      findsOneWidget,
    );
    expect(
      find.descendant(of: bidRow, matching: find.text('Audit trail')),
      findsOneWidget,
    );
    expect(
      find.descendant(
        of: bidRow,
        matching: find.text('Reservation locked by wallet ledger.'),
      ),
      findsOneWidget,
    );

    await tester.tap(find.text('Audit approve'));
    await tester.pumpAndSettle();
    await _expectRequiredNotesGate(
      tester,
      dialogTitle: 'Audit approve transfer bid',
      confirmLabel: 'Audit approve',
    );

    await tester.tap(find.text('Audit counter'));
    await tester.pumpAndSettle();
    await _submitRequiredNotesAction(
      tester,
      dialogTitle: 'Audit counter transfer bid',
      confirmLabel: 'Audit counter',
      notes: 'Counter terms reviewed by finance ops.',
    );
    expect(bidActionRequests, hasLength(1));
    expect(
      bidActionRequests.single.url.path,
      '/api/v2/admin/finance/payment-queue/bids/windows/window-1/bids/bid-1/counter',
    );
    expect(jsonDecode(bidActionRequests.single.body), <String, Object?>{
      'admin_notes': 'Counter terms reviewed by finance ops.',
    });
  });

  testWidgets(
    'admin payment queue blocks when deposit endpoint is unavailable',
    (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1800, 2600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      _installAdminCommandCenterMockClient(
        blockedPaths: const <String>{'/api/v2/admin/finance/payment-queue'},
      );
      await _pumpAdminCommandCenter(
        tester,
        waitFor: find.text('Pending (blocked)'),
      );

      expect(find.text('Pending (blocked)'), findsOneWidget);
      expect(find.text('Payment queue unavailable'), findsOneWidget);
      expect(find.text('Queue clear'), findsNothing);
      expect(find.text('Manual bank-transfer proof'), findsNothing);
    },
  );

  testWidgets(
    'admin payment queue clears stale rows after backend refresh failure',
    (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1800, 4200);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final Set<String> blockedPaths = <String>{};
      _installAdminCommandCenterMockClient(blockedPaths: blockedPaths);
      await _pumpAdminCommandCenter(tester);

      expect(find.text('Pending (2)'), findsOneWidget);
      expect(find.text('Bids (1)'), findsOneWidget);
      expect(find.text('Manual bank-transfer proof'), findsWidgets);

      blockedPaths.add('/api/v2/admin/finance/payment-queue');
      await tester.tap(find.text('Refresh data'));
      await _pumpUntilFound(tester, find.text('Pending (blocked)'));

      expect(find.text('Pending (blocked)'), findsOneWidget);
      expect(find.text('Bids blocked'), findsOneWidget);
      expect(find.text('Payment queue unavailable'), findsOneWidget);
      expect(find.text('Bids (1)'), findsNothing);
      expect(find.text('Manual bank-transfer proof'), findsNothing);
    },
  );
}

void _installAdminCommandCenterMockClient({
  Set<String> blockedPaths = const <String>{},
  List<http.Request>? recordedRequests,
}) {
  GteHttpTransport.clientFactory =
      () => MockClient((http.Request request) async {
        if (request.method == 'POST' &&
            request.url.path.startsWith(
              '/api/v2/admin/finance/payment-queue/bids/windows/',
            )) {
          final Map<String, Object?> body = Map<String, Object?>.from(
            jsonDecode(request.body) as Map,
          );
          if ((body['admin_notes']?.toString().trim() ?? '').isEmpty) {
            return http.Response(
              jsonEncode(<String, Object?>{
                'detail': 'admin_notes is required',
              }),
              400,
            );
          }
          recordedRequests?.add(request);
          return http.Response(
            jsonEncode(<String, Object?>{
              'status': 'audit_recorded',
              'reference': 'transfer-bid:bid-1',
            }),
            200,
          );
        }
        if (blockedPaths.contains(request.url.path)) {
          return http.Response(
            jsonEncode(<String, Object?>{
              'detail': 'Blocked test route ${request.url.path}',
            }),
            404,
          );
        }
        final Object? payload = _payloadFor(request.url.path);
        if (payload == null) {
          return http.Response(
            jsonEncode(<String, Object?>{
              'detail': 'No mocked response for ${request.url.path}',
            }),
            404,
          );
        }
        return http.Response(jsonEncode(payload), 200);
      });
}

Future<void> _pumpAdminCommandCenter(
  WidgetTester tester, {
  Finder? waitFor,
}) async {
  await tester.pumpWidget(
    const MaterialApp(
      home: AdminCommandCenterScreen(
        baseUrl: 'http://gtex.test',
        accessToken: 'admin-token',
        backendMode: GteBackendMode.live,
      ),
    ),
  );
  await _pumpUntilFound(tester, waitFor ?? find.text('Bids (1)'));
}

Future<void> _pumpUntilFound(
  WidgetTester tester,
  Finder finder, {
  int maxPumps = 80,
  Duration step = const Duration(milliseconds: 100),
}) async {
  for (int index = 0; index < maxPumps; index += 1) {
    await tester.pump(step);
    if (finder.evaluate().isNotEmpty) {
      return;
    }
  }
  fail('Timed out waiting for $finder');
}

Future<void> _expectRequiredNotesGate(
  WidgetTester tester, {
  required String dialogTitle,
  required String confirmLabel,
}) async {
  expect(find.text(dialogTitle), findsWidgets);
  expect(find.text('Required for auditable action'), findsOneWidget);
  final Finder notesField = find.byWidgetPredicate(
    (Widget widget) =>
        widget is TextField && widget.decoration?.labelText == 'Admin notes',
  );

  FilledButton confirmButton = tester.widget<FilledButton>(
    find.widgetWithText(FilledButton, confirmLabel).last,
  );
  expect(confirmButton.onPressed, isNull);

  await tester.enterText(notesField, '   ');
  await tester.pump();
  confirmButton = tester.widget<FilledButton>(
    find.widgetWithText(FilledButton, confirmLabel).last,
  );
  expect(confirmButton.onPressed, isNull);

  await tester.enterText(notesField, 'Verified audit note.');
  await tester.pump();
  confirmButton = tester.widget<FilledButton>(
    find.widgetWithText(FilledButton, confirmLabel).last,
  );
  expect(confirmButton.onPressed, isNotNull);

  await tester.tap(find.text('Cancel'));
  await tester.pumpAndSettle();
}

Future<void> _submitRequiredNotesAction(
  WidgetTester tester, {
  required String dialogTitle,
  required String confirmLabel,
  required String notes,
}) async {
  expect(find.text(dialogTitle), findsWidgets);
  final Finder notesField = find.byWidgetPredicate(
    (Widget widget) =>
        widget is TextField && widget.decoration?.labelText == 'Admin notes',
  );
  await tester.enterText(notesField, notes);
  await tester.pump();
  final FilledButton confirmButton = tester.widget<FilledButton>(
    find.widgetWithText(FilledButton, confirmLabel).last,
  );
  expect(confirmButton.onPressed, isNotNull);
  await tester.tap(find.widgetWithText(FilledButton, confirmLabel).last);
  await tester.pumpAndSettle();
}

void _expectNoForbiddenAdminPaymentText() {
  final RegExp forbidden = RegExp(
    r'(Paystack|Unity|native\s+3D|Flutter\s+3D|pseudo[-\s]?3D)',
    caseSensitive: false,
  );
  expect(find.textContaining(forbidden), findsNothing);
}

Object? _payloadFor(String path) {
  switch (path) {
    case '/api/v2/admin/treasury/settings':
      return <String, Object?>{
        'id': 'settings-1',
        'settings_key': 'default',
        'currency_code': 'NGN',
        'deposit_rate_value': 1.0,
        'deposit_rate_direction': 'fiat_per_coin',
        'withdrawal_rate_value': 1.0,
        'withdrawal_rate_direction': 'fiat_per_coin',
        'min_deposit': 100,
        'max_deposit': 100000,
        'min_withdrawal': 50,
        'max_withdrawal': 50000,
        'deposit_mode': 'manual',
        'withdrawal_mode': 'manual',
        'maintenance_message': null,
        'whatsapp_number': '+2348000000000',
        'active_bank_account': _bankAccount(),
      };
    case '/api/v2/admin/treasury/bank-accounts':
      return <Object?>[_bankAccount()];
    case '/api/v2/admin/finance/payment-queue':
      return _paymentQueue(
        <Object?>[
          <String, Object?>{
            'id': 'dep-1',
            'reference': 'DEP-001',
            'status': 'payment_submitted',
            'amount_fiat': 25000,
            'amount_coin': 250,
            'currency_code': 'NGN',
            'payer_name': 'Ada Finance',
            'sender_bank': 'GTEX Bank',
            'transfer_reference': 'TRF-123',
            'created_at': '2026-05-28T09:00:00Z',
            'submitted_at': '2026-05-28T09:05:00Z',
            'reviewed_at': null,
            'confirmed_at': null,
            'rejected_at': null,
            'admin_notes': 'Proof waiting for reviewer.',
            'user_id': 'user-1',
            'user_email': 'ada@gtex.test',
            'user_full_name': 'Ada Finance',
            'user_phone_number': '+2348011111111',
          },
          <String, Object?>{
            'id': 'dep-approved',
            'reference': 'DEP-APPROVED',
            'status': 'confirmed',
            'amount_fiat': 15000,
            'amount_coin': 150,
            'currency_code': 'NGN',
            'payer_name': 'Bola Owner',
            'sender_bank': 'GTEX Bank',
            'transfer_reference': 'TRF-APPROVED',
            'created_at': '2026-05-28T07:00:00Z',
            'submitted_at': '2026-05-28T07:05:00Z',
            'reviewed_at': '2026-05-28T07:15:00Z',
            'confirmed_at': '2026-05-28T07:20:00Z',
            'rejected_at': null,
            'admin_notes': 'Matched against bank statement.',
            'user_id': 'user-2',
            'user_email': 'bola@gtex.test',
            'user_full_name': 'Bola Owner',
            'user_phone_number': '+2348033333333',
          },
          <String, Object?>{
            'id': 'dep-disputed',
            'reference': 'DEP-DISPUTED',
            'status': 'disputed',
            'amount_fiat': 11000,
            'amount_coin': 110,
            'currency_code': 'NGN',
            'payer_name': 'Dayo Supporter',
            'sender_bank': 'GTEX Bank',
            'transfer_reference': 'TRF-DISPUTED',
            'created_at': '2026-05-28T06:30:00Z',
            'submitted_at': '2026-05-28T06:35:00Z',
            'reviewed_at': null,
            'confirmed_at': null,
            'rejected_at': null,
            'admin_notes': 'User opened dispute after proof mismatch.',
            'user_id': 'user-4',
            'user_email': 'dayo@gtex.test',
            'user_full_name': 'Dayo Supporter',
            'user_phone_number': '+2348055555555',
          },
          <String, Object?>{
            'id': 'dep-rejected',
            'reference': 'DEP-REJECTED',
            'status': 'rejected',
            'amount_fiat': 9000,
            'amount_coin': 90,
            'currency_code': 'NGN',
            'payer_name': 'Chika Scout',
            'sender_bank': 'Unknown Bank',
            'transfer_reference': 'TRF-REJECTED',
            'created_at': '2026-05-28T06:00:00Z',
            'submitted_at': '2026-05-28T06:05:00Z',
            'reviewed_at': '2026-05-28T06:15:00Z',
            'confirmed_at': null,
            'rejected_at': '2026-05-28T06:20:00Z',
            'admin_notes': 'Proof amount mismatch.',
            'user_id': 'user-3',
            'user_email': 'chika@gtex.test',
            'user_full_name': 'Chika Scout',
            'user_phone_number': '+2348044444444',
          },
        ],
        bids: <Object?>[_paymentQueueBid()],
      );
    case '/api/v2/admin/treasury/withdrawals':
      return _queue(<Object?>[
        <String, Object?>{
          'id': 'wd-1',
          'reference': 'WD-001',
          'status': 'pending_review',
          'amount_coin': 120,
          'amount_fiat': 12000,
          'currency_code': 'NGN',
          'bank_name': 'GTEX Bank',
          'bank_account_number': '0001112223',
          'bank_account_name': 'Ada Finance',
          'created_at': '2026-05-28T10:00:00Z',
          'reviewed_at': null,
          'approved_at': null,
          'processed_at': null,
          'paid_at': null,
          'rejected_at': null,
          'cancelled_at': null,
          'user_id': 'user-1',
          'user_email': 'ada@gtex.test',
          'user_full_name': 'Ada Finance',
          'user_phone_number': '+2348011111111',
        },
      ]);
    case '/api/v2/admin/treasury/kyc':
      return _queue(<Object?>[
        <String, Object?>{
          'id': 'kyc-1',
          'user_id': 'trader-1',
          'status': 'pending',
          'nin': null,
          'bvn': null,
          'address_line1': '1 Lagos Road',
          'city': 'Lagos',
          'state': 'Lagos',
          'country': 'NG',
          'submitted_at': '2026-05-28T08:00:00Z',
          'reviewed_at': null,
          'rejection_reason': null,
          'user_email': 'trader@gtex.test',
          'user_full_name': 'Trader One',
          'user_phone_number': '+2348022222222',
        },
      ]);
    case '/api/v2/admin/treasury/disputes':
      return _queue(<Object?>[
        <String, Object?>{
          'id': 'dispute-1',
          'status': 'awaiting_admin',
          'reference': 'DSP-001',
          'resource_type': 'deposit',
          'resource_id': 'dep-1',
          'subject': 'Proof mismatch',
          'created_at': '2026-05-28T07:00:00Z',
          'updated_at': '2026-05-28T07:30:00Z',
          'last_message_at': '2026-05-28T07:30:00Z',
          'user_id': 'user-1',
          'user_email': 'ada@gtex.test',
          'user_full_name': 'Ada Finance',
          'user_phone_number': '+2348011111111',
          'messages': const <Object?>[],
        },
      ]);
    case '/api/v2/admin/moderation/reports':
      return <Object?>[
        <String, Object?>{
          'id': 'mod-1',
          'reporter_user_id': 'reporter-1',
          'subject_user_id': 'subject-1',
          'target_type': 'message',
          'target_id': 'msg-1',
          'reason_code': 'abuse',
          'description': 'Abuse in match chat.',
          'evidence_url': null,
          'status': 'open',
          'priority': 'high',
          'assigned_admin_user_id': null,
          'resolution_action': 'none',
          'resolution_note': null,
          'resolved_by_user_id': null,
          'report_count_for_target': 2,
          'created_at': '2026-05-28T06:00:00Z',
          'updated_at': '2026-05-28T06:10:00Z',
        },
      ];
    case '/api/v2/admin/creator/applications':
      return <Object?>[
        <String, Object?>{
          'application_id': 'creator-app-1',
          'user_id': 'creator-1',
          'requested_handle': 'creator-one',
          'display_name': 'Creator One',
          'platform': 'youtube',
          'follower_count': 12000,
          'social_links': const <Object?>['https://creator.test'],
          'email_verified_at': '2026-05-28T05:00:00Z',
          'phone_verified_at': null,
          'status': 'pending',
          'review_notes': null,
          'decision_reason': null,
          'reviewed_by_user_id': null,
          'reviewed_at': null,
          'verification_requested_at': null,
          'approved_at': null,
          'rejected_at': null,
          'created_at': '2026-05-28T04:00:00Z',
          'updated_at': '2026-05-28T04:30:00Z',
          'provisioning': null,
        },
      ];
    case '/api/v2/admin/risk-ops/overview':
      return <String, Object?>{
        'open_aml_cases': 1,
        'open_fraud_cases': 3,
        'open_system_events': 2,
        'high_risk_users': 1,
        'active_scans': 1,
        'last_scan_summary': 'Manual review required.',
      };
    case '/api/v2/admin/god-mode/payment-rails':
      return <String, Object?>{
        'rails': <Object?>[
          <String, Object?>{
            'provider': 'korapay',
            'deposits_enabled': true,
            'withdrawals_enabled': false,
            'is_live': true,
            'maintenance_message': null,
            'updated_at': '2026-05-28T03:00:00Z',
            'updated_by': 'admin-1',
          },
        ],
        'reason': 'test',
      };
    case '/api/v2/admin/god-mode/withdrawal-controls':
      return <String, Object?>{
        'egame_withdrawals_enabled': true,
        'trade_withdrawals_enabled': true,
        'processor_mode': 'manual_bank_transfer',
        'deposits_via_bank_transfer': true,
        'payouts_via_bank_transfer': true,
        'updated_at': '2026-05-28T03:00:00Z',
        'updated_by': 'admin-1',
        'reason': 'test',
      };
  }
  return null;
}

Map<String, Object?> _paymentQueue(
  List<Object?> deposits, {
  List<Object?> bids = const <Object?>[],
}) {
  final Map<String, List<Object?>> buckets = <String, List<Object?>>{
    'pending': <Object?>[],
    'approved': <Object?>[],
    'rejected': <Object?>[],
  };
  for (final Object? deposit in deposits) {
    final Map<String, Object?> item = Map<String, Object?>.from(deposit as Map);
    final String queue = switch (item['status']?.toString()) {
      'confirmed' => 'approved',
      'rejected' => 'rejected',
      _ => 'pending',
    };
    buckets[queue]!.add(_paymentQueueDeposit(item, queue));
  }
  final Map<String, Object?> pending = _paymentQueueSection(
    key: 'pending',
    label: 'Pending',
    items: buckets['pending']!,
  );
  final Map<String, Object?> approved = _paymentQueueSection(
    key: 'approved',
    label: 'Approved',
    items: buckets['approved']!,
  );
  final Map<String, Object?> rejected = _paymentQueueSection(
    key: 'rejected',
    label: 'Rejected',
    items: buckets['rejected']!,
  );
  final Map<String, Object?> bidSection = _paymentQueueSection(
    key: 'bids',
    label: 'Bids',
    items: bids,
    actionState: 'audit_only',
  );
  return <String, Object?>{
    'generated_at': '2026-05-28T10:00:00Z',
    'tabs': <Object?>[
      _paymentQueueTab('pending', 'Pending', buckets['pending']!.length),
      _paymentQueueTab('approved', 'Approved', buckets['approved']!.length),
      _paymentQueueTab('rejected', 'Rejected', buckets['rejected']!.length),
      _paymentQueueTab('bids', 'Bids', bids.length, actionState: 'audit_only'),
    ],
    'sections': <String, Object?>{
      'pending': pending,
      'approved': approved,
      'rejected': rejected,
      'bids': bidSection,
    },
    'pending': pending,
    'approved': approved,
    'rejected': rejected,
    'bids': bidSection,
  };
}

Map<String, Object?> _paymentQueueSection({
  required String key,
  required String label,
  required List<Object?> items,
  String actionState = 'enabled',
}) {
  return <String, Object?>{
    'key': key,
    'label': label,
    'item_type': key == 'bids' ? 'transfer_bid' : 'deposit',
    'statuses': const <Object?>[],
    'items': items,
    'total': items.length,
    'limit': 20,
    'offset': 0,
    'action_state': actionState,
  };
}

Map<String, Object?> _paymentQueueTab(
  String key,
  String label,
  int total, {
  String actionState = 'enabled',
}) {
  return <String, Object?>{
    'key': key,
    'label': label,
    'total': total,
    'action_state': actionState,
  };
}

Map<String, Object?> _paymentQueueBid() {
  return <String, Object?>{
    'id': 'bid-1',
    'window_id': 'window-1',
    'window_label': 'Nigeria summer window',
    'player_id': 'player-1',
    'selling_club_id': 'club-seller',
    'buying_club_id': 'club-buyer',
    'status': 'submitted',
    'bid_amount': '500000',
    'wage_offer_amount': '12000',
    'sell_on_clause_pct': '10',
    'wallet_reservation_status': 'reserved',
    'wallet_reserved_amount': '500000',
    'wallet_reservation_reference': 'bid-reservation-1',
    'structured_terms_json': <String, Object?>{
      'wallet_reservation': <String, Object?>{
        'status': 'reserved',
        'amount_gtex_coin': '500000',
        'reference': 'bid-reservation-1',
      },
    },
    'severity': 'medium',
    'escalation_state': 'watching',
    'audit_reference': 'transfer-bid:bid-1',
    'audit_trail': const <Object?>['Reservation locked by wallet ledger.'],
    'action_state': 'audit_only',
    'business_action_state': 'audit_only',
    'available_actions': const <Object?>['approve', 'reject', 'counter'],
    'action_endpoints': <String, Object?>{
      'approve':
          '/api/admin/finance/payment-queue/bids/windows/window-1/bids/bid-1/approve',
      'reject':
          '/api/admin/finance/payment-queue/bids/windows/window-1/bids/bid-1/reject',
      'counter':
          '/api/admin/finance/payment-queue/bids/windows/window-1/bids/bid-1/counter',
    },
    'notes': 'Waiting for auditable reservation review.',
    'updated_at': '2026-05-28T02:10:00Z',
    'type': 'transfer_bid',
    'queue': 'bids',
  };
}

Map<String, Object?> _paymentQueueDeposit(
  Map<String, Object?> item,
  String queue,
) {
  final String id = item['id'].toString();
  final List<String> actions = switch (queue) {
    'pending' when item['status'] == 'disputed' => <String>['review'],
    'pending' => <String>['review', 'approve', 'reject'],
    'rejected' => <String>['reinstate'],
    _ => <String>[],
  };
  return <String, Object?>{
    ...item,
    'type': 'deposit',
    'queue': queue,
    'audit_reference': 'deposit:$id',
    'available_actions': actions,
    'action_endpoints': <String, Object?>{
      for (final String action in actions)
        action: '/api/admin/finance/payment-queue/deposits/$id/$action',
    },
  };
}

Map<String, Object?> _queue(List<Object?> items) {
  return <String, Object?>{
    'items': items,
    'total': items.length,
    'limit': 20,
    'offset': 0,
  };
}

Map<String, Object?> _bankAccount() {
  return <String, Object?>{
    'id': 'bank-1',
    'currency_code': 'NGN',
    'bank_name': 'GTEX Bank',
    'account_number': '0001112223',
    'account_name': 'GTEX Treasury',
    'bank_code': '999',
    'is_active': true,
    'created_at': '2026-05-28T00:00:00Z',
    'updated_at': '2026-05-28T00:00:00Z',
  };
}
