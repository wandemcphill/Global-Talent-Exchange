import 'package:gte_frontend/data/gte_models.dart';

class CapitalTreasuryFixtureStore {
  CapitalTreasuryFixtureStore.seeded()
    : settings = seedSettings,
      bankAccounts = List<GteTreasuryBankAccount>.of(
        seedBankAccounts,
        growable: true,
      ),
      bankSequence = seedBankAccounts.length;

  GteTreasurySettings settings;
  final List<GteTreasuryBankAccount> bankAccounts;
  int bankSequence;

  GteTreasuryBankAccount get activeBankAccount =>
      settings.activeBankAccount ?? bankAccounts.first;

  GteTreasurySettings updateSettings({
    required GteTreasurySettingsUpdate request,
    required DateTime updatedAt,
  }) {
    settings = GteTreasurySettings(
      id: settings.id,
      settingsKey: settings.settingsKey,
      currencyCode: request.currencyCode ?? settings.currencyCode,
      depositRateValue: request.depositRateValue ?? settings.depositRateValue,
      depositRateDirection:
          request.depositRateDirection ?? settings.depositRateDirection,
      withdrawalRateValue:
          request.withdrawalRateValue ?? settings.withdrawalRateValue,
      withdrawalRateDirection:
          request.withdrawalRateDirection ?? settings.withdrawalRateDirection,
      minDeposit: request.minDeposit ?? settings.minDeposit,
      maxDeposit: request.maxDeposit ?? settings.maxDeposit,
      minWithdrawal: request.minWithdrawal ?? settings.minWithdrawal,
      maxWithdrawal: request.maxWithdrawal ?? settings.maxWithdrawal,
      depositMode: request.depositMode ?? settings.depositMode,
      withdrawalMode: request.withdrawalMode ?? settings.withdrawalMode,
      maintenanceMessage:
          request.maintenanceMessage ?? settings.maintenanceMessage,
      whatsappNumber: request.whatsappNumber ?? settings.whatsappNumber,
      activeBankAccount:
          request.activeBankAccountId == null
              ? settings.activeBankAccount
              : bankAccounts.firstWhere(
                (GteTreasuryBankAccount account) =>
                    account.id == request.activeBankAccountId,
                orElse: () => bankAccounts.first,
              ),
      createdAt: settings.createdAt,
      updatedAt: updatedAt,
    );
    return settings;
  }

  List<GteTreasuryBankAccount> listBankAccounts() =>
      List<GteTreasuryBankAccount>.of(bankAccounts, growable: false);

  GteTreasuryBankAccount createBankAccount({
    required GteTreasuryBankAccountCreate request,
    required DateTime createdAt,
  }) {
    final GteTreasuryBankAccount account = GteTreasuryBankAccount(
      id: 'treasury-bank-${++bankSequence}',
      currencyCode: request.currencyCode,
      bankName: request.bankName,
      accountNumber: request.accountNumber,
      accountName: request.accountName,
      bankCode: request.bankCode,
      isActive: request.isActive,
      createdAt: createdAt,
      updatedAt: createdAt,
    );
    if (request.isActive) {
      _deactivateBankAccounts();
    }
    bankAccounts.insert(0, account);
    return account;
  }

  GteTreasuryBankAccount updateBankAccount({
    required String accountId,
    required GteTreasuryBankAccountUpdate request,
    required DateTime updatedAt,
  }) {
    final int index = bankAccounts.indexWhere(
      (GteTreasuryBankAccount account) => account.id == accountId,
    );
    if (index == -1) {
      throw StateError('Treasury bank account not found');
    }
    if (request.isActive == true) {
      _activateBankAccount(accountId);
    }
    final GteTreasuryBankAccount existing = bankAccounts[index];
    final GteTreasuryBankAccount updated = GteTreasuryBankAccount(
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
    bankAccounts[index] = updated;
    if (settings.activeBankAccount?.id == accountId) {
      settings = GteTreasurySettings(
        id: settings.id,
        settingsKey: settings.settingsKey,
        currencyCode: settings.currencyCode,
        depositRateValue: settings.depositRateValue,
        depositRateDirection: settings.depositRateDirection,
        withdrawalRateValue: settings.withdrawalRateValue,
        withdrawalRateDirection: settings.withdrawalRateDirection,
        minDeposit: settings.minDeposit,
        maxDeposit: settings.maxDeposit,
        minWithdrawal: settings.minWithdrawal,
        maxWithdrawal: settings.maxWithdrawal,
        depositMode: settings.depositMode,
        withdrawalMode: settings.withdrawalMode,
        maintenanceMessage: settings.maintenanceMessage,
        whatsappNumber: settings.whatsappNumber,
        activeBankAccount: updated,
        createdAt: settings.createdAt,
        updatedAt: settings.updatedAt,
      );
    }
    return updated;
  }

  void _deactivateBankAccounts() {
    for (int i = 0; i < bankAccounts.length; i++) {
      final GteTreasuryBankAccount existing = bankAccounts[i];
      bankAccounts[i] = GteTreasuryBankAccount(
        id: existing.id,
        currencyCode: existing.currencyCode,
        bankName: existing.bankName,
        accountNumber: existing.accountNumber,
        accountName: existing.accountName,
        bankCode: existing.bankCode,
        isActive: false,
        createdAt: existing.createdAt,
        updatedAt: existing.updatedAt,
      );
    }
  }

  void _activateBankAccount(String accountId) {
    for (int i = 0; i < bankAccounts.length; i++) {
      final GteTreasuryBankAccount existing = bankAccounts[i];
      bankAccounts[i] = GteTreasuryBankAccount(
        id: existing.id,
        currencyCode: existing.currencyCode,
        bankName: existing.bankName,
        accountNumber: existing.accountNumber,
        accountName: existing.accountName,
        bankCode: existing.bankCode,
        isActive: existing.id == accountId,
        createdAt: existing.createdAt,
        updatedAt: existing.updatedAt,
      );
    }
  }

  static final GteTreasuryBankAccount seedBankAccount = GteTreasuryBankAccount(
    id: 'treasury-bank-1',
    currencyCode: 'NGN',
    bankName: 'GTEX Treasury',
    accountNumber: '0001234567',
    accountName: 'GTEX Treasury Desk',
    bankCode: 'GTB',
    isActive: true,
    createdAt: DateTime.utc(2026, 3, 10, 9),
    updatedAt: DateTime.utc(2026, 3, 10, 9),
  );

  static final List<GteTreasuryBankAccount> seedBankAccounts =
      <GteTreasuryBankAccount>[seedBankAccount];

  static final GteTreasurySettings seedSettings = GteTreasurySettings(
    id: 'treasury-settings-1',
    settingsKey: 'default',
    currencyCode: 'NGN',
    depositRateValue: 900,
    depositRateDirection: GteRateDirection.fiatPerCoin,
    withdrawalRateValue: 880,
    withdrawalRateDirection: GteRateDirection.fiatPerCoin,
    minDeposit: 1000,
    maxDeposit: 500000,
    minWithdrawal: 2000,
    maxWithdrawal: 500000,
    depositMode: GtePaymentMode.manual,
    withdrawalMode: GtePaymentMode.manual,
    maintenanceMessage: null,
    whatsappNumber: '+2347000000000',
    activeBankAccount: seedBankAccount,
    createdAt: DateTime.utc(2026, 3, 10, 9),
    updatedAt: DateTime.utc(2026, 3, 10, 9),
  );
}
