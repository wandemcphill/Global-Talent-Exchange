import 'package:flutter/widgets.dart';

/// The one way to open a player from anywhere inside the GTEX shell.
///
/// Every surface that names a footballer - the market grid and its summary
/// panel, wallet holdings, a club squad room, a match lineup, a search
/// result - resolves to the same canonical player detail. Before this, some
/// of those surfaces were dead text and one of them (search) canonicalised
/// to the market with an unread `?player=` query, so the same player looked
/// like a different object depending on where you clicked.
///
/// This is a lookup for the shell's existing navigation callback, not a
/// second navigation tree: the shell still owns the push, and
/// `/players/:playerId/profile` remains the deep link.
class GtexPlayerNavigator extends InheritedWidget {
  const GtexPlayerNavigator({
    super.key,
    required this.openPlayer,
    required super.child,
  });

  final Future<void> Function(String playerId) openPlayer;

  /// The open callback, or null when this widget is not mounted above
  /// [context] - for example in a widget test that pumps a surface on its
  /// own. Callers must treat null as "not navigable here" rather than
  /// rendering a control that does nothing.
  static Future<void> Function(String playerId)? maybeOf(BuildContext context) {
    return context
        .dependOnInheritedWidgetOfExactType<GtexPlayerNavigator>()
        ?.openPlayer;
  }

  /// Wraps [onOpen] so a row is only tappable when there is both a player to
  /// open and a shell to open it in.
  static VoidCallback? tapToOpen(BuildContext context, String? playerId) {
    final String? id = playerId?.trim();
    if (id == null || id.isEmpty) {
      return null;
    }
    final Future<void> Function(String)? open = maybeOf(context);
    if (open == null) {
      return null;
    }
    return () => open(id);
  }

  @override
  bool updateShouldNotify(GtexPlayerNavigator oldWidget) =>
      oldWidget.openPlayer != openPlayer;
}
