import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/features/capital/wallet/data/capital_wallet_availability.dart';
import 'package:gte_frontend/features/shell/gtex_shell_primitives.dart';
import 'package:gte_frontend/models/regen_creation_models.dart';
import 'package:gte_frontend/shared/providers/regen_provider.dart';

import '../data/build_a_son_creation_client.dart';
import '../providers/build_a_son_providers.dart';

class BuildASonScreen extends ConsumerWidget {
  const BuildASonScreen({super.key, this.onCompleted});

  final Future<void> Function(RegenCreationOrder order)? onCompleted;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final Future<void> Function(RegenCreationOrder order)? externalCompletion =
        onCompleted;
    return BuildASonWizard(
      client: ref.watch(buildASonCreationClientProvider),
      orderRealtimeEvents: ref.watch(buildASonOrderRealtimeEventsProvider),
      onCompleted: (RegenCreationOrder order) async {
        ref.invalidate(regenUniverseHubProvider);
        await externalCompletion?.call(order);
      },
    );
  }
}

class BuildASonWizard extends StatefulWidget {
  const BuildASonWizard({
    super.key,
    required this.client,
    this.orderRealtimeEvents,
    this.onCompleted,
  });

  final BuildASonCreationClient client;
  final Stream<BuildASonOrderRealtimeEvent>? orderRealtimeEvents;
  final Future<void> Function(RegenCreationOrder order)? onCompleted;

  @override
  State<BuildASonWizard> createState() => _BuildASonWizardState();
}

class _BuildASonWizardState extends State<BuildASonWizard> {
  static const int _orderReconciliationAttempts = 4;
  static const Duration _orderReconciliationDelay = Duration(milliseconds: 250);

  static const List<String> _steps = <String>[
    'Choose Parent',
    'Inherit Traits',
    'Name & Position',
    'Confirm',
  ];

  static const Map<String, String> _backendPositionAliases = <String, String>{
    'CDM': 'DM',
    'CAM': 'AM',
    'LCB': 'CB',
    'RCB': 'CB',
    'LWB': 'LB',
    'RWB': 'RB',
    'LM': 'LW',
    'RM': 'RW',
    'CF': 'ST',
  };

  final TextEditingController _nameController = TextEditingController();
  final Set<String> _selectedTraits = <String>{};

  RequestSonOptions? _options;
  RequestSonPreview? _preview;
  RegenCreationOrder? _completedOrder;
  String? _selectedParentId;
  String _selectedPosition = 'AM';
  String _selectedCountryCode = 'NGA';
  String? _previewContractBlock;
  String? _loadMessage;
  String? _previewMessage;
  GtexSurfaceState _loadState = GtexSurfaceState.loading;
  GtexSurfaceState _previewState = GtexSurfaceState.empty;
  int _step = 0;
  int _previewRequestId = 0;
  bool _submitting = false;
  String? _activeOrderId;
  StreamSubscription<BuildASonOrderRealtimeEvent>? _orderRealtimeSubscription;
  Future<void>? _orderRealtimeRefresh;
  final Set<String> _completedCallbackOrderIds = <String>{};

  @override
  void initState() {
    super.initState();
    _subscribeToOrderRealtimeEvents();
    _loadOptions();
  }

  @override
  void didUpdateWidget(BuildASonWizard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.orderRealtimeEvents != widget.orderRealtimeEvents) {
      _subscribeToOrderRealtimeEvents();
    }
  }

  @override
  void dispose() {
    final StreamSubscription<BuildASonOrderRealtimeEvent>? subscription =
        _orderRealtimeSubscription;
    if (subscription != null) {
      unawaited(subscription.cancel());
    }
    _nameController.dispose();
    super.dispose();
  }

  RegenCreationParentPlayer? get _selectedParent {
    final RequestSonOptions? options = _options;
    final String? selectedParentId = _selectedParentId;
    if (options == null || selectedParentId == null) {
      return null;
    }
    for (final RegenCreationParentPlayer parent in options.eligibleParents) {
      if (parent.playerId == selectedParentId) {
        return parent;
      }
    }
    return null;
  }

  List<String> get _availableTraits {
    final List<String> traits = _selectedParent?.traits ?? const <String>[];
    final Set<String> seen = <String>{};
    final List<String> normalized = <String>[];
    for (final String trait in traits) {
      final String trimmed = trait.trim();
      if (trimmed.isEmpty || !seen.add(trimmed.toLowerCase())) {
        continue;
      }
      normalized.add(trimmed);
    }
    return normalized..sort();
  }

  bool get _hasCompleteIdentity {
    return _nameController.text.trim().isNotEmpty &&
        _countryOptionCodes.contains(
          _selectedCountryCode.trim().toUpperCase(),
        ) &&
        _positionOptionCodes.contains(_selectedPosition.trim().toUpperCase());
  }

  List<RequestSonNationalityOption> get _nationalityOptions =>
      _options?.nationalityOptions ?? const <RequestSonNationalityOption>[];

  List<RequestSonPositionOption> get _positionOptions =>
      _options?.positionOptions ?? const <RequestSonPositionOption>[];

  Set<String> get _countryOptionCodes => <String>{
    for (final RequestSonNationalityOption option in _nationalityOptions)
      option.code.trim().toUpperCase(),
  };

  Set<String> get _positionOptionCodes => <String>{
    for (final RequestSonPositionOption option in _positionOptions)
      option.code.trim().toUpperCase(),
  };

  bool get _canConfirmPreview {
    final RequestSonPreview? preview = _preview;
    return preview != null &&
        _previewContractBlock == null &&
        preview.canConfirm &&
        !_submitting;
  }

  Future<void> _loadOptions() async {
    setState(() {
      _loadState = GtexSurfaceState.loading;
      _loadMessage = null;
      _clearPreview();
    });
    try {
      final RequestSonOptions options =
          await widget.client.fetchRequestSonOptions();
      final String? optionsContractBlock = _optionsContractBlock(options);
      if (!mounted) {
        return;
      }
      setState(() {
        _options = options;
        _loadState =
            optionsContractBlock != null
                ? GtexSurfaceState.blocked
                : options.eligibleParents.isEmpty
                ? GtexSurfaceState.empty
                : GtexSurfaceState.confirmed;
        _loadMessage = optionsContractBlock;
        final String? selectedParentId = _selectedParentId;
        final bool selectedStillEligible =
            selectedParentId != null &&
            options.eligibleParents.any(
              (RegenCreationParentPlayer parent) =>
                  parent.playerId == selectedParentId,
            );
        if (!selectedStillEligible) {
          _selectedParentId = null;
          _selectedTraits.clear();
          _selectedPosition = _defaultPositionFor(options);
          _selectedCountryCode = _defaultCountryCodeFor(options);
          _step = 0;
        }
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _loadState = GtexSurfaceState.error;
        _loadMessage = _messageFor(error);
      });
    }
  }

  void _selectParent(
    RegenCreationParentPlayer parent, {
    bool resetPreview = true,
  }) {
    _selectedParentId = parent.playerId;
    final String defaultPosition = _defaultPositionFor(_options);
    _selectedPosition =
        _normalizePosition(parent.position) ??
        (defaultPosition.isNotEmpty ? defaultPosition : _selectedPosition);
    final String? countryCode = parent.countryCode?.trim().toUpperCase();
    if (countryCode != null && _countryOptionCodes.contains(countryCode)) {
      _selectedCountryCode = countryCode;
    } else {
      final String defaultCountryCode = _defaultCountryCodeFor(_options);
      _selectedCountryCode =
          defaultCountryCode.isNotEmpty
              ? defaultCountryCode
              : _selectedCountryCode;
    }
    _selectedTraits.removeWhere(
      (String trait) => !_availableTraits.contains(trait),
    );
    if (resetPreview) {
      _clearPreview();
    }
  }

  String? _normalizePosition(String? position) {
    final String normalized = (position ?? '').trim().toUpperCase();
    final String aliased = _backendPositionAliases[normalized] ?? normalized;
    return _positionOptionCodes.contains(aliased) ? aliased : null;
  }

  String? _optionsContractBlock(RequestSonOptions options) {
    if (options.positionOptions.isEmpty) {
      return 'Backend position options are missing.';
    }
    if (options.nationalityOptions.isEmpty) {
      return 'Backend nationality options are missing.';
    }
    return null;
  }

  String _defaultPositionFor(RequestSonOptions? options) {
    if (options == null || options.positionOptions.isEmpty) {
      return '';
    }
    final String? explicitDefault =
        options.defaultPosition?.trim().toUpperCase();
    if (explicitDefault != null &&
        options.positionOptions.any(
          (RequestSonPositionOption option) =>
              option.code.trim().toUpperCase() == explicitDefault,
        )) {
      return explicitDefault;
    }
    for (final RequestSonPositionOption option in options.positionOptions) {
      if (option.isDefault) {
        return option.code.trim().toUpperCase();
      }
    }
    return options.positionOptions.first.code.trim().toUpperCase();
  }

  String _defaultCountryCodeFor(RequestSonOptions? options) {
    if (options == null || options.nationalityOptions.isEmpty) {
      return '';
    }
    final String? explicitDefault =
        options.defaultCountryCode?.trim().toUpperCase();
    if (explicitDefault != null &&
        options.nationalityOptions.any(
          (RequestSonNationalityOption option) =>
              option.code.trim().toUpperCase() == explicitDefault,
        )) {
      return explicitDefault;
    }
    for (final RequestSonNationalityOption option
        in options.nationalityOptions) {
      if (option.isDefault) {
        return option.code.trim().toUpperCase();
      }
    }
    return options.nationalityOptions.first.code.trim().toUpperCase();
  }

  void _clearPreview() {
    _preview = null;
    _completedOrder = null;
    _activeOrderId = null;
    _completedCallbackOrderIds.clear();
    _previewContractBlock = null;
    _previewMessage = null;
    _previewState = GtexSurfaceState.empty;
  }

  bool _canAdvance() {
    return switch (_step) {
      0 => _selectedParent != null,
      1 => _selectedTraits.length == 3,
      2 => _hasCompleteIdentity,
      _ => false,
    };
  }

  String _advanceBlockMessage() {
    return switch (_step) {
      0 => 'Choose an eligible backend parent before continuing.',
      1 =>
        _availableTraits.length < 3
            ? 'The selected parent does not expose 3 backend-owned traits yet.'
            : 'Choose exactly 3 inherited traits.',
      2 => 'Name the regen and provide nationality and position.',
      _ => 'This step cannot advance yet.',
    };
  }

  void _next() {
    if (!_canAdvance()) {
      setState(() {
        _previewState = GtexSurfaceState.blocked;
        _previewMessage = _advanceBlockMessage();
      });
      return;
    }
    setState(() {
      _step += 1;
      _previewMessage = null;
      if (_step < 3) {
        _previewState = GtexSurfaceState.empty;
      }
    });
    if (_step == 3) {
      _refreshPreview();
    }
  }

  void _back() {
    if (_step == 0 || _submitting) {
      return;
    }
    setState(() {
      _step -= 1;
    });
  }

  RequestSonPreviewDraft? _previewDraft() {
    final RegenCreationParentPlayer? parent = _selectedParent;
    if (parent == null ||
        _selectedTraits.length != 3 ||
        !_hasCompleteIdentity) {
      return null;
    }
    return RequestSonPreviewDraft(
      parentPlayerId: parent.playerId,
      selectedTraits: _selectedTraits.toList(growable: false),
      requestedName: _nameController.text,
      requestedCountryCode: _selectedCountryCode,
      requestedPosition: _selectedPosition,
    );
  }

  Future<void> _refreshPreview() async {
    final RequestSonPreviewDraft? draft = _previewDraft();
    if (draft == null || !draft.hasExactlyThreeTraits) {
      setState(() {
        _preview = null;
        _previewContractBlock = null;
        _previewState = GtexSurfaceState.blocked;
        _previewMessage =
            'Backend preview needs a parent, identity, and exactly 3 traits.';
      });
      return;
    }

    final int requestId = ++_previewRequestId;
    setState(() {
      _preview = null;
      _previewContractBlock = null;
      _previewState = GtexSurfaceState.syncing;
      _previewMessage = null;
    });
    try {
      final RequestSonPreview preview = await widget.client.previewRequestSon(
        draft,
      );
      if (!mounted || requestId != _previewRequestId) {
        return;
      }
      final String? contractBlock = _previewContractBlockReason(preview, draft);
      final String? backendBlock =
          preview.blockedReason ?? preview.walletAvailability.blockedReason;
      setState(() {
        _preview = preview;
        _previewContractBlock = contractBlock;
        _previewState =
            contractBlock == null && preview.canConfirm
                ? GtexSurfaceState.confirmed
                : GtexSurfaceState.blocked;
        _previewMessage =
            contractBlock ??
            backendBlock ??
            (preview.walletAvailability.isAvailable
                ? null
                : 'Backend wallet availability blocked this creation.');
      });
    } catch (error) {
      if (!mounted || requestId != _previewRequestId) {
        return;
      }
      setState(() {
        _preview = null;
        _previewContractBlock = null;
        _previewState = GtexSurfaceState.error;
        _previewMessage = _messageFor(error);
      });
    }
  }

  String? _previewContractBlockReason(
    RequestSonPreview preview,
    RequestSonPreviewDraft draft,
  ) {
    if (preview.parentPlayerId.trim() != draft.parentPlayerId.trim()) {
      return 'Backend preview returned a different parent than the selected player.';
    }
    if (_normalizedTraitSet(preview.selectedTraits).length != 3) {
      return 'Backend preview did not confirm exactly 3 inherited traits.';
    }
    if (!_sameTraits(preview.selectedTraits, draft.selectedTraits)) {
      return 'Backend preview trait echo does not match the selected inheritance set.';
    }
    if (preview.projectedOverall <= 0 || preview.projectedOverall > 99) {
      return 'Backend preview is missing a valid projected OVR.';
    }
    if (preview.projectedPotential <= 0 || preview.projectedPotential > 99) {
      return 'Backend preview is missing a valid projected POT.';
    }
    if (preview.projectedPotential < preview.projectedOverall) {
      return 'Backend preview returned POT below OVR.';
    }
    if (!_hasGenerationTruth(preview)) {
      return 'Backend preview is missing the son generation.';
    }
    final RegenCreationParentPlayer? parent = _selectedParent;
    if (parent?.generationNumber != null &&
        preview.parentGeneration != parent!.generationNumber) {
      return 'Backend preview parent generation does not match the selected player.';
    }
    if (preview.generationNumber != preview.parentGeneration + 1) {
      return 'Backend preview did not return GEN-N+1 generation logic.';
    }
    if (!_hasProjectedDna(preview.projectedDna)) {
      return 'Backend preview is missing projected DNA bars.';
    }
    if (!_hasWalletEvidence(preview.walletAvailability)) {
      return 'Backend wallet availability is missing.';
    }
    if (preview.currency.trim().isEmpty) {
      return 'Backend preview is missing currency.';
    }
    return null;
  }

  Set<String> _normalizedTraitSet(Iterable<String> traits) {
    return traits
        .map((String trait) => trait.trim().toLowerCase())
        .where((String trait) => trait.isNotEmpty)
        .toSet();
  }

  bool _sameTraits(Iterable<String> left, Iterable<String> right) {
    final Set<String> leftSet = _normalizedTraitSet(left);
    final Set<String> rightSet = _normalizedTraitSet(right);
    return leftSet.length == rightSet.length && leftSet.containsAll(rightSet);
  }

  bool _hasGenerationTruth(RequestSonPreview preview) {
    if (preview.generationNumber > 0) {
      return true;
    }
    return RegExp(r'GEN-?\d+').hasMatch(preview.generationLabel.toUpperCase());
  }

  bool _hasProjectedDna(RegenDnaProfile dna) {
    for (final String code in regenDnaStatCodes) {
      final int value = dna.valueFor(code);
      if (value <= 0 || value > 99) {
        return false;
      }
    }
    return true;
  }

  bool _hasWalletEvidence(CapitalWalletAvailability wallet) =>
      wallet.hasBackendEvidence;

  Future<void> _confirm() async {
    final RequestSonPreview? preview = _preview;
    final RegenCreationParentPlayer? parent = _selectedParent;
    if (preview == null ||
        parent == null ||
        _previewContractBlock != null ||
        !preview.canConfirm) {
      setState(() {
        _previewState = GtexSurfaceState.blocked;
        _previewMessage =
            _previewContractBlock ??
            preview?.blockedReason ??
            preview?.walletAvailability.blockedReason ??
            'GTEX needs a confirmed backend preview before creation.';
      });
      return;
    }

    setState(() {
      _submitting = true;
      _previewState = GtexSurfaceState.pending;
      _previewMessage =
          'Creating the order, reserving wallet funds, and reconciling payment.';
    });

    RegenCreationOrder? reservedOrder;
    bool shouldReleaseReservedOrder = false;

    try {
      RegenCreationOrder order = await widget.client.createRequestSonOrder(
        RequestSonOrderDraft(
          parentPlayerId: parent.playerId,
          paymentMethod: 'wallet',
          selectedTraits: _selectedTraits.toList(growable: false),
          requestedName: _nameController.text,
          requestedCountryCode: _selectedCountryCode,
          requestedPosition: _selectedPosition,
        ),
      );
      _trackActiveOrder(order);
      if (!order.usesWallet) {
        throw StateError('Backend returned a non-wallet creation order.');
      }
      bool walletTouched = !order.isPendingPayment;
      if (order.isPendingPayment) {
        if (!order.hasReservedWalletFunds) {
          throw StateError(
            'Backend did not return the reserved wallet state for order ${order.id}.',
          );
        }
        reservedOrder = order;
        shouldReleaseReservedOrder = true;
        await widget.client.refreshWalletTruth();
        order = await widget.client.payWithWallet(order.id);
        _trackActiveOrder(order);
        shouldReleaseReservedOrder = false;
        reservedOrder = null;
        walletTouched = true;
      }
      if (!order.isGenerated && order.status == 'paid') {
        await widget.client.generateAfterPayment(order.id);
      }
      if (walletTouched) {
        await widget.client.refreshWalletTruth();
      }
      order = await _reconcileGeneratedOrder(order.id);
      await _acceptCompletedOrder(
        order,
        message: 'The academy received the generated son.',
      );
    } catch (error) {
      final String primaryMessage = _messageFor(error);
      final String? releaseMessage =
          shouldReleaseReservedOrder
              ? await _releaseReservedOrderAfterFailure(reservedOrder)
              : null;
      if (!mounted) {
        return;
      }
      setState(() {
        _previewState = GtexSurfaceState.error;
        _previewMessage =
            releaseMessage == null
                ? primaryMessage
                : '$primaryMessage $releaseMessage';
      });
    } finally {
      if (mounted) {
        setState(() {
          _submitting = false;
        });
      }
    }
  }

  void _subscribeToOrderRealtimeEvents() {
    final StreamSubscription<BuildASonOrderRealtimeEvent>?
    previousSubscription = _orderRealtimeSubscription;
    if (previousSubscription != null) {
      unawaited(previousSubscription.cancel());
    }
    _orderRealtimeSubscription = widget.orderRealtimeEvents?.listen(
      _handleOrderRealtimeEvent,
    );
  }

  void _handleOrderRealtimeEvent(BuildASonOrderRealtimeEvent event) {
    final String? activeOrderId = _activeOrderId;
    if (activeOrderId == null || !event.appliesToOrder(activeOrderId)) {
      return;
    }
    unawaited(_refreshActiveOrderFromRealtime(activeOrderId, event));
  }

  Future<void> _refreshActiveOrderFromRealtime(
    String orderId,
    BuildASonOrderRealtimeEvent event,
  ) async {
    final Future<void>? currentRefresh = _orderRealtimeRefresh;
    if (currentRefresh != null) {
      await currentRefresh;
      return;
    }
    final Future<void> refresh = _fetchActiveOrderFromRealtime(orderId, event);
    _orderRealtimeRefresh = refresh;
    try {
      await refresh;
    } finally {
      if (_orderRealtimeRefresh == refresh) {
        _orderRealtimeRefresh = null;
      }
    }
  }

  Future<void> _fetchActiveOrderFromRealtime(
    String orderId,
    BuildASonOrderRealtimeEvent event,
  ) async {
    try {
      if (mounted && _isActiveOrder(orderId) && _submitting) {
        setState(() {
          _previewState = GtexSurfaceState.syncing;
          _previewMessage =
              'Backend realtime update received; syncing order truth.';
        });
      }
      final RegenCreationOrder latest = await widget.client.fetchCreationOrder(
        orderId,
      );
      if (!mounted || !_isActiveOrder(orderId)) {
        return;
      }
      if (latest.isGenerated) {
        await _acceptCompletedOrder(
          latest,
          message: 'Backend realtime confirmed the generated son.',
        );
        return;
      }
      if (_submitting ||
          _previewState == GtexSurfaceState.pending ||
          _previewState == GtexSurfaceState.syncing) {
        setState(() {
          _previewState =
              latest.isGenerating ? GtexSurfaceState.syncing : _previewState;
          _previewMessage = _realtimeOrderSyncMessage(latest);
        });
      }
    } catch (_) {
      // Realtime is only a signal path; the existing reconciliation loop keeps
      // polling backend order truth when a websocket refresh fails.
      return;
    }
  }

  void _trackActiveOrder(RegenCreationOrder order) {
    final String orderId = order.id.trim();
    if (orderId.isNotEmpty) {
      _activeOrderId = orderId;
    }
  }

  bool _isActiveOrder(String orderId) {
    return _activeOrderId?.trim() == orderId.trim();
  }

  Future<void> _acceptCompletedOrder(
    RegenCreationOrder order, {
    required String message,
  }) async {
    _trackActiveOrder(order);
    if (_completedCallbackOrderIds.add(order.id)) {
      await widget.onCompleted?.call(order);
    }
    if (!mounted) {
      return;
    }
    setState(() {
      _completedOrder = order;
      _previewState = GtexSurfaceState.confirmed;
      _previewMessage = message;
    });
  }

  String _realtimeOrderSyncMessage(RegenCreationOrder order) {
    if (order.isGenerating) {
      return 'Backend realtime refreshed order ${order.id}; generation is still syncing.';
    }
    if (order.isPaid) {
      return 'Backend realtime refreshed order ${order.id}; waiting for generated son truth.';
    }
    final String status = order.status.trim();
    return status.isEmpty
        ? 'Backend realtime refreshed order ${order.id}; syncing continues.'
        : 'Backend realtime refreshed order ${order.id}; status is $status.';
  }

  Future<RegenCreationOrder> _reconcileGeneratedOrder(String orderId) async {
    RegenCreationOrder? latest;
    for (
      int attempt = 0;
      attempt < _orderReconciliationAttempts;
      attempt += 1
    ) {
      if (attempt > 0) {
        await Future<void>.delayed(_orderReconciliationDelay);
      }
      if (mounted) {
        setState(() {
          _previewState = GtexSurfaceState.syncing;
          _previewMessage =
              attempt == 0
                  ? 'Waiting for backend-generated order truth.'
                  : 'Still syncing backend-generated order truth (${attempt + 1}/$_orderReconciliationAttempts).';
        });
      }

      latest = await widget.client.fetchCreationOrder(orderId);
      if (latest.isGenerated) {
        return latest;
      }
      if (!latest.isGenerating &&
          !latest.isPaid &&
          latest.status != 'generated') {
        break;
      }
    }

    final RegenCreationOrder? unresolvedOrder = latest;
    if (unresolvedOrder != null && unresolvedOrder.status == 'generated') {
      throw StateError(
        'Backend marked order ${unresolvedOrder.id} as generated without generated player truth.',
      );
    }
    throw StateError(
      'Backend reconciliation did not confirm a generated son for order $orderId. '
      'Last status: ${unresolvedOrder?.status ?? 'unknown'}.',
    );
  }

  Future<String?> _releaseReservedOrderAfterFailure(
    RegenCreationOrder? order,
  ) async {
    if (order == null || !order.hasReservedWalletFunds) {
      return null;
    }
    try {
      final RegenCreationOrder cancelled = await widget.client
          .cancelCreationOrder(order.id);
      await widget.client.refreshWalletTruth();
      final RegenCreationWalletReservation? reservation =
          cancelled.walletReservation;
      if (reservation?.isReleased == true || cancelled.isCancelled) {
        return 'Reserved wallet funds were released.';
      }
      return 'GTEX requested release for reserved wallet funds; refresh wallet truth before retrying.';
    } catch (releaseError) {
      return 'GTEX could not automatically release the reserved wallet funds: ${_messageFor(releaseError)}';
    }
  }

  void _invalidatePreview() {
    setState(_clearPreview);
  }

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Build-a-Son'),
        actions: <Widget>[
          IconButton(
            tooltip: 'Refresh backend options',
            onPressed: _submitting ? null : _loadOptions,
            icon: const Icon(Icons.sync_rounded),
          ),
        ],
      ),
      body: SafeArea(
        child: GtexAsyncSurface(
          state: _loadState,
          title: _loadTitle,
          message: _loadMessage ?? _loadFallbackMessage,
          actionLabel: 'Retry',
          onAction: _loadOptions,
          icon: Icons.family_restroom_outlined,
          child: LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool wide = constraints.maxWidth >= 980;
              return SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 1120),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: <Widget>[
                        _buildHeader(theme),
                        const SizedBox(height: 18),
                        _buildStepper(),
                        const SizedBox(height: 18),
                        if (wide)
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Expanded(flex: 3, child: _buildStage(theme)),
                              const SizedBox(width: 18),
                              Expanded(
                                flex: 2,
                                child: _buildLineageRail(theme),
                              ),
                            ],
                          )
                        else ...<Widget>[
                          _buildStage(theme),
                          const SizedBox(height: 18),
                          _buildLineageRail(theme),
                        ],
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }

  String get _loadTitle {
    return switch (_loadState) {
      GtexSurfaceState.blocked => 'Build-a-Son contract blocked',
      GtexSurfaceState.empty => 'No eligible parent players',
      GtexSurfaceState.error => 'Build-a-Son is unavailable',
      _ => 'Loading Build-a-Son',
    };
  }

  String get _loadFallbackMessage {
    return switch (_loadState) {
      GtexSurfaceState.blocked =>
        'The backend did not return the selector contracts required for regen identity creation.',
      GtexSurfaceState.empty =>
        'The backend did not return eligible senior parent players for this club.',
      GtexSurfaceState.error =>
        'GTEX could not load the canonical request-son options.',
      _ => 'Syncing eligible parents, club context, and wallet-aware pricing.',
    };
  }

  Widget _buildHeader(ThemeData theme) {
    final RequestSonOptions? options = _options;
    return _Panel(
      accentColor: const Color(0xFF69F3A4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Build-a-Son',
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Select a live parent, lock exactly 3 inherited traits, request a backend projection, then confirm with wallet availability.',
            style: theme.textTheme.bodyMedium?.copyWith(height: 1.35),
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              _MetricPill(label: 'Club', value: options?.clubName ?? 'Syncing'),
              _MetricPill(
                label: 'Parents',
                value: '${options?.eligibleParents.length ?? 0}',
              ),
              _MetricPill(
                label: 'Payment',
                value: 'Wallet',
                tone: const Color(0xFFFFD75B),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStepper() {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: <Widget>[
        for (int index = 0; index < _steps.length; index += 1)
          _StepPill(
            index: index,
            label: _steps[index],
            active: index == _step,
            complete: index < _step,
          ),
      ],
    );
  }

  Widget _buildStage(ThemeData theme) {
    final Widget body = switch (_step) {
      0 => _buildParentStep(theme),
      1 => _buildTraitStep(theme),
      2 => _buildIdentityStep(theme),
      _ => _buildConfirmStep(theme),
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        body,
        const SizedBox(height: 18),
        Divider(color: theme.dividerColor.withValues(alpha: 0.35)),
        const SizedBox(height: 12),
        Wrap(
          alignment: WrapAlignment.spaceBetween,
          spacing: 12,
          runSpacing: 12,
          children: <Widget>[
            if (_step > 0)
              OutlinedButton.icon(
                onPressed: _submitting ? null : _back,
                icon: const Icon(Icons.chevron_left_rounded),
                label: const Text('Back'),
              ),
            if (_step < 3)
              FilledButton.icon(
                onPressed: _submitting ? null : _next,
                icon: const Icon(Icons.chevron_right_rounded),
                label: const Text('Next'),
              )
            else ...<Widget>[
              FilledButton.icon(
                onPressed: _canConfirmPreview ? _confirm : null,
                icon: const Icon(Icons.verified_outlined),
                label: Text(_confirmLabel),
              ),
              OutlinedButton.icon(
                onPressed: _submitting ? null : _refreshPreview,
                icon: const Icon(Icons.sync_rounded),
                label: const Text('Refresh preview'),
              ),
            ],
          ],
        ),
      ],
    );
  }

  String get _confirmLabel {
    final RequestSonPreview? preview = _preview;
    if (_submitting) {
      return 'Creating';
    }
    if (preview == null || _previewContractBlock != null) {
      return 'Awaiting backend preview';
    }
    return 'Create ${preview.generationLabel} Regen - ${_formatCoin(preview.totalCostCoin, currency: preview.currency)}';
  }

  Widget _buildParentStep(ThemeData theme) {
    final List<RegenCreationParentPlayer> parents =
        _options?.eligibleParents ?? const <RegenCreationParentPlayer>[];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const _SectionHeading(
          title: 'Choose a senior parent',
          message:
              'Eligible parents, ratings, lineage, and available inherited traits come from the backend.',
        ),
        const SizedBox(height: 14),
        for (final RegenCreationParentPlayer parent in parents) ...<Widget>[
          _ParentCard(
            parent: parent,
            selected: parent.playerId == _selectedParentId,
            onTap:
                () => setState(() {
                  _selectParent(parent);
                }),
          ),
          const SizedBox(height: 10),
        ],
      ],
    );
  }

  Widget _buildTraitStep(ThemeData theme) {
    final Set<String> parentTraits = _normalizedTraitSet(
      _selectedParent?.traits ?? const <String>[],
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const _SectionHeading(
          title: 'Choose exactly 3 inherited traits',
          message:
              'The backend receives only the selected 3 traits. Parent traits are marked when the option came with the selected player.',
        ),
        const SizedBox(height: 12),
        Text(
          '${_selectedTraits.length}/3 selected',
          style: theme.textTheme.labelLarge?.copyWith(
            color:
                _selectedTraits.length == 3
                    ? const Color(0xFF69F3A4)
                    : theme.colorScheme.onSurfaceVariant,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: <Widget>[
            for (final String trait in _availableTraits)
              _TraitChip(
                label: trait,
                selected: _selectedTraits.contains(trait),
                inherited: parentTraits.contains(trait.toLowerCase()),
                disabled:
                    _selectedTraits.length >= 3 &&
                    !_selectedTraits.contains(trait),
                onSelected: () {
                  setState(() {
                    if (_selectedTraits.contains(trait)) {
                      _selectedTraits.remove(trait);
                    } else if (_selectedTraits.length < 3) {
                      _selectedTraits.add(trait);
                    }
                    _clearPreview();
                  });
                },
              ),
          ],
        ),
      ],
    );
  }

  Widget _buildIdentityStep(ThemeData theme) {
    final Set<String> positionCodes = _positionOptionCodes;
    final Set<String> countryCodes = _countryOptionCodes;
    final String? selectedPositionValue =
        positionCodes.contains(_selectedPosition) ? _selectedPosition : null;
    final String? selectedCountryValue =
        countryCodes.contains(_selectedCountryCode)
            ? _selectedCountryCode
            : null;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const _SectionHeading(
          title: 'Identity',
          message:
              'Name, position, and nationality are sent to preview before any wallet action is attempted.',
        ),
        const SizedBox(height: 14),
        TextField(
          controller: _nameController,
          enabled: !_submitting,
          textCapitalization: TextCapitalization.words,
          onChanged: (_) => _invalidatePreview(),
          decoration: const InputDecoration(
            labelText: 'Regen name',
            hintText: 'e.g. Adebayo Jr.',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 14),
        Row(
          children: <Widget>[
            Expanded(
              child: DropdownButtonFormField<String>(
                value: selectedPositionValue,
                isExpanded: true,
                decoration: const InputDecoration(
                  labelText: 'Position',
                  border: OutlineInputBorder(),
                ),
                items: _positionOptions
                    .map(
                      (RequestSonPositionOption option) =>
                          DropdownMenuItem<String>(
                            value: option.code,
                            child: Text(option.displayLabel),
                          ),
                    )
                    .toList(growable: false),
                onChanged:
                    _submitting
                        ? null
                        : (String? value) => setState(() {
                          _selectedPosition = value ?? _selectedPosition;
                          _clearPreview();
                        }),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: DropdownButtonFormField<String>(
                value: selectedCountryValue,
                isExpanded: true,
                decoration: const InputDecoration(
                  labelText: 'Nationality',
                  border: OutlineInputBorder(),
                ),
                items: _nationalityOptions
                    .map(
                      (RequestSonNationalityOption option) =>
                          DropdownMenuItem<String>(
                            value: option.code,
                            child: Text(option.displayLabel),
                          ),
                    )
                    .toList(growable: false),
                onChanged:
                    _submitting
                        ? null
                        : (String? value) => setState(() {
                          _selectedCountryCode =
                              (value ?? _selectedCountryCode)
                                  .trim()
                                  .toUpperCase();
                          _clearPreview();
                        }),
              ),
            ),
          ],
        ),
        const SizedBox(height: 14),
        GtexStatePanel(
          state: GtexSurfaceState.pending,
          title: 'Backend-owned projection',
          message:
              'Projected DNA, OVR, POT, generation, cost, and wallet availability are not calculated in Flutter.',
          icon: Icons.analytics_outlined,
        ),
      ],
    );
  }

  Widget _buildConfirmStep(ThemeData theme) {
    final RequestSonPreview? preview = _preview;
    final bool canShowProjection =
        preview != null && _previewContractBlock == null;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const _SectionHeading(
          title: 'Backend preview and confirmation',
          message:
              'Creation remains blocked until the preview returns complete backend projection and wallet truth.',
        ),
        const SizedBox(height: 14),
        if (_submitting) ...<Widget>[
          const LinearProgressIndicator(),
          const SizedBox(height: 14),
        ],
        if (preview == null)
          GtexStatePanel(
            state: _previewState,
            title: _previewTitle,
            message: _previewMessage ?? _previewFallbackMessage,
            actionLabel:
                _previewState == GtexSurfaceState.syncing
                    ? null
                    : 'Retry preview',
            onAction: _refreshPreview,
            icon: Icons.analytics_outlined,
          )
        else ...<Widget>[
          if (_previewState != GtexSurfaceState.confirmed) ...<Widget>[
            GtexStatePanel(
              state: _previewState,
              title: _previewTitle,
              message: _previewMessage ?? _previewFallbackMessage,
              actionLabel: _submitting ? null : 'Retry preview',
              onAction: _refreshPreview,
              icon: Icons.lock_outline_rounded,
            ),
            const SizedBox(height: 14),
          ],
          if (canShowProjection) ...<Widget>[
            _PreviewCard(
              preview: preview,
              displayName: _nameController.text.trim(),
              traits: _selectedTraits.toList(growable: false),
            ),
            const SizedBox(height: 14),
            _WalletAvailabilityCard(
              preview.walletAvailability,
              currency: preview.currency,
            ),
          ],
          if (_completedOrder != null) ...<Widget>[
            const SizedBox(height: 14),
            GtexStatePanel(
              state: GtexSurfaceState.confirmed,
              title: 'Regen creation confirmed',
              message: _completionMessage(_completedOrder!),
              icon: Icons.verified_outlined,
            ),
          ],
        ],
      ],
    );
  }

  String get _previewTitle {
    return switch (_previewState) {
      GtexSurfaceState.syncing => 'Syncing backend preview',
      GtexSurfaceState.blocked => 'Creation blocked',
      GtexSurfaceState.pending => 'Creation pending',
      GtexSurfaceState.error => 'Preview unavailable',
      GtexSurfaceState.confirmed => 'Preview confirmed',
      _ => 'Preview required',
    };
  }

  String get _previewFallbackMessage {
    return switch (_previewState) {
      GtexSurfaceState.syncing =>
        'GTEX is requesting projected DNA, OVR, POT, generation, cost, and wallet availability.',
      GtexSurfaceState.blocked =>
        'The backend preview is missing, blocked, or waiting for wallet confirmation.',
      GtexSurfaceState.pending =>
        'GTEX is creating the order and waiting for wallet reconciliation.',
      GtexSurfaceState.error =>
        'The preview endpoint did not return backend-derived projection truth.',
      GtexSurfaceState.confirmed => 'The preview is confirmed.',
      _ => 'Generate a backend preview before confirming creation.',
    };
  }

  Widget _buildLineageRail(ThemeData theme) {
    final RegenCreationParentPlayer? parent = _selectedParent;
    return _Panel(
      accentColor: const Color(0xFFFFD75B),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Lineage Intelligence',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 12),
          if (parent == null)
            const Text('Select a backend parent to inspect lineage and DNA.')
          else ...<Widget>[
            _MetricPill(label: 'Parent', value: parent.fullName),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: <Widget>[
                _MetricPill(label: 'Position', value: parent.position ?? 'N/A'),
                _MetricPill(
                  label: 'OVR',
                  value: parent.overallRating?.toString() ?? 'N/A',
                  tone: const Color(0xFF69F3A4),
                ),
                _MetricPill(
                  label: 'Generation',
                  value: parent.generationLabel ?? 'Backend pending',
                  tone: const Color(0xFFB987FF),
                ),
              ],
            ),
            if (parent.lineage.isNotEmpty) ...<Widget>[
              const SizedBox(height: 14),
              _RailBlock(title: 'Lineage', values: parent.lineage),
            ],
            if (parent.traits.isNotEmpty) ...<Widget>[
              const SizedBox(height: 14),
              _RailBlock(title: 'Parent traits', values: parent.traits),
            ],
            if (parent.dnaProfile != null) ...<Widget>[
              const SizedBox(height: 14),
              Text(
                'Parent DNA',
                style: theme.textTheme.labelLarge?.copyWith(
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 8),
              for (final String code in regenDnaStatCodes)
                _DnaBar(label: code, value: parent.dnaProfile!.valueFor(code)),
            ],
          ],
        ],
      ),
    );
  }

  String _completionMessage(RegenCreationOrder order) {
    final RegenCreationGeneratedPlayer? player = order.generatedPlayer;
    if (player == null) {
      return 'Order ${order.id} is ${order.status}; generated player data is not available yet.';
    }
    final String core =
        '${player.fullName} entered the academy as ${player.position}, OVR ${player.currentRating}, POT ${player.potentialRating}.';
    final List<String> auditParts = <String>[
      'Order ${order.id}',
      if ((order.paymentReference ?? '').trim().isNotEmpty)
        'payment reference ${order.paymentReference}',
    ];
    final RegenCreationWalletReservation? reservation = order.walletReservation;
    if (reservation == null) {
      return '$core ${auditParts.join('; ')}.';
    }
    final String amount = _formatCoin(
      reservation.amountCoin,
      currency: reservation.currency,
    );
    final String status =
        reservation.isSettled ? 'settled' : reservation.status;
    auditParts.add('reservation ${reservation.reference ?? reservation.key}');
    return '$core ${auditParts.join('; ')}. Wallet reservation $status for $amount.';
  }

  String _messageFor(Object error) {
    final String message = error.toString();
    return message
        .replaceFirst('Exception: ', '')
        .replaceFirst('GteParsingException: ', '')
        .trim();
  }
}

class _SectionHeading extends StatelessWidget {
  const _SectionHeading({required this.title, required this.message});

  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          title,
          style: theme.textTheme.titleLarge?.copyWith(
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          message,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurface.withValues(alpha: 0.72),
            height: 1.35,
          ),
        ),
      ],
    );
  }
}

class _ParentCard extends StatelessWidget {
  const _ParentCard({
    required this.parent,
    required this.selected,
    required this.onTap,
  });

  final RegenCreationParentPlayer parent;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Color tone = selected ? const Color(0xFFB987FF) : theme.dividerColor;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onTap,
        child: Ink(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: tone.withValues(alpha: selected ? 0.11 : 0.03),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: tone.withValues(alpha: selected ? 0.58 : 0.3),
            ),
          ),
          child: Row(
            children: <Widget>[
              CircleAvatar(
                backgroundColor: tone.withValues(alpha: 0.18),
                child: Text(
                  _initials(parent.fullName),
                  style: theme.textTheme.labelMedium?.copyWith(
                    color: tone,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      parent.fullName,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${parent.position ?? 'N/A'} / OVR ${parent.overallRating?.toString() ?? 'N/A'} / ${parent.countryCode ?? parent.countryName ?? '---'}',
                      style: theme.textTheme.bodySmall,
                    ),
                    if (parent.traits.isNotEmpty) ...<Widget>[
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 6,
                        runSpacing: 6,
                        children: parent.traits
                            .take(4)
                            .map((String trait) => _MiniTag(label: trait))
                            .toList(growable: false),
                      ),
                    ],
                  ],
                ),
              ),
              if (selected)
                const Icon(
                  Icons.check_circle_rounded,
                  color: Color(0xFFB987FF),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _TraitChip extends StatelessWidget {
  const _TraitChip({
    required this.label,
    required this.selected,
    required this.inherited,
    required this.disabled,
    required this.onSelected,
  });

  final String label;
  final bool selected;
  final bool inherited;
  final bool disabled;
  final VoidCallback onSelected;

  @override
  Widget build(BuildContext context) {
    final Color tone =
        inherited ? const Color(0xFFB987FF) : const Color(0xFF69F3A4);
    return FilterChip(
      selected: selected,
      onSelected: disabled ? null : (_) => onSelected(),
      label: Text(inherited ? '$label - Parent' : label),
      checkmarkColor: tone,
      selectedColor: tone.withValues(alpha: 0.16),
      side: BorderSide(
        color: tone.withValues(alpha: inherited || selected ? 0.7 : 0.26),
      ),
    );
  }
}

class _PreviewCard extends StatelessWidget {
  const _PreviewCard({
    required this.preview,
    required this.displayName,
    required this.traits,
  });

  final RequestSonPreview preview;
  final String displayName;
  final List<String> traits;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final String name = displayName.isEmpty ? 'Unnamed Son' : displayName;
    return _Panel(
      accentColor: const Color(0xFFB987FF),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            '$name - ${preview.generationLabel}',
            style: theme.textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              _MetricPill(
                label: 'Projected OVR',
                value: '${preview.projectedOverall}',
                tone: const Color(0xFF69F3A4),
              ),
              _MetricPill(
                label: 'Projected POT',
                value: '${preview.projectedPotential}',
                tone: const Color(0xFFFFD75B),
              ),
              _MetricPill(
                label: 'Generation',
                value: preview.generationLabel,
                tone: const Color(0xFFB987FF),
              ),
              _MetricPill(
                label: 'Cost',
                value: _formatCoin(
                  preview.totalCostCoin,
                  currency: preview.currency,
                ),
                tone: const Color(0xFFFFD75B),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: traits
                .map((String trait) => _MiniTag(label: trait, regen: true))
                .toList(growable: false),
          ),
          const SizedBox(height: 16),
          Text(
            'Projected DNA Stats',
            style: theme.textTheme.labelLarge?.copyWith(
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 8),
          for (final String code in regenDnaStatCodes)
            _DnaBar(label: code, value: preview.projectedDna.valueFor(code)),
        ],
      ),
    );
  }
}

class _WalletAvailabilityCard extends StatelessWidget {
  const _WalletAvailabilityCard(this.wallet, {required this.currency});

  final CapitalWalletAvailability wallet;
  final String currency;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Color tone =
        wallet.isAvailable ? const Color(0xFF69F3A4) : theme.colorScheme.error;
    final bool hasBalanceFigures =
        wallet.isAvailable ||
        wallet.availableBalanceCoin != 0 ||
        wallet.reservedBalanceCoin != 0 ||
        wallet.lockedBalanceCoin != 0 ||
        wallet.pendingWithdrawalBalanceCoin != 0;
    return _Panel(
      accentColor: tone,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            wallet.isAvailable ? 'Wallet available' : 'Wallet blocked',
            style: theme.textTheme.titleMedium?.copyWith(
              color: tone,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 12),
          if (hasBalanceFigures)
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: <Widget>[
                _MetricPill(
                  label: 'Available',
                  value: _formatCoin(
                    wallet.availableBalanceCoin,
                    currency: currency,
                  ),
                  tone: const Color(0xFF69F3A4),
                ),
                _MetricPill(
                  label: 'Reserved',
                  value: _formatCoin(
                    wallet.reservedBalanceCoin,
                    currency: currency,
                  ),
                ),
                _MetricPill(
                  label: 'Locked',
                  value: _formatCoin(
                    wallet.lockedBalanceCoin,
                    currency: currency,
                  ),
                  tone: theme.colorScheme.error,
                ),
                _MetricPill(
                  label: 'Pending withdrawal',
                  value: _formatCoin(
                    wallet.pendingWithdrawalBalanceCoin,
                    currency: currency,
                  ),
                ),
              ],
            )
          else
            Text(
              'Balance figures were not included in the backend availability response.',
              style: theme.textTheme.bodyMedium?.copyWith(height: 1.35),
            ),
          if ((wallet.blockedReason ?? '').trim().isNotEmpty) ...<Widget>[
            const SizedBox(height: 10),
            Text(wallet.blockedReason!),
          ],
          if (wallet.lockReasons.isNotEmpty) ...<Widget>[
            const SizedBox(height: 10),
            _RailBlock(title: 'Lock reasons', values: wallet.lockReasons),
          ],
        ],
      ),
    );
  }
}

class _RailBlock extends StatelessWidget {
  const _RailBlock({required this.title, required this.values});

  final String title;
  final List<String> values;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          title,
          style: Theme.of(
            context,
          ).textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w900),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children:
              values.map((String value) => _MiniTag(label: value)).toList(),
        ),
      ],
    );
  }
}

class _DnaBar extends StatelessWidget {
  const _DnaBar({required this.label, required this.value});

  final String label;
  final int value;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final double normalized = value.clamp(0, 99) / 99;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: <Widget>[
          SizedBox(
            width: 34,
            child: Text(
              label,
              style: theme.textTheme.labelMedium?.copyWith(
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(999),
              child: LinearProgressIndicator(
                minHeight: 7,
                value: normalized,
                color: _dnaTone(label),
                backgroundColor: theme.dividerColor.withValues(alpha: 0.18),
              ),
            ),
          ),
          const SizedBox(width: 10),
          SizedBox(
            width: 32,
            child: Text(
              '$value',
              textAlign: TextAlign.right,
              style: theme.textTheme.labelMedium?.copyWith(
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Color _dnaTone(String code) {
    return switch (code) {
      'PAC' => const Color(0xFF69F3A4),
      'SHO' => const Color(0xFFFFD75B),
      'PAS' => const Color(0xFF64B5F6),
      'DRI' => const Color(0xFFB987FF),
      'DEF' => const Color(0xFFFF6B6B),
      _ => const Color(0xFFFFB35C),
    };
  }
}

class _StepPill extends StatelessWidget {
  const _StepPill({
    required this.index,
    required this.label,
    required this.active,
    required this.complete,
  });

  final int index;
  final String label;
  final bool active;
  final bool complete;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Color tone =
        complete
            ? const Color(0xFF69F3A4)
            : active
            ? const Color(0xFFFFD75B)
            : theme.dividerColor;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
      decoration: BoxDecoration(
        color: tone.withValues(alpha: active || complete ? 0.13 : 0.04),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tone.withValues(alpha: 0.4)),
      ),
      child: Text(
        '${index + 1}. $label',
        style: theme.textTheme.labelMedium?.copyWith(
          color: active || complete ? tone : null,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}

class _MetricPill extends StatelessWidget {
  const _MetricPill({required this.label, required this.value, this.tone});

  final String label;
  final String value;
  final Color? tone;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Color accent = tone ?? theme.colorScheme.onSurfaceVariant;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 9),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: accent.withValues(alpha: 0.28)),
        color: accent.withValues(alpha: 0.07),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            label.toUpperCase(),
            style: theme.textTheme.labelSmall?.copyWith(
              color: accent,
              fontWeight: FontWeight.w900,
              letterSpacing: 0,
            ),
          ),
          const SizedBox(height: 3),
          Text(
            value,
            style: theme.textTheme.labelLarge?.copyWith(
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

class _MiniTag extends StatelessWidget {
  const _MiniTag({required this.label, this.regen = false});

  final String label;
  final bool regen;

  @override
  Widget build(BuildContext context) {
    final Color tone =
        regen ? const Color(0xFFB987FF) : const Color(0xFF64B5F6);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: tone.withValues(alpha: 0.1),
        border: Border.all(color: tone.withValues(alpha: 0.34)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
          color: tone,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class _Panel extends StatelessWidget {
  const _Panel({required this.child, required this.accentColor});

  final Widget child;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Color.alphaBlend(
          accentColor.withValues(alpha: 0.035),
          theme.colorScheme.surface,
        ),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: accentColor.withValues(alpha: 0.2)),
      ),
      child: child,
    );
  }
}

String _initials(String name) {
  final List<String> parts = name
      .trim()
      .split(RegExp(r'\s+'))
      .where((String part) => part.isNotEmpty)
      .toList(growable: false);
  if (parts.isEmpty) {
    return 'GT';
  }
  if (parts.length == 1) {
    final int take = parts.first.length < 2 ? parts.first.length : 2;
    return parts.first.substring(0, take).toUpperCase();
  }
  return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
}

String _formatCoin(double value, {required String currency}) {
  final String label = currency.trim().isEmpty ? 'GTC' : currency.trim();
  if (value == value.roundToDouble()) {
    return '$label ${value.toStringAsFixed(0)}';
  }
  return '$label ${value.toStringAsFixed(1)}';
}
