import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'theme/app_theme.dart';
import 'screens/settings_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/query_screen.dart';
import 'screens/tabs/social_media_tab.dart';
import 'screens/tabs/ads_ide_tab.dart';
import 'screens/tabs/machine_relations_tab.dart';
import 'screens/tabs/white_label_tab.dart';
import 'screens/tabs/modo_ia_tab.dart';
import 'core/providers.dart';

void main() {
  runApp(
    const ProviderScope(
      child: InhausMarketingApp(),
    ),
  );
}

class InhausMarketingApp extends ConsumerWidget {
  const InhausMarketingApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp(
      title: 'Inhaus Marketing API',
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ThemeMode.system,
      home: const AuthWrapper(),
      debugShowCheckedModeBanner: false,
    );
  }
}

class AuthWrapper extends ConsumerWidget {
  const AuthWrapper({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final credentialsCheck = ref.watch(credentialsCheckProvider);

    return credentialsCheck.when(
      data: (hasCredentials) {
        if (hasCredentials) {
          return const MainScreen();
        } else {
          return const SettingsScreen();
        }
      },
      loading: () => const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      ),
      error: (error, stack) => Scaffold(
        body: Center(child: Text('Error: $error')),
      ),
    );
  }
}

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _currentIndex = 0;

  final List<Widget> _screens = const [
    DashboardScreen(),
    QueryScreen(),
    SocialMediaTab(),
    AdsIdeTab(),
    MachineRelationsTab(),
    WhiteLabelTab(),
    ModoIaTab(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Inhaus Marketing API'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const SettingsScreen(showBackButton: true)),
              );
            },
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: Row(
        children: [
          NavigationRail(
            selectedIndex: _currentIndex,
            onDestinationSelected: (int index) {
              setState(() {
                _currentIndex = index;
              });
            },
            labelType: NavigationRailLabelType.all,
            backgroundColor: AppTheme.surfaceColor,
            selectedIconTheme: const IconThemeData(color: AppTheme.primaryColor),
            selectedLabelTextStyle: const TextStyle(color: AppTheme.primaryColor),
            unselectedIconTheme: const IconThemeData(color: AppTheme.mutedTextColor),
            unselectedLabelTextStyle: const TextStyle(color: AppTheme.mutedTextColor),
            destinations: const [
              NavigationRailDestination(
                icon: Icon(Icons.dashboard_outlined),
                selectedIcon: Icon(Icons.dashboard),
                label: Text('Dashboard'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.analytics_outlined),
                selectedIcon: Icon(Icons.analytics),
                label: Text('Query'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.trending_up_outlined),
                selectedIcon: Icon(Icons.trending_up),
                label: Text('Social SOTA'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.campaign_outlined),
                selectedIcon: Icon(Icons.campaign),
                label: Text('Ads IDE'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.hub_outlined),
                selectedIcon: Icon(Icons.hub),
                label: Text('SEO/ASO'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.palette_outlined),
                selectedIcon: Icon(Icons.palette),
                label: Text('Brand Portal'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.smart_toy_outlined),
                selectedIcon: Icon(Icons.smart_toy),
                label: Text('Modo IA'),
              ),
            ],
          ),
          const VerticalDivider(thickness: 1, width: 1, color: Color(0xFF2E364F)),
          Expanded(
            child: _screens[_currentIndex],
          ),
        ],
      ),
    );
  }
}
