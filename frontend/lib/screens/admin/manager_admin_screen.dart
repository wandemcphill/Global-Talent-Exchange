import 'package:flutter/material.dart';

import '../../core/app_feedback.dart';
import '../../data/competition_control_repository.dart';
import '../../data/gte_api_repository.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import '../../widgets/gtex_branding.dart';
import '../../data/gte_http_transport.dart';
import '../../data/manager_market_repository.dart';

class ManagerAdminScreen extends StatefulWidget {
  const ManagerAdminScreen({
    super.key,
    required this.baseUrl,
    required this.accessToken,
    required this.role,
  });

  final String baseUrl;
  final String accessToken;
  final String role;

  @override
  State<ManagerAdminScreen> createState() => _ManagerAdminScreenState();
}

class _ManagerAdminScreenState extends State<ManagerAdminScreen> {
  final TextEditingController _email = TextEditingController();
  late final ManagerAdminRepository _repository;
  late final CompetitionControlRepository _competitionRepository;
  final TextEditingController _username = TextEditingController();
  final TextEditingController _password =
      TextEditingController(text: 'AdminPass123!');
  final TextEditingController _catalogSearch = TextEditingController();

  bool _loading = true;
  bool _saving = false;
  String? _error;

  List<Map<String, dynamic>> _competitions = <Map<String, dynamic>>[];
  List<Map<String, dynamic>> _catalog = <Map<String, dynamic>>[];
  List<Map<String, dynamic>> _admins = <Map<String, dynamic>>[];
  List<Map<String, dynamic>> _auditLog = <Map<String, dynamic>>[];
  List<String> _permissionCatalog = <String>[];
  Map<String, dynamic>? _orchestrationPreview;

  final Set<String> _newAdminPermissions = <String>{
    'manage_manager_catalog',
    'manage_competitions',
    'manage_manager_supply',
  };
  final Map<String, Set<String>> _editedPermissions = <String, Set<String>>{};
  final Map<String, bool> _editedEnabled = <String, bool>{};

  @override
  void initState() {
    super.initState();
    _repository = ManagerAdminRepository.standard(
      baseUrl: widget.baseUrl,
      accessToken: widget.accessToken,
    );
    _competitionRepository = CompetitionControlRepository.standard(
      baseUrl: widget.baseUrl,
      accessToken: widget.accessToken,
    );
    _catalogSearch.addListener(() {
      if (mounted) {
        setState(() {});
      }
    });
    _load();
  }

  @override
  void dispose() {
    _email.dispose();
    _username.dispose();
    _password.dispose();
    _catalogSearch.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    if (mounted) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      final List<Future<Object>> requests = <Future<Object>>[
        _competitionRepository.fetchAdminCompetitions(),
        _repository.fetchCatalog(limit: 500),
        _repository.fetchAuditLog(),
      ];
      if (widget.role == 'super_admin') {
        requests.add(_repository.fetchAdmins());
        requests.add(_repository.fetchPermissionCatalog());
      }
      final List<Object> responses = await Future.wait<Object>(requests);
      if (!mounted) {
        return;
      }
      setState(() {
        _competitions = (responses[0] as List<dynamic>).cast<Map<String, dynamic>>();
        _catalog = (((responses[1] as Map<String, dynamic>)['items'] as List<dynamic>? ?? <dynamic>[]))
            .whereType<Map>()
            .map((dynamic item) => Map<String, dynamic>.from(item as Map))
            .toList();
        _auditLog = (responses[2] as List<dynamic>).cast<Map<String, dynamic>>();
        _admins = widget.role == 'super_admin'
            ? (responses[3] as List<dynamic>).cast<Map<String, dynamic>>()
            : <Map<String, dynamic>>[];
        _permissionCatalog = widget.role == 'super_admin'
            ? ((((responses[4] as Map<String, dynamic>)['permissions'] as List<dynamic>? ?? <dynamic>[]).map((dynamic item) => item.toString())).toList())
            : <String>[];
        _editedPermissions.clear();
        _editedEnabled.clear();
        for (final Map<String, dynamic> admin in _admins) {
          _editedPermissions[admin['id'].toString()] =
              ((admin['permissions'] as List<dynamic>? ?? <dynamic>[]).cast<String>()).toSet();
          _editedEnabled[admin['id'].toString()] = (admin['is_active'] ?? true) as bool;
        }
      });
      if (_competitions.isNotEmpty) {
        await _loadOrchestrationPreview((_competitions.first['code'] ?? '').toString());
      }
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = AppFeedback.messageFor(error);
      });
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  Future<void> _loadOrchestrationPreview(String code) async {
    if (code.isEmpty) {
      return;
    }
    try {
      final Map<String, dynamic> response = await _competitionRepository.fetchOrchestrationPreview(code);
      if (!mounted) {
        return;
      }
      setState(() {
        _orchestrationPreview = response;
      });
    } catch (_) {
      // Keep admin surface usable even if orchestration preview is unavailable.
    }
  }

  Future<void> _runAdminAction(Future<void> Function() action,
      {String? successMessage}) async {
    if (mounted) {
      setState(() {
        _saving = true;
      });
    }
    try {
      await action();
      if (!mounted) {
        return;
      }
      if (successMessage != null && successMessage.isNotEmpty) {
        AppFeedback.showSuccess(context, successMessage);
      }
    } catch (error) {
      if (!mounted) {
        return;
      }
      AppFeedback.showError(context, error);
    } finally {
      if (mounted) {
        setState(() {
          _saving = false;
        });
      }
    }
  }

  Future<void> _toggleCompetition(Map<String, dynamic> item, bool value) async {
    await _runAdminAction(() async {
      await _competitionRepository.updateCompetition(
        item['code'].toString(),
        <String, Object?>{'enabled': value},
      );
      await _load();
    }, successMessage: 'Competition settings updated.');
  }

  Future<void> _bumpSupply(Map<String, dynamic> item, int delta) async {
    final int current = (item['supply_total'] ?? 0) as int? ?? 0;
    await _runAdminAction(() async {
      await _repository.updateManagerSupply(
        item['manager_id'].toString(),
        current + delta < 0 ? 0 : current + delta,
        delta > 0 ? 'Admin increased supply' : 'Admin reduced supply',
      );
      await _load();
    }, successMessage: 'Manager supply updated.');
  }

  Future<void> _createAdmin() async {
    if (_email.text.trim().isEmpty ||
        _username.text.trim().isEmpty ||
        _password.text.isEmpty) {
      AppFeedback.showError(context, 'Email, username, and password are required.');
      return;
    }
    await _runAdminAction(() async {
      await _repository.createAdmin(
        email: _email.text.trim(),
        username: _username.text.trim(),
        password: _password.text,
        permissions: _newAdminPermissions.toList()..sort(),
      );
      _email.clear();
      _username.clear();
      _password.text = 'AdminPass123!';
      await _load();
    }, successMessage: 'Admin account created.');
  }

  Future<void> _saveAdmin(Map<String, dynamic> admin) async {
    final String userId = admin['id'].toString();
    await _runAdminAction(() async {
      await _repository.updateAdminPermissions(
        userId: userId,
        permissions: (_editedPermissions[userId] ?? <String>{}).toList()..sort(),
        isEnabled: _editedEnabled[userId] ?? true,
      );
      await _load();
    }, successMessage: 'Admin permissions updated.');
  }

  Widget _stateCard({
    required IconData icon,
    required String title,
    required String message,
    String? actionLabel,
    VoidCallback? onAction,
  }) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          children: <Widget>[
            Icon(icon, size: 32),
            const SizedBox(height: 12),
            Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text(message, textAlign: TextAlign.center),
            if (actionLabel != null && onAction != null) ...<Widget>[
              const SizedBox(height: 12),
              FilledButton.tonal(onPressed: onAction, child: Text(actionLabel)),
            ],
          ],
        ),
      ),
    );
  }

  Widget _permissionWrap(Set<String> selected, ValueChanged<String> toggle) {
    final List<String> options = _permissionCatalog.isEmpty
        ? <String>[
            'manage_manager_catalog',
            'manage_competitions',
            'manage_manager_supply',
            'review_audit_log',
          ]
        : _permissionCatalog;
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: options.map((String permission) {
        final bool active = selected.contains(permission);
        return FilterChip(
          selected: active,
          label: Text(permission),
          onSelected: (_) => toggle(permission),
        );
      }).toList(),
    );
  }

  List<Map<String, dynamic>> get _filteredCatalog {
    final String term = _catalogSearch.text.trim().toLowerCase();
    if (term.isEmpty) {
      return _catalog;
    }
    return _catalog.where((Map<String, dynamic> item) {
      final String displayName =
          (item['display_name'] ?? '').toString().toLowerCase();
      final String rarity = (item['rarity'] ?? '').toString().toLowerCase();
      final String mentality =
          (item['mentality'] ?? '').toString().toLowerCase();
      return displayName.contains(term) ||
          rarity.contains(term) ||
          mentality.contains(term);
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final List<Map<String, dynamic>> visibleCatalog =
        _filteredCatalog.take(120).toList();

    return Scaffold(
      appBar: AppBar(title: const Text('Manager operations desk')),
      body: _loading
          ? const Padding(
              padding: EdgeInsets.all(24),
              child: GteStatePanel(
                eyebrow: 'MANAGER OPERATIONS',
                title: 'Loading manager operations desk',
                message: 'Preparing coach scarcity, competition orchestration, and admin control signals.',
                icon: Icons.sports_outlined,
                accentColor: Colors.orangeAccent,
              ),
            )
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: _stateCard(
                      icon: Icons.warning_amber_rounded,
                      title: 'Admin data unavailable',
                      message: _error!,
                      actionLabel: 'Retry',
                      onAction: _load,
                    ),
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: <Widget>[
                      GtexHeroBanner(
                        eyebrow: 'MANAGER OPERATIONS',
                        title: 'Run the scarce coach ecosystem with premium controls and clean market integrity.',
                        description: 'Supply, metadata, traits, tactics, competition orchestration, and audit review all live here. This surface should read like a premium control tower for coach scarcity, not an admin spreadsheet dump.',
                        accent: Colors.orangeAccent,
                        chips: <Widget>[
                          Chip(label: Text('Catalog ${_catalog.length}')),
                          Chip(label: Text('Admins ${_admins.length}')),
                          Chip(label: Text('Competitions ${_competitions.length}')),
                        ],
                      ),
                      const SizedBox(height: 16),
                      if (_saving) ...<Widget>[
                        const LinearProgressIndicator(),
                        const SizedBox(height: 16),
                      ],
                      const _SectionHeading(
                        eyebrow: 'MATCH GOVERNANCE',
                        title: 'Competition controls',
                        detail: 'Keep creator and manager competitions live, stable, and orchestrated without breaking integrity.',
                      ),
                      const SizedBox(height: 8),
                      if (_competitions.isEmpty)
                        _stateCard(
                          icon: Icons.emoji_events_outlined,
                          title: 'No competitions configured',
                          message:
                              'Competition controls have not been seeded yet.',
                        )
                      else
                        ..._competitions.map(
                          (Map<String, dynamic> item) => SwitchListTile(
                            value: (item['enabled'] ?? false) as bool,
                            onChanged: _saving
                                ? null
                                : (bool value) => _toggleCompetition(item, value),
                            secondary: IconButton(
                              tooltip: 'Preview orchestration',
                              onPressed: _saving ? null : () => _loadOrchestrationPreview((item['code'] ?? '').toString()),
                              icon: const Icon(Icons.visibility_outlined),
                            ),
                            title: Text((item['label'] ?? '').toString()),
                            subtitle: Text(
                              'Min participants: ${(item['minimum_viable_participants'] ?? '').toString()}'
                              ' • fallback: ${(item['allow_fallback_fill'] ?? false) ? 'on' : 'off'}',
                            ),
                          ),
                        ),
                      if (_orchestrationPreview != null) ...<Widget>[
                        const SizedBox(height: 12),
                        Card(
                          child: Padding(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                const Text('Competition orchestration preview', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                                const SizedBox(height: 8),
                                Text('Code: ${(_orchestrationPreview!['code'] ?? '').toString()} • Entrants: ${(_orchestrationPreview!['entrants'] ?? '').toString()} • Fallback: ${((_orchestrationPreview!['fallback_used'] ?? false) as bool) ? 'on' : 'off'}'),
                                const SizedBox(height: 8),
                                Text(((_orchestrationPreview!['notes'] as List<dynamic>? ?? <dynamic>[]).join(' • ')).toString()),
                              ],
                            ),
                          ),
                        ),
                      ],
                      const Divider(height: 32),
                      const _SectionHeading(
                        eyebrow: 'SCARCITY CONTROL',
                        title: 'Manager supply desk',
                        detail: 'Search the coach catalog, tune supply, and preserve rarity without muddying the market story.',
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: _catalogSearch,
                        decoration: const InputDecoration(
                          labelText: 'Search coach catalog',
                          hintText: 'Name, mentality, or rarity',
                          prefixIcon: Icon(Icons.search),
                        ),
                      ),
                      const SizedBox(height: 12),
                      if (visibleCatalog.isEmpty)
                        _stateCard(
                          icon: Icons.search_off,
                          title: 'No coach rows matched this control view',
                          message: _catalogSearch.text.trim().isEmpty
                              ? 'Manager supply data is empty.'
                              : 'Try a different name, mentality, or rarity signal.',
                          actionLabel: _catalogSearch.text.trim().isEmpty
                              ? null
                              : 'Clear search',
                          onAction: _catalogSearch.text.trim().isEmpty
                              ? null
                              : () {
                                  _catalogSearch.clear();
                                },
                        )
                      else
                        ...visibleCatalog.map(
                          (Map<String, dynamic> item) => ListTile(
                            title: Text((item['display_name'] ?? '').toString()),
                            subtitle: Text(
                              '${(item['rarity'] ?? '').toString()} • total: ${(item['supply_total'] ?? '').toString()}'
                              ' • available: ${(item['supply_available'] ?? '').toString()}',
                            ),
                            trailing: Wrap(
                              spacing: 8,
                              children: <Widget>[
                                IconButton(
                                  onPressed: _saving
                                      ? null
                                      : () => _bumpSupply(item, -1),
                                  icon: const Icon(Icons.remove_circle_outline),
                                ),
                                IconButton(
                                  onPressed: _saving
                                      ? null
                                      : () => _bumpSupply(item, 1),
                                  icon: const Icon(Icons.add_circle_outline),
                                ),
                              ],
                            ),
                          ),
                        ),
                      if (widget.role == 'super_admin') ...<Widget>[
                        const Divider(height: 32),
                        const Text(
                          'Create admin',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 8),
                        TextField(
                          controller: _email,
                          decoration:
                              const InputDecoration(labelText: 'Email'),
                        ),
                        const SizedBox(height: 8),
                        TextField(
                          controller: _username,
                          decoration:
                              const InputDecoration(labelText: 'Username'),
                        ),
                        const SizedBox(height: 8),
                        TextField(
                          controller: _password,
                          decoration:
                              const InputDecoration(labelText: 'Password'),
                        ),
                        const SizedBox(height: 12),
                        _permissionWrap(_newAdminPermissions, (String permission) {
                          setState(() {
                            if (_newAdminPermissions.contains(permission)) {
                              _newAdminPermissions.remove(permission);
                            } else {
                              _newAdminPermissions.add(permission);
                            }
                          });
                        }),
                        const SizedBox(height: 8),
                        FilledButton(
                          onPressed: _saving ? null : _createAdmin,
                          child: const Text('Create admin'),
                        ),
                        const SizedBox(height: 16),
                        const Text(
                          'Existing admins',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 8),
                        if (_admins.isEmpty)
                          _stateCard(
                            icon: Icons.admin_panel_settings_outlined,
                            title: 'No delegated admins yet',
                            message:
                                'Super admin can create scoped admin accounts from this desk.',
                          )
                        else
                          ..._admins.map(
                            (Map<String, dynamic> item) => Card(
                              child: Padding(
                                padding: const EdgeInsets.all(12),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: <Widget>[
                                    Row(
                                      children: <Widget>[
                                        Expanded(
                                          child: Text(
                                            (item['email'] ?? '').toString(),
                                            style: const TextStyle(
                                              fontWeight: FontWeight.bold,
                                            ),
                                          ),
                                        ),
                                        Switch(
                                          value: _editedEnabled[item['id'].toString()] ?? true,
                                          onChanged: _saving
                                              ? null
                                              : (bool value) => setState(
                                                    () => _editedEnabled[item['id'].toString()] = value,
                                                  ),
                                        ),
                                      ],
                                    ),
                                    Text(
                                      '${(item['role'] ?? '').toString()} • ${(item['username'] ?? '').toString()}',
                                    ),
                                    const SizedBox(height: 8),
                                    _permissionWrap(
                                      _editedPermissions[item['id'].toString()] ?? <String>{},
                                      (String permission) {
                                        final Set<String> selected =
                                            _editedPermissions[item['id'].toString()] ??
                                                <String>{};
                                        setState(() {
                                          if (selected.contains(permission)) {
                                            selected.remove(permission);
                                          } else {
                                            selected.add(permission);
                                          }
                                          _editedPermissions[item['id'].toString()] =
                                              selected;
                                        });
                                      },
                                    ),
                                    const SizedBox(height: 8),
                                    Align(
                                      alignment: Alignment.centerRight,
                                      child: FilledButton.tonal(
                                        onPressed: _saving
                                            ? null
                                            : () => _saveAdmin(item),
                                        child: const Text('Save admin access'),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                      ],
                      const Divider(height: 32),
                      const Text(
                        'Recent audit log',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      if (_auditLog.isEmpty)
                        _stateCard(
                          icon: Icons.history_outlined,
                          title: 'Audit log is empty',
                          message:
                              'Privileged coach-market actions, supply changes, and admin interventions will appear here once the control tower starts seeing traffic.',
                        )
                      else
                        ..._auditLog.take(30).map(
                          (Map<String, dynamic> event) => ListTile(
                            dense: true,
                            title: Text((event['event_type'] ?? '').toString()),
                            subtitle: Text(
                              '${(event['actor_email'] ?? '').toString()} • ${(event['created_at'] ?? '').toString()}\n'
                              '${(event['payload'] ?? const <String, dynamic>{}).toString()}',
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
    );
  }
}


class ManagerAdminRepository {
  ManagerAdminRepository({required this.config, required this.transport, required this.accessToken})
      : _managerRepository = ManagerMarketRepository(config: config, transport: transport, accessToken: accessToken);

  final GteRepositoryConfig config;
  final GteTransport transport;
  final String accessToken;
  final ManagerMarketRepository _managerRepository;

  factory ManagerAdminRepository.standard({required String baseUrl, required String accessToken, GteBackendMode mode = GteBackendMode.liveThenFixture}) {
    return ManagerAdminRepository(
      config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
      transport: GteHttpTransport(),
      accessToken: accessToken,
    );
  }

  Future<Map<String, dynamic>> fetchCatalog({int limit = 500}) => _managerRepository.fetchCatalog(limit: limit);
  Future<List<Map<String, dynamic>>> fetchAuditLog() => _getList('/api/admin/managers/audit-log');
  Future<List<Map<String, dynamic>>> fetchAdmins() => _getList('/api/admin/access');
  Future<Map<String, dynamic>> fetchPermissionCatalog() => _getMap('/api/admin/access/permissions');
  Future<void> updateManagerSupply(String managerId, int supplyTotal, String reason) => _request('PUT', '/api/admin/managers/catalog/$managerId/supply', body: <String, Object?>{'supply_total': supplyTotal, 'reason': reason});
  Future<void> createAdmin({required String email, required String username, required String password, required List<String> permissions}) => _request('POST', '/api/admin/access', body: <String, Object?>{'email': email, 'username': username, 'password': password, 'permissions': permissions});
  Future<void> updateAdminPermissions({required String userId, required List<String> permissions, required bool isEnabled}) => _request('PUT', '/api/admin/access/$userId/permissions', body: <String, Object?>{'permissions': permissions, 'is_enabled': isEnabled});

  Future<Map<String, dynamic>> _getMap(String path) async {
    final Object? body = await _request('GET', path);
    if (body is Map<String, dynamic>) return body;
    throw const GteApiException(type: GteApiErrorType.parsing, message: 'Unexpected admin response shape.');
  }

  Future<List<Map<String, dynamic>>> _getList(String path) async {
    final Object? body = await _request('GET', path);
    if (body is List) return body.whereType<Map>().map((dynamic item) => Map<String, dynamic>.from(item as Map)).toList(growable: false);
    throw const GteApiException(type: GteApiErrorType.parsing, message: 'Unexpected admin list response shape.');
  }

  Future<Object?> _request(String method, String path, {Object? body}) async {
    final GteTransportResponse response = await transport.send(
      GteTransportRequest(
        method: method,
        uri: config.uriFor(path),
        headers: <String, String>{
          'Authorization': 'Bearer $accessToken',
          'Content-Type': 'application/json',
        },
        body: body,
      ),
    );
    if (response.statusCode >= 400) {
      throw _toException(response);
    }
    return response.body;
  }

  GteApiException _toException(GteTransportResponse response) {
    final Object? body = response.body;
    String message = 'Admin request failed.';
    if (body is Map<String, dynamic>) {
      message = (body['detail'] ?? body['message'] ?? message).toString();
    } else if (body is String && body.trim().isNotEmpty) {
      message = body;
    }
    return GteApiException(type: GteApiErrorType.unknown, message: message, statusCode: response.statusCode);
  }
}

class _SectionHeading extends StatelessWidget {
  const _SectionHeading({
    required this.eyebrow,
    required this.title,
    required this.detail,
  });

  final String eyebrow;
  final String title;
  final String detail;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            eyebrow,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: Colors.orangeAccent,
              letterSpacing: 1.0,
            ),
          ),
          const SizedBox(height: 8),
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 6),
          Text(detail, style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    );
  }
}
