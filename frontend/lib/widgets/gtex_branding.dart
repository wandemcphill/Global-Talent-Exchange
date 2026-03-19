import 'package:flutter/material.dart';

import 'gte_shell_theme.dart';
import 'gte_surface_panel.dart';

class GtexBrandAssets {
  const GtexBrandAssets._();

  static const String icon = 'assets/branding/gtex_icon.png';
  static const String logo = 'assets/branding/gtex_logo.png';
}

class GtexLogoMark extends StatelessWidget {
  const GtexLogoMark({super.key, this.size = 56, this.compact = false});

  final double size;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return SizedBox.square(
      dimension: size,
      child: Image.asset(
        GtexBrandAssets.icon,
        fit: BoxFit.contain,
        filterQuality: FilterQuality.high,
        isAntiAlias: true,
        semanticLabel: compact ? 'GTEX icon' : 'GTEX brand icon',
      ),
    );
  }
}

class GtexWordmark extends StatelessWidget {
  const GtexWordmark({super.key, this.compact = false, this.showTagline = true});

  final bool compact;
  final bool showTagline;

  @override
  Widget build(BuildContext context) {
    final TextTheme textTheme = Theme.of(context).textTheme;
    final double logoHeight = compact ? 40 : 58;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        SizedBox(
          height: logoHeight,
          child: Image.asset(
            GtexBrandAssets.logo,
            fit: BoxFit.contain,
            alignment: Alignment.centerLeft,
            filterQuality: FilterQuality.high,
            isAntiAlias: true,
            semanticLabel: 'GTEX logo',
          ),
        ),
        if (showTagline) ...<Widget>[
          const SizedBox(height: 6),
          Text(
            'Trade football upside. Run the matchday universe.',
            style: textTheme.bodySmall?.copyWith(color: GteShellTheme.textMuted),
          ),
        ],
      ],
    );
  }
}

class GtexHeroBanner extends StatelessWidget {
  const GtexHeroBanner({
    super.key,
    required this.eyebrow,
    required this.title,
    required this.description,
    required this.chips,
    this.actions = const <Widget>[],
    this.accent = GteShellTheme.accent,
    this.sidePanel,
  });

  final String eyebrow;
  final String title;
  final String description;
  final List<Widget> chips;
  final List<Widget> actions;
  final Color accent;
  final Widget? sidePanel;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: true,
      accentColor: accent,
      padding: const EdgeInsets.all(24),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: Stack(
          children: <Widget>[
            Positioned.fill(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: <Color>[
                      accent.withValues(alpha: 0.11),
                      Colors.white.withValues(alpha: 0.01),
                      GteShellTheme.accentWarm.withValues(alpha: 0.06),
                    ],
                    stops: const <double>[0, 0.52, 1],
                  ),
                ),
              ),
            ),
            Positioned(
              top: -72,
              right: -24,
              child: _GlowOrb(size: 180, color: accent.withValues(alpha: 0.18)),
            ),
            Positioned(
              bottom: -80,
              left: -22,
              child: _GlowOrb(size: 168, color: GteShellTheme.accentWarm.withValues(alpha: 0.12)),
            ),
            Padding(
              padding: const EdgeInsets.all(0),
              child: LayoutBuilder(
                builder: (BuildContext context, BoxConstraints constraints) {
                  final bool stacked = constraints.maxWidth < 900;
                  final Widget main = Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      GtexSectionBadge(label: eyebrow, color: accent),
                      const SizedBox(height: 18),
                      Text(title, style: Theme.of(context).textTheme.displaySmall),
                      const SizedBox(height: 12),
                      Text(description, style: Theme.of(context).textTheme.bodyLarge),
                      const SizedBox(height: 18),
                      Wrap(spacing: 10, runSpacing: 10, children: chips),
                      if (actions.isNotEmpty) ...<Widget>[
                        const SizedBox(height: 20),
                        Wrap(spacing: 12, runSpacing: 12, children: actions),
                      ],
                    ],
                  );
                  final Widget right =
                      sidePanel ?? _DefaultSignalPanel(accent: accent);
                  if (stacked) {
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[main, const SizedBox(height: 18), right],
                    );
                  }
                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Expanded(flex: 6, child: main),
                      const SizedBox(width: 20),
                      Expanded(flex: 4, child: right),
                    ],
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class GtexSectionBadge extends StatelessWidget {
  const GtexSectionBadge({super.key, required this.label, this.color = GteShellTheme.accent});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: color.withValues(alpha: 0.12),
        border: Border.all(color: color.withValues(alpha: 0.24)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(color: color),
      ),
    );
  }
}

class GtexSectionHeader extends StatelessWidget {
  const GtexSectionHeader({
    super.key,
    required this.eyebrow,
    required this.title,
    required this.description,
    this.accent = GteShellTheme.accent,
  });

  final String eyebrow;
  final String title;
  final String description;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        GtexSectionBadge(label: eyebrow, color: accent),
        const SizedBox(height: 10),
        Text(title, style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 6),
        Text(description, style: Theme.of(context).textTheme.bodyMedium),
      ],
    );
  }
}

class GtexSignalStrip extends StatelessWidget {
  const GtexSignalStrip({
    super.key,
    required this.title,
    required this.subtitle,
    required this.tiles,
    this.accent = GteShellTheme.accent,
  });

  final String title;
  final String subtitle;
  final List<Widget> tiles;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor: accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(title, style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 6),
                    Text(subtitle, style: Theme.of(context).textTheme.bodyMedium),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Container(
                width: 10,
                height: 10,
                decoration: BoxDecoration(
                  color: accent,
                  shape: BoxShape.circle,
                  boxShadow: <BoxShadow>[
                    BoxShadow(color: accent.withValues(alpha: 0.35), blurRadius: 14, spreadRadius: 2),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              if (constraints.maxWidth < 720) {
                return Column(
                  children: tiles
                      .map((Widget tile) => Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: tile,
                          ))
                      .toList(growable: false),
                );
              }
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: tiles
                    .map((Widget tile) => Expanded(
                          child: Padding(
                            padding: const EdgeInsets.only(right: 12),
                            child: tile,
                          ),
                        ))
                    .toList(growable: false),
              );
            },
          ),
        ],
      ),
    );
  }
}

class GtexSignalTile extends StatelessWidget {
  const GtexSignalTile({
    super.key,
    required this.label,
    required this.value,
    required this.caption,
    required this.icon,
    this.color = GteShellTheme.accent,
  });

  final String label;
  final String value;
  final String caption;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        color: Colors.white.withValues(alpha: 0.035),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              color: color.withValues(alpha: 0.12),
            ),
            child: Icon(icon, color: color, size: 20),
          ),
          const SizedBox(height: 14),
          Text(label, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 4),
          Text(value, style: Theme.of(context).textTheme.titleMedium?.copyWith(color: color)),
          const SizedBox(height: 8),
          Text(caption, style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}

class _GlowOrb extends StatelessWidget {
  const _GlowOrb({required this.size, required this.color});

  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: RadialGradient(
            colors: <Color>[color, Colors.transparent],
          ),
        ),
      ),
    );
  }
}

class _DefaultSignalPanel extends StatelessWidget {
  const _DefaultSignalPanel({required this.accent});
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            Colors.white.withValues(alpha: 0.04),
            accent.withValues(alpha: 0.12),
            GteShellTheme.accentWarm.withValues(alpha: 0.08),
          ],
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const <Widget>[
          _SignalRow(label: 'Trading Pulse', value: 'LIVE', icon: Icons.show_chart),
          SizedBox(height: 12),
          _SignalRow(label: 'E-Game Arena', value: 'SIM READY', icon: Icons.stadium_outlined),
          SizedBox(height: 12),
          _SignalRow(label: 'Wallet', value: 'CAPITAL LINKED', icon: Icons.account_balance_wallet_outlined),
        ],
      ),
    );
  }
}

class _SignalRow extends StatelessWidget {
  const _SignalRow({required this.label, required this.value, required this.icon});

  final String label;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: Colors.white12,
            borderRadius: BorderRadius.circular(14),
          ),
          child: Icon(icon, size: 18, color: GteShellTheme.textPrimary),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(label, style: Theme.of(context).textTheme.bodySmall),
              const SizedBox(height: 2),
              Text(value, style: Theme.of(context).textTheme.titleMedium),
            ],
          ),
        ),
      ],
    );
  }
}
