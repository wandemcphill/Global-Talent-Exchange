import 'dart:math' as math;
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../data/owner_console_api.dart';
import '../data/showroom_glb.dart';

/// Lightweight club showroom. Match 3D stays on the match scene.
/// Reduced motion uses the static card instead of the turntable.
class ClubLegacyShowroom extends StatefulWidget {
  const ClubLegacyShowroom({
    super.key,
    required this.exhibits,
    this.forceStatic = false,
    this.requirePurchaseConfirm = false,
    this.onAction,
    this.loadGiftRecipients,
    this.giftOwnedAsset,
    this.onGiftCompleted,
  });

  final List<ShowroomExhibit> exhibits;
  final bool forceStatic;
  final bool requirePurchaseConfirm;
  final Future<void> Function(String action, Map<String, Object?> payload)? onAction;
  final Future<List<OwnerGiftRecipient>> Function()? loadGiftRecipients;
  final Future<void> Function({required String assetId, required String playerId})?
      giftOwnedAsset;
  final Future<void> Function()? onGiftCompleted;

  /// Resolves the H9 visibility / broadcast classification label for an exhibit.
  static String visibilityBadgeLabel(ShowroomExhibit exhibit) {
    if (exhibit.category == 'jet') {
      return 'Public Broadcast · Fleet Aviation';
    }
    if (exhibit.id.startsWith('facility:')) {
      return 'Club Facility · Infrastructure Broadcast';
    }
    return 'Private Collection · No Global Broadcast';
  }

  /// Resolves the H9 public broadcast notice shown in [GtexConfirmSheet] when
  /// purchasing an asset that triggers a global broadcast (`jet` or `facility:*`).
  static String? publicBroadcastNoticeFor(ShowroomExhibit exhibit) {
    if (exhibit.category == 'jet') {
      return 'Private jet purchases broadcast globally to the ticker and newsroom with verified price.';
    }
    if (exhibit.id.startsWith('facility:')) {
      return 'Facility upgrades debit the club ledger and publish a global infrastructure broadcast and newsroom article.';
    }
    return null;
  }

  @override
  State<ClubLegacyShowroom> createState() => _ClubLegacyShowroomState();
}

class _ClubLegacyShowroomState extends State<ClubLegacyShowroom> {
  int _index = 0;
  double _yaw = 0;
  double _pitch = 0;
  double _zoom = 1;
  int _ticket = 0;
  final Map<String, String> _purchaseIdempotencyKeys = <String, String>{};
  final Set<String> _pendingPurchases = <String>{};
  ShowroomGlb? _model;
  Object? _loadError;

  @override
  void initState() {
    super.initState();
    _loadCurrent();
  }

  ShowroomExhibit? get _current =>
      widget.exhibits.isEmpty
          ? null
          : widget.exhibits[_index.clamp(0, widget.exhibits.length - 1)];

  void _reset() {
    setState(() {
      _yaw = 0;
      _pitch = 0;
      _zoom = 1;
    });
  }

  void _turn(double delta) => setState(() => _yaw += delta);

  Future<void> _handleBuyTap(ShowroomExhibit exhibit) async {
    final String? sku = exhibit.sku;
    if (sku == null ||
        widget.onAction == null ||
        _pendingPurchases.contains(exhibit.id)) {
      return;
    }
    final String idempotencyKey = _purchaseIdempotencyKeys.putIfAbsent(
      exhibit.id,
      () => 'buy_${sku}_${DateTime.now().microsecondsSinceEpoch}',
    );
    if (!widget.requirePurchaseConfirm) {
      final bool purchased = await _purchaseAsset(
        exhibit,
        idempotencyKey: idempotencyKey,
      );
      if (purchased && mounted) await _showAssetAcquired(exhibit);
      return;
    }

    final String? broadcastNotice =
        ClubLegacyShowroom.publicBroadcastNoticeFor(exhibit);
    bool purchased = false;
    await GtexConfirmSheet.show(
      context,
      title: 'Acquire ${exhibit.name}',
      summary:
          'Buy this asset for your club collection. The club treasury pays the verified showroom price.',
      confirmLabel: 'Confirm acquisition',
      variant: GtexConfirmVariant.financial,
      idempotencyKey: idempotencyKey,
      publicAnnouncementNotice: broadcastNotice,
      financialDetails: GtexConfirmFinancialDetails(
        amountLabel: exhibit.price ?? 'Price shown by the club asset catalogue',
        currencyCode: 'GTX',
        idempotencyKey: idempotencyKey,
      ),
      onConfirm: (String resolvedKey) async {
        purchased = await _purchaseAsset(exhibit, idempotencyKey: resolvedKey);
      },
    );
    if (purchased && mounted) await _showAssetAcquired(exhibit);
  }

  Future<bool> _purchaseAsset(
    ShowroomExhibit exhibit, {
    String? idempotencyKey,
  }) async {
    final String? sku = exhibit.sku;
    final Future<void> Function(String, Map<String, Object?>)? onAction = widget.onAction;
    if (sku == null || onAction == null || _pendingPurchases.contains(exhibit.id)) {
      return false;
    }
    final String resolvedKey =
        idempotencyKey ??
        _purchaseIdempotencyKeys.putIfAbsent(
          exhibit.id,
          () => 'buy_${sku}_${DateTime.now().microsecondsSinceEpoch}',
        );
    setState(() => _pendingPurchases.add(exhibit.id));
    try {
      await onAction('purchase', <String, Object?>{
        'sku': sku,
        'idempotency_key': resolvedKey,
        'owner_class': 'club',
      });
      return true;
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Purchase failed: ${_friendlyOwnerActionError(error)}')),
        );
      }
      return false;
    } finally {
      if (mounted) {
        setState(() => _pendingPurchases.remove(exhibit.id));
      }
    }
  }

  Future<void> _giftAsset(ShowroomExhibit exhibit) async {
    final Future<void> Function(String, Map<String, Object?>)? onAction = widget.onAction;
    if (onAction == null) return;

    final Future<List<OwnerGiftRecipient>> Function()? loadRecipients =
        widget.loadGiftRecipients;
    final Future<void> Function({required String assetId, required String playerId})?
        giftOwnedAsset = widget.giftOwnedAsset;
    if (loadRecipients != null && giftOwnedAsset != null) {
      await _giftToSquadPlayer(
        exhibit,
        loadRecipients: loadRecipients,
        giftOwnedAsset: giftOwnedAsset,
      );
      return;
    }

    // Compatibility for standalone legacy showroom consumers that haven't
    // supplied the live squad gateway. The owner console uses the roster picker.
    String recipientInput = '';
    final String? recipientRef = await showDialog<String>(
      context: context,
      builder: (BuildContext dialogContext) => AlertDialog(
        title: Text('Gift ${exhibit.name}'),
        content: TextField(
          key: const Key('club-showroom-gift-recipient'),
          autofocus: true,
          onChanged: (String value) => recipientInput = value,
          decoration: const InputDecoration(
            labelText: 'Recipient GTEX user ID',
            hintText: 'Enter the intended recipient ID',
          ),
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            key: const Key('club-showroom-gift-confirm'),
            onPressed: () => Navigator.of(dialogContext).pop(recipientInput.trim()),
            child: const Text('Send gift'),
          ),
        ],
      ),
    );
    final String normalizedRef = (recipientRef ?? '').trim();
    if (!mounted || normalizedRef.isEmpty) return;
    try {
      await onAction('gift', <String, Object?>{
        'asset_id': exhibit.id,
        'recipient_ref': normalizedRef,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${exhibit.name} gift offered to ${normalizedRef.substring(0, normalizedRef.length > 8 ? 8 : normalizedRef.length)}.')),
        );
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Gift failed: ${_friendlyOwnerActionError(error)}')),
        );
      }
    }
  }

  Future<void> _giftToSquadPlayer(
    ShowroomExhibit exhibit, {
    required Future<List<OwnerGiftRecipient>> Function() loadRecipients,
    required Future<void> Function({required String assetId, required String playerId})
        giftOwnedAsset,
  }) async {
    late final Future<List<OwnerGiftRecipient>> recipientsFuture;
    try {
      recipientsFuture = loadRecipients();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not load your squad: ${_friendlyOwnerActionError(error)}')),
        );
      }
      return;
    }

    OwnerGiftRecipient? selectedPlayer;
    final OwnerGiftRecipient? recipient = await showDialog<OwnerGiftRecipient>(
      context: context,
      builder: (BuildContext dialogContext) => StatefulBuilder(
        builder: (BuildContext context, StateSetter setDialogState) => AlertDialog(
          backgroundColor: const Color(0xFF0D1726),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(24),
            side: BorderSide(color: GtexColors.gold.withValues(alpha: 0.34)),
          ),
          titlePadding: const EdgeInsets.fromLTRB(20, 20, 12, 8),
          contentPadding: const EdgeInsets.fromLTRB(14, 8, 14, 8),
          actionsPadding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
          title: Row(
            children: <Widget>[
              const Icon(Icons.card_giftcard_rounded, color: GtexColors.gold),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Choose the recipient',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ],
          ),
          content: SizedBox(
            width: 460,
            child: FutureBuilder<List<OwnerGiftRecipient>>(
              future: recipientsFuture,
              builder: (BuildContext context, AsyncSnapshot<List<OwnerGiftRecipient>> snapshot) {
                if (snapshot.connectionState != ConnectionState.done) {
                  return const SizedBox(
                    height: 180,
                    child: Center(child: CircularProgressIndicator()),
                  );
                }
                if (snapshot.hasError) {
                  return const Padding(
                    padding: EdgeInsets.all(18),
                    child: Text(
                      'Your squad could not be loaded. Close this window and try again.',
                      style: TextStyle(color: Color(0xFFB9C5D7)),
                    ),
                  );
                }
                final List<OwnerGiftRecipient> players = snapshot.data ?? const <OwnerGiftRecipient>[];
                if (players.isEmpty) {
                  return const Padding(
                    padding: EdgeInsets.all(18),
                    child: Text(
                      'No squad players are available to receive a luxury gift yet.',
                      style: TextStyle(color: Color(0xFFB9C5D7)),
                    ),
                  );
                }
                return SizedBox(
                  height: players.length > 4 ? 340 : players.length * 82.0,
                  child: ListView.separated(
                    shrinkWrap: true,
                    itemCount: players.length,
                    separatorBuilder: (_, __) => Divider(
                      height: 1,
                      color: Colors.white.withValues(alpha: 0.07),
                    ),
                    itemBuilder: (BuildContext context, int index) {
                      final OwnerGiftRecipient player = players[index];
                      final bool chosen = selectedPlayer?.id == player.id;
                      return InkWell(
                        key: Key('club-showroom-recipient-${player.id}'),
                        borderRadius: BorderRadius.circular(14),
                        onTap: () => setDialogState(() => selectedPlayer = player),
                        child: AnimatedContainer(
                          duration: const Duration(milliseconds: 180),
                          padding: const EdgeInsets.all(9),
                          decoration: BoxDecoration(
                            color: chosen ? GtexColors.gold.withValues(alpha: 0.12) : Colors.transparent,
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(
                              color: chosen ? GtexColors.gold : Colors.transparent,
                            ),
                          ),
                          child: Row(
                            children: <Widget>[
                              CircleAvatar(
                                radius: 24,
                                backgroundColor: const Color(0xFF1C2B40),
                                foregroundImage: (player.portraitUrl ?? '').startsWith('http')
                                    ? NetworkImage(player.portraitUrl!)
                                    : null,
                                child: Text(
                                  player.name.isEmpty ? '?' : player.name.substring(0, 1).toUpperCase(),
                                  style: const TextStyle(color: GtexColors.gold, fontWeight: FontWeight.w900),
                                ),
                              ),
                              const SizedBox(width: 11),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: <Widget>[
                                    Text(
                                      player.name,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900),
                                    ),
                                    const SizedBox(height: 3),
                                    Text(
                                      '${player.position}  ·  OVR ${player.rating}  ·  Morale ${player.morale}',
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(color: Color(0xFFAAB8CB), fontSize: 11),
                                    ),
                                  ],
                                ),
                              ),
                              Icon(
                                chosen ? Icons.check_circle_rounded : Icons.circle_outlined,
                                color: chosen ? GtexColors.gold : const Color(0xFF75859A),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                );
              },
            ),
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Cancel'),
            ),
            FilledButton.icon(
              key: const Key('club-showroom-gift-confirm'),
              onPressed: selectedPlayer == null ? null : () => Navigator.of(dialogContext).pop(selectedPlayer),
              icon: const Icon(Icons.redeem_rounded),
              label: const Text('Gift selected player'),
            ),
          ],
        ),
      ),
    );
    if (!mounted || recipient == null) return;

    try {
      setState(() => _pendingPurchases.add('gift:${exhibit.id}'));
      await giftOwnedAsset(assetId: exhibit.id, playerId: recipient.id);
      if (!mounted) return;
      await widget.onGiftCompleted?.call();
      if (!mounted) return;
      await _showGiftArrived(exhibit, recipient);
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Gift could not be delivered: ${_friendlyOwnerActionError(error)}')),
        );
      }
    } finally {
      if (mounted) setState(() => _pendingPurchases.remove('gift:${exhibit.id}'));
    }
  }

  Future<void> _showAssetAcquired(ShowroomExhibit exhibit) async {
    await showDialog<void>(
      context: context,
      barrierColor: Colors.black.withValues(alpha: 0.72),
      builder: (BuildContext context) => _LuxuryArrivalDialog(
        eyebrow: 'ADDED TO YOUR COLLECTION',
        title: exhibit.name,
        subtitle: 'The acquisition has been recorded for your club.',
        preview: _staticCard(exhibit),
        actionLabel: 'Back to showroom',
      ),
    );
  }

  Future<void> _showGiftArrived(
    ShowroomExhibit exhibit,
    OwnerGiftRecipient recipient,
  ) async {
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      barrierColor: Colors.black.withValues(alpha: 0.78),
      builder: (BuildContext context) => _LuxuryArrivalDialog(
        eyebrow: 'A MOMENT FOR THE HISTORY BOOKS',
        title: '${exhibit.name} gifted',
        subtitle: '${recipient.name} has received the luxury gift from the club owner. Player morale and the gift event are recorded by GTEX.',
        preview: _staticCard(exhibit),
        recipient: recipient,
        actionLabel: 'Return to collection',
      ),
    );
  }

  Future<void> _loadCurrent() async {
    final ShowroomExhibit? exhibit = _current;
    if (exhibit == null) {
      return;
    }
    final int ticket = ++_ticket;
    final String path = exhibitModelPath(
      category: exhibit.category,
      modelFile: exhibit.modelFile,
    );
    try {
      final ShowroomGlb model = await loadShowroomGlb(path);
      if (!mounted || ticket != _ticket) {
        return;
      }
      setState(() {
        _model = model;
        _loadError = null;
      });
    } catch (error) {
      if (!mounted || ticket != _ticket) {
        return;
      }
      setState(() => _loadError = error);
    }
  }

  Future<void> _openFullscreen(ShowroomExhibit exhibit, bool reduceMotion) {
    return showDialog<void>(
      context: context,
      builder:
          (BuildContext context) =>
              _ShowroomFullscreen(exhibit: exhibit, reduceMotion: reduceMotion),
    );
  }

  @override
  Widget build(BuildContext context) {
    final bool reduceMotion =
        widget.forceStatic || MediaQuery.disableAnimationsOf(context);
    final ShowroomExhibit? exhibit = _current;
    if (exhibit == null) {
      return const GtexEmptyState(
        key: Key('club-showroom-empty'),
        title: 'Showroom is empty',
        message: 'Claim a club to preview its collection.',
        icon: Icons.museum_outlined,
      );
    }
    return ListView(
      key: const Key('club-showroom'),
      padding: const EdgeInsets.all(GtexSpacing.sm),
      children: <Widget>[
        _stage(exhibit, reduceMotion),
        const SizedBox(height: GtexSpacing.sm),
        Wrap(
          spacing: GtexSpacing.xs,
          runSpacing: GtexSpacing.xs,
          children: <Widget>[
            for (int i = 0; i < widget.exhibits.length; i++)
              ChoiceChip(
                key: Key('club-showroom-pick-${widget.exhibits[i].id}'),
                label: Text(widget.exhibits[i].name),
                selected: i == _index,
                onSelected: (_) {
                  setState(() => _index = i);
                  _reset();
                  _loadCurrent();
                },
              ),
          ],
        ),
      ],
    );
  }

  Widget _assetDetails(ShowroomExhibit exhibit) {
    final String price = exhibit.price?.trim() ?? '';
    final bool hasScarcity = exhibit.supplyCap != null || exhibit.mintedCount != null;
    if (price.isEmpty && !hasScarcity) return const SizedBox.shrink();
    final String scarcity = exhibit.supplyCap != null && exhibit.mintedCount != null
        ? '${exhibit.mintedCount} of ${exhibit.supplyCap} editions minted'
        : exhibit.supplyCap != null
            ? '${exhibit.supplyCap} editions maximum'
            : exhibit.mintedCount != null
                ? '${exhibit.mintedCount} editions minted'
                : '';
    return Container(
      key: const Key('club-showroom-asset-details'),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFF0B1422),
        borderRadius: BorderRadius.circular(13),
        border: Border.all(color: GtexColors.gold.withValues(alpha: 0.22)),
      ),
      child: Row(
        children: <Widget>[
          const Icon(Icons.diamond_outlined, color: GtexColors.gold, size: 22),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                if (price.isNotEmpty)
                  Text(
                    '$price GTX',
                    style: const TextStyle(color: Color(0xFFEBD28E), fontWeight: FontWeight.w900, fontSize: 15),
                  ),
                if (scarcity.isNotEmpty)
                  Text(
                    scarcity,
                    style: const TextStyle(color: Color(0xFF9EACC0), fontSize: 10),
                  ),
              ],
            ),
          ),
          if (exhibit.owned)
            const Icon(Icons.verified_rounded, color: Color(0xFF79D8A4), size: 20),
        ],
      ),
    );
  }

  Widget _stage(ShowroomExhibit exhibit, bool reduceMotion) {
    final Widget card =
        reduceMotion ? _staticCard(exhibit) : _turntable(exhibit);
    final String visibilityBadge =
        ClubLegacyShowroom.visibilityBadgeLabel(exhibit);
    final bool isPublicBroadcast =
        ClubLegacyShowroom.publicBroadcastNoticeFor(exhibit) != null;
    final GtexColorTokens navy = GtexColors.navy;

    return GtexPanel(
      key: Key(reduceMotion ? 'club-showroom-static' : 'club-showroom-stage'),
      title: exhibit.name,
      subtitle: exhibit.ownershipLabel,
      accent: exhibit.owned ? GtexColors.pitch : GtexColors.gold,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          SizedBox(height: 220, child: card),
          const SizedBox(height: GtexSpacing.sm),
          Wrap(
            spacing: GtexSpacing.xs,
            runSpacing: GtexSpacing.xs,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: <Widget>[
              Text(
                exhibit.ownershipLabel,
                key: const Key('club-showroom-ownership'),
                style: const TextStyle(
                  color: GtexColors.text,
                  fontWeight: FontWeight.w900,
                ),
              ),
              Container(
                key: const Key('club-showroom-category-badge'),
                padding: const EdgeInsets.symmetric(
                  horizontal: GtexSpacing.xs,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color:
                      (isPublicBroadcast ? navy.gold500 : navy.info)
                          .withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(GtexRadius.pill),
                  border: Border.all(
                    color: isPublicBroadcast ? navy.gold500 : navy.lineSubtle,
                  ),
                ),
                child: Text(
                  visibilityBadge,
                  style: GtexTypography.bodyS(
                    color: isPublicBroadcast ? navy.gold300 : navy.textSecondary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            _statusLine(exhibit),
            key: const Key('club-showroom-model-file'),
            style: const TextStyle(
              color: GtexColors.textSecondary,
              fontSize: 12,
            ),
          ),
          Text(
            exhibit.fallbackLabel,
            style: const TextStyle(
              color: GtexColors.textSecondary,
              fontSize: 12,
            ),
          ),
          _assetDetails(exhibit),
          if (widget.onAction != null) ...<Widget>[
            const SizedBox(height: GtexSpacing.sm),
            Wrap(
              spacing: GtexSpacing.xs,
              children: <Widget>[
                if (!exhibit.owned && exhibit.sku != null)
                  GtexActionButton(
                    key: Key('club-showroom-buy-${exhibit.sku}'),
                    label: 'Buy ${exhibit.name}',
                    icon: Icons.shopping_cart_rounded,
                    compact: true,
                    onPressed: _pendingPurchases.contains(exhibit.id)
                        ? null
                        : () => _handleBuyTap(exhibit),
                  ),
                if (exhibit.owned &&
                    exhibit.ownerClass != 'player' &&
                    exhibit.status != 'offered' &&
                    !exhibit.id.startsWith('facility:'))
                  GtexActionButton(
                    key: Key('club-showroom-gift-${exhibit.id}'),
                    label: 'Gift ${exhibit.name}',
                    icon: Icons.card_giftcard_rounded,
                    compact: true,
                    secondary: true,
                    onPressed: _pendingPurchases.contains('gift:${exhibit.id}')
                        ? null
                        : () => _giftAsset(exhibit),
                  ),
              ],
            ),
          ],
          if (!reduceMotion) ...<Widget>[
            const SizedBox(height: GtexSpacing.sm),
            Wrap(
              spacing: GtexSpacing.xs,
              children: <Widget>[
                GtexActionButton(
                  key: const Key('club-showroom-rotate-left'),
                  label: 'Turn left',
                  icon: Icons.rotate_left_rounded,
                  compact: true,
                  secondary: true,
                  onPressed: () => _turn(-0.4),
                ),
                GtexActionButton(
                  key: const Key('club-showroom-rotate-right'),
                  label: 'Turn right',
                  icon: Icons.rotate_right_rounded,
                  compact: true,
                  secondary: true,
                  onPressed: () => _turn(0.4),
                ),
                GtexActionButton(
                  key: const Key('club-showroom-reset'),
                  label: 'Reset',
                  icon: Icons.center_focus_strong_rounded,
                  compact: true,
                  secondary: true,
                  onPressed: _reset,
                ),
                GtexActionButton(
                  key: const Key('club-showroom-fullscreen'),
                  label: 'Full screen',
                  icon: Icons.fullscreen_rounded,
                  compact: true,
                  onPressed: () => _openFullscreen(exhibit, reduceMotion),
                ),
              ],
            ),
            Text(
              'Turn ${_yaw.toStringAsFixed(1)}',
              key: const Key('club-showroom-yaw'),
            ),
          ],
        ],
      ),
    );
  }

  Widget _staticCard(ShowroomExhibit exhibit) {
    final String preview = exhibitPreviewPath(
      category: exhibit.category,
      previewFile: exhibit.previewFile,
      modelFile: exhibit.modelFile,
    );
    return DecoratedBox(
      key: const Key('club-showroom-static-card'),
      decoration: BoxDecoration(
        color: GtexColors.panelStrong,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: GtexColors.gold.withValues(alpha: 0.5)),
      ),
      child: Image.asset(
        preview,
        key: const Key('club-showroom-preview'),
        fit: BoxFit.contain,
        errorBuilder: (
          BuildContext context,
          Object error,
          StackTrace? stackTrace,
        ) {
          return Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Icon(_icon(exhibit.category), color: GtexColors.gold, size: 64),
                const SizedBox(height: 8),
                Text(
                  exhibit.fallbackLabel,
                  style: const TextStyle(color: GtexColors.text),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  String _statusLine(ShowroomExhibit exhibit) {
    final String path = exhibitModelPath(
      category: exhibit.category,
      modelFile: exhibit.modelFile,
    );
    if (_loadError != null) {
      return 'Could not read $path';
    }
    if (_model == null || _model!.assetPath != path) {
      return 'Loading $path';
    }
    return _model!.loadedLabel;
  }

  Widget _turntable(ShowroomExhibit exhibit) {
    final String path = exhibitModelPath(
      category: exhibit.category,
      modelFile: exhibit.modelFile,
    );
    final ShowroomGlb? model = _model;
    if (_loadError != null) {
      return _staticCard(exhibit);
    }
    if (model == null || model.assetPath != path) {
      return const Center(
        child: CircularProgressIndicator(key: Key('club-showroom-loading')),
      );
    }
    return GestureDetector(
      key: const Key('club-showroom-zoom'),
      onScaleUpdate: (ScaleUpdateDetails details) {
        setState(() {
          _yaw += details.focalPointDelta.dx * 0.01;
          _pitch = (_pitch + details.focalPointDelta.dy * 0.01).clamp(
            -1.2,
            1.2,
          );
          if (details.pointerCount > 1) {
            _zoom = (_zoom * details.scale).clamp(0.8, 2.5);
          }
        });
      },
      child: Center(
        child: Transform.scale(
          scale: _zoom,
          child: CustomPaint(
            key: const Key('club-showroom-model-loaded'),
            size: const Size(220, 160),
            painter: _MeshPainter(model.parts, _yaw, _pitch),
          ),
        ),
      ),
    );
  }

  IconData _icon(String category) {
    return switch (category) {
      'jet' => Icons.flight_rounded,
      'coach' => Icons.directions_bus_rounded,
      _ => Icons.watch_rounded,
    };
  }
}

class _ShowroomFullscreen extends StatefulWidget {
  const _ShowroomFullscreen({
    required this.exhibit,
    required this.reduceMotion,
  });

  final ShowroomExhibit exhibit;
  final bool reduceMotion;

  @override
  State<_ShowroomFullscreen> createState() => _ShowroomFullscreenState();
}

class _ShowroomFullscreenState extends State<_ShowroomFullscreen> {
  double _yaw = 0;
  double _pitch = 0;
  ShowroomGlb? _model;
  Object? _loadError;

  @override
  void initState() {
    super.initState();
    loadShowroomGlb(
      exhibitModelPath(
        category: widget.exhibit.category,
        modelFile: widget.exhibit.modelFile,
      ),
    ).then(
      (ShowroomGlb model) {
        if (mounted) {
          setState(() => _model = model);
        }
      },
      onError: (Object error) {
        if (mounted) {
          setState(() => _loadError = error);
        }
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final ShowroomExhibit exhibit = widget.exhibit;
    return Dialog(
      key: const Key('club-showroom-fullscreen-view'),
      backgroundColor: GtexColors.panelStrong,
      child: Padding(
        padding: const EdgeInsets.all(GtexSpacing.md),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Text(
              exhibit.name,
              style: const TextStyle(
                color: GtexColors.text,
                fontSize: 22,
                fontWeight: FontWeight.w900,
              ),
            ),
            Text(
              exhibit.ownershipLabel,
              key: const Key('club-showroom-fullscreen-ownership'),
              style: const TextStyle(
                color: GtexColors.gold,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: GtexSpacing.sm),
            SizedBox(
              height: 360,
              child:
                  widget.reduceMotion || _loadError != null
                      ? Image.asset(
                        exhibitPreviewPath(
                          category: exhibit.category,
                          previewFile: exhibit.previewFile,
                          modelFile: exhibit.modelFile,
                        ),
                        key: const Key('club-showroom-fullscreen-preview'),
                        fit: BoxFit.contain,
                      )
                      : _model == null
                      ? const Center(child: CircularProgressIndicator())
                      : GestureDetector(
                        onScaleUpdate: (ScaleUpdateDetails details) {
                          setState(() {
                            _yaw += details.focalPointDelta.dx * 0.01;
                            _pitch = (_pitch +
                                    details.focalPointDelta.dy * 0.01)
                                .clamp(-1.2, 1.2);
                          });
                        },
                        child: Center(
                          child: CustomPaint(
                            key: const Key('club-showroom-fullscreen-model'),
                            size: const Size(280, 180),
                            painter: _MeshPainter(_model!.parts, _yaw, _pitch),
                          ),
                        ),
                      ),
            ),
            if (widget.reduceMotion)
              Text(
                exhibit.fallbackLabel,
                key: const Key('club-showroom-fullscreen-static'),
              ),
            const SizedBox(height: GtexSpacing.sm),
            Wrap(
              spacing: GtexSpacing.xs,
              children: <Widget>[
                if (!widget.reduceMotion)
                  GtexActionButton(
                    key: const Key('club-showroom-fullscreen-rotate'),
                    label: 'Turn',
                    icon: Icons.rotate_right_rounded,
                    compact: true,
                    secondary: true,
                    onPressed: () => setState(() => _yaw += 0.4),
                  ),
                GtexActionButton(
                  key: const Key('club-showroom-fullscreen-close'),
                  label: 'Close',
                  icon: Icons.close_rounded,
                  compact: true,
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            if (!widget.reduceMotion)
              Text(
                'Turn ${_yaw.toStringAsFixed(1)}',
                key: const Key('club-showroom-fullscreen-yaw'),
              ),
          ],
        ),
      ),
    );
  }
}

class ShowroomSection extends StatefulWidget {
  const ShowroomSection({
    super.key,
    required this.load,
    this.onAction,
    this.loadGiftRecipients,
    this.giftOwnedAsset,
  });

  final Future<List<ShowroomExhibit>> Function() load;
  final Future<void> Function(String action, [Map<String, Object?> payload])? onAction;
  final Future<List<OwnerGiftRecipient>> Function()? loadGiftRecipients;
  final Future<void> Function({required String assetId, required String playerId})?
      giftOwnedAsset;

  @override
  State<ShowroomSection> createState() => _ShowroomSectionState();
}

class _ShowroomSectionState extends State<ShowroomSection> {
  late Future<List<ShowroomExhibit>> _exhibits;

  @override
  void initState() {
    super.initState();
    _exhibits = widget.load();
  }

  void _reload() {
    setState(() {
      _exhibits = widget.load();
    });
  }

  Future<void> _handleAction(String action, Map<String, Object?> payload) async {
    if (widget.onAction != null) {
      await widget.onAction!(action, payload);
      if (mounted) {
        _reload();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<ShowroomExhibit>>(
      future: _exhibits,
      builder: (
        BuildContext context,
        AsyncSnapshot<List<ShowroomExhibit>> snap,
      ) {
        if (snap.connectionState != ConnectionState.done) {
          return const Padding(
            padding: EdgeInsets.all(GtexSpacing.md),
            child: GtexSkeleton.box(height: 220),
          );
        }
        if (snap.hasError || snap.data == null) {
          return ClubLegacyShowroom(
            forceStatic: true,
            onAction: null,
            exhibits: const <ShowroomExhibit>[
              ShowroomExhibit(
                id: 'catalogue:gtex-jet-harbour',
                sku: 'gtex-jet-harbour',
                name: 'Harbour Jet',
                category: 'jet',
                ownershipLabel: 'Not owned',
                fallbackLabel: 'Static jet card',
              ),
              ShowroomExhibit(
                id: 'catalogue:gtex-coach-lagoon',
                sku: 'gtex-coach-lagoon',
                name: 'Lagoon Coach',
                category: 'coach',
                ownershipLabel: 'Not owned',
                fallbackLabel: 'Static coach card',
              ),
              ShowroomExhibit(
                id: 'catalogue:gtex-watch-icon',
                sku: 'gtex-watch-icon',
                name: 'Icon Watch',
                category: 'watch',
                ownershipLabel: 'Not owned',
                fallbackLabel: 'Static watch card',
              ),
            ],
          );
        }
        return ClubLegacyShowroom(
          exhibits: snap.data!,
          requirePurchaseConfirm: true,
          onAction: _handleAction,
          loadGiftRecipients: widget.loadGiftRecipients,
          giftOwnedAsset: widget.giftOwnedAsset,
          onGiftCompleted: () async {
            if (mounted) _reload();
          },
        );
      },
    );
  }
}

class _MeshPainter extends CustomPainter {
  _MeshPainter(this.parts, this.yaw, this.pitch);

  final List<ShowroomMeshPart> parts;
  final double yaw;
  final double pitch;

  @override
  void paint(Canvas canvas, Size size) {
    if (parts.isEmpty) {
      return;
    }
    double minX = double.infinity;
    double minY = double.infinity;
    double minZ = double.infinity;
    double maxX = -double.infinity;
    double maxY = -double.infinity;
    double maxZ = -double.infinity;
    for (final ShowroomMeshPart part in parts) {
      for (int i = 0; i < part.positions.length; i += 3) {
        final double x = part.positions[i];
        final double y = part.positions[i + 1];
        final double z = part.positions[i + 2];
        minX = math.min(minX, x);
        minY = math.min(minY, y);
        minZ = math.min(minZ, z);
        maxX = math.max(maxX, x);
        maxY = math.max(maxY, y);
        maxZ = math.max(maxZ, z);
      }
    }
    final double extent = math.max(
      maxX - minX,
      math.max(maxY - minY, maxZ - minZ),
    );
    final double unit = extent == 0 ? 1 : extent;
    final double pixel = math.min(size.width, size.height) * 0.92;
    final double midX = (minX + maxX) / 2;
    final double midY = (minY + maxY) / 2;
    final double midZ = (minZ + maxZ) / 2;
    final double cx = size.width / 2;
    final double cy = size.height / 2;
    final double cosY = math.cos(yaw);
    final double sinY = math.sin(yaw);
    final double cosP = math.cos(pitch);
    final double sinP = math.sin(pitch);

    (Offset, double) project(Float32List positions, int vertex) {
      final double x = (positions[vertex * 3] - midX) / unit;
      final double y = (positions[vertex * 3 + 1] - midY) / unit;
      final double z = (positions[vertex * 3 + 2] - midZ) / unit;
      final double xr = x * cosY + z * sinY;
      final double yr = y;
      final double zr = -x * sinY + z * cosY;
      final double yp = yr * cosP - zr * sinP;
      final double zp = yr * sinP + zr * cosP;
      final double perspective = 2.6 / (2.6 + zp);
      return (
        Offset(cx + xr * pixel * perspective, cy - yp * pixel * perspective),
        zp,
      );
    }

    final List<({Path path, double depth, Color color})> drawn =
        <({Path path, double depth, Color color})>[];
    for (final ShowroomMeshPart part in parts) {
      final int vertexCount = part.positions.length ~/ 3;
      for (int index = 0; index + 2 < part.indices.length; index += 3) {
        final int a = part.indices[index];
        final int b = part.indices[index + 1];
        final int c = part.indices[index + 2];
        if (a >= vertexCount || b >= vertexCount || c >= vertexCount) {
          continue;
        }
        final (Offset pa, double da) = project(part.positions, a);
        final (Offset pb, double db) = project(part.positions, b);
        final (Offset pc, double dc) = project(part.positions, c);
        drawn.add((
          path:
              Path()
                ..moveTo(pa.dx, pa.dy)
                ..lineTo(pb.dx, pb.dy)
                ..lineTo(pc.dx, pc.dy)
                ..close(),
          depth: (da + db + dc) / 3,
          color: part.color,
        ));
      }
    }
    drawn.sort(
      (
        ({Path path, double depth, Color color}) left,
        ({Path path, double depth, Color color}) right,
      ) => right.depth.compareTo(left.depth),
    );
    final Paint fill = Paint();
    final double far = drawn.isEmpty ? 0 : drawn.first.depth;
    final double near = drawn.isEmpty ? 1 : drawn.last.depth;
    final double span = (near - far).abs() < 0.001 ? 1 : (near - far).abs();
    for (final ({Path path, double depth, Color color}) triangle in drawn) {
      final double shade = (0.45 + 0.55 * ((triangle.depth - far) / span))
          .clamp(0.35, 1.0);
      fill.color = Color.lerp(GtexColors.navy.bgInset, triangle.color, shade)!;
      canvas.drawPath(triangle.path, fill);
    }
  }

  @override
  bool shouldRepaint(covariant _MeshPainter oldDelegate) =>
      oldDelegate.yaw != yaw ||
      oldDelegate.pitch != pitch ||
      oldDelegate.parts != parts;
}


String _friendlyOwnerActionError(Object error) {
  final String text = error.toString().replaceFirst(RegExp(r'^(Exception|StateError|FormatException):\\s*'), '').trim();
  return text.isEmpty ? 'please try again' : text;
}

class _LuxuryArrivalDialog extends StatelessWidget {
  const _LuxuryArrivalDialog({
    required this.eyebrow,
    required this.title,
    required this.subtitle,
    required this.preview,
    required this.actionLabel,
    this.recipient,
  });

  final String eyebrow;
  final String title;
  final String subtitle;
  final Widget preview;
  final OwnerGiftRecipient? recipient;
  final String actionLabel;

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
      child: TweenAnimationBuilder<double>(
        tween: Tween<double>(begin: 0.84, end: 1),
        duration: const Duration(milliseconds: 400),
        curve: Curves.easeOutBack,
        builder: (BuildContext context, double value, Widget? child) =>
            Transform.scale(scale: value, child: child),
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[Color(0xFF1A2A41), Color(0xFF0A1220)],
            ),
            borderRadius: BorderRadius.circular(26),
            border: Border.all(color: GtexColors.gold.withValues(alpha: 0.68), width: 1.3),
            boxShadow: <BoxShadow>[
              BoxShadow(color: GtexColors.gold.withValues(alpha: 0.18), blurRadius: 36),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              const Icon(Icons.auto_awesome_rounded, color: GtexColors.gold, size: 24),
              const SizedBox(height: 9),
              Text(
                eyebrow,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Color(0xFFEAD18E), fontWeight: FontWeight.w900, fontSize: 10, letterSpacing: 2),
              ),
              const SizedBox(height: 14),
              SizedBox(height: 150, width: double.infinity, child: preview),
              if (recipient != null) ...<Widget>[
                const SizedBox(height: 14),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: <Widget>[
                    CircleAvatar(
                      radius: 24,
                      backgroundColor: const Color(0xFF20324A),
                      foregroundImage: (recipient!.portraitUrl ?? '').startsWith('http')
                          ? NetworkImage(recipient!.portraitUrl!)
                          : null,
                      child: Text(
                        recipient!.name.isEmpty ? '?' : recipient!.name.substring(0, 1).toUpperCase(),
                        style: const TextStyle(color: GtexColors.gold, fontWeight: FontWeight.w900),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Flexible(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(recipient!.name, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14)),
                          Text('${recipient!.position} · OVR ${recipient!.rating}', style: const TextStyle(color: Color(0xFFABBAD0), fontSize: 11)),
                        ],
                      ),
                    ),
                    const Icon(Icons.check_circle_rounded, color: Color(0xFF79D8A4)),
                  ],
                ),
              ],
              const SizedBox(height: 17),
              Text(
                title,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(color: Colors.white, fontWeight: FontWeight.w900),
              ),
              const SizedBox(height: 8),
              Text(
                subtitle,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Color(0xFFB4C1D4), fontSize: 12, height: 1.5),
              ),
              const SizedBox(height: 18),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: () => Navigator.of(context).pop(),
                  style: FilledButton.styleFrom(
                    backgroundColor: GtexColors.gold,
                    foregroundColor: const Color(0xFF15120B),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13)),
                  ),
                  key: const Key('club-showroom-arrival-close'),
                  child: Text(actionLabel, style: const TextStyle(fontWeight: FontWeight.w900)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
