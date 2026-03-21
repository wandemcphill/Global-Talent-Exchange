import 'package:flutter/material.dart';

import '../widgets/gte_shell_theme.dart';
import 'gte_theme_controller.dart';
import 'gte_theme_registry.dart';
import 'gte_theme_scope.dart';
import 'gte_theme_tokens.dart';

class GteThemePickerSheet extends StatelessWidget {
  const GteThemePickerSheet({super.key});

  @override
  Widget build(BuildContext context) {
    final GteThemeController controller = GteThemeControllerScope.of(context);
    final GteThemeDefinition activeTheme = controller.activeTheme;
    final GteThemeTokens tokens = GteShellTheme.tokensOf(context);
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          tokens.spaceLg,
          tokens.spaceMd,
          tokens.spaceLg,
          tokens.spaceLg,
        ),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 760, maxHeight: 640),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Icon(Icons.palette_outlined, color: tokens.accent),
                  SizedBox(width: tokens.spaceSm),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Theme Lobby',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        Text(
                          'Current: ${activeTheme.metadata.label}',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    tooltip: 'Close',
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
              SizedBox(height: tokens.spaceSm),
              Text(
                'Choose the shell mood for the transfer market, club lane, and live arena.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              SizedBox(height: tokens.spaceLg),
              Expanded(
                child: ListView.separated(
                  shrinkWrap: true,
                  itemCount: GteThemeRegistry.themes.length,
                  separatorBuilder: (BuildContext context, int index) =>
                      SizedBox(height: tokens.spaceSm),
                  itemBuilder: (BuildContext context, int index) {
                    final GteThemeDefinition definition =
                        GteThemeRegistry.themes[index];
                    return _ThemeOptionTile(
                      definition: definition,
                      selected:
                          definition.metadata.id == controller.activeThemeId,
                      onSelected: () async {
                        await controller.selectTheme(definition.metadata.id);
                        if (context.mounted) {
                          Navigator.of(context).pop();
                        }
                      },
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

class _ThemeOptionTile extends StatelessWidget {
  const _ThemeOptionTile({
    required this.definition,
    required this.selected,
    required this.onSelected,
  });

  final GteThemeDefinition definition;
  final bool selected;
  final Future<void> Function() onSelected;

  @override
  Widget build(BuildContext context) {
    final GteThemeTokens activeTokens = GteShellTheme.tokensOf(context);
    final GteThemeTokens preview = definition.tokens;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(preview.radiusLarge),
        onTap: onSelected,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          padding: EdgeInsets.all(activeTokens.spaceMd),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(preview.radiusLarge),
            border: Border.all(
              color: selected ? activeTokens.accent : preview.outline,
              width: selected ? 1.6 : 1,
            ),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[
                preview.panelStrong,
                preview.panel,
                preview.backgroundSoft,
              ],
            ),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: preview.shadow.withValues(alpha: 0.16),
                blurRadius: 20,
                offset: const Offset(0, 10),
              ),
            ],
          ),
          child: Row(
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      children: <Widget>[
                        Icon(
                          definition.metadata.icon,
                          color: preview.accent,
                          size: 18,
                        ),
                        SizedBox(width: activeTokens.spaceSm),
                        Expanded(
                          child: Text(
                            definition.metadata.label,
                            style: Theme.of(context)
                                .textTheme
                                .titleMedium
                                ?.copyWith(
                                  color: preview.textPrimary,
                                ),
                          ),
                        ),
                        if (selected)
                          Icon(
                            Icons.check_circle,
                            color: activeTokens.accent,
                            size: 20,
                          ),
                      ],
                    ),
                    SizedBox(height: activeTokens.spaceXs),
                    Text(
                      definition.metadata.tagline,
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                            color: preview.accentWarm,
                          ),
                    ),
                    SizedBox(height: activeTokens.spaceXs),
                    Text(
                      definition.metadata.description,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: preview.textMuted,
                          ),
                    ),
                  ],
                ),
              ),
              SizedBox(width: activeTokens.spaceMd),
              _ThemePreviewSwatches(tokens: preview),
            ],
          ),
        ),
      ),
    );
  }
}

class _ThemePreviewSwatches extends StatelessWidget {
  const _ThemePreviewSwatches({required this.tokens});

  final GteThemeTokens tokens;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: <Color>[
        tokens.accent,
        tokens.accentArena,
        tokens.accentClub,
        tokens.accentCapital,
      ]
          .map(
            (Color color) => Container(
              width: 24,
              height: 24,
              decoration: BoxDecoration(
                color: color,
                shape: BoxShape.circle,
                border: Border.all(
                  color: tokens.surfaceHighlight.withValues(alpha: 0.2),
                ),
              ),
            ),
          )
          .toList(growable: false),
    );
  }
}
