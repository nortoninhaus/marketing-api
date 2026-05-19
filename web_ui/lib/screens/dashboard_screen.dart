import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/providers.dart';
import '../theme/app_theme.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final healthAsync = ref.watch(healthCheckProvider);
    final platformsByType = ref.watch(platformsByTypeProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Dashboard', style: Theme.of(context).textTheme.headlineLarge),
          const SizedBox(height: 32),
          
          // Health Status Section
          healthAsync.when(
            data: (health) => _buildHealthCard(context, true, health),
            loading: () => const Center(child: Padding(
              padding: EdgeInsets.all(32),
              child: CircularProgressIndicator(),
            )),
            error: (error, stack) => _buildHealthCard(context, false, {'error': error.toString()}),
          ),

          const SizedBox(height: 40),

          // Platforms grouped by type
          platformsByType.when(
            data: (grouped) => _buildGroupedPlatforms(context, grouped),
            loading: () => const Center(child: Padding(
              padding: EdgeInsets.all(32),
              child: CircularProgressIndicator(),
            )),
            error: (error, stack) => Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline, color: Colors.red),
                    const SizedBox(width: 12),
                    Text('Failed to load platforms: $error', style: const TextStyle(color: Colors.red)),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHealthCard(BuildContext context, bool isHealthy, Map<String, dynamic> data) {
    final configured = data['platforms_configured'] ?? 0;
    final total = data['platforms_total'] ?? 14;
    final version = data['version'] ?? '';
    final details = (data['details'] as Map<String, dynamic>?) ?? {};

    // Count per-platform health statuses
    int unconfiguredCount = 0;
    for (final entry in details.entries) {
      if (entry.value != 'configured' && entry.value != 'healthy') {
        unconfiguredCount++;
      }
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: isHealthy ? AppTheme.primaryColor.withOpacity(0.1) : Colors.red.withOpacity(0.1),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    isHealthy ? Icons.check_circle : Icons.error,
                    color: isHealthy ? AppTheme.primaryColor : Colors.red,
                    size: 28,
                  ),
                ),
                const SizedBox(width: 20),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        isHealthy ? 'API is Online' : 'API Connection Error',
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          color: isHealthy ? AppTheme.primaryColor : Colors.red,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        isHealthy
                            ? 'All systems operational. Ready to handle requests.'
                            : data['error']?.toString() ?? 'Unknown error occurred.',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppTheme.mutedTextColor),
                      ),
                    ],
                  ),
                ),
                if (isHealthy && version.isNotEmpty)
                  Chip(
                    label: Text('v$version'),
                    backgroundColor: AppTheme.primaryColor.withOpacity(0.15),
                    labelStyle: const TextStyle(color: AppTheme.primaryColor, fontSize: 12, fontWeight: FontWeight.w600),
                    side: BorderSide.none,
                  ),
              ],
            ),
            if (isHealthy) ...[
              const SizedBox(height: 20),
              const Divider(color: Color(0xFF2E364F)),
              const SizedBox(height: 16),
              Row(
                children: [
                  _buildStatChip(context, '$configured', 'Configured', AppTheme.primaryColor),
                  const SizedBox(width: 16),
                  _buildStatChip(context, '$unconfiguredCount', 'Not Configured', AppTheme.mutedTextColor),
                  const SizedBox(width: 16),
                  _buildStatChip(context, '$total', 'Total', AppTheme.secondaryColor),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildStatChip(BuildContext context, String value, String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withOpacity(0.15)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(value, style: TextStyle(color: color, fontSize: 20, fontWeight: FontWeight.bold)),
          const SizedBox(width: 8),
          Text(label, style: TextStyle(color: color.withOpacity(0.7), fontSize: 12)),
        ],
      ),
    );
  }

  Widget _buildGroupedPlatforms(BuildContext context, Map<String, List<dynamic>> grouped) {
    // Define display order
    const typeOrder = ['ads', 'organic', 'analytics', 'app_store'];
    const typeLabels = {
      'ads': 'Advertising Platforms',
      'organic': 'Organic & Social',
      'analytics': 'Analytics',
      'app_store': 'App Stores',
    };

    final sections = <Widget>[];

    for (final type in typeOrder) {
      final platforms = grouped[type];
      if (platforms == null || platforms.isEmpty) continue;

      final color = AppTheme.colorForPlatformType(type);
      final icon = AppTheme.iconForPlatformType(type);
      final label = typeLabels[type] ?? type.replaceAll('_', ' ').toUpperCase();

      sections.add(
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: color, size: 20),
                const SizedBox(width: 8),
                Text(label, style: Theme.of(context).textTheme.titleLarge?.copyWith(color: color)),
                const Spacer(),
                Text(
                  '${platforms.where((p) => p['configured'] == true).length}/${platforms.length} configured',
                  style: TextStyle(color: AppTheme.mutedTextColor.withOpacity(0.6), fontSize: 12),
                ),
              ],
            ),
            const SizedBox(height: 12),
            GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                maxCrossAxisExtent: 340,
                mainAxisExtent: 110,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
              ),
              itemCount: platforms.length,
              itemBuilder: (context, index) => _buildPlatformCard(context, platforms[index], color),
            ),
            const SizedBox(height: 32),
          ],
        ),
      );
    }

    // Handle any unknown types
    for (final entry in grouped.entries) {
      if (!typeOrder.contains(entry.key) && entry.value.isNotEmpty) {
        sections.add(
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(entry.key.toUpperCase(), style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 12),
              GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                  maxCrossAxisExtent: 340,
                  mainAxisExtent: 110,
                  crossAxisSpacing: 12,
                  mainAxisSpacing: 12,
                ),
                itemCount: entry.value.length,
                itemBuilder: (context, index) => _buildPlatformCard(context, entry.value[index], AppTheme.mutedTextColor),
              ),
              const SizedBox(height: 32),
            ],
          ),
        );
      }
    }

    return Column(children: sections);
  }

  Widget _buildPlatformCard(BuildContext context, Map<String, dynamic> platform, Color typeColor) {
    final displayName = (platform['display_name'] ?? platform['platform'] ?? '').toString();
    final isConfigured = platform['configured'] == true;
    final metrics = (platform['available_metrics'] as List<dynamic>?) ?? [];
    final description = (platform['description'] ?? '').toString();

    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: typeColor.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(
                    AppTheme.iconForPlatformType((platform['type'] ?? '').toString()),
                    color: typeColor,
                    size: 18,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    displayName,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                // Config status dot
                Container(
                  width: 10,
                  height: 10,
                  decoration: BoxDecoration(
                    color: isConfigured ? AppTheme.primaryColor : AppTheme.mutedTextColor.withOpacity(0.3),
                    shape: BoxShape.circle,
                    boxShadow: isConfigured ? [
                      BoxShadow(color: AppTheme.primaryColor.withOpacity(0.4), blurRadius: 6),
                    ] : null,
                  ),
                ),
              ],
            ),
            const Spacer(),
            Row(
              children: [
                if (metrics.isNotEmpty) ...[
                  Icon(Icons.bar_chart, size: 14, color: AppTheme.mutedTextColor.withOpacity(0.6)),
                  const SizedBox(width: 4),
                  Text(
                    '${metrics.length} metrics',
                    style: TextStyle(color: AppTheme.mutedTextColor.withOpacity(0.6), fontSize: 11),
                  ),
                ] else ...[
                  Text(
                    description.isNotEmpty ? description : 'No metrics available',
                    style: TextStyle(color: AppTheme.mutedTextColor.withOpacity(0.5), fontSize: 11),
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: isConfigured ? AppTheme.primaryColor.withOpacity(0.1) : Colors.transparent,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(
                      color: isConfigured ? AppTheme.primaryColor.withOpacity(0.3) : AppTheme.mutedTextColor.withOpacity(0.2),
                    ),
                  ),
                  child: Text(
                    isConfigured ? 'Ready' : 'Not configured',
                    style: TextStyle(
                      color: isConfigured ? AppTheme.primaryColor : AppTheme.mutedTextColor.withOpacity(0.5),
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
