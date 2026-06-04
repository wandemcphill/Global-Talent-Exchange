import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/features/capital/wallet/presentation/gte_bank_details_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets(
    'bank details require backend/user currency instead of default NGN',
    (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1400, 1600);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final _BankDetailsTruthApi repository = _BankDetailsTruthApi();
      final GteExchangeController controller = GteExchangeController(
        api: _fixtureClient(repository),
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: GteBankDetailsScreen(controller: controller),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Add bank details'));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField).at(0), 'Backend Bank');
      await tester.enterText(find.byType(TextField).at(1), '1234567890');
      await tester.enterText(find.byType(TextField).at(2), 'Ayo Martins');
      await tester.tap(find.text('Save bank details'));
      await tester.pumpAndSettle();

      expect(find.text('Currency code is required.'), findsOneWidget);
      expect(repository.createdCurrencyCode, isNull);

      await tester.enterText(find.byType(TextField).at(4), 'usd');
      await tester.tap(find.text('Save bank details'));
      await tester.pumpAndSettle();

      expect(repository.createdCurrencyCode, 'USD');
      expect(find.textContaining('Currency: USD'), findsOneWidget);
      expect(find.textContaining('NGN'), findsNothing);
    },
  );
}

class _BankDetailsTruthApi extends GteMockApi {
  String? createdCurrencyCode;
  GteUserBankAccount? _account;

  @override
  Future<List<GteUserBankAccount>> listUserBankAccounts() async {
    return _account == null
        ? <GteUserBankAccount>[]
        : <GteUserBankAccount>[_account!];
  }

  @override
  Future<GteUserBankAccount> createUserBankAccount(
    GteUserBankAccountCreate request,
  ) async {
    createdCurrencyCode = request.currencyCode;
    _account = GteUserBankAccount(
      id: 'bank-1',
      currencyCode: request.currencyCode,
      bankName: request.bankName,
      accountNumber: request.accountNumber,
      accountName: request.accountName,
      bankCode: request.bankCode,
      isActive: request.setActive,
      createdAt: null,
      updatedAt: null,
    );
    return _account!;
  }
}

GteExchangeApiClient _fixtureClient(GteMockApi repository) {
  return GteExchangeApiClient(
    config: const GteRepositoryConfig(
      baseUrl: 'http://127.0.0.1:8000',
      mode: GteBackendMode.fixture,
    ),
    transport: GteHttpTransport(),
    repository: repository,
  );
}
