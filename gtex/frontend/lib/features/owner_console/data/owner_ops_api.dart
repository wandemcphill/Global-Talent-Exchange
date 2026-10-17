import 'package:flutter/material.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

/// Owner console operations over the existing `/owner/*` backend.
abstract class OwnerOpsClient {
  Future<Map<String, dynamic>> get(String path, {Map<String, Object?> query});

  Future<Map<String, dynamic>> post(String path, {Object? body});

  Future<Map<String, dynamic>> put(String path, {Object? body});
}

class GteOwnerOpsClient implements OwnerOpsClient {
  GteOwnerOpsClient(this.client);

  final GteAuthedApi client;

  Map<String, dynamic> _wrap(Object? v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{'items': v};

  @override
  Future<Map<String, dynamic>> get(String path, {Map<String, Object?> query = const <String, Object?>{}}) async =>
      _wrap(await client.request('GET', path, query: query));

  @override
  Future<Map<String, dynamic>> post(String path, {Object? body}) async => _wrap(await client.post(path, body: body));

  @override
  Future<Map<String, dynamic>> put(String path, {Object? body}) async => _wrap(await client.request('PUT', path, body: body));
}

double opsNum(Object? v) => v is num ? v.toDouble() : double.tryParse('${v ?? ''}') ?? 0;

int opsInt(Object? v) => opsNum(v).round();

String opsStr(Object? v, [String fallback = '-']) {
  final String s = '${v ?? ''}'.trim();
  return s.isEmpty || s == 'null' ? fallback : s;
}

Map<String, dynamic> opsMap(Object? v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};

List<Map<String, dynamic>> opsMaps(Object? v) =>
    v is List ? v.whereType<Map>().map((Map m) => Map<String, dynamic>.from(m)).toList() : <Map<String, dynamic>>[];

String opsLabel(Object? v) => opsStr(v, '').replaceAll('_', ' ');

String opsFmt(Object? v, {int digits = 0}) {
  final double n = opsNum(v);
  final String fixed = n.toStringAsFixed(n % 1 == 0 ? 0 : digits);
  final List<String> parts = fixed.split('.');
  final String whole = parts.first.replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+$)'), (Match m) => '${m[1]},');
  return parts.length > 1 ? '$whole.${parts[1]}' : whole;
}

String opsGtx(Object? v) => '${opsFmt(v, digits: 2)} GTX';

String opsError(Object e) => e is GteApiException ? e.message : '$e'.replaceFirst('Exception: ', '');

/// Runs an owner action, shows a snackbar with the result and returns the response (null on failure).
Future<Map<String, dynamic>?> runOwnerAction(
  BuildContext context,
  Future<Map<String, dynamic>> Function() call, {
  String Function(Map<String, dynamic> r)? success,
}) async {
  final ScaffoldMessengerState? messenger = ScaffoldMessenger.maybeOf(context);
  try {
    final Map<String, dynamic> r = await call();
    if (success != null) messenger?.showSnackBar(SnackBar(content: Text(success(r)), key: const Key('owner-ops-snackbar')));
    return r;
  } catch (e) {
    messenger?.showSnackBar(SnackBar(content: Text(opsError(e)), backgroundColor: GtexColors.red, key: const Key('owner-ops-error')));
    return null;
  }
}

/// Loads one endpoint with skeleton, retry and a reload hook for the builder.
class OpsLoader extends StatefulWidget {
  const OpsLoader({super.key, required this.load, required this.builder, this.label = 'Loading'});

  final Future<Map<String, dynamic>> Function() load;
  final Widget Function(BuildContext context, Map<String, dynamic> data, VoidCallback reload) builder;
  final String label;

  @override
  State<OpsLoader> createState() => _OpsLoaderState();
}

class _OpsLoaderState extends State<OpsLoader> {
  late Future<Map<String, dynamic>> _future = widget.load();

  void _reload() => setState(() {
    _future = widget.load();
  });

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Map<String, dynamic>>(
      future: _future,
      builder: (BuildContext context, AsyncSnapshot<Map<String, dynamic>> snap) {
        if (snap.connectionState != ConnectionState.done) return const GtexSkeleton.box(height: 120);
        if (snap.hasError || !snap.hasData) {
          return GtexBlockedState(
            title: '${widget.label} unavailable',
            reason: snap.error == null ? 'No response' : opsError(snap.error!),
            severity: GtexBlockedSeverity.warning,
            icon: Icons.cloud_off_rounded,
            ctaLabel: 'Retry',
            ctaAction: _reload,
          );
        }
        return widget.builder(context, snap.data!, _reload);
      },
    );
  }
}

class OpsStat extends StatelessWidget {
  const OpsStat(this.label, this.value, {super.key, this.color = GtexColors.text});

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: 150,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(label.toUpperCase(), style: const TextStyle(color: GtexColors.textMuted, fontSize: 10, letterSpacing: 1)),
        const SizedBox(height: 2),
        Text(value, style: TextStyle(color: color, fontWeight: FontWeight.w800, fontSize: 15)),
      ],
    ),
  );
}

class OpsField extends StatelessWidget {
  const OpsField({super.key, required this.controller, required this.label, this.number = false, this.width = 200, this.onChanged});

  final TextEditingController controller;
  final String label;
  final bool number;
  final double width;
  final ValueChanged<String>? onChanged;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: width,
    child: TextField(
      controller: controller,
      onChanged: onChanged,
      keyboardType: number ? const TextInputType.numberWithOptions(decimal: true) : TextInputType.text,
      style: const TextStyle(color: GtexColors.text),
      decoration: InputDecoration(labelText: label, isDense: true, border: const OutlineInputBorder()),
    ),
  );
}

class OpsSelect extends StatelessWidget {
  const OpsSelect({super.key, required this.value, required this.options, required this.hint, required this.onChanged});

  final String? value;
  final List<(String, String)> options;
  final String hint;
  final ValueChanged<String?> onChanged;

  @override
  Widget build(BuildContext context) => DropdownButton<String>(
    value: options.any(((String, String) o) => o.$1 == value) ? value : null,
    hint: Text(hint, style: const TextStyle(color: GtexColors.textSecondary)),
    dropdownColor: GtexColors.panelStrong,
    style: const TextStyle(color: GtexColors.text),
    onChanged: onChanged,
    items: <DropdownMenuItem<String>>[
      for (final (String id, String name) in options) DropdownMenuItem<String>(value: id, child: Text(name)),
    ],
  );
}

class OpsLine extends StatelessWidget {
  const OpsLine({super.key, required this.title, this.subtitle, this.trailing, this.accent = GtexColors.cyan, this.onTap});

  final String title;
  final String? subtitle;
  final Widget? trailing;
  final Color accent;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => InkWell(
    onTap: onTap,
    child: Container(
      margin: const EdgeInsets.only(bottom: GtexSpacing.xs),
      padding: const EdgeInsets.all(GtexSpacing.sm),
      decoration: BoxDecoration(
        color: GtexColors.panelStrong,
        borderRadius: BorderRadius.circular(8),
        border: Border(left: BorderSide(color: accent, width: 3)),
      ),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(title, style: const TextStyle(color: GtexColors.text, fontWeight: FontWeight.w700)),
                if (subtitle != null && subtitle!.isNotEmpty)
                  Text(subtitle!, style: const TextStyle(color: GtexColors.textSecondary, fontSize: 12)),
              ],
            ),
          ),
          if (trailing != null) trailing!,
        ],
      ),
    ),
  );
}

class OpsNote extends StatelessWidget {
  const OpsNote(this.text, {super.key, this.color = GtexColors.textMuted});

  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: GtexSpacing.xs),
    child: Text(text, style: TextStyle(color: color, fontSize: 12)),
  );
}

Widget opsList(List<Widget> children) => ListView.separated(
  padding: const EdgeInsets.all(GtexSpacing.md),
  itemCount: children.length,
  separatorBuilder: (_, __) => const SizedBox(height: GtexSpacing.md),
  itemBuilder: (_, int i) => children[i],
);

Widget opsNoClub() => const GtexEmptyState(
  title: 'No club yet',
  message: 'Create and activate a club in Club Setup first.',
  icon: Icons.shield_outlined,
  accent: GtexColors.gold,
);
