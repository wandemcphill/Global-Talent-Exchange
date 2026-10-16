import 'package:flutter/material.dart';

const gtexCreatorBg = Color(0xFF070B12);
const gtexCreatorPanel = Color(0xFF0B1320);
const gtexCreatorPanel2 = Color(0xFF101B2C);
const gtexCreatorGreen = Color(0xFF23F58A);
const gtexCreatorGold = Color(0xFFFFC857);
const gtexCreatorTextSoft = Color(0xFFB8C5D8);

BoxDecoration gtexCreatorPanelDecoration({bool selected = false}) {
  return BoxDecoration(
    color: selected ? gtexCreatorPanel2 : gtexCreatorPanel,
    borderRadius: BorderRadius.circular(22),
    border: Border.all(color: selected ? gtexCreatorGreen.withOpacity(.65) : Colors.white.withOpacity(.07)),
    boxShadow: [
      BoxShadow(
        color: (selected ? gtexCreatorGreen : Colors.black).withOpacity(selected ? .16 : .20),
        blurRadius: 24,
        offset: const Offset(0, 16),
      ),
    ],
  );
}

class GtexPill extends StatelessWidget {
  const GtexPill({super.key, required this.label, this.color = gtexCreatorGreen});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withOpacity(.12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withOpacity(.35)),
      ),
      child: Text(label, style: TextStyle(color: color, fontWeight: FontWeight.w800, fontSize: 12)),
    );
  }
}

class GtexPanel extends StatelessWidget {
  const GtexPanel({super.key, required this.child, this.padding = const EdgeInsets.all(18), this.selected = false});

  final Widget child;
  final EdgeInsets padding;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: gtexCreatorPanelDecoration(selected: selected),
      child: child,
    );
  }
}
