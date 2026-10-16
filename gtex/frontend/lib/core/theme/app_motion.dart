import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class AppMotion {
  const AppMotion._();

  static const Duration fast = Duration(milliseconds: 120);
  static const Duration hover = Duration(milliseconds: 200);
  static const Duration medium = Duration(milliseconds: 180);
  static const Duration slow = Duration(milliseconds: 280);

  static const Curve easeOut = Curves.easeOut;
  static const Curve easeInOut = Curves.easeInOut;
  static const Curve elasticOut = Curves.elasticOut;

  static CustomTransitionPage<T> slidePage<T>({
    required GoRouterState state,
    required Widget child,
    bool reverse = false,
  }) {
    return CustomTransitionPage<T>(
      key: state.pageKey,
      transitionDuration: slow,
      reverseTransitionDuration: medium,
      child: child,
      transitionsBuilder: (
        BuildContext context,
        Animation<double> animation,
        Animation<double> secondaryAnimation,
        Widget child,
      ) {
        final Animation<double> opacity = CurvedAnimation(
          parent: animation,
          curve: easeInOut,
          reverseCurve: easeOut,
        );
        final Animation<Offset> position = Tween<Offset>(
          begin: Offset(reverse ? -0.06 : 0.06, 0),
          end: Offset.zero,
        ).animate(
          CurvedAnimation(
            parent: animation,
            curve: Curves.easeOutCubic,
            reverseCurve: easeOut,
          ),
        );

        return FadeTransition(
          opacity: Tween<double>(begin: 0.88, end: 1).animate(opacity),
          child: SlideTransition(position: position, child: child),
        );
      },
    );
  }
}
