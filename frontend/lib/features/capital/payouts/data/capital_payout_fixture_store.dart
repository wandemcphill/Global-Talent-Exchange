import 'dart:math' as math;

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/capital/settlement/data/capital_treasury_fixture_store.dart';
import 'package:gte_frontend/features/capital/wallet/data/capital_wallet_fixture_store.dart';

const int _withdrawalFeeBps = 1000;
const double _withdrawalMinimumFee = 0;

class CapitalPayoutFixtureStore {
  CapitalPayoutFixtureStore.seeded({
    required CapitalWalletFixtureStore wallet,
    required CapitalTreasuryFixtureStore treasury,
  }) : _wallet = wallet,
       _treasury = treasury,
       withdrawalRequests = List<GteTreasuryWithdrawalRequest>.of(
         seedWithdrawals,
         growable: true,
       ),
       withdrawalSequence = seedWithdrawals.length;

  final CapitalWalletFixtureStore _wallet;
  final CapitalTreasuryFixtureStore _treasury;
  final List<GteTreasuryWithdrawalRequest> withdrawalRequests;
  int withdrawalSequence;

  int get activeWithdrawalCount =>
      withdrawalRequests.where(_isActiveWithdrawal).length;

  double get activeWithdrawalAmount => withdrawalRequests
      .where(_isActiveWithdrawal)
      .fold<double>(0, (double sum, GteTreasuryWithdrawalRequest withdrawal) {
        return sum + withdrawal.amountCoin;
      });

  List<GteTreasuryWithdrawalRequest> listWithdrawalRequests() =>
      List<GteTreasuryWithdrawalRequest>.of(
        withdrawalRequests,
        growable: false,
      );

  GteWithdrawalEligibility fetchWithdrawalEligibility({
    required DateTime now,
    required List<GtePolicyRequirementSummary> missingPolicies,
  }) {
    return _computeWithdrawalEligibility(
      now: now,
      missingPolicies: missingPolicies,
    );
  }

  GteWithdrawalQuote fetchWithdrawalQuote({
    required GteWithdrawalQuoteRequest request,
    required DateTime now,
    required List<GtePolicyRequirementSummary> missingPolicies,
  }) {
    final GteWithdrawalEligibility eligibility = _computeWithdrawalEligibility(
      now: now,
      missingPolicies: missingPolicies,
    );
    final GteTreasurySettings settings = _treasury.settings;
    final double feeAmount = _withdrawalFeeAmount(request.amountCoin);
    final double netAmount = _withdrawalNetAmount(
      grossAmount: request.amountCoin,
      feeAmount: feeAmount,
    );
    final double totalDebit = request.amountCoin;
    final double rateValue = settings.withdrawalRateValue;
    final double estimatedFiat = _withdrawalFiatPayout(
      netAmount: netAmount,
      settings: settings,
    );
    String? blockedReason;
    if (eligibility.policyBlocked) {
      blockedReason =
          eligibility.policyBlockReason ??
          'Policy acceptance required before withdrawal is enabled.';
    } else if (eligibility.requiresKyc) {
      blockedReason = 'KYC required before withdrawals are enabled.';
    } else if (eligibility.requiresBankAccount) {
      blockedReason = 'Bank account required before withdrawals are enabled.';
    } else if (request.amountCoin > eligibility.withdrawableNow) {
      blockedReason = 'Withdrawal exceeds available balance.';
    }
    return GteWithdrawalQuote(
      grossAmount: request.amountCoin,
      feeAmount: feeAmount,
      netAmount: netAmount,
      totalDebit: totalDebit,
      sourceScope: request.sourceScope,
      currencyCode: settings.currencyCode,
      rateValue: rateValue,
      rateDirection: settings.withdrawalRateDirection,
      estimatedFiatPayout: estimatedFiat,
      processorMode: 'manual_bank_transfer',
      payoutChannel: 'bank_transfer',
      feeBps: _withdrawalFeeBps,
      minimumFee: _withdrawalMinimumFee,
      eligibility: eligibility,
      blockedReason: blockedReason,
    );
  }

  GteWithdrawalReceipt fetchWithdrawalReceipt({
    required String withdrawalId,
    required DateTime Function() nextTimestamp,
  }) {
    final GteTreasuryWithdrawalRequest withdrawal = withdrawalRequests
        .firstWhere(
          (GteTreasuryWithdrawalRequest item) => item.id == withdrawalId,
          orElse:
              () =>
                  withdrawalRequests.isNotEmpty
                      ? withdrawalRequests.first
                      : _buildWithdrawalFixture(
                        withdrawalId: withdrawalId,
                        createdAt: nextTimestamp(),
                      ),
        );
    return GteWithdrawalReceipt(
      withdrawal: withdrawal,
      grossAmount: withdrawal.amountCoin,
      feeAmount: withdrawal.feeAmount,
      netAmount: _withdrawalNetAmount(
        grossAmount: withdrawal.amountCoin,
        feeAmount: withdrawal.feeAmount,
      ),
      totalDebit: withdrawal.totalDebit,
      sourceScope: 'trade',
      processorMode: 'manual_bank_transfer',
      payoutChannel: 'bank_transfer',
    );
  }

  GteTreasuryWithdrawalRequest createWithdrawalRequest({
    required GteWithdrawalCreateRequest request,
    required DateTime eligibilityNow,
    required DateTime createdAt,
    required List<GtePolicyRequirementSummary> missingPolicies,
  }) {
    final GteWithdrawalEligibility eligibility = _computeWithdrawalEligibility(
      now: eligibilityNow,
      missingPolicies: missingPolicies,
    );
    if (eligibility.requiresKyc || eligibility.requiresBankAccount) {
      throw const GteApiException(
        type: GteApiErrorType.validation,
        message: 'KYC and bank details are required before withdrawing.',
      );
    }
    if (request.amountCoin > eligibility.withdrawableNow) {
      throw const GteApiException(
        type: GteApiErrorType.validation,
        message: 'Insufficient withdrawable balance.',
      );
    }
    final GteUserBankAccount bank = _wallet.resolveBankAccount(
      request.bankAccountId,
    );
    final GteTreasurySettings settings = _treasury.settings;
    final double rateValue = settings.withdrawalRateValue;
    final double feeAmount = _withdrawalFeeAmount(request.amountCoin);
    final double netAmount = _withdrawalNetAmount(
      grossAmount: request.amountCoin,
      feeAmount: feeAmount,
    );
    final double amountFiat = _withdrawalFiatPayout(
      netAmount: netAmount,
      settings: settings,
    );
    final String reference = 'WDR-${++withdrawalSequence}';
    final GteTreasuryWithdrawalRequest withdrawal =
        GteTreasuryWithdrawalRequest(
          id: 'withdrawal-$withdrawalSequence',
          payoutRequestId: 'payout-$withdrawalSequence',
          reference: reference,
          status: GteWithdrawalStatus.pendingReview,
          unit: GteLedgerUnit.coin,
          amountCoin: request.amountCoin,
          amountFiat: amountFiat,
          currencyCode: settings.currencyCode,
          rateValue: rateValue,
          rateDirection: settings.withdrawalRateDirection,
          bankName: bank.bankName,
          bankAccountNumber: bank.accountNumber,
          bankAccountName: bank.accountName,
          bankCode: bank.bankCode,
          kycStatusSnapshot: _wallet.kycStatusLabel,
          kycTierSnapshot: _wallet.kycStatusLabel,
          feeAmount: feeAmount,
          totalDebit: request.amountCoin,
          notes: request.notes,
          createdAt: createdAt,
          reviewedAt: null,
          approvedAt: null,
          processedAt: null,
          paidAt: null,
          rejectedAt: null,
          cancelledAt: null,
        );
    withdrawalRequests.insert(0, withdrawal);
    _wallet.reserveWithdrawal(
      amount: request.amountCoin,
      reference: reference,
      createdAt: createdAt,
    );
    return withdrawal;
  }

  GteAdminQueuePage<GteAdminWithdrawal> fetchAdminWithdrawals({
    required int limit,
    required int offset,
    required String? status,
    required String? query,
    required GteCurrentUser user,
  }) {
    Iterable<GteTreasuryWithdrawalRequest> items = withdrawalRequests;
    if (status != null) {
      final GteWithdrawalStatus parsed = _withdrawalStatusFromString(status);
      items = items.where(
        (GteTreasuryWithdrawalRequest withdrawal) =>
            withdrawal.status == parsed,
      );
    }
    if (query != null && query.isNotEmpty) {
      final String needle = query.toLowerCase();
      items = items.where(
        (GteTreasuryWithdrawalRequest withdrawal) =>
            withdrawal.reference.toLowerCase().contains(needle) ||
            withdrawal.bankAccountName.toLowerCase().contains(needle) ||
            withdrawal.bankAccountNumber.contains(needle),
      );
    }
    final List<GteAdminWithdrawal> mapped = items
        .skip(offset)
        .take(limit)
        .map(
          (GteTreasuryWithdrawalRequest withdrawal) => GteAdminWithdrawal(
            id: withdrawal.id,
            reference: withdrawal.reference,
            status: withdrawal.status,
            amountCoin: withdrawal.amountCoin,
            amountFiat: withdrawal.amountFiat,
            feeAmount: withdrawal.feeAmount,
            netAmount: _withdrawalNetAmount(
              grossAmount: withdrawal.amountCoin,
              feeAmount: withdrawal.feeAmount,
            ),
            totalDebit: withdrawal.totalDebit,
            currencyCode: withdrawal.currencyCode,
            bankName: withdrawal.bankName,
            bankAccountNumber: withdrawal.bankAccountNumber,
            bankAccountName: withdrawal.bankAccountName,
            createdAt: withdrawal.createdAt,
            reviewedAt: withdrawal.reviewedAt,
            approvedAt: withdrawal.approvedAt,
            processedAt: withdrawal.processedAt,
            paidAt: withdrawal.paidAt,
            rejectedAt: withdrawal.rejectedAt,
            cancelledAt: withdrawal.cancelledAt,
            userId: user.id,
            userEmail: user.email,
            userFullName: user.fullName,
            userPhoneNumber: user.phoneNumber,
          ),
        )
        .toList(growable: false);
    return GteAdminQueuePage<GteAdminWithdrawal>(
      items: mapped,
      total: items.length,
      limit: limit,
      offset: offset,
    );
  }

  GteTreasuryWithdrawalRequest adminUpdateWithdrawalStatus({
    required String withdrawalId,
    required GteWithdrawalStatus status,
    required String? adminNotes,
    required DateTime updatedAt,
  }) {
    final int index = withdrawalRequests.indexWhere(
      (GteTreasuryWithdrawalRequest withdrawal) =>
          withdrawal.id == withdrawalId,
    );
    if (index == -1) {
      throw StateError('Withdrawal not found');
    }
    final GteTreasuryWithdrawalRequest existing = withdrawalRequests[index];
    final GteTreasuryWithdrawalRequest updated = GteTreasuryWithdrawalRequest(
      id: existing.id,
      payoutRequestId: existing.payoutRequestId,
      reference: existing.reference,
      status: status,
      unit: existing.unit,
      amountCoin: existing.amountCoin,
      amountFiat: existing.amountFiat,
      currencyCode: existing.currencyCode,
      rateValue: existing.rateValue,
      rateDirection: existing.rateDirection,
      bankName: existing.bankName,
      bankAccountNumber: existing.bankAccountNumber,
      bankAccountName: existing.bankAccountName,
      bankCode: existing.bankCode,
      kycStatusSnapshot: existing.kycStatusSnapshot,
      kycTierSnapshot: existing.kycTierSnapshot,
      feeAmount: existing.feeAmount,
      totalDebit: existing.totalDebit,
      notes: existing.notes,
      createdAt: existing.createdAt,
      reviewedAt:
          status == GteWithdrawalStatus.pendingReview ||
                  status == GteWithdrawalStatus.approved
              ? updatedAt
              : existing.reviewedAt,
      approvedAt:
          status == GteWithdrawalStatus.approved
              ? updatedAt
              : existing.approvedAt,
      processedAt:
          status == GteWithdrawalStatus.processing
              ? updatedAt
              : existing.processedAt,
      paidAt: status == GteWithdrawalStatus.paid ? updatedAt : existing.paidAt,
      rejectedAt:
          status == GteWithdrawalStatus.rejected
              ? updatedAt
              : existing.rejectedAt,
      cancelledAt:
          status == GteWithdrawalStatus.cancelled
              ? updatedAt
              : existing.cancelledAt,
    );
    withdrawalRequests[index] = updated;
    if (status == GteWithdrawalStatus.paid) {
      _wallet.settlePaidWithdrawal(existing.amountCoin);
    } else if (status == GteWithdrawalStatus.rejected ||
        status == GteWithdrawalStatus.cancelled) {
      _wallet.releaseWithdrawal(existing.amountCoin);
    }
    return updated;
  }

  GteWithdrawalEligibility _computeWithdrawalEligibility({
    required DateTime now,
    required List<GtePolicyRequirementSummary> missingPolicies,
  }) {
    final GteKycStatus status = _wallet.kycProfile.status;
    final bool requiresKyc =
        status == GteKycStatus.unverified ||
        status == GteKycStatus.pending ||
        status == GteKycStatus.rejected;
    final bool requiresBankAccount = !_wallet.hasActiveBankAccount;
    final double available = _wallet.coinSummary.availableBalance;
    double withdrawable = available;
    double remainingAllowance = available;
    DateTime? nextEligibleAt;
    if (requiresKyc || requiresBankAccount) {
      withdrawable = 0;
      remainingAllowance = 0;
    } else if (status == GteKycStatus.partialVerifiedNoId) {
      final DateTime windowStart = now.subtract(const Duration(hours: 24));
      final List<GteTreasuryWithdrawalRequest> recent = withdrawalRequests
          .where(
            (GteTreasuryWithdrawalRequest withdrawal) =>
                (withdrawal.createdAt ?? now).isAfter(windowStart) &&
                (withdrawal.status == GteWithdrawalStatus.pendingReview ||
                    withdrawal.status == GteWithdrawalStatus.processing ||
                    withdrawal.status == GteWithdrawalStatus.approved ||
                    withdrawal.status == GteWithdrawalStatus.paid),
          )
          .toList(growable: false);
      final double recentTotal = recent.fold<double>(
        0,
        (double sum, GteTreasuryWithdrawalRequest withdrawal) =>
            sum + withdrawal.amountCoin,
      );
      final double limit = available * 0.3;
      remainingAllowance = math.max(0, limit - recentTotal);
      withdrawable = math.min(available, remainingAllowance);
      if (remainingAllowance <= 0 && recent.isNotEmpty) {
        final DateTime earliest = recent
            .map(
              (GteTreasuryWithdrawalRequest withdrawal) =>
                  withdrawal.createdAt ?? now,
            )
            .reduce(
              (DateTime left, DateTime right) =>
                  left.isBefore(right) ? left : right,
            );
        nextEligibleAt = earliest.add(const Duration(hours: 24));
      }
    }
    if (missingPolicies.isNotEmpty) {
      withdrawable = 0;
      remainingAllowance = 0;
    }
    return GteWithdrawalEligibility(
      availableBalance: available,
      withdrawableNow: withdrawable,
      remainingAllowance: remainingAllowance,
      nextEligibleAt: nextEligibleAt,
      kycStatus: status,
      requiresKyc: requiresKyc,
      requiresBankAccount: requiresBankAccount,
      pendingWithdrawals: activeWithdrawalAmount,
      countryCode: _wallet.countryCode,
      countryWithdrawalsEnabled: true,
      missingRequiredPolicies: missingPolicies
          .map((GtePolicyRequirementSummary item) => item.documentKey)
          .toList(growable: false),
      policyBlocked: missingPolicies.isNotEmpty,
      policyBlockReason:
          missingPolicies.isEmpty
              ? null
              : 'Policy acceptance required before withdrawal is enabled.',
    );
  }

  GteTreasuryWithdrawalRequest _buildWithdrawalFixture({
    required String withdrawalId,
    required DateTime createdAt,
  }) {
    final GteUserBankAccount? bank = _wallet.firstUserBankAccount;
    final GteTreasurySettings settings = _treasury.settings;
    return GteTreasuryWithdrawalRequest(
      id: withdrawalId,
      payoutRequestId: 'payout-$withdrawalId',
      reference: 'WDR-FIXTURE',
      status: GteWithdrawalStatus.pendingReview,
      unit: GteLedgerUnit.coin,
      amountCoin: 0,
      amountFiat: 0,
      currencyCode: settings.currencyCode,
      rateValue: settings.withdrawalRateValue,
      rateDirection: settings.withdrawalRateDirection,
      bankName: bank?.bankName ?? 'Unknown bank',
      bankAccountNumber: bank?.accountNumber ?? '0000000000',
      bankAccountName: bank?.accountName ?? 'Unknown account',
      bankCode: bank?.bankCode,
      kycStatusSnapshot: _wallet.kycProfile.status.name,
      kycTierSnapshot: _wallet.kycProfile.status.name,
      feeAmount: 0,
      totalDebit: 0,
      notes: 'Generated fallback withdrawal fixture.',
      createdAt: createdAt,
      reviewedAt: null,
      approvedAt: null,
      processedAt: null,
      paidAt: null,
      rejectedAt: null,
      cancelledAt: null,
    );
  }

  static final List<GteTreasuryWithdrawalRequest> seedWithdrawals =
      <GteTreasuryWithdrawalRequest>[
        GteTreasuryWithdrawalRequest(
          id: 'withdrawal-1',
          payoutRequestId: 'payout-1',
          reference: 'WDR-2001',
          status: GteWithdrawalStatus.processing,
          unit: GteLedgerUnit.coin,
          amountCoin: 120,
          amountFiat: 95040,
          currencyCode: 'NGN',
          rateValue: 880,
          rateDirection: GteRateDirection.fiatPerCoin,
          bankName: 'Zenith Bank',
          bankAccountNumber: '0123456789',
          bankAccountName: 'Ayo Martins',
          bankCode: 'ZENITH',
          kycStatusSnapshot: 'partial_verified_no_id',
          kycTierSnapshot: 'partial_verified_no_id',
          feeAmount: 12,
          totalDebit: 120,
          notes: 'Weekly payout',
          createdAt: DateTime.utc(2026, 3, 11, 7),
          reviewedAt: DateTime.utc(2026, 3, 11, 7, 10),
          approvedAt: DateTime.utc(2026, 3, 11, 7, 12),
          processedAt: DateTime.utc(2026, 3, 11, 7, 30),
          paidAt: null,
          rejectedAt: null,
          cancelledAt: null,
        ),
      ];
}

bool _isActiveWithdrawal(GteTreasuryWithdrawalRequest withdrawal) {
  return withdrawal.status == GteWithdrawalStatus.pendingReview ||
      withdrawal.status == GteWithdrawalStatus.processing ||
      withdrawal.status == GteWithdrawalStatus.approved;
}

double _withdrawalFeeAmount(double grossAmount) {
  return grossAmount * _withdrawalFeeBps.toDouble() / 10000;
}

double _withdrawalNetAmount({
  required double grossAmount,
  required double feeAmount,
}) {
  return math.max(0, grossAmount - feeAmount);
}

double _withdrawalFiatPayout({
  required double netAmount,
  required GteTreasurySettings settings,
}) {
  final double rateValue = settings.withdrawalRateValue;
  return settings.withdrawalRateDirection == GteRateDirection.fiatPerCoin
      ? netAmount * rateValue
      : netAmount / math.max(rateValue, 0.0001);
}

GteWithdrawalStatus _withdrawalStatusFromString(String value) {
  switch (value.toLowerCase()) {
    case 'draft':
      return GteWithdrawalStatus.draft;
    case 'processing':
      return GteWithdrawalStatus.processing;
    case 'approved':
      return GteWithdrawalStatus.approved;
    case 'paid':
      return GteWithdrawalStatus.paid;
    case 'rejected':
      return GteWithdrawalStatus.rejected;
    case 'disputed':
      return GteWithdrawalStatus.disputed;
    case 'cancelled':
      return GteWithdrawalStatus.cancelled;
    case 'pending_kyc':
      return GteWithdrawalStatus.pendingKyc;
    case 'pending_review':
    default:
      return GteWithdrawalStatus.pendingReview;
  }
}
