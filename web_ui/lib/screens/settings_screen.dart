import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';
// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;

import '../core/providers.dart';
import '../core/config_provider.dart';
import '../theme/app_theme.dart';
import '../main.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  final bool showBackButton;
  const SettingsScreen({super.key, this.showBackButton = false});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  final _baseUrlController = TextEditingController();
  final _apiKeyController = TextEditingController();
  bool _isTesting = false;

  @override
  void initState() {
    super.initState();
    // Pre-fill text fields with current config if available
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final config = ref.read(configProvider).value;
      if (config != null) {
        _baseUrlController.text = config.baseUrl ?? 'http://127.0.0.1:8000';
        _apiKeyController.text = config.apiKey ?? '';
      } else {
        _baseUrlController.text = 'http://127.0.0.1:8000';
      }
      _checkOAuthCallback();
    });
  }

  void _checkOAuthCallback() {
    if (!kIsWeb) return;
    final uri = Uri.base;
    if (uri.queryParameters['oauth'] == 'success') {
      final platform = uri.queryParameters['platform'] ?? 'Unknown Platform';
      
      // Clear URL parameters to prevent re-triggering on refresh
      html.window.history.replaceState(null, 'Settings', uri.path);
      
      // Refresh the connections provider for this platform
      if (platform == 'meta_ads' || platform == 'google_ads') {
         ref.invalidate(oauthConnectionsProvider(platform));
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Successfully connected $platform account!'),
          backgroundColor: Colors.green,
        ),
      );
    }
  }

  Future<void> _testConnection() async {
    setState(() => _isTesting = true);
    
    // Save temporarily to test
    await ref.read(configProvider.notifier).saveCredentials(_baseUrlController.text, _apiKeyController.text);

    try {
      final client = ref.read(apiClientProvider);
      await client.checkHealth();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Connection successful!'), backgroundColor: Colors.green),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Connection failed: $e'), backgroundColor: Colors.red),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isTesting = false);
      }
    }
  }

  Future<void> _saveSettings() async {
    await ref.read(configProvider.notifier).saveCredentials(_baseUrlController.text, _apiKeyController.text);

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Settings saved successfully')),
      );
      
      if (!widget.showBackButton) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => const MainScreen()),
        );
      } else {
        Navigator.pop(context);
      }
    }
  }

  @override
  void dispose() {
    _baseUrlController.dispose();
    _apiKeyController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final configState = ref.watch(configProvider);
    final isLoading = configState.isLoading || configState.value?.isLoading == true;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
        leading: widget.showBackButton 
            ? IconButton(icon: const Icon(Icons.arrow_back), onPressed: () => Navigator.pop(context)) 
            : null,
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 800),
          child: SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(32),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Master API Configuration', style: Theme.of(context).textTheme.headlineMedium),
                          const SizedBox(height: 8),
                          Text('Configure your connection to the Inhaus Marketing Data API.', style: Theme.of(context).textTheme.bodyMedium),
                          const SizedBox(height: 32),
                          TextField(
                            controller: _baseUrlController,
                            decoration: const InputDecoration(
                              labelText: 'Base URL',
                              hintText: 'e.g. http://127.0.0.1:8000',
                              prefixIcon: Icon(Icons.link),
                            ),
                          ),
                          const SizedBox(height: 24),
                          TextField(
                            controller: _apiKeyController,
                            obscureText: true,
                            decoration: const InputDecoration(
                              labelText: 'API Key',
                              hintText: 'Enter your X-API-Key',
                              prefixIcon: Icon(Icons.vpn_key),
                            ),
                          ),
                          const SizedBox(height: 48),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.end,
                            children: [
                              TextButton.icon(
                                onPressed: isLoading ? null : () async {
                                  final messenger = ScaffoldMessenger.of(context);
                                  final confirm = await showDialog<bool>(
                                    context: context,
                                    builder: (ctx) => AlertDialog(
                                      title: const Text('Clear Credentials?'),
                                      content: const Text('This will remove your saved API key and base URL. You will need to reconfigure.'),
                                      actions: [
                                        TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
                                        TextButton(
                                          onPressed: () => Navigator.pop(ctx, true),
                                          style: TextButton.styleFrom(foregroundColor: Colors.red),
                                          child: const Text('Clear'),
                                        ),
                                      ],
                                    ),
                                  );
                                  if (confirm == true) {
                                    await ref.read(configProvider.notifier).clearCredentials();
                                    messenger.showSnackBar(
                                      const SnackBar(content: Text('Credentials cleared.'), backgroundColor: Colors.orange),
                                    );
                                  }
                                },
                                icon: const Icon(Icons.delete_outline, size: 18),
                                label: const Text('Clear'),
                                style: TextButton.styleFrom(foregroundColor: Colors.red.withOpacity(0.7)),
                              ),
                              const Spacer(),
                              OutlinedButton.icon(
                                onPressed: _isTesting || isLoading ? null : _testConnection,
                                icon: _isTesting 
                                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                                    : const Icon(Icons.wifi),
                                label: const Text('Test Connection'),
                              ),
                              const SizedBox(width: 16),
                              ElevatedButton.icon(
                                onPressed: isLoading ? null : _saveSettings,
                                icon: isLoading 
                                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                                    : const Icon(Icons.save),
                                label: const Text('Save Configuration'),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),
                  _buildDynamicPlatformConnections(context, ref),
                  const SizedBox(height: 24),
                  _buildConnectedAccountsSection(context, ref),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDynamicPlatformConnections(BuildContext context, WidgetRef ref) {
    final platformsByType = ref.watch(platformsByTypeProvider);
    
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text('Platform Connections', style: Theme.of(context).textTheme.headlineMedium),
                const Spacer(),
                IconButton(
                  onPressed: () => ref.invalidate(platformsProvider),
                  icon: const Icon(Icons.refresh, size: 20),
                  tooltip: 'Refresh platforms',
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Status of all platform connectors from the API.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppTheme.mutedTextColor),
            ),
            const SizedBox(height: 24),
            platformsByType.when(
              data: (grouped) => _buildGroupedPlatformsList(context, grouped),
              loading: () => const Center(child: Padding(
                padding: EdgeInsets.all(32),
                child: CircularProgressIndicator(),
              )),
              error: (error, _) => Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.red.withOpacity(0.05),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.red.withOpacity(0.2)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline, color: Colors.red, size: 18),
                    const SizedBox(width: 12),
                    Expanded(child: Text('Failed to load platforms: $error', style: const TextStyle(color: Colors.red))),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildGroupedPlatformsList(BuildContext context, Map<String, List<dynamic>> grouped) {
    const typeOrder = ['ads', 'organic', 'analytics', 'app_store'];
    const typeLabels = {
      'ads': 'Advertising',
      'organic': 'Organic & Social',
      'analytics': 'Analytics',
      'app_store': 'App Stores',
    };

    final sections = <Widget>[];

    for (final type in typeOrder) {
      final platforms = grouped[type];
      if (platforms == null || platforms.isEmpty) continue;

      final color = AppTheme.colorForPlatformType(type);
      final label = typeLabels[type] ?? type;
      final configuredCount = platforms.where((p) => p['configured'] == true).length;

      sections.add(
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(AppTheme.iconForPlatformType(type), color: color, size: 16),
                const SizedBox(width: 8),
                Text(label, style: TextStyle(color: color, fontWeight: FontWeight.w600, fontSize: 13)),
                const Spacer(),
                Text(
                  '$configuredCount/${platforms.length}',
                  style: TextStyle(color: color.withOpacity(0.6), fontSize: 12),
                ),
              ],
            ),
            const SizedBox(height: 8),
            ...platforms.map((p) => _buildPlatformRow(context, p, color)),
            const SizedBox(height: 16),
          ],
        ),
      );
    }

    // Unknown types
    for (final entry in grouped.entries) {
      if (!typeOrder.contains(entry.key) && entry.value.isNotEmpty) {
        sections.add(
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(entry.key.toUpperCase(), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
              const SizedBox(height: 8),
              ...entry.value.map((p) => _buildPlatformRow(context, p, AppTheme.mutedTextColor)),
              const SizedBox(height: 16),
            ],
          ),
        );
      }
    }

    if (sections.isEmpty) {
      return const Center(child: Text('No platforms found.'));
    }

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: sections);
  }

  Widget _buildPlatformRow(BuildContext context, dynamic platform, Color typeColor) {
    final name = (platform['display_name'] ?? platform['platform'] ?? 'Unknown').toString();
    final isConfigured = platform['configured'] == true;
    final metrics = (platform['available_metrics'] as List<dynamic>?) ?? [];

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest.withOpacity(0.1),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Theme.of(context).dividerColor.withOpacity(0.08)),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          // Status dot
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: isConfigured ? AppTheme.primaryColor : AppTheme.mutedTextColor.withOpacity(0.3),
              shape: BoxShape.circle,
              boxShadow: isConfigured ? [BoxShadow(color: AppTheme.primaryColor.withOpacity(0.4), blurRadius: 4)] : null,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name, style: Theme.of(context).textTheme.titleSmall),
                if (metrics.isNotEmpty)
                  Text(
                    '${metrics.length} metrics available',
                    style: TextStyle(color: AppTheme.mutedTextColor.withOpacity(0.6), fontSize: 11),
                  ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: isConfigured ? AppTheme.primaryColor.withOpacity(0.1) : Colors.transparent,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(
                color: isConfigured ? AppTheme.primaryColor.withOpacity(0.3) : AppTheme.mutedTextColor.withOpacity(0.15),
              ),
            ),
            child: Text(
              isConfigured ? 'Configured' : 'Not configured',
              style: TextStyle(
                color: isConfigured ? AppTheme.primaryColor : AppTheme.mutedTextColor.withOpacity(0.5),
                fontSize: 11,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildConnectedAccountsSection(BuildContext context, WidgetRef ref) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Connected Ad Accounts', style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 8),
            Text(
              'Connect your personal or agency accounts to securely query data without exposing manual credentials.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppTheme.mutedTextColor),
            ),
            const SizedBox(height: 24),
            _buildOAuthPlatformCard(context, ref, 'meta_ads', 'Meta Ads', Icons.facebook, Colors.blue),
            const SizedBox(height: 16),
            _buildOAuthPlatformCard(context, ref, 'meta_organic', 'Meta Pages & Organic', Icons.pages, Colors.teal),
            const SizedBox(height: 16),
            _buildOAuthPlatformCard(context, ref, 'google_ads', 'Google Ads', Icons.search, Colors.red),
          ],
        ),
      ),
    );
  }

  Widget _buildOAuthPlatformCard(BuildContext context, WidgetRef ref, String platformId, String platformName, IconData icon, Color color) {
    final connectionsAsync = ref.watch(oauthConnectionsProvider(platformId));
    
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Theme.of(context).dividerColor.withOpacity(0.1)),
      ),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 24),
              const SizedBox(width: 12),
              Text(platformName, style: Theme.of(context).textTheme.titleMedium),
              const Spacer(),
              TextButton.icon(
                onPressed: () => ref.invalidate(oauthConnectionsProvider(platformId)),
                icon: const Icon(Icons.refresh, size: 16),
                label: const Text('Refresh'),
              ),
              const SizedBox(width: 8),
              FilledButton.icon(
                onPressed: () async {
                  try {
                    final client = ref.read(apiClientProvider);
                    final data = await client.getOAuthAuthorizeUrl(platformId);
                    if (data['url'] != null) {
                      final url = Uri.parse(data['url']);
                      if (await canLaunchUrl(url)) {
                        await launchUrl(url, webOnlyWindowName: '_self');
                      }
                    }
                  } catch (e) {
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed to get auth URL: $e'), backgroundColor: Colors.red));
                    }
                  }
                },
                icon: const Icon(Icons.add_link, size: 18),
                label: const Text('Connect'),
              ),
            ],
          ),
          const SizedBox(height: 16),
          connectionsAsync.when(
            data: (connections) {
              if (connections.isEmpty) {
                return Text('No accounts connected.', style: TextStyle(color: AppTheme.mutedTextColor, fontSize: 13));
              }
              return Column(
                children: connections.map((conn) {
                  final accountId = conn['account_id']?.toString() ?? 'Unknown ID';
                  final accountName = conn['account_name']?.toString() ?? 'Unnamed Account';
                  return ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: CircleAvatar(
                      backgroundColor: color.withOpacity(0.1),
                      child: Icon(Icons.account_circle, color: color, size: 20),
                    ),
                    title: Text(accountName, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                    subtitle: Text('ID: $accountId', style: const TextStyle(fontSize: 12)),
                    trailing: IconButton(
                      icon: const Icon(Icons.link_off, color: Colors.red, size: 20),
                      tooltip: 'Disconnect Account',
                      onPressed: () async {
                        final confirm = await showDialog<bool>(
                          context: context,
                          builder: (ctx) => AlertDialog(
                            title: const Text('Disconnect Account?'),
                            content: Text('Are you sure you want to disconnect $accountName ($accountId)?'),
                            actions: [
                              TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
                              TextButton(
                                onPressed: () => Navigator.pop(ctx, true),
                                style: TextButton.styleFrom(foregroundColor: Colors.red),
                                child: const Text('Disconnect'),
                              ),
                            ],
                          ),
                        );
                        if (confirm == true) {
                          try {
                            await ref.read(apiClientProvider).disconnectOAuthAccount(platformId, accountId);
                            ref.invalidate(oauthConnectionsProvider(platformId));
                            if (mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Account disconnected')));
                            }
                          } catch (e) {
                            if (mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed to disconnect: $e'), backgroundColor: Colors.red));
                            }
                          }
                        }
                      },
                    ),
                  );
                }).toList(),
              );
            },
            loading: () => const Center(child: Padding(padding: EdgeInsets.all(16), child: CircularProgressIndicator())),
            error: (e, _) => Text('Failed to load connections: $e', style: const TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }
}

