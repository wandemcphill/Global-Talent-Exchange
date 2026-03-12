import 'package:flutter/material.dart';

import 'gte_app_controller.dart';
import '../widgets/gte_shell_theme.dart';
import 'gte_dashboard_screen.dart';
import 'gte_market_screen.dart';
import 'gte_player_detail_screen.dart';
import 'gte_players_screen.dart';
import 'gte_transfer_room_screen.dart';

@Deprecated(
    'Use GteFrontendApp and GteExchangeShellScreen for the canonical MVP app.')
class GteAppShellScreen extends StatefulWidget {
  const GteAppShellScreen({
    super.key,
    this.controller,
  });

  final GteAppController? controller;

  @override
  State<GteAppShellScreen> createState() => _GteAppShellScreenState();
}

class _GteAppShellScreenState extends State<GteAppShellScreen> {
  late final GteAppController _controller;
  late final bool _ownsController;

  @override
  void initState() {
    super.initState();
    _ownsController = widget.controller == null;
    _controller = widget.controller ?? GteAppController();
    _controller.bootstrap();
  }

  @override
  void dispose() {
    if (_ownsController) {
      _controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Theme(
      data: GteShellTheme.build(),
      child: Container(
        decoration: gteBackdropDecoration(),
        child: AnimatedBuilder(
          animation: _controller,
          builder: (BuildContext context, Widget? child) {
            if (_controller.isBootstrapping && _controller.players.isEmpty) {
              return const Scaffold(
                body: Center(child: CircularProgressIndicator()),
              );
            }

            if (_controller.players.isEmpty &&
                _controller.errorMessage != null) {
              return Scaffold(
                body: Center(
                  child: FilledButton(
                    onPressed: () {
                      _controller.bootstrap();
                    },
                    child: Text('Retry: ${_controller.errorMessage}'),
                  ),
                ),
              );
            }

            return LayoutBuilder(
              builder: (BuildContext context, BoxConstraints constraints) {
                final bool useRail = constraints.maxWidth >= 1080;
                final Widget body = _ShellBody(
                  controller: _controller,
                  onOpenPlayer: (String playerId) {
                    _openPlayer(playerId);
                  },
                  onOpenTransferRoom: () {
                    _openTransferRoom();
                  },
                );

                if (useRail) {
                  return Scaffold(
                    appBar: _buildAppBar(),
                    body: Row(
                      children: <Widget>[
                        NavigationRail(
                          selectedIndex: _controller.currentTabIndex,
                          onDestinationSelected: _controller.switchTab,
                          labelType: NavigationRailLabelType.all,
                          destinations: const <NavigationRailDestination>[
                            NavigationRailDestination(
                              icon: Icon(Icons.space_dashboard_outlined),
                              selectedIcon: Icon(Icons.space_dashboard),
                              label: Text('Overview'),
                            ),
                            NavigationRailDestination(
                              icon: Icon(Icons.groups_outlined),
                              selectedIcon: Icon(Icons.groups),
                              label: Text('Players'),
                            ),
                            NavigationRailDestination(
                              icon: Icon(Icons.candlestick_chart_outlined),
                              selectedIcon: Icon(Icons.candlestick_chart),
                              label: Text('Market'),
                            ),
                          ],
                        ),
                        const VerticalDivider(width: 1),
                        Expanded(child: body),
                      ],
                    ),
                  );
                }

                return Scaffold(
                  appBar: _buildAppBar(),
                  body: body,
                  bottomNavigationBar: NavigationBar(
                    selectedIndex: _controller.currentTabIndex,
                    onDestinationSelected: _controller.switchTab,
                    destinations: const <NavigationDestination>[
                      NavigationDestination(
                        icon: Icon(Icons.space_dashboard_outlined),
                        selectedIcon: Icon(Icons.space_dashboard),
                        label: 'Overview',
                      ),
                      NavigationDestination(
                        icon: Icon(Icons.groups_outlined),
                        selectedIcon: Icon(Icons.groups),
                        label: 'Players',
                      ),
                      NavigationDestination(
                        icon: Icon(Icons.candlestick_chart_outlined),
                        selectedIcon: Icon(Icons.candlestick_chart),
                        label: 'Market',
                      ),
                    ],
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }

  PreferredSizeWidget _buildAppBar() {
    return AppBar(
      title: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Global Talent Exchange'),
          Text(
            'Scouting and transfer intelligence shell',
            style: TextStyle(fontSize: 12),
          ),
        ],
      ),
      actions: <Widget>[
        Padding(
          padding: const EdgeInsets.only(right: 16),
          child: Center(
            child: Text(
              '${_controller.watchlistPlayers.length} watchlisted / ${_controller.transferRoomPlayers.length} in room',
            ),
          ),
        ),
      ],
    );
  }

  Future<void> _openPlayer(String playerId) async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => GtePlayerDetailScreen(
          controller: _controller,
          playerId: playerId,
        ),
      ),
    );
  }

  Future<void> _openTransferRoom() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => GteTransferRoomScreen(
          controller: _controller,
          onOpenPlayer: (String playerId) {
            _openPlayer(playerId);
          },
        ),
      ),
    );
  }
}

class _ShellBody extends StatelessWidget {
  const _ShellBody({
    required this.controller,
    required this.onOpenPlayer,
    required this.onOpenTransferRoom,
  });

  final GteAppController controller;
  final ValueChanged<String> onOpenPlayer;
  final VoidCallback onOpenTransferRoom;

  @override
  Widget build(BuildContext context) {
    switch (controller.currentTabIndex) {
      case 1:
        return GtePlayersScreen(
          controller: controller,
          onOpenPlayer: onOpenPlayer,
        );
      case 2:
        return GteMarketScreen(
          controller: controller,
          onOpenPlayer: onOpenPlayer,
          onOpenTransferRoom: onOpenTransferRoom,
        );
      case 0:
      default:
        return GteDashboardScreen(
          controller: controller,
          onOpenPlayer: onOpenPlayer,
          onOpenPlayersTab: () => controller.switchTab(1),
          onOpenMarketTab: () => controller.switchTab(2),
        );
    }
  }
}
