import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/app_breakpoints.dart';
import '../../core/constants/app_spacing.dart';
import '../../core/utils/app_formatters.dart';
import '../../shared/providers/exchange_hub_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/metric_pill.dart';
import 'widgets/exchange_hub_widgets.dart';

class TransferMarketScreen extends ConsumerStatefulWidget {
  const TransferMarketScreen({super.key});

  @override
  ConsumerState<TransferMarketScreen> createState() =>
      _TransferMarketScreenState();
}

class _TransferMarketScreenState extends ConsumerState<TransferMarketScreen> {
  Timer? _simulationTicker;

  @override
  void initState() {
    super.initState();
    _simulationTicker = Timer.periodic(
      const Duration(seconds: 2),
      (_) => ref.read(exchangeHubProvider.notifier).tickMarket(),
    );
  }

  @override
  void dispose() {
    _simulationTicker?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ExchangeHubState state = ref.watch(exchangeHubProvider);
    final ExchangeHubNotifier notifier = ref.read(exchangeHubProvider.notifier);

    return AppPageLayout(
      title: 'Transfer Market',
      subtitle:
          'Wallet dashboard, payments, player trading, compliance controls, and AI liquidity in one football-fintech desk.',
      trailing: MetricPill(
        label: 'Wallet',
        value: AppFormatters.gtex(state.walletBalanceGtex),
        highlight: true,
      ),
      children: <Widget>[
        ExchangeWalletDashboardCard(
          state: state,
          onDeposit: () => _openDepositFlow(context),
          onWithdraw: () => _openWithdrawalFlow(context),
          onConvert: () => _openConvertFlow(context),
        ),
        ExchangeActivityPanel(state: state),
        LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final Widget tradingDesk = TradingDeskSection(
              state: state,
              onSearchChanged: notifier.setSearchQuery,
              onFilterChanged: notifier.setFilter,
              onOpenPlayer:
                  (String playerId) => _openPlayerTradeSheet(context, playerId),
            );
            final Widget rail = ComplianceRail(state: state);

            if (constraints.maxWidth < AppBreakpoints.medium) {
              return Column(
                children: <Widget>[
                  tradingDesk,
                  const SizedBox(height: spacingLG),
                  rail,
                ],
              );
            }

            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Expanded(flex: 7, child: tradingDesk),
                const SizedBox(width: spacingLG),
                Expanded(flex: 4, child: rail),
              ],
            );
          },
        ),
      ],
    );
  }

  Future<void> _openDepositFlow(BuildContext pageContext) {
    return showModalBottomSheet<void>(
      context: pageContext,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (BuildContext sheetContext) {
        return DepositFlowSheet(
          onSubmitInstant: (DepositFlowRequest request) {
            final ExchangeActionResult result = ref
                .read(exchangeHubProvider.notifier)
                .fundInstantWallet(
                  method: request.method,
                  amountNaira: request.amountNaira,
                );
            _reportResult(
              pageContext: pageContext,
              sheetContext: sheetContext,
              result: result,
            );
          },
          onSubmitManual: (DepositFlowRequest request) {
            final ExchangeActionResult result = ref
                .read(exchangeHubProvider.notifier)
                .submitManualDeposit(amountNaira: request.amountNaira);
            _reportResult(
              pageContext: pageContext,
              sheetContext: sheetContext,
              result: result,
            );
          },
        );
      },
    );
  }

  Future<void> _openWithdrawalFlow(BuildContext pageContext) {
    return showModalBottomSheet<void>(
      context: pageContext,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (BuildContext sheetContext) {
        return Consumer(
          builder: (BuildContext context, WidgetRef ref, Widget? child) {
            final ExchangeHubState state = ref.watch(exchangeHubProvider);
            return WithdrawalFlowSheet(
              state: state,
              onSelectBank: ref.read(exchangeHubProvider.notifier).selectBank,
              onSubmit: (double amountGtex) {
                final ExchangeActionResult result = ref
                    .read(exchangeHubProvider.notifier)
                    .requestWithdrawal(amountGtex);
                _reportResult(
                  pageContext: pageContext,
                  sheetContext: sheetContext,
                  result: result,
                );
              },
            );
          },
        );
      },
    );
  }

  Future<void> _openConvertFlow(BuildContext pageContext) {
    return showModalBottomSheet<void>(
      context: pageContext,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (BuildContext sheetContext) {
        return Consumer(
          builder: (BuildContext context, WidgetRef ref, Widget? child) {
            final ExchangeHubState state = ref.watch(exchangeHubProvider);
            return ConvertFlowSheet(
              availableBalance: state.walletBalanceGtex,
              onSubmit: (double amountGtex) {
                final ExchangeActionResult result = ref
                    .read(exchangeHubProvider.notifier)
                    .convertToFanCoin(amountGtex);
                _reportResult(
                  pageContext: pageContext,
                  sheetContext: sheetContext,
                  result: result,
                );
              },
            );
          },
        );
      },
    );
  }

  Future<void> _openPlayerTradeSheet(
    BuildContext pageContext,
    String playerId,
  ) {
    return showModalBottomSheet<void>(
      context: pageContext,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (BuildContext sheetContext) {
        return Consumer(
          builder: (BuildContext context, WidgetRef ref, Widget? child) {
            final ExchangeHubState state = ref.watch(exchangeHubProvider);
            final PlayerShareListing? player = state.playerById(playerId);
            if (player == null) {
              return const SizedBox.shrink();
            }
            return PlayerTradeSheet(
              state: state,
              player: player,
              onBuy: (int shares) {
                final ExchangeActionResult result = ref
                    .read(exchangeHubProvider.notifier)
                    .buyShares(playerId: player.id, shares: shares);
                _reportResult(
                  pageContext: pageContext,
                  sheetContext: sheetContext,
                  result: result,
                );
              },
              onSell: (int shares) {
                final ExchangeActionResult result = ref
                    .read(exchangeHubProvider.notifier)
                    .sellShares(playerId: player.id, shares: shares);
                _reportResult(
                  pageContext: pageContext,
                  sheetContext: sheetContext,
                  result: result,
                );
              },
            );
          },
        );
      },
    );
  }

  void _reportResult({
    required BuildContext pageContext,
    required BuildContext sheetContext,
    required ExchangeActionResult result,
  }) {
    if (!result.isError && Navigator.of(sheetContext).canPop()) {
      Navigator.of(sheetContext).pop();
    }
    ScaffoldMessenger.of(
      pageContext,
    ).showSnackBar(SnackBar(content: Text(result.message)));
  }
}
