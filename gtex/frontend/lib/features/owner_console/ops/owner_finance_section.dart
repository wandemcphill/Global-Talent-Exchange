import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';
import 'package:url_launcher/url_launcher.dart';

import '../data/owner_ops_api.dart';

/// Where Paystack sends the owner back after paying (hash route works at any base href).
String ownerPaymentCallbackUrl([Uri? base]) {
  final Uri b = base ?? Uri.base;
  return '${b.origin}${b.path}#/payment/callback';
}

const List<(String, String)> _balanceRows = <(String, String)>[
  ('withdrawable', 'Withdrawable'), ('non_withdrawable', 'Non-withdrawable'), ('earned', 'Earned'), ('deposited', 'Deposited'),
  ('promotional', 'Promotional'), ('pending_review', 'Pending review'), ('exchange_activity', 'Exchange & traders'),
];

class FinanceSection extends StatelessWidget {
  const FinanceSection({super.key, required this.client, required this.onNavigate, this.launch});

  final OwnerOpsClient client;
  final ValueChanged<String> onNavigate;
  final Future<bool> Function(Uri uri)? launch;

  @override
  Widget build(BuildContext context) {
    return OpsLoader(
      key: const Key('owner-finance'),
      label: 'Finance',
      load: () => client.get('/owner/finance'),
      builder: (BuildContext context, Map<String, dynamic> d, VoidCallback reload) {
        final Map<String, dynamic> w = opsMap(d['wallet']);
        return opsList(<Widget>[
          GtexPanel(
            key: const Key('owner-finance-balances'),
            title: 'Balances',
            subtitle: 'One GTEX wallet for the exchange, coin traders and your clubs',
            accent: GtexColors.pitch,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Wrap(spacing: GtexSpacing.md, runSpacing: GtexSpacing.sm, children: <Widget>[
                  OpsStat('GTEX Coin total', opsGtx(w['gtex_total']), key: const Key('owner-finance-gtex-total'), color: GtexColors.pitch),
                  OpsStat('Fan Coin', '${opsFmt(w['fan_total'])} FAN', color: GtexColors.gold),
                  for (final (String k, String l) in _balanceRows) OpsStat(l, opsFmt(w[k], digits: 2)),
                ]),
                const OpsNote('Fan Coin is for gifting and fan actions and is never withdrawable. Promotional grants can be spent but not withdrawn.'),
              ],
            ),
          ),
          for (final Map<String, dynamic> c in opsMaps(d['clubs']))
            GtexPanel(
              key: Key('owner-finance-treasury-${c['club_id']}'),
              title: opsStr(c['club_name']),
              subtitle: 'Club treasury',
              accent: GtexColors.gold,
              child: Wrap(spacing: GtexSpacing.md, runSpacing: GtexSpacing.sm, children: <Widget>[
                OpsStat('Cash', opsGtx(c['cash_gtex'])),
                OpsStat('Distributable', opsGtx(c['distributable'])),
                OpsStat('Held payouts', opsGtx(c['pending_payouts'])),
                for (final MapEntry<String, dynamic> e in opsMap(c['earnings_sources']).entries) OpsStat(opsLabel(e.key), opsFmt(e.value)),
              ]),
            ),
          _DepositPanel(client: client, data: d, launch: launch ?? (Uri u) => launchUrl(u, webOnlyWindowName: '_self')),
          _WithdrawPanel(client: client, rates: opsMap(d['treasury_rates']), onDone: reload),
          if (opsMaps(d['withdrawals']).isNotEmpty)
            GtexPanel(
              key: const Key('owner-finance-withdrawals'),
              title: 'Withdrawals',
              accent: GtexColors.cyan,
              child: Column(children: <Widget>[
                for (final Map<String, dynamic> x in opsMaps(d['withdrawals']))
                  OpsLine(
                    title: '${opsFmt(x['amount_coin'])} GTX → ${opsStr(x['bank_name'])} ••${opsStr(x['account_last4'])}',
                    trailing: GtexStatusChip(label: opsLabel(x['status']), color: x['status'] == 'approved' ? GtexColors.pitch : x['status'] == 'rejected' ? GtexColors.red : GtexColors.gold, compact: true),
                  ),
              ]),
            ),
          _LedgerPanel(rows: opsMaps(d['ledger'])),
          _FanCoinPanel(client: client, rate: opsNum(d['fan_coin_per_gtex']), onDone: reload),
          _SupportUnitsPanel(client: client, data: d, onDone: reload),
          GtexPanel(
            key: const Key('owner-finance-coin-traders'),
            title: 'Coin traders',
            subtitle: 'Buy or sell GTEX Coin with verified traders',
            accent: GtexColors.cyan,
            child: Align(
              alignment: Alignment.centerLeft,
              child: GtexActionButton(label: 'Open coin trader desk', icon: Icons.currency_exchange_rounded, compact: true, secondary: true, onPressed: () => onNavigate('/app/coin-traders')),
            ),
          ),
        ]);
      },
    );
  }
}

class _DepositPanel extends StatefulWidget {
  const _DepositPanel({required this.client, required this.data, required this.launch});

  final OwnerOpsClient client;
  final Map<String, dynamic> data;
  final Future<bool> Function(Uri uri) launch;

  @override
  State<_DepositPanel> createState() => _DepositPanelState();
}

class _DepositPanelState extends State<_DepositPanel> {
  final TextEditingController _amount = TextEditingController(text: '5000');
  bool _busy = false;

  @override
  void dispose() {
    _amount.dispose();
    super.dispose();
  }

  Future<void> _pay() async {
    setState(() => _busy = true);
    final Map<String, dynamic>? r = await runOwnerAction(context, () => widget.client.post('/owner/deposits/init', body: <String, Object?>{
      'amount_ngn': opsNum(_amount.text),
      'callback_url': ownerPaymentCallbackUrl(),
    }));
    if (r != null && r['authorization_url'] != null) await widget.launch(Uri.parse('${r['authorization_url']}'));
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final Map<String, dynamic> rates = opsMap(widget.data['treasury_rates']);
    final double rate = opsNum(rates['deposit_rate']);
    final double ngn = opsNum(_amount.text);
    final double coins = rates['deposit_direction'] == 'coin_per_fiat' ? ngn * rate : ngn / (rate == 0 ? 1 : rate);
    final bool configured = widget.data['paystack_configured'] == true;
    return GtexPanel(
      key: const Key('owner-finance-deposit'),
      title: 'Deposit',
      subtitle: 'Paystack · NGN${widget.data['paystack_mode'] == 'live' ? ' · live payments' : ''}',
      accent: GtexColors.pitch,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          OpsField(key: const Key('owner-deposit-amount'), controller: _amount, label: 'Amount (₦)', number: true, onChanged: (_) => setState(() {})),
          OpsNote('You receive ${opsFmt(coins, digits: 2)} GTX at the treasury rate of ₦${opsFmt(rate)} per GTEX Coin.', key: const Key('owner-deposit-preview'), color: GtexColors.textSecondary),
          const SizedBox(height: GtexSpacing.sm),
          GtexActionButton(key: const Key('owner-deposit-button'), label: _busy ? 'Opening Paystack...' : 'Pay with Paystack', icon: Icons.payments_rounded, onPressed: configured && !_busy && ngn >= 100 ? _pay : null),
          if (!configured) const OpsNote('Paystack keys are not connected yet, so Naira deposits are switched off.', key: Key('owner-deposit-not-configured'), color: GtexColors.gold),
          const OpsNote('Deposits credit your wallet as "deposited" GTEX Coin after Paystack verification.'),
        ],
      ),
    );
  }
}

class _WithdrawPanel extends StatefulWidget {
  const _WithdrawPanel({required this.client, required this.rates, required this.onDone});

  final OwnerOpsClient client;
  final Map<String, dynamic> rates;
  final VoidCallback onDone;

  @override
  State<_WithdrawPanel> createState() => _WithdrawPanelState();
}

class _WithdrawPanelState extends State<_WithdrawPanel> {
  final TextEditingController _amount = TextEditingController();
  final TextEditingController _bank = TextEditingController();
  final TextEditingController _number = TextEditingController();
  final TextEditingController _name = TextEditingController();
  Map<String, dynamic>? _elig;

  @override
  void initState() {
    super.initState();
    _check();
  }

  @override
  void dispose() {
    for (final TextEditingController c in <TextEditingController>[_amount, _bank, _number, _name]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _check() async {
    try {
      final Map<String, dynamic> e = await widget.client.get('/owner/withdrawals/eligibility', query: <String, Object?>{'amount': opsNum(_amount.text) > 0 ? opsNum(_amount.text) : 1});
      if (mounted) setState(() => _elig = e);
    } catch (_) {}
  }

  Future<void> _submit() async {
    final Map<String, dynamic>? r = await runOwnerAction(
      context,
      () => widget.client.post('/owner/withdrawals', body: <String, Object?>{'amount_coin': opsNum(_amount.text), 'bank_name': _bank.text.trim(), 'account_number': _number.text.trim(), 'account_name': _name.text.trim()}),
      success: (_) => 'Withdrawal submitted for review',
    );
    if (r != null) widget.onDone();
  }

  @override
  Widget build(BuildContext context) {
    final double rate = opsNum(widget.rates['withdrawal_rate']);
    final double coins = opsNum(_amount.text);
    final double ngn = widget.rates['withdrawal_direction'] == 'coin_per_fiat' ? coins / (rate == 0 ? 1 : rate) : coins * rate;
    final Map<String, dynamic>? e = _elig;
    return GtexPanel(
      key: const Key('owner-finance-withdraw'),
      title: 'Withdraw',
      subtitle: 'Payout · reviewed by an admin, then paid by manual bank transfer',
      accent: GtexColors.gold,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Wrap(spacing: GtexSpacing.sm, runSpacing: GtexSpacing.sm, children: <Widget>[
            OpsField(key: const Key('owner-withdraw-amount'), controller: _amount, label: 'Amount (GTX)', number: true, width: 150, onChanged: (_) => _check()),
            OpsField(key: const Key('owner-withdraw-bank'), controller: _bank, label: 'Bank', width: 170),
            OpsField(key: const Key('owner-withdraw-account-number'), controller: _number, label: '10-digit NUBAN', width: 170),
            OpsField(key: const Key('owner-withdraw-account-name'), controller: _name, label: 'Account name', width: 200),
          ]),
          if (e != null) ...<Widget>[
            const SizedBox(height: GtexSpacing.sm),
            Wrap(key: const Key('owner-withdraw-eligibility'), spacing: GtexSpacing.xs, runSpacing: GtexSpacing.xs, children: <Widget>[
              for (final MapEntry<String, dynamic> c in opsMap(e['checks']).entries)
                GtexStatusChip(label: opsLabel(c.key), color: c.value == true ? GtexColors.pitch : GtexColors.red, compact: true),
              GtexStatusChip(label: 'Integrity ${opsStr(e['integrity_score'])}', color: GtexColors.cyan, compact: true),
              GtexStatusChip(label: 'KYC ${opsStr(e['kyc_status'])} · required above ${opsFmt(e['kyc_threshold'])}', color: GtexColors.textSecondary, compact: true),
            ]),
          ],
          const SizedBox(height: GtexSpacing.sm),
          GtexActionButton(
            key: const Key('owner-withdraw-submit'),
            label: coins > 0 ? 'Request withdrawal · ₦${opsFmt(ngn)}' : 'Request withdrawal',
            onPressed: e?['eligible'] == true && coins > 0 && _bank.text.isNotEmpty && _number.text.length >= 10 && _name.text.isNotEmpty ? _submit : null,
          ),
          OpsNote('Every withdrawal goes to manual fraud review. Available in: ${(e?['supported_countries'] as List<dynamic>? ?? const <dynamic>[]).join(', ')}. Only earned and deposited GTEX Coin is withdrawable.'),
        ],
      ),
    );
  }
}

class _LedgerPanel extends StatelessWidget {
  const _LedgerPanel({required this.rows});

  final List<Map<String, dynamic>> rows;

  @override
  Widget build(BuildContext context) => GtexPanel(
    key: const Key('owner-finance-ledger'),
    title: 'Unified ledger',
    subtitle: 'Gross, platform fee and net for every event',
    accent: GtexColors.cyan,
    child: Column(children: <Widget>[
      if (rows.isEmpty) const OpsNote('No ledger events yet'),
      for (final Map<String, dynamic> e in rows.take(40))
        OpsLine(
          title: '${opsLabel(e['event_type'])} · ${opsFmt(e['net_amount'], digits: 2)} ${e['currency'] == 'FAN_COIN' ? 'FAN' : 'GTX'}',
          subtitle: <String>[
            opsStr(e['memo'], ''),
            'gross ${opsFmt(e['gross_amount'], digits: 2)} · fee ${opsFmt(e['platform_fee'], digits: 2)}',
            opsLabel(e['balance_class']),
            opsStr(e['created_at'], '').split('T').first,
          ].where((String s) => s.isNotEmpty).join(' · '),
          accent: e['status'] == 'completed' ? GtexColors.pitch : e['status'] == 'reversed' ? GtexColors.red : GtexColors.gold,
          trailing: GtexStatusChip(label: opsLabel(e['status']), color: GtexColors.textSecondary, compact: true),
        ),
    ]),
  );
}

class _FanCoinPanel extends StatefulWidget {
  const _FanCoinPanel({required this.client, required this.rate, required this.onDone});

  final OwnerOpsClient client;
  final double rate;
  final VoidCallback onDone;

  @override
  State<_FanCoinPanel> createState() => _FanCoinPanelState();
}

class _FanCoinPanelState extends State<_FanCoinPanel> {
  final TextEditingController _amount = TextEditingController(text: '100');

  @override
  void dispose() {
    _amount.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => GtexPanel(
    key: const Key('owner-finance-fan-coin'),
    title: 'Fan Coin',
    subtitle: 'Convert GTEX Coin at 1 : ${opsFmt(widget.rate)} for gifts and fan actions',
    accent: GtexColors.gold,
    child: Wrap(spacing: GtexSpacing.sm, crossAxisAlignment: WrapCrossAlignment.center, children: <Widget>[
      OpsField(key: const Key('owner-fan-coin-amount'), controller: _amount, label: 'GTX to convert', number: true, width: 150),
      GtexActionButton(
        key: const Key('owner-fan-coin-buy'),
        label: 'Convert',
        compact: true,
        secondary: true,
        onPressed: () async {
          final Map<String, dynamic>? r = await runOwnerAction(context, () => widget.client.post('/owner/fan-coin/buy', body: <String, Object?>{'amount': opsNum(_amount.text)}), success: (Map<String, dynamic> r) => '+${opsFmt(r['fan_coin'])} Fan Coin');
          if (r != null) widget.onDone();
        },
      ),
    ]),
  );
}

class _SupportUnitsPanel extends StatefulWidget {
  const _SupportUnitsPanel({required this.client, required this.data, required this.onDone});

  final OwnerOpsClient client;
  final Map<String, dynamic> data;
  final VoidCallback onDone;

  @override
  State<_SupportUnitsPanel> createState() => _SupportUnitsPanelState();
}

class _SupportUnitsPanelState extends State<_SupportUnitsPanel> {
  final TextEditingController _units = TextEditingController(text: '1');
  List<(String, String)> _world = const <(String, String)>[];
  String? _club;

  @override
  void initState() {
    super.initState();
    widget.client.get('/owner/world/clubs').then((Map<String, dynamic> r) {
      if (!mounted) return;
      setState(() => _world = <(String, String)>[
        for (final Map<String, dynamic> c in opsMaps(r['clubs'])) ('${c['club_id']}', '${opsStr(c['club_name'])}${c['multi_club_group'] == true ? ' (multi-club group)' : ''}'),
      ]);
    }, onError: (Object _) {});
  }

  @override
  void dispose() {
    _units.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final double price = opsNum(widget.data['support_unit_price']);
    return GtexPanel(
      key: const Key('owner-finance-support-units'),
      title: 'Club Support Units',
      subtitle: 'Supporter memberships',
      accent: GtexColors.purple,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const OpsNote('Support Units are supporter memberships. They are not shares, not an investment, and carry no dividends, returns or ownership rights.', color: GtexColors.gold),
          Wrap(spacing: GtexSpacing.sm, crossAxisAlignment: WrapCrossAlignment.center, children: <Widget>[
            OpsSelect(key: const Key('owner-support-club-select'), value: _club, options: _world, hint: 'Choose a club', onChanged: (String? v) => setState(() => _club = v)),
            OpsField(key: const Key('owner-support-units'), controller: _units, label: 'Units', number: true, width: 90, onChanged: (_) => setState(() {})),
            GtexActionButton(
              key: const Key('owner-support-buy'),
              label: 'Support · ${opsFmt(opsNum(_units.text) * price)} GTX',
              compact: true,
              onPressed: _club == null
                  ? null
                  : () async {
                      final Map<String, dynamic>? r = await runOwnerAction(context, () => widget.client.post('/owner/support-units/buy', body: <String, Object?>{'club_id': _club, 'units': opsInt(_units.text)}), success: (Map<String, dynamic> r) => 'You now hold ${r['units']} units · ${opsStr(r['tier'])}');
                      if (r != null) widget.onDone();
                    },
            ),
          ]),
          for (final Map<String, dynamic> h in opsMaps(widget.data['support_units']))
            OpsLine(title: '${opsStr(h['club_name'])} · ${h['units']} units · ${opsStr(h['tier'])}', subtitle: (h['benefits'] as List<dynamic>? ?? const <dynamic>[]).join(' · '), accent: GtexColors.purple),
        ],
      ),
    );
  }
}

/// Paystack return page: verifies the reference, then sends the owner back to the console.
class OwnerPaymentCallbackScreen extends StatefulWidget {
  const OwnerPaymentCallbackScreen({super.key, required this.client, required this.reference, required this.onDone});

  final OwnerOpsClient client;
  final String? reference;
  final VoidCallback onDone;

  @override
  State<OwnerPaymentCallbackScreen> createState() => _OwnerPaymentCallbackScreenState();
}

class _OwnerPaymentCallbackScreenState extends State<OwnerPaymentCallbackScreen> {
  String _message = 'Verifying your Paystack payment';
  bool? _ok;

  @override
  void initState() {
    super.initState();
    final String ref = (widget.reference ?? '').trim();
    if (ref.isEmpty) {
      _message = 'Missing payment reference.';
      _ok = false;
      return;
    }
    widget.client.get('/owner/deposits/verify/$ref').then((Map<String, dynamic> r) {
      if (!mounted) return;
      final bool ok = r['status'] == 'success';
      setState(() {
        _ok = ok;
        _message = ok ? 'Payment verified. GTEX Coin has been added to your wallet.' : 'Payment was not successful. No coins were credited.';
      });
    }, onError: (Object _) {
      if (mounted) {
        setState(() {
          _ok = false;
          _message = 'We could not verify this payment. If you were charged, contact support with your reference.';
        });
      }
    });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    key: const Key('owner-payment-callback'),
    backgroundColor: GtexColors.surfaceBase,
    body: Center(
      child: Padding(
        padding: const EdgeInsets.all(GtexSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            if (_ok == null) const CircularProgressIndicator(color: GtexColors.pitch) else Icon(_ok! ? Icons.check_circle_rounded : Icons.error_outline_rounded, color: _ok! ? GtexColors.pitch : GtexColors.red, size: 48),
            const SizedBox(height: GtexSpacing.md),
            Text(_message, key: const Key('owner-payment-callback-message'), textAlign: TextAlign.center, style: const TextStyle(color: GtexColors.text, fontSize: 16, fontWeight: FontWeight.w700)),
            if (widget.reference != null) OpsNote('Reference: ${widget.reference}'),
            const SizedBox(height: GtexSpacing.md),
            if (_ok != null) GtexActionButton(key: const Key('owner-payment-callback-done'), label: 'Back to Owner Console', onPressed: widget.onDone),
          ],
        ),
      ),
    ),
  );
}
