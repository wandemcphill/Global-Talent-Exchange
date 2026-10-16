class ClubFinanceSnapshot {
  const ClubFinanceSnapshot({
    required this.clubId,
    required this.clubName,
    required this.balanceSummary,
    required this.budgetAllocations,
    required this.incomeBreakdown,
    required this.expenseBreakdown,
    required this.cashflow,
    required this.ledgerEntries,
    required this.financeNotes,
  });

  final String clubId;
  final String clubName;
  final ClubBalanceSummary balanceSummary;
  final List<FinanceCategoryBreakdown> budgetAllocations;
  final List<FinanceCategoryBreakdown> incomeBreakdown;
  final List<FinanceCategoryBreakdown> expenseBreakdown;
  final List<CashflowPoint> cashflow;
  final List<LedgerEntry> ledgerEntries;
  final List<String> financeNotes;
}

class ClubBalanceSummary {
  const ClubBalanceSummary({
    required this.currentBalance,
    required this.operatingBudget,
    required this.reserveTarget,
    required this.monthlyIncome,
    required this.monthlyExpenses,
    required this.payrollCommitment,
    required this.nextPayrollDate,
    required this.nextPayrollAmount,
    required this.cashRunwayMonths,
    required this.balanceDeltaPercent,
  });

  final double currentBalance;
  final double operatingBudget;
  final double reserveTarget;
  final double monthlyIncome;
  final double monthlyExpenses;
  final double payrollCommitment;
  final DateTime nextPayrollDate;
  final double nextPayrollAmount;
  final double cashRunwayMonths;
  final double balanceDeltaPercent;

  double get netMonthlyMovement => monthlyIncome - monthlyExpenses;
}

class FinanceCategoryBreakdown {
  const FinanceCategoryBreakdown({
    required this.label,
    required this.amount,
    required this.sharePercent,
    this.detail,
  });

  final String label;
  final double amount;
  final double sharePercent;
  final String? detail;
}

class CashflowPoint {
  const CashflowPoint({
    required this.label,
    required this.inflow,
    required this.outflow,
    required this.closingBalance,
  });

  final String label;
  final double inflow;
  final double outflow;
  final double closingBalance;

  double get net => inflow - outflow;
}

enum LedgerEntryType {
  income,
  expense,
}

class LedgerEntry {
  const LedgerEntry({
    required this.id,
    required this.title,
    required this.category,
    required this.counterparty,
    required this.type,
    required this.amount,
    required this.runningBalance,
    required this.occurredAt,
    required this.note,
  });

  final String id;
  final String title;
  final String category;
  final String counterparty;
  final LedgerEntryType type;
  final double amount;
  final double runningBalance;
  final DateTime occurredAt;
  final String note;
}

class ClubOpsAdminSnapshot {
  const ClubOpsAdminSnapshot({
    required this.clubsMonitored,
    required this.totalOperatingBudget,
    required this.activeContracts,
    required this.academyPromotions,
    required this.activeAssignments,
    required this.youthConversionPercent,
    required this.statusNotes,
  });

  final int clubsMonitored;
  final double totalOperatingBudget;
  final int activeContracts;
  final int academyPromotions;
  final int activeAssignments;
  final double youthConversionPercent;
  final List<String> statusNotes;
}

class ClubFinanceAnalyticsSnapshot {
  const ClubFinanceAnalyticsSnapshot({
    required this.averageMonthlyBalance,
    required this.operatingMarginPercent,
    required this.payrollSharePercent,
    required this.developmentSharePercent,
    required this.commercialSharePercent,
    required this.revenueReliabilityLabel,
    required this.topExpenseLabel,
    required this.categoryMix,
    required this.quarterlyCashflow,
  });

  final double averageMonthlyBalance;
  final double operatingMarginPercent;
  final double payrollSharePercent;
  final double developmentSharePercent;
  final double commercialSharePercent;
  final String revenueReliabilityLabel;
  final String topExpenseLabel;
  final List<FinanceCategoryBreakdown> categoryMix;
  final List<CashflowPoint> quarterlyCashflow;
}
