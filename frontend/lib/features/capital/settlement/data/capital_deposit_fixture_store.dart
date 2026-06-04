import 'dart:math' as math;

import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/capital/settlement/data/capital_treasury_fixture_store.dart';
import 'package:gte_frontend/features/capital/wallet/data/capital_wallet_fixture_store.dart';

class CapitalDepositFixtureStore {
  CapitalDepositFixtureStore.seeded({
    required CapitalWalletFixtureStore wallet,
    required CapitalTreasuryFixtureStore treasury,
  }) : _wallet = wallet,
       _treasury = treasury,
       depositRequests = List<GteDepositRequest>.of(
         seedDeposits,
         growable: true,
       ),
       depositSequence = seedDeposits.length;

  final CapitalWalletFixtureStore _wallet;
  final CapitalTreasuryFixtureStore _treasury;
  final List<GteDepositRequest> depositRequests;
  int depositSequence;

  int get pendingDepositCount =>
      depositRequests.where(_isPendingDeposit).length;

  double get pendingDepositAmount => depositRequests
      .where(_isPendingDeposit)
      .fold<double>(0, (double sum, GteDepositRequest deposit) {
        return sum + deposit.amountCoin;
      });

  List<GteDepositRequest> listDepositRequests() =>
      List<GteDepositRequest>.of(depositRequests, growable: false);

  GteDepositRequest createDepositRequest({
    required GteDepositCreateRequest request,
    required DateTime createdAt,
  }) {
    final GteTreasurySettings settings = _treasury.settings;
    final GteTreasuryBankAccount bank = _treasury.activeBankAccount;
    final double rateValue = settings.depositRateValue;
    final bool fiatPerCoin =
        settings.depositRateDirection == GteRateDirection.fiatPerCoin;
    double amountFiat = 0;
    double amountCoin = 0;
    if (request.inputUnit == 'coin') {
      amountCoin = request.amount;
      amountFiat =
          fiatPerCoin
              ? request.amount * rateValue
              : request.amount / math.max(rateValue, 0.0001);
    } else {
      amountFiat = request.amount;
      amountCoin =
          fiatPerCoin
              ? request.amount / math.max(rateValue, 0.0001)
              : request.amount * rateValue;
    }
    final String reference = 'DEP-${++depositSequence}';
    final GteDepositRequest deposit = GteDepositRequest(
      id: 'deposit-$depositSequence',
      reference: reference,
      status: GteDepositStatus.awaitingPayment,
      amountFiat: amountFiat,
      amountCoin: amountCoin,
      currencyCode: settings.currencyCode,
      rateValue: rateValue,
      rateDirection: settings.depositRateDirection,
      bankName: bank.bankName,
      bankAccountNumber: bank.accountNumber,
      bankAccountName: bank.accountName,
      bankCode: bank.bankCode,
      payerName: null,
      senderBank: null,
      transferReference: null,
      proofAttachmentId: null,
      adminNotes: null,
      createdAt: createdAt,
      submittedAt: null,
      reviewedAt: null,
      confirmedAt: null,
      rejectedAt: null,
      expiresAt: null,
    );
    depositRequests.insert(0, deposit);
    return deposit;
  }

  GteDepositRequest submitDepositRequest({
    required String depositId,
    required GteDepositSubmitRequest request,
    required DateTime submittedAt,
  }) {
    final int index = depositRequests.indexWhere(
      (GteDepositRequest item) => item.id == depositId,
    );
    if (index == -1) {
      throw StateError('Deposit not found');
    }
    final GteDepositRequest existing = depositRequests[index];
    final GteDepositRequest updated = GteDepositRequest(
      id: existing.id,
      reference: existing.reference,
      status: GteDepositStatus.paymentSubmitted,
      amountFiat: existing.amountFiat,
      amountCoin: existing.amountCoin,
      currencyCode: existing.currencyCode,
      rateValue: existing.rateValue,
      rateDirection: existing.rateDirection,
      bankName: existing.bankName,
      bankAccountNumber: existing.bankAccountNumber,
      bankAccountName: existing.bankAccountName,
      bankCode: existing.bankCode,
      payerName: request.payerName ?? existing.payerName,
      senderBank: request.senderBank ?? existing.senderBank,
      transferReference:
          request.transferReference ?? existing.transferReference,
      proofAttachmentId:
          request.proofAttachmentId ?? existing.proofAttachmentId,
      adminNotes: existing.adminNotes,
      createdAt: existing.createdAt,
      submittedAt: submittedAt,
      reviewedAt: existing.reviewedAt,
      confirmedAt: existing.confirmedAt,
      rejectedAt: existing.rejectedAt,
      expiresAt: existing.expiresAt,
    );
    depositRequests[index] = updated;
    return updated;
  }

  GteAdminQueuePage<GteAdminDeposit> fetchAdminDeposits({
    required int limit,
    required int offset,
    required String? status,
    required String? query,
    required GteCurrentUser user,
  }) {
    Iterable<GteDepositRequest> items = depositRequests;
    if (status != null) {
      final GteDepositStatus parsed = _depositStatusFromString(status);
      items = items.where(
        (GteDepositRequest deposit) => deposit.status == parsed,
      );
    }
    if (query != null && query.isNotEmpty) {
      final String needle = query.toLowerCase();
      items = items.where(
        (GteDepositRequest deposit) =>
            deposit.reference.toLowerCase().contains(needle) ||
            (deposit.payerName ?? '').toLowerCase().contains(needle) ||
            (deposit.senderBank ?? '').toLowerCase().contains(needle),
      );
    }
    final List<GteAdminDeposit> mapped = items
        .skip(offset)
        .take(limit)
        .map(
          (GteDepositRequest deposit) => GteAdminDeposit(
            id: deposit.id,
            reference: deposit.reference,
            status: deposit.status,
            amountFiat: deposit.amountFiat,
            amountCoin: deposit.amountCoin,
            currencyCode: deposit.currencyCode,
            payerName: deposit.payerName,
            senderBank: deposit.senderBank,
            transferReference: deposit.transferReference,
            createdAt: deposit.createdAt,
            submittedAt: deposit.submittedAt,
            reviewedAt: deposit.reviewedAt,
            confirmedAt: deposit.confirmedAt,
            rejectedAt: deposit.rejectedAt,
            adminNotes: deposit.adminNotes,
            userId: user.id,
            userEmail: user.email,
            userFullName: user.fullName,
            userPhoneNumber: user.phoneNumber,
          ),
        )
        .toList(growable: false);
    return GteAdminQueuePage<GteAdminDeposit>(
      items: mapped,
      total: items.length,
      limit: limit,
      offset: offset,
    );
  }

  GteDepositRequest adminConfirmDeposit({
    required String depositId,
    required String? adminNotes,
    required DateTime confirmedAt,
  }) {
    final int index = _indexOfDeposit(depositId);
    final GteDepositRequest existing = depositRequests[index];
    final GteDepositRequest updated = _copyDeposit(
      existing,
      status: GteDepositStatus.confirmed,
      adminNotes: adminNotes ?? existing.adminNotes,
      reviewedAt: confirmedAt,
      confirmedAt: confirmedAt,
      rejectedAt: null,
    );
    depositRequests[index] = updated;
    _wallet.creditCoin(
      amount: existing.amountCoin,
      reason: 'deposit_confirmed',
      description: 'Deposit confirmed ${existing.reference}',
      createdAt: confirmedAt,
    );
    return updated;
  }

  GteDepositRequest adminRejectDeposit({
    required String depositId,
    required String? adminNotes,
    required DateTime rejectedAt,
  }) {
    final int index = _indexOfDeposit(depositId);
    final GteDepositRequest existing = depositRequests[index];
    final GteDepositRequest updated = _copyDeposit(
      existing,
      status: GteDepositStatus.rejected,
      adminNotes: adminNotes ?? existing.adminNotes,
      reviewedAt: rejectedAt,
      confirmedAt: null,
      rejectedAt: rejectedAt,
    );
    depositRequests[index] = updated;
    return updated;
  }

  GteDepositRequest adminReviewDeposit({
    required String depositId,
    required String? adminNotes,
    required DateTime reviewedAt,
  }) {
    final int index = _indexOfDeposit(depositId);
    final GteDepositRequest existing = depositRequests[index];
    final GteDepositRequest updated = _copyDeposit(
      existing,
      status: GteDepositStatus.underReview,
      adminNotes: adminNotes ?? existing.adminNotes,
      reviewedAt: reviewedAt,
      confirmedAt: existing.confirmedAt,
      rejectedAt: existing.rejectedAt,
    );
    depositRequests[index] = updated;
    return updated;
  }

  int _indexOfDeposit(String depositId) {
    final int index = depositRequests.indexWhere(
      (GteDepositRequest deposit) => deposit.id == depositId,
    );
    if (index == -1) {
      throw StateError('Deposit not found');
    }
    return index;
  }

  GteDepositRequest _copyDeposit(
    GteDepositRequest existing, {
    required GteDepositStatus status,
    required String? adminNotes,
    required DateTime? reviewedAt,
    required DateTime? confirmedAt,
    required DateTime? rejectedAt,
  }) {
    return GteDepositRequest(
      id: existing.id,
      reference: existing.reference,
      status: status,
      amountFiat: existing.amountFiat,
      amountCoin: existing.amountCoin,
      currencyCode: existing.currencyCode,
      rateValue: existing.rateValue,
      rateDirection: existing.rateDirection,
      bankName: existing.bankName,
      bankAccountNumber: existing.bankAccountNumber,
      bankAccountName: existing.bankAccountName,
      bankCode: existing.bankCode,
      payerName: existing.payerName,
      senderBank: existing.senderBank,
      transferReference: existing.transferReference,
      proofAttachmentId: existing.proofAttachmentId,
      adminNotes: adminNotes,
      createdAt: existing.createdAt,
      submittedAt: existing.submittedAt,
      reviewedAt: reviewedAt,
      confirmedAt: confirmedAt,
      rejectedAt: rejectedAt,
      expiresAt: existing.expiresAt,
    );
  }

  static final List<GteDepositRequest> seedDeposits = <GteDepositRequest>[
    GteDepositRequest(
      id: 'deposit-1',
      reference: 'DEP-1001',
      status: GteDepositStatus.paymentSubmitted,
      amountFiat: 250000,
      amountCoin: 277.78,
      currencyCode: 'NGN',
      rateValue: 900,
      rateDirection: GteRateDirection.fiatPerCoin,
      bankName: 'GTEX Treasury',
      bankAccountNumber: '0001234567',
      bankAccountName: 'GTEX Treasury Desk',
      bankCode: 'GTB',
      payerName: 'Ayo Martins',
      senderBank: 'GTBank',
      transferReference: 'TRX-8493',
      proofAttachmentId: null,
      adminNotes: null,
      createdAt: DateTime.utc(2026, 3, 11, 8),
      submittedAt: DateTime.utc(2026, 3, 11, 8, 5),
      reviewedAt: null,
      confirmedAt: null,
      rejectedAt: null,
      expiresAt: null,
    ),
    GteDepositRequest(
      id: 'deposit-2',
      reference: 'DEP-1000',
      status: GteDepositStatus.confirmed,
      amountFiat: 50000,
      amountCoin: 55.56,
      currencyCode: 'NGN',
      rateValue: 900,
      rateDirection: GteRateDirection.fiatPerCoin,
      bankName: 'GTEX Treasury',
      bankAccountNumber: '0001234567',
      bankAccountName: 'GTEX Treasury Desk',
      bankCode: 'GTB',
      payerName: 'Ayo Martins',
      senderBank: 'Access Bank',
      transferReference: 'TRX-8390',
      proofAttachmentId: null,
      adminNotes: 'Matched transfer reference.',
      createdAt: DateTime.utc(2026, 3, 10, 9),
      submittedAt: DateTime.utc(2026, 3, 10, 9, 3),
      reviewedAt: DateTime.utc(2026, 3, 10, 9, 10),
      confirmedAt: DateTime.utc(2026, 3, 10, 9, 11),
      rejectedAt: null,
      expiresAt: null,
    ),
  ];
}

bool _isPendingDeposit(GteDepositRequest deposit) {
  return deposit.status == GteDepositStatus.awaitingPayment ||
      deposit.status == GteDepositStatus.paymentSubmitted ||
      deposit.status == GteDepositStatus.underReview;
}

GteDepositStatus _depositStatusFromString(String value) {
  switch (value.toLowerCase()) {
    case 'payment_submitted':
      return GteDepositStatus.paymentSubmitted;
    case 'under_review':
      return GteDepositStatus.underReview;
    case 'confirmed':
      return GteDepositStatus.confirmed;
    case 'rejected':
      return GteDepositStatus.rejected;
    case 'expired':
      return GteDepositStatus.expired;
    case 'disputed':
      return GteDepositStatus.disputed;
    case 'awaiting_payment':
    default:
      return GteDepositStatus.awaitingPayment;
  }
}
