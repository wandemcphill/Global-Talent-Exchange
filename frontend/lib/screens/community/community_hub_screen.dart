import 'package:flutter/material.dart';

import '../../core/app_feedback.dart';
import '../../data/community_api.dart';
import '../../data/discovery_api.dart';
import '../../data/dispute_engine_api.dart';
import '../../data/gte_api_repository.dart';
import '../../data/governance_api.dart';
import '../../data/moderation_api.dart';
import '../../data/notification_settings_api.dart';
import '../../data/story_feed_api.dart';
import '../../models/community_models.dart';
import '../../models/discovery_models.dart';
import '../../models/dispute_engine_models.dart';
import '../../models/governance_models.dart';
import '../../models/moderation_models.dart';
import '../../models/notification_settings_models.dart';
import '../../models/story_feed_models.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_metric_chip.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import '../../widgets/gtex_branding.dart';

class CommunityHubScreen extends StatefulWidget {
  const CommunityHubScreen({
    super.key,
    required this.controller,
    required this.baseUrl,
    required this.backendMode,
    this.onOpenAdmin,
  });

  final GteExchangeController controller;
  final String baseUrl;
  final GteBackendMode backendMode;
  final VoidCallback? onOpenAdmin;

  @override
  State<CommunityHubScreen> createState() => _CommunityHubScreenState();
}

enum CommunitySection {
  discovery,
  notifications,
  feed,
  community,
  reports,
  disputes,
  governance,
}

extension CommunitySectionX on CommunitySection {
  String get label {
    switch (this) {
      case CommunitySection.discovery:
        return 'Discovery';
      case CommunitySection.notifications:
        return 'Notifications';
      case CommunitySection.feed:
        return 'Story feed';
      case CommunitySection.community:
        return 'Live threads';
      case CommunitySection.reports:
        return 'Reports';
      case CommunitySection.disputes:
        return 'Disputes';
      case CommunitySection.governance:
        return 'Governance';
    }
  }

  IconData get icon {
    switch (this) {
      case CommunitySection.discovery:
        return Icons.travel_explore_outlined;
      case CommunitySection.notifications:
        return Icons.notifications_active_outlined;
      case CommunitySection.feed:
        return Icons.article_outlined;
      case CommunitySection.community:
        return Icons.forum_outlined;
      case CommunitySection.reports:
        return Icons.report_gmailerrorred_outlined;
      case CommunitySection.disputes:
        return Icons.gavel_outlined;
      case CommunitySection.governance:
        return Icons.how_to_vote_outlined;
    }
  }

  String get subtitle {
    switch (this) {
      case CommunitySection.discovery:
        return 'Rails, search, and saved discovery cues.';
      case CommunitySection.notifications:
        return 'Preferences, subscriptions, and broadcasts.';
      case CommunitySection.feed:
        return 'Story cards and matchday narratives.';
      case CommunitySection.community:
        return 'Live threads, watchlist, and private messages.';
      case CommunitySection.reports:
        return 'Moderation reports and follow-ups.';
      case CommunitySection.disputes:
        return 'Case creation, status, and messaging.';
      case CommunitySection.governance:
        return 'Proposals, voting, and personal overview.';
    }
  }
}

class _CommunityHubScreenState extends State<CommunityHubScreen> {
  CommunitySection _section = CommunitySection.discovery;

  void _selectSection(CommunitySection section) {
    setState(() {
      _section = section;
    });
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool isWide = constraints.maxWidth >= 1100;
        final Widget sectionPicker = isWide
            ? NavigationRail(
                selectedIndex: CommunitySection.values.indexOf(_section),
                onDestinationSelected: (int index) {
                  _selectSection(CommunitySection.values[index]);
                },
                backgroundColor: Colors.transparent,
                labelType: NavigationRailLabelType.all,
                destinations: CommunitySection.values
                    .map(
                      (CommunitySection section) => NavigationRailDestination(
                        icon: Icon(section.icon),
                        selectedIcon: Icon(section.icon),
                        label: Text(section.label),
                      ),
                    )
                    .toList(growable: false),
              )
            : GteSurfacePanel(
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<CommunitySection>(
                    value: _section,
                    isExpanded: true,
                    onChanged: (CommunitySection? value) {
                      if (value != null) {
                        _selectSection(value);
                      }
                    },
                    items: CommunitySection.values
                        .map(
                          (CommunitySection section) =>
                              DropdownMenuItem<CommunitySection>(
                            value: section,
                            child: Text(section.label),
                          ),
                        )
                        .toList(growable: false),
                  ),
                ),
              );

        final Widget content = _CommunitySectionHost(
          section: _section,
          baseUrl: widget.baseUrl,
          backendMode: widget.backendMode,
          accessToken: widget.controller.accessToken,
          isAuthenticated: widget.controller.isAuthenticated,
        );

        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            if (isWide)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 16, 0, 0),
                child: sectionPicker,
              ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    GtexHeroBanner(
                      eyebrow: 'COMMUNITY + GOVERNANCE',
                      title:
                          'Threads, discovery rails, and proposals stay visible without crowding the trading floor.',
                      description:
                          'The community lane keeps live threads, notifications, disputes, and governance in one structured area so market execution never loses clarity.',
                      accent: GteShellTheme.accentCommunity,
                      chips: <Widget>[
                        GteMetricChip(label: 'Section', value: _section.label),
                        GteMetricChip(
                          label: 'Access',
                          value: widget.controller.isAuthenticated
                              ? 'SIGNED IN'
                              : 'PREVIEW',
                          positive: widget.controller.isAuthenticated,
                        ),
                        const GteMetricChip(
                          label: 'Lane',
                          value: 'COMMUNITY',
                          positive: true,
                        ),
                      ],
                      actions: <Widget>[
                        if (widget.controller.isAdmin &&
                            widget.onOpenAdmin != null)
                          FilledButton.tonalIcon(
                            onPressed: widget.onOpenAdmin,
                            icon:
                                const Icon(Icons.admin_panel_settings_outlined),
                            label: const Text('Open admin ops'),
                          ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    if (!isWide) sectionPicker,
                    const SizedBox(height: 16),
                    content,
                  ],
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}

class _CommunitySectionHost extends StatelessWidget {
  const _CommunitySectionHost({
    required this.section,
    required this.baseUrl,
    required this.backendMode,
    required this.accessToken,
    required this.isAuthenticated,
  });

  final CommunitySection section;
  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final bool isAuthenticated;

  @override
  Widget build(BuildContext context) {
    switch (section) {
      case CommunitySection.discovery:
        return _DiscoverySection(
          baseUrl: baseUrl,
          backendMode: backendMode,
          accessToken: accessToken,
          isAuthenticated: isAuthenticated,
        );
      case CommunitySection.notifications:
        return _NotificationsSection(
          baseUrl: baseUrl,
          backendMode: backendMode,
          accessToken: accessToken,
          isAuthenticated: isAuthenticated,
        );
      case CommunitySection.feed:
        return _FeedSection(
          baseUrl: baseUrl,
          backendMode: backendMode,
          accessToken: accessToken,
        );
      case CommunitySection.community:
        return _CommunityThreadsSection(
          baseUrl: baseUrl,
          backendMode: backendMode,
          accessToken: accessToken,
          isAuthenticated: isAuthenticated,
        );
      case CommunitySection.reports:
        return _ReportsSection(
          baseUrl: baseUrl,
          backendMode: backendMode,
          accessToken: accessToken,
          isAuthenticated: isAuthenticated,
        );
      case CommunitySection.disputes:
        return _DisputesSection(
          baseUrl: baseUrl,
          backendMode: backendMode,
          accessToken: accessToken,
          isAuthenticated: isAuthenticated,
        );
      case CommunitySection.governance:
        return _GovernanceSection(
          baseUrl: baseUrl,
          backendMode: backendMode,
          accessToken: accessToken,
          isAuthenticated: isAuthenticated,
        );
    }
  }
}

class _DiscoverySection extends StatefulWidget {
  const _DiscoverySection({
    required this.baseUrl,
    required this.backendMode,
    required this.accessToken,
    required this.isAuthenticated,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final bool isAuthenticated;

  @override
  State<_DiscoverySection> createState() => _DiscoverySectionState();
}

class _DiscoverySectionState extends State<_DiscoverySection> {
  late DiscoveryApi _api;
  late Future<DiscoveryHome> _homeFuture;
  late Future<List<SavedSearch>> _savedFuture;
  final TextEditingController _searchController = TextEditingController();
  String _entityScope = 'all';
  List<DiscoveryItem> _results = <DiscoveryItem>[];
  bool _isSearching = false;
  String? _searchError;

  @override
  void initState() {
    super.initState();
    _buildApi();
    _load();
  }

  @override
  void didUpdateWidget(covariant _DiscoverySection oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.baseUrl != widget.baseUrl ||
        oldWidget.backendMode != widget.backendMode ||
        oldWidget.accessToken != widget.accessToken) {
      _buildApi();
      _load();
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _buildApi() {
    _api = DiscoveryApi.standard(
      baseUrl: widget.baseUrl,
      accessToken: widget.accessToken,
      mode: widget.backendMode,
    );
  }

  void _load() {
    _homeFuture = _api.fetchHome();
    _savedFuture = _api.listSavedSearches();
  }

  Future<void> _runSearch() async {
    final String query = _searchController.text.trim();
    if (query.isEmpty) {
      setState(() {
        _searchError = 'Enter a query to search.';
        _results = <DiscoveryItem>[];
      });
      return;
    }
    setState(() {
      _isSearching = true;
      _searchError = null;
    });
    try {
      final List<DiscoveryItem> items = await _api.search(
        query: query,
        entityScope: _entityScope,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _results = items;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _searchError = AppFeedback.messageFor(error);
        _results = <DiscoveryItem>[];
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSearching = false;
        });
      }
    }
  }

  Future<void> _saveSearch() async {
    final String query = _searchController.text.trim();
    if (query.isEmpty) {
      setState(() {
        _searchError = 'Enter a query before saving.';
      });
      return;
    }
    try {
      await _api.createSavedSearch(query: query, entityScope: _entityScope);
      if (!mounted) {
        return;
      }
      setState(() {
        _savedFuture = _api.listSavedSearches();
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _searchError = AppFeedback.messageFor(error);
      });
    }
  }

  Future<void> _deleteSaved(String id) async {
    try {
      await _api.deleteSavedSearch(id);
      if (!mounted) {
        return;
      }
      setState(() {
        _savedFuture = _api.listSavedSearches();
      });
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _savedFuture = _api.listSavedSearches();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        if (!widget.isAuthenticated)
          const GteStatePanel(
            eyebrow: 'DISCOVERY ACCESS',
            title: 'Sign in to unlock discovery and saved searches.',
            message:
                'Preview mode shows curated rails, but personalized search and saved queries require an authenticated session.',
            icon: Icons.lock_outline,
          ),
        const SizedBox(height: 16),
        GteSurfacePanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Search the discovery rails',
                  style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 12),
              TextField(
                controller: _searchController,
                decoration: const InputDecoration(
                  labelText: 'Search query',
                  prefixIcon: Icon(Icons.search),
                ),
                textInputAction: TextInputAction.search,
                onSubmitted: (_) => _runSearch(),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: _entityScope,
                items: const <DropdownMenuItem<String>>[
                  DropdownMenuItem(value: 'all', child: Text('All lanes')),
                  DropdownMenuItem(value: 'market', child: Text('Market')),
                  DropdownMenuItem(
                      value: 'competition', child: Text('Competitions')),
                  DropdownMenuItem(
                      value: 'community', child: Text('Community')),
                ],
                onChanged: (String? value) {
                  if (value != null) {
                    setState(() {
                      _entityScope = value;
                    });
                  }
                },
                decoration: const InputDecoration(
                  labelText: 'Entity scope',
                  prefixIcon: Icon(Icons.tune_outlined),
                ),
              ),
              if (_searchError != null) ...<Widget>[
                const SizedBox(height: 12),
                GteStatePanel(
                  title: 'Search error',
                  message: _searchError!,
                  icon: Icons.warning_amber_outlined,
                ),
              ],
              const SizedBox(height: 12),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: <Widget>[
                  FilledButton.icon(
                    onPressed: _isSearching ? null : _runSearch,
                    icon: const Icon(Icons.search),
                    label: Text(_isSearching ? 'Searching...' : 'Run search'),
                  ),
                  OutlinedButton.icon(
                    onPressed: _isSearching ? null : _saveSearch,
                    icon: const Icon(Icons.bookmark_add_outlined),
                    label: const Text('Save search'),
                  ),
                ],
              ),
              if (_results.isNotEmpty) ...<Widget>[
                const SizedBox(height: 16),
                Text('Results',
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 12),
                for (final DiscoveryItem item in _results)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: _DiscoveryItemTile(item: item),
                  ),
              ]
            ],
          ),
        ),
        const SizedBox(height: 16),
        FutureBuilder<List<SavedSearch>>(
          future: _savedFuture,
          builder:
              (BuildContext context, AsyncSnapshot<List<SavedSearch>> snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const GteSurfacePanel(
                child: Text('Loading saved searches...'),
              );
            }
            final List<SavedSearch> saved = snapshot.data ?? <SavedSearch>[];
            return GteSurfacePanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Saved searches',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 12),
                  if (saved.isEmpty)
                    const Text('No saved searches yet.')
                  else
                    for (final SavedSearch search in saved)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Row(
                          children: <Widget>[
                            Expanded(
                              child: Text(
                                '${search.query} • ${search.entityScope}',
                                style: Theme.of(context).textTheme.bodyMedium,
                              ),
                            ),
                            IconButton(
                              onPressed: () => _deleteSaved(search.id),
                              icon: const Icon(Icons.close),
                            ),
                          ],
                        ),
                      ),
                ],
              ),
            );
          },
        ),
        const SizedBox(height: 16),
        FutureBuilder<DiscoveryHome>(
          future: _homeFuture,
          builder: (BuildContext context,
              AsyncSnapshot<DiscoveryHome> snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const GteSurfacePanel(
                child: Text('Loading discovery rails...'),
              );
            }
            if (!snapshot.hasData) {
              return GteStatePanel(
                title: 'Discovery rails unavailable',
                message: snapshot.error == null
                    ? 'Unable to load discovery rails right now.'
                    : AppFeedback.messageFor(snapshot.error!),
                icon: Icons.warning_amber_outlined,
                actionLabel: 'Retry',
                onAction: () {
                  setState(() {
                    _homeFuture = _api.fetchHome();
                  });
                },
              );
            }
            final DiscoveryHome home = snapshot.data!;
            return GteSurfacePanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Discovery rails',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 12),
                  for (final FeaturedRail rail in home.featuredRails)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _DiscoveryRailTile(rail: rail),
                    ),
                  const Divider(height: 24),
                  Text('Featured items',
                      style: Theme.of(context).textTheme.titleSmall),
                  const SizedBox(height: 10),
                  if (home.featuredItems.isEmpty)
                    const Text('No featured items yet.')
                  else
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: home.featuredItems
                          .map((DiscoveryItem item) =>
                              _DiscoveryItemChip(item: item))
                          .toList(growable: false),
                    ),
                  const SizedBox(height: 16),
                  Text('Live now',
                      style: Theme.of(context).textTheme.titleSmall),
                  const SizedBox(height: 10),
                  if (home.liveNowItems.isEmpty)
                    const Text('No live items flagged yet.')
                  else
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: home.liveNowItems
                          .map((DiscoveryItem item) =>
                              _DiscoveryItemChip(item: item))
                          .toList(growable: false),
                    ),
                ],
              ),
            );
          },
        ),
      ],
    );
  }
}

class _DiscoveryRailTile extends StatelessWidget {
  const _DiscoveryRailTile({required this.rail});

  final FeaturedRail rail;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: Colors.white.withValues(alpha: 0.04),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(rail.title, style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 4),
          Text(rail.subtitle, style: Theme.of(context).textTheme.bodySmall),
          if (rail.queryHint != null && rail.queryHint!.isNotEmpty) ...<Widget>[
            const SizedBox(height: 6),
            Text('Hint: ${rail.queryHint}',
                style: Theme.of(context).textTheme.bodySmall),
          ],
        ],
      ),
    );
  }
}

class _DiscoveryItemTile extends StatelessWidget {
  const _DiscoveryItemTile({required this.item});

  final DiscoveryItem item;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: Colors.white.withValues(alpha: 0.04),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(item.title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 4),
          Text(item.subtitle, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 6),
          Text('Type: ${item.itemType}',
              style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}

class _DiscoveryItemChip extends StatelessWidget {
  const _DiscoveryItemChip({required this.item});

  final DiscoveryItem item;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: Colors.white.withValues(alpha: 0.05),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Text(item.title, style: Theme.of(context).textTheme.labelLarge),
    );
  }
}

class _NotificationsSection extends StatefulWidget {
  const _NotificationsSection({
    required this.baseUrl,
    required this.backendMode,
    required this.accessToken,
    required this.isAuthenticated,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final bool isAuthenticated;

  @override
  State<_NotificationsSection> createState() => _NotificationsSectionState();
}

class _NotificationsSectionState extends State<_NotificationsSection> {
  late NotificationSettingsApi _api;
  NotificationPreference? _preference;
  List<NotificationSubscription> _subscriptions =
      const <NotificationSubscription>[];
  List<PlatformAnnouncement> _announcements = const <PlatformAnnouncement>[];
  bool _loading = true;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _buildApi();
    _load();
  }

  @override
  void didUpdateWidget(covariant _NotificationsSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.baseUrl != widget.baseUrl ||
        oldWidget.backendMode != widget.backendMode ||
        oldWidget.accessToken != widget.accessToken) {
      _buildApi();
      _load();
    }
  }

  void _buildApi() {
    _api = NotificationSettingsApi.standard(
      baseUrl: widget.baseUrl,
      accessToken: widget.accessToken,
      mode: widget.backendMode,
    );
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final List<dynamic> payload = await Future.wait<dynamic>(<Future<dynamic>>[
        if (widget.isAuthenticated) _api.fetchPreferences(),
        if (widget.isAuthenticated) _api.listSubscriptions(),
        _api.listAnnouncements(),
      ]);
      if (!mounted) {
        return;
      }
      setState(() {
        int index = 0;
        if (widget.isAuthenticated) {
          _preference = payload[index++] as NotificationPreference;
          _subscriptions = payload[index++] as List<NotificationSubscription>;
        }
        _announcements = payload[index] as List<PlatformAnnouncement>;
      });
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

  Future<void> _savePreferences() async {
    if (_preference == null) {
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final NotificationPreference next =
          await _api.updatePreferences(_preference!);
      if (!mounted) {
        return;
      }
      setState(() {
        _preference = next;
      });
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
          _saving = false;
        });
      }
    }
  }

  Future<void> _toggleSubscription(NotificationSubscription subscription) async {
    try {
      final NotificationSubscription updated = await _api.upsertSubscription(
        subscriptionKey: subscription.subscriptionKey,
        label: subscription.label,
        subscriptionType: subscription.subscriptionType,
        active: !subscription.active,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _subscriptions = _subscriptions
            .map((NotificationSubscription item) =>
                item.id == updated.id ? updated : item)
            .toList(growable: false);
      });
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = 'Unable to update subscription.';
      });
    }
  }

  void _updatePreference(NotificationPreference next) {
    setState(() {
      _preference = next;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const GteSurfacePanel(
        child: Text('Loading notification settings...'),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        if (_error != null)
          GteStatePanel(
            title: 'Notification settings error',
            message: _error!,
            icon: Icons.warning_amber_outlined,
            actionLabel: 'Retry',
            onAction: _load,
          ),
        if (widget.isAuthenticated && _preference != null) ...<Widget>[
          GteSurfacePanel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('Preferences',
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                SwitchListTile.adaptive(
                  value: _preference!.allowWallet,
                  onChanged: (bool value) => _updatePreference(
                      _preference!.copyWith(allowWallet: value)),
                  title: const Text('Wallet alerts'),
                ),
                SwitchListTile.adaptive(
                  value: _preference!.allowMarket,
                  onChanged: (bool value) => _updatePreference(
                      _preference!.copyWith(allowMarket: value)),
                  title: const Text('Market alerts'),
                ),
                SwitchListTile.adaptive(
                  value: _preference!.allowCompetition,
                  onChanged: (bool value) => _updatePreference(
                      _preference!.copyWith(allowCompetition: value)),
                  title: const Text('Competition alerts'),
                ),
                SwitchListTile.adaptive(
                  value: _preference!.allowSocial,
                  onChanged: (bool value) => _updatePreference(
                      _preference!.copyWith(allowSocial: value)),
                  title: const Text('Social alerts'),
                ),
                SwitchListTile.adaptive(
                  value: _preference!.allowBroadcasts,
                  onChanged: (bool value) => _updatePreference(
                      _preference!.copyWith(allowBroadcasts: value)),
                  title: const Text('Broadcast alerts'),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: _saving ? null : _savePreferences,
                    icon: const Icon(Icons.save_outlined),
                    label: Text(_saving ? 'Saving...' : 'Save preferences'),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          GteSurfacePanel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('Subscriptions',
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                if (_subscriptions.isEmpty)
                  const Text('No subscriptions found.')
                else
                  for (final NotificationSubscription sub in _subscriptions)
                    SwitchListTile.adaptive(
                      value: sub.active,
                      onChanged: (_) => _toggleSubscription(sub),
                      title: Text(sub.label),
                      subtitle: Text(sub.subscriptionType),
                    ),
              ],
            ),
          ),
          const SizedBox(height: 16),
        ] else if (!widget.isAuthenticated) ...<Widget>[
          const GteStatePanel(
            eyebrow: 'NOTIFICATIONS',
            title: 'Sign in to manage notification preferences.',
            message:
                'Broadcast announcements are visible, but preferences and subscriptions require an authenticated account.',
            icon: Icons.lock_outline,
          ),
          const SizedBox(height: 16),
        ],
        GteSurfacePanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Announcements',
                  style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 12),
              if (_announcements.isEmpty)
                const Text('No announcements published yet.')
              else
                for (final PlatformAnnouncement announcement in _announcements)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(announcement.title,
                            style: Theme.of(context).textTheme.titleSmall),
                        const SizedBox(height: 4),
                        Text(announcement.body,
                            style: Theme.of(context).textTheme.bodySmall),
                        const SizedBox(height: 4),
                        Text(
                          'Published ${gteFormatDateTime(announcement.publishedAt)}',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
            ],
          ),
        ),
      ],
    );
  }
}

class _FeedSection extends StatefulWidget {
  const _FeedSection({
    required this.baseUrl,
    required this.backendMode,
    required this.accessToken,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;

  @override
  State<_FeedSection> createState() => _FeedSectionState();
}

class _FeedSectionState extends State<_FeedSection> {
  late StoryFeedApi _api;
  late Future<List<StoryFeedItem>> _feedFuture;
  late Future<StoryDigest> _digestFuture;

  @override
  void initState() {
    super.initState();
    _buildApi();
    _load();
  }

  @override
  void didUpdateWidget(covariant _FeedSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.baseUrl != widget.baseUrl ||
        oldWidget.backendMode != widget.backendMode ||
        oldWidget.accessToken != widget.accessToken) {
      _buildApi();
      _load();
    }
  }

  void _buildApi() {
    _api = StoryFeedApi.standard(
      baseUrl: widget.baseUrl,
      accessToken: widget.accessToken,
      mode: widget.backendMode,
    );
  }

  void _load() {
    _feedFuture = _api.listFeed();
    _digestFuture = _api.fetchDigest();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        FutureBuilder<StoryDigest>(
          future: _digestFuture,
          builder: (BuildContext context, AsyncSnapshot<StoryDigest> snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const GteSurfacePanel(
                child: Text('Loading story digest...'),
              );
            }
            if (!snapshot.hasData) {
              return const GteStatePanel(
                title: 'Story digest unavailable',
                message: 'Unable to load story digest right now.',
                icon: Icons.warning_amber_outlined,
              );
            }
            final StoryDigest digest = snapshot.data!;
            return GteSurfacePanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Story digest',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 12),
                  _StoryLane(title: 'Top stories', stories: digest.topStories),
                  const SizedBox(height: 12),
                  _StoryLane(
                      title: 'Country spotlight',
                      stories: digest.countrySpotlight),
                  const SizedBox(height: 12),
                  _StoryLane(
                      title: 'Feature stories',
                      stories: digest.featureStories),
                ],
              ),
            );
          },
        ),
        const SizedBox(height: 16),
        FutureBuilder<List<StoryFeedItem>>(
          future: _feedFuture,
          builder: (BuildContext context,
              AsyncSnapshot<List<StoryFeedItem>> snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const GteSurfacePanel(
                child: Text('Loading story feed...'),
              );
            }
            final List<StoryFeedItem> stories =
                snapshot.data ?? <StoryFeedItem>[];
            if (stories.isEmpty) {
              return const GteStatePanel(
                title: 'No stories yet',
                message: 'Story feed items will appear here.',
                icon: Icons.article_outlined,
              );
            }
            return GteSurfacePanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Story feed',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 12),
                  for (final StoryFeedItem story in stories)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _StoryCard(story: story),
                    ),
                ],
              ),
            );
          },
        ),
      ],
    );
  }
}

class _StoryLane extends StatelessWidget {
  const _StoryLane({required this.title, required this.stories});

  final String title;
  final List<StoryFeedItem> stories;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(title, style: Theme.of(context).textTheme.titleSmall),
        const SizedBox(height: 6),
        if (stories.isEmpty)
          const Text('No stories in this lane yet.')
        else
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: stories
                .map((StoryFeedItem story) => _StoryChip(story: story))
                .toList(growable: false),
          ),
      ],
    );
  }
}

class _StoryChip extends StatelessWidget {
  const _StoryChip({required this.story});

  final StoryFeedItem story;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: Colors.white.withValues(alpha: 0.05),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Text(story.title, style: Theme.of(context).textTheme.labelLarge),
    );
  }
}

class _StoryCard extends StatelessWidget {
  const _StoryCard({required this.story});

  final StoryFeedItem story;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: Colors.white.withValues(alpha: 0.04),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(story.title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 4),
          Text(story.body, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 6),
          Text('Type: ${story.storyType}',
              style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 4),
          Text('Published ${gteFormatDateTime(story.createdAt)}',
              style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}

class _CommunityThreadsSection extends StatefulWidget {
  const _CommunityThreadsSection({
    required this.baseUrl,
    required this.backendMode,
    required this.accessToken,
    required this.isAuthenticated,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final bool isAuthenticated;

  @override
  State<_CommunityThreadsSection> createState() =>
      _CommunityThreadsSectionState();
}

class _CommunityThreadsSectionState extends State<_CommunityThreadsSection> {
  late CommunityApi _api;
  late Future<CommunityDigest> _digestFuture;
  late Future<List<LiveThread>> _threadsFuture;
  late Future<List<CommunityWatchlistItem>> _watchlistFuture;
  late Future<List<PrivateMessageThread>> _privateFuture;

  @override
  void initState() {
    super.initState();
    _buildApi();
    _load();
  }

  @override
  void didUpdateWidget(covariant _CommunityThreadsSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.baseUrl != widget.baseUrl ||
        oldWidget.backendMode != widget.backendMode ||
        oldWidget.accessToken != widget.accessToken) {
      _buildApi();
      _load();
    }
  }

  void _buildApi() {
    _api = CommunityApi.standard(
      baseUrl: widget.baseUrl,
      accessToken: widget.accessToken,
      mode: widget.backendMode,
    );
  }

  void _load() {
    _digestFuture = _api.fetchDigest();
    _threadsFuture = _api.listLiveThreads();
    _watchlistFuture = _api.listWatchlist();
    _privateFuture = _api.listPrivateThreads();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        if (!widget.isAuthenticated)
          const GteStatePanel(
            eyebrow: 'COMMUNITY ACCESS',
            title: 'Sign in to view live threads and private messages.',
            message:
                'Community watchlists and direct messages are unlocked with an authenticated session.',
            icon: Icons.lock_outline,
          ),
        const SizedBox(height: 16),
        FutureBuilder<CommunityDigest>(
          future: _digestFuture,
          builder:
              (BuildContext context, AsyncSnapshot<CommunityDigest> snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const GteSurfacePanel(
                child: Text('Loading community digest...'),
              );
            }
            final CommunityDigest? digest = snapshot.data;
            return GteSurfacePanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Community digest',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: <Widget>[
                      _MetricPill(
                        label: 'Watchlist',
                        value: digest?.watchlistCount.toString() ?? '0',
                      ),
                      _MetricPill(
                        label: 'Live threads',
                        value: digest?.liveThreadCount.toString() ?? '0',
                      ),
                      _MetricPill(
                        label: 'Private',
                        value: digest?.privateThreadCount.toString() ?? '0',
                      ),
                      _MetricPill(
                        label: 'Unread',
                        value: digest?.unreadHintCount.toString() ?? '0',
                      ),
                    ],
                  ),
                ],
              ),
            );
          },
        ),
        const SizedBox(height: 16),
        FutureBuilder<List<LiveThread>>(
          future: _threadsFuture,
          builder:
              (BuildContext context, AsyncSnapshot<List<LiveThread>> snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const GteSurfacePanel(
                child: Text('Loading live threads...'),
              );
            }
            final List<LiveThread> threads =
                snapshot.data ?? <LiveThread>[];
            return GteSurfacePanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Live threads',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 12),
                  if (threads.isEmpty)
                    const Text('No live threads are active.')
                  else
                    for (final LiveThread thread in threads)
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(thread.title),
                        subtitle: Text(
                          thread.lastMessageAt == null
                              ? 'No messages yet'
                              : 'Last message ${gteFormatDateTime(thread.lastMessageAt)}',
                        ),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: widget.isAuthenticated
                            ? () {
                                Navigator.of(context).push<void>(
                                  MaterialPageRoute<void>(
                                    builder: (BuildContext context) =>
                                        LiveThreadDetailScreen(
                                      api: _api,
                                      thread: thread,
                                    ),
                                  ),
                                );
                              }
                            : null,
                      ),
                ],
              ),
            );
          },
        ),
        const SizedBox(height: 16),
        FutureBuilder<List<CommunityWatchlistItem>>(
          future: _watchlistFuture,
          builder: (BuildContext context,
              AsyncSnapshot<List<CommunityWatchlistItem>> snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const GteSurfacePanel(
                child: Text('Loading watchlist...'),
              );
            }
            final List<CommunityWatchlistItem> items =
                snapshot.data ?? <CommunityWatchlistItem>[];
            return GteSurfacePanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Watchlist',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 12),
                  if (items.isEmpty)
                    const Text('No watchlist items yet.')
                  else
                    for (final CommunityWatchlistItem item in items)
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(item.competitionTitle),
                        subtitle: Text(item.competitionType),
                        trailing: IconButton(
                          icon: const Icon(Icons.remove_circle_outline),
                          onPressed: () async {
                            await _api.removeWatchlist(item.competitionKey);
                            if (mounted) {
                              setState(() {
                                _watchlistFuture = _api.listWatchlist();
                                _digestFuture = _api.fetchDigest();
                              });
                            }
                          },
                        ),
                      ),
                ],
              ),
            );
          },
        ),
        const SizedBox(height: 16),
        FutureBuilder<List<PrivateMessageThread>>(
          future: _privateFuture,
          builder: (BuildContext context,
              AsyncSnapshot<List<PrivateMessageThread>> snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const GteSurfacePanel(
                child: Text('Loading private messages...'),
              );
            }
            final List<PrivateMessageThread> threads =
                snapshot.data ?? <PrivateMessageThread>[];
            return GteSurfacePanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Private messages',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 12),
                  if (threads.isEmpty)
                    const Text('No private message threads yet.')
                  else
                    for (final PrivateMessageThread thread in threads)
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(thread.subject ?? 'Private thread'),
                        subtitle: Text(
                          'Updated ${gteFormatDateTime(thread.updatedAt)}',
                        ),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: widget.isAuthenticated
                            ? () {
                                Navigator.of(context).push<void>(
                                  MaterialPageRoute<void>(
                                    builder: (BuildContext context) =>
                                        PrivateMessageThreadScreen(
                                      api: _api,
                                      thread: thread,
                                    ),
                                  ),
                                );
                              }
                            : null,
                      ),
                ],
              ),
            );
          },
        ),
      ],
    );
  }
}

class LiveThreadDetailScreen extends StatefulWidget {
  const LiveThreadDetailScreen({
    super.key,
    required this.api,
    required this.thread,
  });

  final CommunityApi api;
  final LiveThread thread;

  @override
  State<LiveThreadDetailScreen> createState() => _LiveThreadDetailScreenState();
}

class _LiveThreadDetailScreenState extends State<LiveThreadDetailScreen> {
  late Future<List<LiveThreadMessage>> _messagesFuture;
  final TextEditingController _messageController = TextEditingController();
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    _messagesFuture = widget.api.listLiveThreadMessages(widget.thread.id);
  }

  @override
  void dispose() {
    _messageController.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final String body = _messageController.text.trim();
    if (body.isEmpty) {
      return;
    }
    setState(() {
      _sending = true;
    });
    try {
      await widget.api.postLiveThreadMessage(
        threadId: widget.thread.id,
        body: body,
      );
      _messageController.clear();
      setState(() {
        _messagesFuture =
            widget.api.listLiveThreadMessages(widget.thread.id);
      });
    } finally {
      if (mounted) {
        setState(() {
          _sending = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.thread.title)),
      body: Column(
        children: <Widget>[
          Expanded(
            child: FutureBuilder<List<LiveThreadMessage>>(
              future: _messagesFuture,
              builder: (BuildContext context,
                  AsyncSnapshot<List<LiveThreadMessage>> snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                final List<LiveThreadMessage> messages =
                    snapshot.data ?? <LiveThreadMessage>[];
                if (messages.isEmpty) {
                  return const Center(
                    child: Text('No messages yet.'),
                  );
                }
                return ListView.separated(
                  padding: const EdgeInsets.all(20),
                  itemCount: messages.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (BuildContext context, int index) {
                    final LiveThreadMessage message = messages[index];
                    return GteSurfacePanel(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(message.body,
                              style: Theme.of(context).textTheme.bodyMedium),
                          const SizedBox(height: 6),
                          Text(
                            'By ${message.authorUserId} • ${gteFormatDateTime(message.createdAt)}',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    );
                  },
                );
              },
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: <Widget>[
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    decoration: const InputDecoration(
                      labelText: 'Message',
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                FilledButton(
                  onPressed: _sending ? null : _send,
                  child: Text(_sending ? 'Sending...' : 'Send'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class PrivateMessageThreadScreen extends StatefulWidget {
  const PrivateMessageThreadScreen({
    super.key,
    required this.api,
    required this.thread,
  });

  final CommunityApi api;
  final PrivateMessageThread thread;

  @override
  State<PrivateMessageThreadScreen> createState() =>
      _PrivateMessageThreadScreenState();
}

class _PrivateMessageThreadScreenState
    extends State<PrivateMessageThreadScreen> {
  late Future<List<PrivateMessage>> _messagesFuture;
  final TextEditingController _messageController = TextEditingController();
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    _messagesFuture = widget.api.listPrivateMessages(widget.thread.id);
  }

  @override
  void dispose() {
    _messageController.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final String body = _messageController.text.trim();
    if (body.isEmpty) {
      return;
    }
    setState(() {
      _sending = true;
    });
    try {
      await widget.api.postPrivateMessage(
        threadId: widget.thread.id,
        body: body,
      );
      _messageController.clear();
      setState(() {
        _messagesFuture = widget.api.listPrivateMessages(widget.thread.id);
      });
    } finally {
      if (mounted) {
        setState(() {
          _sending = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.thread.subject ?? 'Private messages'),
      ),
      body: Column(
        children: <Widget>[
          Expanded(
            child: FutureBuilder<List<PrivateMessage>>(
              future: _messagesFuture,
              builder: (BuildContext context,
                  AsyncSnapshot<List<PrivateMessage>> snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                final List<PrivateMessage> messages =
                    snapshot.data ?? <PrivateMessage>[];
                if (messages.isEmpty) {
                  return const Center(child: Text('No messages yet.'));
                }
                return ListView.separated(
                  padding: const EdgeInsets.all(20),
                  itemCount: messages.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (BuildContext context, int index) {
                    final PrivateMessage message = messages[index];
                    return GteSurfacePanel(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(message.body,
                              style: Theme.of(context).textTheme.bodyMedium),
                          const SizedBox(height: 6),
                          Text(
                            'From ${message.senderUserId} • ${gteFormatDateTime(message.createdAt)}',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    );
                  },
                );
              },
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: <Widget>[
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    decoration: const InputDecoration(
                      labelText: 'Message',
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                FilledButton(
                  onPressed: _sending ? null : _send,
                  child: Text(_sending ? 'Sending...' : 'Send'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ReportsSection extends StatefulWidget {
  const _ReportsSection({
    required this.baseUrl,
    required this.backendMode,
    required this.accessToken,
    required this.isAuthenticated,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final bool isAuthenticated;

  @override
  State<_ReportsSection> createState() => _ReportsSectionState();
}

class _ReportsSectionState extends State<_ReportsSection> {
  late ModerationApi _api;
  late Future<List<ModerationReport>> _reportsFuture;
  final TextEditingController _targetTypeController = TextEditingController();
  final TextEditingController _targetIdController = TextEditingController();
  final TextEditingController _reasonController =
      TextEditingController(text: 'abuse');
  final TextEditingController _descriptionController = TextEditingController();
  final TextEditingController _evidenceController = TextEditingController();
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _buildApi();
    _reportsFuture = _api.listMyReports();
  }

  @override
  void didUpdateWidget(covariant _ReportsSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.baseUrl != widget.baseUrl ||
        oldWidget.backendMode != widget.backendMode ||
        oldWidget.accessToken != widget.accessToken) {
      _buildApi();
      _reportsFuture = _api.listMyReports();
    }
  }

  @override
  void dispose() {
    _targetTypeController.dispose();
    _targetIdController.dispose();
    _reasonController.dispose();
    _descriptionController.dispose();
    _evidenceController.dispose();
    super.dispose();
  }

  void _buildApi() {
    _api = ModerationApi.standard(
      baseUrl: widget.baseUrl,
      accessToken: widget.accessToken,
      mode: widget.backendMode,
    );
  }

  Future<void> _submitReport() async {
    if (!widget.isAuthenticated) {
      setState(() {
        _error = 'Sign in to submit reports.';
      });
      return;
    }
    final String targetType = _targetTypeController.text.trim();
    final String targetId = _targetIdController.text.trim();
    final String reason = _reasonController.text.trim();
    final String description = _descriptionController.text.trim();
    if (targetType.isEmpty || targetId.isEmpty || description.isEmpty) {
      setState(() {
        _error = 'Fill in target type, target id, and description.';
      });
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await _api.createReport(
        targetType: targetType,
        targetId: targetId,
        reasonCode: reason.isEmpty ? 'abuse' : reason,
        description: description,
        evidenceUrl: _evidenceController.text.trim().isEmpty
            ? null
            : _evidenceController.text.trim(),
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _reportsFuture = _api.listMyReports();
        _descriptionController.clear();
        _evidenceController.clear();
      });
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
          _submitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        GteSurfacePanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Submit a report',
                  style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 12),
              TextField(
                controller: _targetTypeController,
                decoration: const InputDecoration(
                  labelText: 'Target type (e.g. message, user, competition)',
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _targetIdController,
                decoration: const InputDecoration(
                  labelText: 'Target id',
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _reasonController,
                decoration: const InputDecoration(
                  labelText: 'Reason code (abuse, spam, cheating)',
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _descriptionController,
                decoration: const InputDecoration(
                  labelText: 'Description',
                ),
                maxLines: 3,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _evidenceController,
                decoration: const InputDecoration(
                  labelText: 'Evidence URL (optional)',
                ),
              ),
              if (_error != null) ...<Widget>[
                const SizedBox(height: 12),
                GteStatePanel(
                  title: 'Report error',
                  message: _error!,
                  icon: Icons.warning_amber_outlined,
                ),
              ],
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: _submitting ? null : _submitReport,
                  child: Text(_submitting ? 'Submitting...' : 'Submit report'),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        FutureBuilder<List<ModerationReport>>(
          future: _reportsFuture,
          builder: (BuildContext context,
              AsyncSnapshot<List<ModerationReport>> snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const GteSurfacePanel(
                child: Text('Loading my reports...'),
              );
            }
            final List<ModerationReport> reports =
                snapshot.data ?? <ModerationReport>[];
            if (reports.isEmpty) {
              return const GteStatePanel(
                title: 'No reports yet',
                message: 'Your submitted reports will appear here.',
                icon: Icons.report_outlined,
              );
            }
            return GteSurfacePanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('My reports',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 12),
                  for (final ModerationReport report in reports)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(report.reasonCode,
                              style: Theme.of(context).textTheme.titleSmall),
                          const SizedBox(height: 4),
                          Text(report.description,
                              style: Theme.of(context).textTheme.bodySmall),
                          const SizedBox(height: 4),
                          Text('Status: ${report.status}',
                              style: Theme.of(context).textTheme.bodySmall),
                        ],
                      ),
                    ),
                ],
              ),
            );
          },
        ),
      ],
    );
  }
}

class _DisputesSection extends StatefulWidget {
  const _DisputesSection({
    required this.baseUrl,
    required this.backendMode,
    required this.accessToken,
    required this.isAuthenticated,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final bool isAuthenticated;

  @override
  State<_DisputesSection> createState() => _DisputesSectionState();
}

class _DisputesSectionState extends State<_DisputesSection> {
  late DisputeEngineApi _api;
  late Future<List<DisputeEngineCase>> _disputesFuture;
  final TextEditingController _resourceTypeController =
      TextEditingController();
  final TextEditingController _resourceIdController = TextEditingController();
  final TextEditingController _referenceController = TextEditingController();
  final TextEditingController _subjectController = TextEditingController();
  final TextEditingController _messageController = TextEditingController();
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _buildApi();
    _disputesFuture = _api.listMyDisputes();
  }

  @override
  void didUpdateWidget(covariant _DisputesSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.baseUrl != widget.baseUrl ||
        oldWidget.backendMode != widget.backendMode ||
        oldWidget.accessToken != widget.accessToken) {
      _buildApi();
      _disputesFuture = _api.listMyDisputes();
    }
  }

  @override
  void dispose() {
    _resourceTypeController.dispose();
    _resourceIdController.dispose();
    _referenceController.dispose();
    _subjectController.dispose();
    _messageController.dispose();
    super.dispose();
  }

  void _buildApi() {
    _api = DisputeEngineApi.standard(
      baseUrl: widget.baseUrl,
      accessToken: widget.accessToken,
      mode: widget.backendMode,
    );
  }

  Future<void> _createDispute() async {
    if (!widget.isAuthenticated) {
      setState(() {
        _error = 'Sign in to create a dispute.';
      });
      return;
    }
    final String resourceType = _resourceTypeController.text.trim();
    final String resourceId = _resourceIdController.text.trim();
    final String reference = _referenceController.text.trim();
    final String subject = _subjectController.text.trim();
    final String message = _messageController.text.trim();
    if (resourceType.isEmpty ||
        resourceId.isEmpty ||
        reference.isEmpty ||
        message.isEmpty) {
      setState(() {
        _error = 'Complete all required fields before submitting.';
      });
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await _api.createDispute(
        resourceType: resourceType,
        resourceId: resourceId,
        reference: reference,
        subject: subject,
        message: message,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _disputesFuture = _api.listMyDisputes();
        _messageController.clear();
      });
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
          _submitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        GteSurfacePanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Create dispute',
                  style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 12),
              TextField(
                controller: _resourceTypeController,
                decoration: const InputDecoration(
                  labelText: 'Resource type (deposit, withdrawal, competition)',
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _resourceIdController,
                decoration: const InputDecoration(
                  labelText: 'Resource id',
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _referenceController,
                decoration: const InputDecoration(
                  labelText: 'Reference',
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _subjectController,
                decoration: const InputDecoration(
                  labelText: 'Subject (optional)',
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _messageController,
                decoration: const InputDecoration(
                  labelText: 'Message',
                ),
                maxLines: 3,
              ),
              if (_error != null) ...<Widget>[
                const SizedBox(height: 12),
                GteStatePanel(
                  title: 'Dispute error',
                  message: _error!,
                  icon: Icons.warning_amber_outlined,
                ),
              ],
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: _submitting ? null : _createDispute,
                  child: Text(_submitting ? 'Submitting...' : 'Create dispute'),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        FutureBuilder<List<DisputeEngineCase>>(
          future: _disputesFuture,
          builder: (BuildContext context,
              AsyncSnapshot<List<DisputeEngineCase>> snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const GteSurfacePanel(
                child: Text('Loading disputes...'),
              );
            }
            final List<DisputeEngineCase> disputes =
                snapshot.data ?? <DisputeEngineCase>[];
            if (disputes.isEmpty) {
              return const GteStatePanel(
                title: 'No disputes yet',
                message: 'Create a dispute to start a support thread.',
                icon: Icons.support_agent_outlined,
              );
            }
            return GteSurfacePanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('My disputes',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 12),
                  for (final DisputeEngineCase dispute in disputes)
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(dispute.reference),
                      subtitle: Text('Status: ${dispute.status}'),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () {
                        Navigator.of(context).push<void>(
                          MaterialPageRoute<void>(
                            builder: (BuildContext context) =>
                                DisputeDetailScreen(
                              api: _api,
                              disputeId: dispute.id,
                            ),
                          ),
                        );
                      },
                    ),
                ],
              ),
            );
          },
        ),
      ],
    );
  }
}

class DisputeDetailScreen extends StatefulWidget {
  const DisputeDetailScreen({
    super.key,
    required this.api,
    required this.disputeId,
  });

  final DisputeEngineApi api;
  final String disputeId;

  @override
  State<DisputeDetailScreen> createState() => _DisputeDetailScreenState();
}

class _DisputeDetailScreenState extends State<DisputeDetailScreen> {
  late Future<DisputeEngineDetail> _detailFuture;
  final TextEditingController _messageController = TextEditingController();
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    _detailFuture = widget.api.fetchDispute(widget.disputeId);
  }

  @override
  void dispose() {
    _messageController.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final String body = _messageController.text.trim();
    if (body.isEmpty) {
      return;
    }
    setState(() {
      _sending = true;
    });
    try {
      await widget.api.addMessage(
        disputeId: widget.disputeId,
        message: body,
      );
      _messageController.clear();
      setState(() {
        _detailFuture = widget.api.fetchDispute(widget.disputeId);
      });
    } finally {
      if (mounted) {
        setState(() {
          _sending = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Dispute thread')),
      body: Column(
        children: <Widget>[
          Expanded(
            child: FutureBuilder<DisputeEngineDetail>(
              future: _detailFuture,
              builder: (BuildContext context,
                  AsyncSnapshot<DisputeEngineDetail> snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (!snapshot.hasData) {
                  return const Center(child: Text('Unable to load dispute.'));
                }
                final DisputeEngineDetail detail = snapshot.data!;
                return ListView.separated(
                  padding: const EdgeInsets.all(20),
                  itemCount: detail.messages.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (BuildContext context, int index) {
                    final DisputeEngineMessage message =
                        detail.messages[index];
                    return GteSurfacePanel(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(message.message,
                              style: Theme.of(context).textTheme.bodyMedium),
                          const SizedBox(height: 6),
                          Text(
                            '${message.senderRole.toUpperCase()} • ${gteFormatDateTime(message.createdAt)}',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    );
                  },
                );
              },
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: <Widget>[
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    decoration: const InputDecoration(
                      labelText: 'Message',
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                FilledButton(
                  onPressed: _sending ? null : _send,
                  child: Text(_sending ? 'Sending...' : 'Send'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _GovernanceSection extends StatefulWidget {
  const _GovernanceSection({
    required this.baseUrl,
    required this.backendMode,
    required this.accessToken,
    required this.isAuthenticated,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final bool isAuthenticated;

  @override
  State<_GovernanceSection> createState() => _GovernanceSectionState();
}

class _GovernanceSectionState extends State<_GovernanceSection> {
  late GovernanceApi _api;
  late Future<List<GovernanceProposal>> _proposalsFuture;
  late Future<GovernanceOverview> _overviewFuture;

  @override
  void initState() {
    super.initState();
    _buildApi();
    _load();
  }

  @override
  void didUpdateWidget(covariant _GovernanceSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.baseUrl != widget.baseUrl ||
        oldWidget.backendMode != widget.backendMode ||
        oldWidget.accessToken != widget.accessToken) {
      _buildApi();
      _load();
    }
  }

  void _buildApi() {
    _api = GovernanceApi.standard(
      baseUrl: widget.baseUrl,
      accessToken: widget.accessToken,
      mode: widget.backendMode,
    );
  }

  void _load() {
    _proposalsFuture = _api.listProposals();
    _overviewFuture = _api.fetchOverview();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        FutureBuilder<GovernanceOverview>(
          future: _overviewFuture,
          builder: (BuildContext context,
              AsyncSnapshot<GovernanceOverview> snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const GteSurfacePanel(
                child: Text('Loading governance overview...'),
              );
            }
            if (!snapshot.hasData) {
              return const GteStatePanel(
                title: 'Governance overview unavailable',
                message: 'Unable to load governance overview.',
                icon: Icons.warning_amber_outlined,
              );
            }
            final GovernanceOverview overview = snapshot.data!;
            return GteSurfacePanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('My governance overview',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: <Widget>[
                      _MetricPill(
                        label: 'Voting power',
                        value: overview.votingPower.toString(),
                      ),
                      _MetricPill(
                        label: 'Active votes',
                        value: overview.activeVotes.toString(),
                      ),
                      _MetricPill(
                        label: 'Proposals',
                        value: overview.openProposals.toString(),
                      ),
                      _MetricPill(
                        label: 'Participation',
                        value: '${overview.participationRate}%',
                      ),
                    ],
                  ),
                ],
              ),
            );
          },
        ),
        const SizedBox(height: 16),
        FutureBuilder<List<GovernanceProposal>>(
          future: _proposalsFuture,
          builder: (BuildContext context,
              AsyncSnapshot<List<GovernanceProposal>> snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const GteSurfacePanel(
                child: Text('Loading proposals...'),
              );
            }
            final List<GovernanceProposal> proposals =
                snapshot.data ?? <GovernanceProposal>[];
            if (proposals.isEmpty) {
              return const GteStatePanel(
                title: 'No proposals yet',
                message: 'Governance proposals will appear here.',
                icon: Icons.how_to_vote_outlined,
              );
            }
            return GteSurfacePanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Proposals',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 12),
                  for (final GovernanceProposal proposal in proposals)
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(proposal.title),
                      subtitle: Text(proposal.summary),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () {
                        Navigator.of(context).push<void>(
                          MaterialPageRoute<void>(
                            builder: (BuildContext context) =>
                                GovernanceProposalDetailScreen(
                              api: _api,
                              proposalId: proposal.id,
                            ),
                          ),
                        );
                      },
                    ),
                ],
              ),
            );
          },
        ),
      ],
    );
  }
}

class GovernanceProposalDetailScreen extends StatefulWidget {
  const GovernanceProposalDetailScreen({
    super.key,
    required this.api,
    required this.proposalId,
  });

  final GovernanceApi api;
  final String proposalId;

  @override
  State<GovernanceProposalDetailScreen> createState() =>
      _GovernanceProposalDetailScreenState();
}

class _GovernanceProposalDetailScreenState
    extends State<GovernanceProposalDetailScreen> {
  late Future<GovernanceProposalDetail> _detailFuture;
  final TextEditingController _commentController = TextEditingController();
  bool _voting = false;

  @override
  void initState() {
    super.initState();
    _detailFuture = widget.api.fetchProposal(widget.proposalId);
  }

  @override
  void dispose() {
    _commentController.dispose();
    super.dispose();
  }

  Future<void> _vote(String choice) async {
    setState(() {
      _voting = true;
    });
    try {
      await widget.api.vote(
        proposalId: widget.proposalId,
        choice: choice,
        comment: _commentController.text.trim().isEmpty
            ? null
            : _commentController.text.trim(),
      );
      setState(() {
        _detailFuture = widget.api.fetchProposal(widget.proposalId);
        _commentController.clear();
      });
    } finally {
      if (mounted) {
        setState(() {
          _voting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Proposal detail')),
      body: FutureBuilder<GovernanceProposalDetail>(
        future: _detailFuture,
        builder: (BuildContext context,
            AsyncSnapshot<GovernanceProposalDetail> snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (!snapshot.hasData) {
            return const Center(child: Text('Unable to load proposal.'));
          }
          final GovernanceProposalDetail detail = snapshot.data!;
          final GovernanceProposal proposal = detail.proposal;
          return ListView(
            padding: const EdgeInsets.all(20),
            children: <Widget>[
              GteSurfacePanel(
                emphasized: true,
                accentColor: GteShellTheme.accentCommunity,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(proposal.title,
                        style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 6),
                    Text(proposal.summary,
                        style: Theme.of(context).textTheme.bodyMedium),
                    const SizedBox(height: 12),
                    Text('Status: ${proposal.status}',
                        style: Theme.of(context).textTheme.bodySmall),
                    const SizedBox(height: 6),
                    Text('Voting ends ${proposal.votingEndsAtIso}',
                        style: Theme.of(context).textTheme.bodySmall),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text('Cast vote',
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 8),
                    TextField(
                      controller: _commentController,
                      decoration: const InputDecoration(
                        labelText: 'Comment (optional)',
                      ),
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: <Widget>[
                        FilledButton(
                          onPressed: _voting ? null : () => _vote('yes'),
                          child: const Text('Vote yes'),
                        ),
                        FilledButton.tonal(
                          onPressed: _voting ? null : () => _vote('no'),
                          child: const Text('Vote no'),
                        ),
                        OutlinedButton(
                          onPressed: _voting ? null : () => _vote('abstain'),
                          child: const Text('Abstain'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _MetricPill extends StatelessWidget {
  const _MetricPill({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: Colors.white.withValues(alpha: 0.04),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.labelMedium),
          const SizedBox(height: 4),
          Text(value, style: Theme.of(context).textTheme.titleMedium),
        ],
      ),
    );
  }
}
