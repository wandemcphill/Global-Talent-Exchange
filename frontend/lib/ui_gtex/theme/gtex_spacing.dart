import 'package:flutter/material.dart';

class GtexSpacing {
  const GtexSpacing._();

  static const double xxs = 4;
  static const double xs = 8;
  static const double sm = 12;
  static const double md = 16;
  static const double lg = 20;
  static const double xl = 24;
  static const double xxl = 32;
  static const double xxxl = 40;
  static const double base = 16;
  static const double section = 64;

  static const double radiusSm = 4;
  static const double radiusMd = 8;
  static const double radiusLg = 12;
  static const double radiusXl = 16;
  static const double radiusPill = 999;

  /// Canonical Document F5 layout & touch target tokens.
  static const double marginPhone = 16;
  static const double marginTablet = 24;
  static const double marginDesktop = 32;
  static const double cardPaddingValue = 16;
  static const double listRowMinHeight = 56;
  static const double sectionGap = 24;
  static const double minTouchTarget = 48;
  static const double maxContentWidth = 1280;

  static const EdgeInsets screenPadding = EdgeInsets.all(lg);
  static const EdgeInsets panelPadding = EdgeInsets.all(md);
  static const EdgeInsets cardPadding = EdgeInsets.all(md);

  static double screenMarginForWidth(double width) {
    if (width >= GtexBreakpoints.desktop) {
      return marginDesktop;
    }
    if (width >= GtexBreakpoints.mobile) {
      return marginTablet;
    }
    return marginPhone;
  }
}

class GtexRadius {
  const GtexRadius._();

  static const double xs = 4;
  static const double sm = 6;
  static const double md = 8;
  static const double lg = 12;
  static const double xl = 16;
  static const double pill = 999;

  /// Canonical Document F5 radius tokens (6 chip/input, 10 card, 16 sheet/hero, pill).
  static const double chip = 6;
  static const double input = 6;
  static const double card = 10;
  static const double sheet = 16;
  static const double hero = 16;
  static const double badge = pill;
}

class GtexGrid {
  const GtexGrid._();

  static const int phoneColumns = 4;
  static const int tabletColumns = 8;
  static const int desktopColumns = 12;
  static const double gutter = 16;
  static const double maxContentWidth = 1280;

  static int columnsForWidth(double width) {
    if (width >= GtexBreakpoints.desktop) {
      return desktopColumns;
    }
    if (width >= GtexBreakpoints.mobile) {
      return tabletColumns;
    }
    return phoneColumns;
  }
}

class GtexElevation {
  const GtexElevation._();

  static const BoxShadow card = BoxShadow(
    color: Color(0x33000000),
    blurRadius: 12,
    offset: Offset(0, 4),
  );
  static const BoxShadow panel = BoxShadow(
    color: Color(0x44000000),
    blurRadius: 24,
    offset: Offset(0, 8),
  );
  static const BoxShadow modal = BoxShadow(
    color: Color(0x66000000),
    blurRadius: 40,
    offset: Offset(0, 16),
  );
}

class GtexBreakpoints {
  const GtexBreakpoints._();

  static const double mobile = 720;
  static const double tablet = 1024;
  static const double desktop = 1280;

  static bool isCompact(BuildContext context) =>
      MediaQuery.sizeOf(context).width < mobile;

  static bool isMedium(BuildContext context) {
    final double width = MediaQuery.sizeOf(context).width;
    return width >= mobile && width < desktop;
  }

  static bool isWide(BuildContext context) =>
      MediaQuery.sizeOf(context).width >= desktop;
}
