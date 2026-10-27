import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';
import '../theme/gtex_typography.dart';

/// Explicit currency unit used across GTEX shell surfaces (Decision O-02 & Document F8).
enum GtexCurrencyUnit {
  gtc('GTC'),
  fnc('FNC'),
  gtx('GTX'),
  fan('FAN');

  const GtexCurrencyUnit(this.code);
  final String code;
}

/// Numeric scale used by [GtexMoney] (Document F4).
enum GtexMoneySize {
  small,
  medium,
  large,
}

/// Canonical currency value widget (Master Plan Document F8 & Decision O-02).
///
/// Always displays the explicit currency code (`GTC` / `FNC` / `GTX` / `FAN`)
/// using tabular monospace figures. Pending values render in italics with a
/// clock icon so pending transactions are never mistaken for settled balances.
class GtexMoney extends StatelessWidget {
  const GtexMoney({
    super.key,
    required this.amount,
    this.unit = GtexCurrencyUnit.gtc,
    this.customCurrencyCode,
    this.isPending = false,
    this.showPlusSign = false,
    this.fractionDigits = 0,
    this.size = GtexMoneySize.medium,
  });

  final num amount;
  final GtexCurrencyUnit unit;
  final String? customCurrencyCode;
  final bool isPending;
  final bool showPlusSign;
  final int fractionDigits;
  final GtexMoneySize size;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    final String code =
        (customCurrencyCode ?? '').trim().isNotEmpty
            ? customCurrencyCode!.trim().toUpperCase()
            : unit.code;
    final bool isNegative = amount < 0;
    final String formattedNumber = _formatNumber(
      amount.abs(),
      fractionDigits: fractionDigits,
    );
    final String prefix =
        isNegative
            ? '-'
            : (showPlusSign && amount > 0)
            ? '+'
            : '';
    final String textValue = '$prefix$formattedNumber $code';

    final Color resolvedColor =
        isPending
            ? navy.warning
            : isNegative
            ? navy.danger
            : _unitColor(navy);

    final TextStyle baseStyle = switch (size) {
      GtexMoneySize.large => GtexTypography.numericL(color: resolvedColor),
      GtexMoneySize.medium => GtexTypography.numericM(color: resolvedColor),
      GtexMoneySize.small => GtexTypography.numericS(color: resolvedColor),
    };
    final TextStyle effectiveStyle =
        isPending
            ? baseStyle.copyWith(fontStyle: FontStyle.italic)
            : baseStyle;

    return Semantics(
      label: isPending ? '$textValue (Pending)' : textValue,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          if (isPending) ...<Widget>[
            Icon(
              Icons.schedule_rounded,
              key: const Key('gtex-money-pending-icon'),
              size: size == GtexMoneySize.large ? 16 : 13,
              color: resolvedColor,
            ),
            const SizedBox(width: GtexSpacing.xxs),
          ],
          Text(textValue, style: effectiveStyle),
        ],
      ),
    );
  }

  Color _unitColor(GtexColorTokens navy) {
    return switch (unit) {
      GtexCurrencyUnit.gtc || GtexCurrencyUnit.gtx => navy.currencyGtc,
      GtexCurrencyUnit.fnc || GtexCurrencyUnit.fan => navy.currencyFnc,
    };
  }

  static String _formatNumber(num value, {required int fractionDigits}) {
    final String fixed = value.toStringAsFixed(fractionDigits.clamp(0, 4));
    final List<String> parts = fixed.split('.');
    final String integerPart = parts.first.replaceAllMapped(
      RegExp(r'\B(?=(\d{3})+(?!\d))'),
      (Match _) => ',',
    );
    if (parts.length == 1 || parts[1].isEmpty) {
      return integerPart;
    }
    return '$integerPart.${parts[1]}';
  }
}
