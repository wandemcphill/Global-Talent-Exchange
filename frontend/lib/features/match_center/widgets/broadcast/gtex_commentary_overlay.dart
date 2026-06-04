import 'package:flutter/material.dart';

class GtexCommentaryOverlay extends StatelessWidget {
  const GtexCommentaryOverlay({
    super.key,
    required this.commentary,
    this.detail,
  });

  final String? commentary;
  final String? detail;

  @override
  Widget build(BuildContext context) {
    final bool visible = commentary?.trim().isNotEmpty == true;
    return Align(
      alignment: Alignment.bottomLeft,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(18, 0, 18, 24),
        child: AnimatedOpacity(
          duration: const Duration(milliseconds: 200),
          opacity: visible ? 1 : 0,
          child:
              visible
                  ? Container(
                    constraints: const BoxConstraints(maxWidth: 320),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 12,
                    ),
                    decoration: BoxDecoration(
                      color: const Color(0xD90A1824),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color: Colors.white.withValues(alpha: 0.08),
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: <Widget>[
                        Text(
                          commentary!,
                          style: Theme.of(
                            context,
                          ).textTheme.bodyMedium?.copyWith(
                            color: Colors.white,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        if (detail?.trim().isNotEmpty == true) ...<Widget>[
                          const SizedBox(height: 4),
                          Text(
                            detail!,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context).textTheme.bodySmall
                                ?.copyWith(color: Colors.white70),
                          ),
                        ],
                      ],
                    ),
                  )
                  : const SizedBox.shrink(),
        ),
      ),
    );
  }
}
