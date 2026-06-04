import 'package:flutter/material.dart';

import '../domain/gtex_surface_state.dart';
import 'gtex_state_panel.dart';

class GtexCommandAction {
  const GtexCommandAction({
    required this.id,
    required this.label,
    required this.description,
    required this.icon,
    required this.onSelected,
    this.isEnabled = true,
    this.state = GtexSurfaceState.confirmed,
    this.routePath,
  });

  factory GtexCommandAction.route({
    required String id,
    required String label,
    required String description,
    required IconData icon,
    required String routePath,
    required ValueChanged<String> onRouteSelected,
    bool isEnabled = true,
    GtexSurfaceState state = GtexSurfaceState.confirmed,
  }) {
    return GtexCommandAction(
      id: id,
      label: label,
      description: description,
      icon: icon,
      routePath: routePath,
      isEnabled: isEnabled,
      state: state,
      onSelected: () => onRouteSelected(routePath),
    );
  }

  final String id;
  final String label;
  final String description;
  final IconData icon;
  final VoidCallback onSelected;
  final bool isEnabled;
  final GtexSurfaceState state;
  final String? routePath;

  bool get canSelect =>
      isEnabled &&
      state != GtexSurfaceState.loading &&
      state != GtexSurfaceState.blocked &&
      state != GtexSurfaceState.error;
}

Future<void> showGtexCommandPalette({
  required BuildContext context,
  required List<GtexCommandAction> actions,
  GtexSurfaceState state = GtexSurfaceState.confirmed,
}) {
  return showDialog<void>(
    context: context,
    builder:
        (BuildContext context) =>
            GtexCommandPalette(actions: actions, state: state),
  );
}

class GtexCommandPalette extends StatefulWidget {
  const GtexCommandPalette({
    super.key,
    required this.actions,
    this.state = GtexSurfaceState.confirmed,
  });

  final List<GtexCommandAction> actions;
  final GtexSurfaceState state;

  @override
  State<GtexCommandPalette> createState() => _GtexCommandPaletteState();
}

class _GtexCommandPaletteState extends State<GtexCommandPalette> {
  final TextEditingController _controller = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final List<GtexCommandAction> visible = widget.actions
        .where((GtexCommandAction action) {
          final String q = _query.trim().toLowerCase();
          if (q.isEmpty) {
            return true;
          }
          return action.label.toLowerCase().contains(q) ||
              action.description.toLowerCase().contains(q) ||
              (action.routePath?.toLowerCase().contains(q) ?? false);
        })
        .toList(growable: false);
    return Dialog(
      insetPadding: const EdgeInsets.all(18),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 720, maxHeight: 620),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              TextField(
                controller: _controller,
                autofocus: true,
                onChanged: (String value) => setState(() => _query = value),
                decoration: const InputDecoration(
                  prefixIcon: Icon(Icons.search_rounded),
                  hintText: 'Search commands',
                ),
              ),
              const SizedBox(height: 12),
              if (!_isConfirmedLike(widget.state)) ...<Widget>[
                GtexStateBanner(
                  state: widget.state,
                  title: gtexSurfaceTitleFor(widget.state),
                  message: gtexSurfaceMessageFor(widget.state),
                  dense: true,
                ),
                const SizedBox(height: 12),
              ],
              Flexible(
                child:
                    visible.isEmpty
                        ? widget.actions.isEmpty &&
                                !_isConfirmedLike(widget.state)
                            ? GtexStatePanel(
                              state: widget.state,
                              eyebrow: 'COMMANDS',
                              title: gtexSurfaceTitleFor(widget.state),
                              message: gtexSurfaceMessageFor(widget.state),
                            )
                            : Center(
                              child: Padding(
                                padding: const EdgeInsets.all(24),
                                child: Text(
                                  'No command matches this search.',
                                  style: theme.textTheme.bodyMedium,
                                ),
                              ),
                            )
                        : ListView.separated(
                          shrinkWrap: true,
                          itemCount: visible.length,
                          separatorBuilder:
                              (BuildContext context, int index) =>
                                  const Divider(height: 1),
                          itemBuilder: (BuildContext context, int index) {
                            final GtexCommandAction action = visible[index];
                            final String? routePath = _clean(action.routePath);
                            final bool canSelect = action.canSelect;
                            return ListTile(
                              enabled: canSelect,
                              leading: Icon(action.icon),
                              title: Text(action.label),
                              subtitle: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisSize: MainAxisSize.min,
                                children: <Widget>[
                                  Text(action.description),
                                  if (routePath != null) ...<Widget>[
                                    const SizedBox(height: 4),
                                    Text(
                                      routePath,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: theme.textTheme.labelSmall
                                          ?.copyWith(
                                            color: theme.colorScheme.onSurface
                                                .withValues(alpha: 0.56),
                                            fontWeight: FontWeight.w700,
                                            letterSpacing: 0,
                                          ),
                                    ),
                                  ],
                                ],
                              ),
                              trailing:
                                  routePath == null &&
                                          _isConfirmedLike(action.state)
                                      ? null
                                      : Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: <Widget>[
                                          if (!_isConfirmedLike(action.state))
                                            GtexSurfaceStateBadge(
                                              state: action.state,
                                              compact: true,
                                            ),
                                          if (routePath != null) ...<Widget>[
                                            const SizedBox(width: 8),
                                            const Icon(
                                              Icons.arrow_forward_rounded,
                                            ),
                                          ],
                                        ],
                                      ),
                              onTap:
                                  canSelect
                                      ? () {
                                        Navigator.of(context).pop();
                                        action.onSelected();
                                      }
                                      : null,
                            );
                          },
                        ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

bool _isConfirmedLike(GtexSurfaceState state) {
  return state == GtexSurfaceState.confirmed || state == GtexSurfaceState.data;
}

String? _clean(String? value) {
  final String? trimmed = value?.trim();
  if (trimmed == null || trimmed.isEmpty) {
    return null;
  }
  return trimmed;
}
