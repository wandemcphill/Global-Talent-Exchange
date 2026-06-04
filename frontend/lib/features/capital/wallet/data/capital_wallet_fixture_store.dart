import 'dart:math' as math;

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_models.dart';

class CapitalWalletFixtureStore {
  CapitalWalletFixtureStore.seeded()
    : coinSummary = seedCoinSummary,
      fanSummary = seedFanSummary,
      ledger = List<GteWalletLedgerEntry>.of(seedLedger, growable: true),
      userBankAccounts = List<GteUserBankAccount>.of(
        seedUserBankAccounts,
        growable: true,
      ),
      kycProfile = seedKycProfile,
      ledgerSequence = seedLedger.length,
      userBankSequence = seedUserBankAccounts.length;

  GteWalletSummary coinSummary;
  GteWalletSummary fanSummary;
  final List<GteWalletLedgerEntry> ledger;
  final List<GteUserBankAccount> userBankAccounts;
  final List<GteWalletTransactionRecord> transactions =
      <GteWalletTransactionRecord>[];
  final Map<String, GteWalletTopUpSession> topUpSessions =
      <String, GteWalletTopUpSession>{};
  GteKycProfile kycProfile;
  int ledgerSequence;
  int transactionSequence = 0;
  int userBankSequence;

  String get nextLedgerId => 'ledger-${ledgerSequence + 1}';

  String get countryCode => kycProfile.country?.toUpperCase() ?? 'NG';

  bool get hasActiveBankAccount =>
      userBankAccounts.any((GteUserBankAccount account) => account.isActive);

  GteUserBankAccount? get firstUserBankAccount =>
      userBankAccounts.isEmpty ? null : userBankAccounts.first;

  String get kycStatusLabel => _kycStatusToString(kycProfile.status);

  String nextTransactionReference(String prefix) =>
      '$prefix-${++transactionSequence}';

  void reserveOrderFunds({
    required double amount,
    required String playerId,
    required DateTime createdAt,
  }) {
    _reserveCoin(amount);
    _insertLedger(
      amount: -amount,
      reason: 'order_funds_reserved',
      description: 'Reserved GTEX Coin for $playerId buy order',
      createdAt: createdAt,
    );
  }

  void releaseOrderFunds({
    required double amount,
    required String orderId,
    required DateTime createdAt,
  }) {
    _releaseReservedCoin(amount);
    _insertLedger(
      amount: amount,
      reason: 'order_cancel_release',
      description: 'Released GTEX Coin from cancelled order $orderId',
      createdAt: createdAt,
    );
  }

  void creditCoin({
    required double amount,
    required String reason,
    required String description,
    required DateTime createdAt,
  }) {
    coinSummary = GteWalletSummary(
      availableBalance: coinSummary.availableBalance + amount,
      reservedBalance: coinSummary.reservedBalance,
      lockedBalance: coinSummary.lockedBalance,
      lockReasons: coinSummary.lockReasons,
      totalBalance: coinSummary.totalBalance + amount,
      currency: coinSummary.currency,
    );
    _insertLedger(
      amount: amount,
      reason: reason,
      description: description,
      createdAt: createdAt,
    );
  }

  void convertCoinToFan({
    required double sourceAmount,
    required double targetAmount,
    required String reference,
    required String userId,
    required DateTime createdAt,
  }) {
    coinSummary = GteWalletSummary(
      availableBalance: coinSummary.availableBalance - sourceAmount,
      reservedBalance: coinSummary.reservedBalance,
      lockedBalance: coinSummary.lockedBalance,
      lockReasons: coinSummary.lockReasons,
      totalBalance: coinSummary.totalBalance - sourceAmount,
      currency: coinSummary.currency,
    );
    fanSummary = GteWalletSummary(
      availableBalance: fanSummary.availableBalance + targetAmount,
      reservedBalance: fanSummary.reservedBalance,
      lockedBalance: fanSummary.lockedBalance,
      lockReasons: fanSummary.lockReasons,
      totalBalance: fanSummary.totalBalance + targetAmount,
      currency: fanSummary.currency,
    );
    _insertLedger(
      amount: -sourceAmount,
      reason: 'adjustment',
      description:
          'Converted ${sourceAmount.toStringAsFixed(2)} GTEX Coin into ${targetAmount.toStringAsFixed(2)} Fan Coin',
      createdAt: createdAt,
    );
    transactions.insert(
      0,
      GteWalletTransactionRecord(
        id: 'wallet-txn-$reference',
        userId: userId,
        type: 'conversion',
        amount: sourceAmount,
        status: 'verified',
        reference: reference,
        createdAt: createdAt,
      ),
    );
  }

  void reserveWithdrawal({
    required double amount,
    required String reference,
    required DateTime createdAt,
  }) {
    _reserveCoin(amount);
    _insertLedger(
      amount: -amount,
      reason: 'withdrawal_hold',
      description: 'Withdrawal hold for $reference',
      createdAt: createdAt,
    );
  }

  void settlePaidWithdrawal(double amount) {
    coinSummary = GteWalletSummary(
      availableBalance: coinSummary.availableBalance,
      reservedBalance: math.max(0, coinSummary.reservedBalance - amount),
      lockedBalance: coinSummary.lockedBalance,
      lockReasons: coinSummary.lockReasons,
      totalBalance: coinSummary.totalBalance - amount,
      currency: coinSummary.currency,
    );
  }

  void releaseWithdrawal(double amount) {
    _releaseReservedCoin(amount);
  }

  void putTopUpSession(
    String reference,
    GteWalletTopUpSession session,
    GteWalletTransactionRecord transaction,
  ) {
    topUpSessions[reference] = session;
    transactions.insert(0, transaction);
  }

  GteWalletTopUpSession? topUpSession(String reference) =>
      topUpSessions[reference];

  GteWalletTransactionRecord transactionForReference(String reference) {
    final int index = transactions.indexWhere(
      (GteWalletTransactionRecord item) => item.reference == reference,
    );
    if (index < 0) {
      throw const GteApiException(
        type: GteApiErrorType.notFound,
        message: 'Wallet transaction was not found.',
      );
    }
    return transactions[index];
  }

  void verifyTopUp({
    required String reference,
    required GteWalletTransactionRecord updated,
    required DateTime createdAt,
  }) {
    final int index = transactions.indexWhere(
      (GteWalletTransactionRecord item) => item.reference == reference,
    );
    if (index < 0) {
      throw const GteApiException(
        type: GteApiErrorType.notFound,
        message: 'Wallet transaction was not found.',
      );
    }
    transactions[index] = updated;
    topUpSessions.remove(reference);
    creditCoin(
      amount: updated.amount,
      reason: 'wallet_top_up',
      description: 'Wallet top-up credited via KoraPay',
      createdAt: createdAt,
    );
  }

  GteKycProfile submitKycProfile({
    required GteKycSubmitRequest request,
    required DateTime submittedAt,
  }) {
    kycProfile = GteKycProfile(
      id: kycProfile.id,
      status: GteKycStatus.pending,
      nin: request.nin ?? kycProfile.nin,
      bvn: request.bvn ?? kycProfile.bvn,
      addressLine1: request.addressLine1,
      addressLine2: request.addressLine2,
      city: request.city,
      state: request.state,
      country: request.country,
      idDocumentAttachmentId: request.idDocumentAttachmentId,
      submittedAt: submittedAt,
      reviewedAt: null,
      rejectionReason: null,
      createdAt: kycProfile.createdAt,
      updatedAt: submittedAt,
    );
    return kycProfile;
  }

  GteAdminQueuePage<GteAdminKyc> fetchAdminKyc({
    required int limit,
    required int offset,
    required String? status,
    required String? query,
    required GteCurrentUser user,
  }) {
    Iterable<GteAdminKyc> items = <GteAdminKyc>[
      GteAdminKyc(
        id: kycProfile.id,
        userId: user.id,
        status: kycProfile.status,
        nin: kycProfile.nin,
        bvn: kycProfile.bvn,
        addressLine1: kycProfile.addressLine1,
        city: kycProfile.city,
        state: kycProfile.state,
        country: kycProfile.country,
        submittedAt: kycProfile.submittedAt,
        reviewedAt: kycProfile.reviewedAt,
        rejectionReason: kycProfile.rejectionReason,
        userEmail: user.email,
        userFullName: user.fullName,
        userPhoneNumber: user.phoneNumber,
      ),
    ];
    if (status != null && status.isNotEmpty) {
      final String normalizedStatus = status.toLowerCase();
      items = items.where(
        (GteAdminKyc item) =>
            _kycStatusToString(item.status) == normalizedStatus,
      );
    }
    if (query != null && query.isNotEmpty) {
      final String needle = query.toLowerCase();
      items = items.where(
        (GteAdminKyc item) =>
            item.userEmail.toLowerCase().contains(needle) ||
            (item.userFullName ?? '').toLowerCase().contains(needle),
      );
    }
    final List<GteAdminKyc> paged = items
        .skip(offset)
        .take(limit)
        .toList(growable: false);
    return GteAdminQueuePage<GteAdminKyc>(
      items: paged,
      total: items.length,
      limit: limit,
      offset: offset,
    );
  }

  GteKycProfile reviewKyc({
    required String profileId,
    required GteKycReviewRequest request,
    required DateTime reviewedAt,
  }) {
    if (profileId != kycProfile.id) {
      throw StateError('KYC profile not found');
    }
    kycProfile = GteKycProfile(
      id: kycProfile.id,
      status: request.status,
      nin: kycProfile.nin,
      bvn: kycProfile.bvn,
      addressLine1: kycProfile.addressLine1,
      addressLine2: kycProfile.addressLine2,
      city: kycProfile.city,
      state: kycProfile.state,
      country: kycProfile.country,
      idDocumentAttachmentId: kycProfile.idDocumentAttachmentId,
      submittedAt: kycProfile.submittedAt,
      reviewedAt: reviewedAt,
      rejectionReason: request.rejectionReason,
      createdAt: kycProfile.createdAt,
      updatedAt: reviewedAt,
    );
    return kycProfile;
  }

  List<GteUserBankAccount> listUserBankAccounts() =>
      List<GteUserBankAccount>.of(userBankAccounts, growable: false);

  GteUserBankAccount createUserBankAccount({
    required GteUserBankAccountCreate request,
    required DateTime createdAt,
  }) {
    if (request.setActive) {
      _deactivateUserBankAccounts();
    }
    final GteUserBankAccount account = GteUserBankAccount(
      id: 'user-bank-${++userBankSequence}',
      currencyCode: request.currencyCode,
      bankName: request.bankName,
      accountNumber: request.accountNumber,
      accountName: request.accountName,
      bankCode: request.bankCode,
      isActive: request.setActive,
      createdAt: createdAt,
      updatedAt: createdAt,
    );
    userBankAccounts.insert(0, account);
    return account;
  }

  GteUserBankAccount updateUserBankAccount({
    required String bankAccountId,
    required GteUserBankAccountUpdate request,
    required DateTime updatedAt,
  }) {
    final int index = userBankAccounts.indexWhere(
      (GteUserBankAccount account) => account.id == bankAccountId,
    );
    if (index == -1) {
      throw StateError('Bank account not found');
    }
    if (request.isActive == true) {
      _activateUserBankAccount(bankAccountId);
    }
    final GteUserBankAccount existing = userBankAccounts[index];
    final GteUserBankAccount updated = GteUserBankAccount(
      id: existing.id,
      currencyCode: request.currencyCode ?? existing.currencyCode,
      bankName: request.bankName ?? existing.bankName,
      accountNumber: request.accountNumber ?? existing.accountNumber,
      accountName: request.accountName ?? existing.accountName,
      bankCode: request.bankCode ?? existing.bankCode,
      isActive: request.isActive ?? existing.isActive,
      createdAt: existing.createdAt,
      updatedAt: updatedAt,
    );
    userBankAccounts[index] = updated;
    return updated;
  }

  GteUserBankAccount resolveBankAccount(String? bankAccountId) {
    if (bankAccountId != null) {
      return userBankAccounts.firstWhere(
        (GteUserBankAccount account) => account.id == bankAccountId,
      );
    }
    final Iterable<GteUserBankAccount> active = userBankAccounts.where(
      (GteUserBankAccount account) => account.isActive,
    );
    if (active.isNotEmpty) {
      return active.first;
    }
    if (userBankAccounts.isEmpty) {
      throw const GteApiException(
        type: GteApiErrorType.validation,
        message: 'No bank account on file.',
      );
    }
    return userBankAccounts.first;
  }

  void _reserveCoin(double amount) {
    coinSummary = GteWalletSummary(
      availableBalance: coinSummary.availableBalance - amount,
      reservedBalance: coinSummary.reservedBalance + amount,
      lockedBalance: coinSummary.lockedBalance,
      lockReasons: coinSummary.lockReasons,
      totalBalance: coinSummary.totalBalance,
      currency: coinSummary.currency,
    );
  }

  void _releaseReservedCoin(double amount) {
    coinSummary = GteWalletSummary(
      availableBalance: coinSummary.availableBalance + amount,
      reservedBalance: math.max(0.0, coinSummary.reservedBalance - amount),
      lockedBalance: coinSummary.lockedBalance,
      lockReasons: coinSummary.lockReasons,
      totalBalance: coinSummary.totalBalance,
      currency: coinSummary.currency,
    );
  }

  void _deactivateUserBankAccounts() {
    for (int i = 0; i < userBankAccounts.length; i++) {
      final GteUserBankAccount account = userBankAccounts[i];
      userBankAccounts[i] = GteUserBankAccount(
        id: account.id,
        currencyCode: account.currencyCode,
        bankName: account.bankName,
        accountNumber: account.accountNumber,
        accountName: account.accountName,
        bankCode: account.bankCode,
        isActive: false,
        createdAt: account.createdAt,
        updatedAt: account.updatedAt,
      );
    }
  }

  void _activateUserBankAccount(String bankAccountId) {
    for (int i = 0; i < userBankAccounts.length; i++) {
      final GteUserBankAccount account = userBankAccounts[i];
      userBankAccounts[i] = GteUserBankAccount(
        id: account.id,
        currencyCode: account.currencyCode,
        bankName: account.bankName,
        accountNumber: account.accountNumber,
        accountName: account.accountName,
        bankCode: account.bankCode,
        isActive: account.id == bankAccountId,
        createdAt: account.createdAt,
        updatedAt: account.updatedAt,
      );
    }
  }

  void _insertLedger({
    required double amount,
    required String reason,
    required String description,
    required DateTime createdAt,
  }) {
    ledger.insert(
      0,
      GteWalletLedgerEntry(
        id: 'ledger-${++ledgerSequence}',
        amount: amount,
        reason: reason,
        description: description,
        createdAt: createdAt,
      ),
    );
  }

  static const GteWalletSummary seedCoinSummary = GteWalletSummary(
    availableBalance: 1200,
    reservedBalance: 62.5,
    lockedBalance: 62.5,
    lockReasons: <String>[
      'Active orders, withdrawals, or settlement commitments are reserving GTEX Coin.',
    ],
    totalBalance: 1262.5,
    currency: GteLedgerUnit.coin,
  );

  static const GteWalletSummary seedFanSummary = GteWalletSummary(
    availableBalance: 4800,
    reservedBalance: 0,
    totalBalance: 4800,
    currency: GteLedgerUnit.credit,
  );

  static final List<GteWalletLedgerEntry> seedLedger = <GteWalletLedgerEntry>[
    GteWalletLedgerEntry(
      id: 'ledger-1',
      amount: -62.5,
      reason: 'withdrawal_hold',
      description: 'Reserved GTEX Coin for resting buy order',
      createdAt: DateTime.utc(2026, 3, 11, 11, 30),
    ),
    GteWalletLedgerEntry(
      id: 'ledger-2',
      amount: 1200,
      reason: 'adjustment',
      description: 'Demo wallet seed',
      createdAt: DateTime.utc(2026, 3, 11, 8),
    ),
    GteWalletLedgerEntry(
      id: 'ledger-3',
      amount: -1095,
      reason: 'trade_execution',
      description: 'Portfolio acquisition cash leg',
      createdAt: DateTime.utc(2026, 3, 10, 18, 15),
    ),
  ];

  static final List<GteUserBankAccount> seedUserBankAccounts =
      <GteUserBankAccount>[
        GteUserBankAccount(
          id: 'user-bank-1',
          currencyCode: 'NGN',
          bankName: 'Zenith Bank',
          accountNumber: '0123456789',
          accountName: 'Ayo Martins',
          bankCode: 'ZENITH',
          isActive: true,
          createdAt: DateTime.utc(2026, 3, 10, 11),
          updatedAt: DateTime.utc(2026, 3, 10, 11),
        ),
      ];

  static final GteKycProfile seedKycProfile = GteKycProfile(
    id: 'kyc-1',
    status: GteKycStatus.partialVerifiedNoId,
    nin: 'NIN-4392901',
    bvn: null,
    addressLine1: '12 Adeola Odeku St',
    addressLine2: null,
    city: 'Lagos',
    state: 'Lagos',
    country: 'Nigeria',
    idDocumentAttachmentId: null,
    submittedAt: DateTime.utc(2026, 3, 10, 12),
    reviewedAt: DateTime.utc(2026, 3, 10, 14),
    rejectionReason: null,
    createdAt: DateTime.utc(2026, 3, 10, 12),
    updatedAt: DateTime.utc(2026, 3, 10, 14),
  );
}

String _kycStatusToString(GteKycStatus status) {
  switch (status) {
    case GteKycStatus.unverified:
      return 'unverified';
    case GteKycStatus.pending:
      return 'pending';
    case GteKycStatus.partialVerifiedNoId:
      return 'partial_verified_no_id';
    case GteKycStatus.fullyVerified:
      return 'fully_verified';
    case GteKycStatus.rejected:
      return 'rejected';
  }
}
