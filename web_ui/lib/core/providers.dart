import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'api_client.dart';
import 'config_provider.dart';

final apiClientProvider = Provider<ApiClient>((ref) {
  final config = ref.watch(configProvider).value;
  return ApiClient(
    baseUrl: config?.baseUrl,
    apiKey: config?.apiKey,
    onUnauthorized: () {
      // Clear credentials reactively on 401
      ref.read(configProvider.notifier).clearCredentials();
    },
  );
});

final credentialsCheckProvider = Provider<AsyncValue<bool>>((ref) {
  return ref.watch(configProvider).whenData((config) => config.hasCredentials);
});

final healthCheckProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final apiClient = ref.watch(apiClientProvider);
  return await apiClient.checkHealth();
});

final platformsProvider = FutureProvider<List<dynamic>>((ref) async {
  final apiClient = ref.watch(apiClientProvider);
  return await apiClient.getPlatforms();
});

/// Schema provider — fetches metrics/dimensions for a specific platform.
/// Usage: ref.watch(schemaProvider('meta_ads'))
final schemaProvider = FutureProvider.family<Map<String, dynamic>, String>((ref, platform) async {
  final apiClient = ref.watch(apiClientProvider);
  return await apiClient.getSchema(platform);
});

/// Derives only configured platforms from the full list.
final configuredPlatformsProvider = Provider<AsyncValue<List<dynamic>>>((ref) {
  return ref.watch(platformsProvider).whenData(
    (platforms) => platforms.where((p) => p['configured'] == true).toList(),
  );
});

/// Groups platforms by their type (ads, organic, analytics, app_store).
final platformsByTypeProvider = Provider<AsyncValue<Map<String, List<dynamic>>>>((ref) {
  return ref.watch(platformsProvider).whenData((platforms) {
    final Map<String, List<dynamic>> grouped = {};
    for (final p in platforms) {
      final type = (p['type'] ?? 'other').toString();
      grouped.putIfAbsent(type, () => []).add(p);
    }
    return grouped;
  });
});

/// Fetches connected OAuth accounts for a given platform (e.g., 'meta_ads' or 'google_ads')
final oauthConnectionsProvider = FutureProvider.family<List<dynamic>, String>((ref, platform) async {
  final apiClient = ref.watch(apiClientProvider);
  return await apiClient.getOAuthConnections(platform);
});
