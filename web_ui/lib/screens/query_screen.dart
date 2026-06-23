import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/providers.dart';
import '../theme/app_theme.dart';

class QueryScreen extends ConsumerStatefulWidget {
  const QueryScreen({super.key});

  @override
  ConsumerState<QueryScreen> createState() => _QueryScreenState();
}

class _QueryScreenState extends ConsumerState<QueryScreen> {
  final _clientIdController = TextEditingController(text: 'client_1');
  final _userIdController = TextEditingController(text: 'user_1');
  final _accountIdController = TextEditingController(text: 'account_1');
  
  // Optional context fields
  final _postIdController = TextEditingController();
  final _videoIdController = TextEditingController();
  final _appIdController = TextEditingController();
  
  final List<String> _selectedPlatforms = [];
  final List<String> _selectedMetrics = [];
  final List<String> _selectedDimensions = [];
  DateTimeRange? _selectedDateRange;
  
  bool _isLoading = false;
  String? _results;
  bool _isBatchResult = false;
  Map<String, dynamic>? _batchResults;

  // All OAuth-supported platforms for account discovery
  static const _oauthPlatforms = [
    'meta_ads', 'meta_organic', 'google_ads', 'ga4',
    'youtube', 'threads', 'tiktok_ads', 'tiktok_organic'
  ];

  /// Searches all loaded connection lists for the current accountId and returns its human-readable name.
  String? _resolveAccountName(WidgetRef ref) {
    final accountId = _accountIdController.text.trim();
    if (accountId.isEmpty || accountId == 'account_1') return null;
    for (final platform in _oauthPlatforms) {
      final connsAsync = ref.read(oauthConnectionsProvider(platform));
      final conns = connsAsync.value ?? [];
      for (final conn in conns) {
        if (conn['account_id']?.toString() == accountId) {
          final name = conn['account_name']?.toString();
          if (name != null && name.isNotEmpty && name != accountId) return name;
        }
      }
    }
    return null;
  }
  
  @override
  void initState() {
    super.initState();
    _accountIdController.addListener(_onAccountIdChanged);
  }

  void _onAccountIdChanged() {
    setState(() {});
  }

  @override
  void dispose() {
    _accountIdController.removeListener(_onAccountIdChanged);
    _clientIdController.dispose();
    _userIdController.dispose();
    _accountIdController.dispose();
    _postIdController.dispose();
    _videoIdController.dispose();
    _appIdController.dispose();
    super.dispose();
  }

  /// Returns the platform type string (ads, organic, analytics, app_store)
  /// based on the currently selected single platform data from the API.
  String _getPlatformType(List<dynamic> platforms, String platformName) {
    for (final p in platforms) {
      if (p['platform'] == platformName) {
        return (p['type'] ?? '').toString();
      }
    }
    return '';
  }

  Future<void> _pickDateRange() async {
    final range = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2020),
      lastDate: DateTime.now(),
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: const ColorScheme.dark(
              primary: AppTheme.primaryColor,
              onPrimary: AppTheme.backgroundColor,
              surface: AppTheme.surfaceColor,
              onSurface: AppTheme.textPrimaryColor,
            ),
          ),
          child: child!,
        );
      },
    );
    if (range != null) {
      setState(() {
        _selectedDateRange = range;
      });
    }
  }

  Map<String, dynamic> _buildRequestData({bool isBatch = false}) {
    final Map<String, dynamic> data = {
      'client_id': _clientIdController.text,
      'user_id': _userIdController.text,
      'account_id': _accountIdController.text,
      'metrics': _selectedMetrics.isNotEmpty ? _selectedMetrics : ['impressions'],
    };

    if (isBatch) {
      data['platforms'] = _selectedPlatforms.isNotEmpty ? _selectedPlatforms : [];
    } else {
      if (_selectedPlatforms.isNotEmpty) {
        data['platform'] = _selectedPlatforms.first;
      }
    }

    if (_selectedDateRange != null) {
      data['start_date'] = _selectedDateRange!.start.toIso8601String().split('T')[0];
      data['end_date'] = _selectedDateRange!.end.toIso8601String().split('T')[0];
    }

    // Optional context fields
    if (_postIdController.text.isNotEmpty) {
      data['post_id'] = _postIdController.text;
    }
    if (_videoIdController.text.isNotEmpty) {
      data['video_id'] = _videoIdController.text;
    }
    if (_appIdController.text.isNotEmpty) {
      data['app_id'] = _appIdController.text;
    }
    if (_selectedDimensions.isNotEmpty) {
      data['dimensions'] = _selectedDimensions;
    }
    
    return data;
  }

  Future<void> _runSingleQuery() async {
    if (_selectedPlatforms.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Please select at least one platform')));
      return;
    }
    if (_selectedMetrics.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Please select at least one metric')));
      return;
    }
    if (_selectedDateRange == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Please select a date range')));
      return;
    }

    setState(() {
      _isLoading = true;
      _results = null;
      _batchResults = null;
      _isBatchResult = false;
    });

    try {
      final client = ref.read(apiClientProvider);
      final res = await client.runSingleQuery(_buildRequestData(isBatch: false));
      setState(() {
        _results = const JsonEncoder.withIndent('  ').convert(res);
        _isBatchResult = false;
      });
    } catch (e) {
      setState(() {
        _results = 'Error: $e';
        _isBatchResult = false;
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _runBatchQuery() async {
    if (_selectedMetrics.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Please select at least one metric')));
      return;
    }
    if (_selectedDateRange == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Please select a date range')));
      return;
    }

    setState(() {
      _isLoading = true;
      _results = null;
      _batchResults = null;
      _isBatchResult = true;
    });

    try {
      final client = ref.read(apiClientProvider);
      final res = await client.runBatchQuery(_buildRequestData(isBatch: true));
      setState(() {
        _batchResults = res;
        _results = const JsonEncoder.withIndent('  ').convert(res);
      });
    } catch (e) {
      setState(() {
        _results = 'Error: $e';
        _batchResults = null;
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  void _copyResults() {
    if (_results != null) {
      Clipboard.setData(ClipboardData(text: _results!));
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Copied to clipboard')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final platformsAsync = ref.watch(platformsProvider);

    // If exactly one platform is selected, watch its schema
    final String? activePlatform = _selectedPlatforms.length == 1 ? _selectedPlatforms.first : null;

    return Padding(
      padding: const EdgeInsets.all(32),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Left Column - Form
          Expanded(
            flex: 1,
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Query Data', style: Theme.of(context).textTheme.headlineLarge),
                  const SizedBox(height: 32),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(24.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Identity', style: Theme.of(context).textTheme.titleLarge),
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              Expanded(child: TextField(controller: _clientIdController, decoration: const InputDecoration(labelText: 'Client ID'))),
                              const SizedBox(width: 16),
                              Expanded(child: TextField(controller: _userIdController, decoration: const InputDecoration(labelText: 'User ID'))),
                            ],
                          ),
                          const SizedBox(height: 16),
                          Builder(
                            builder: (context) {
                              final resolvedName = _resolveAccountName(ref);
                              return TextField(
                                controller: _accountIdController,
                                decoration: InputDecoration(
                                  labelText: 'Account ID',
                                  helperText: resolvedName != null ? '✓ $resolvedName' : null,
                                  helperStyle: const TextStyle(color: AppTheme.primaryColor, fontWeight: FontWeight.w500),
                                  suffixIcon: resolvedName != null
                                      ? Tooltip(
                                          message: resolvedName,
                                          child: const Icon(Icons.verified_outlined, color: AppTheme.primaryColor, size: 18),
                                        )
                                      : null,
                                ),
                              );
                            },
                          ),
                          _buildConnectedAccountsSection(),
                          
                          const SizedBox(height: 32),
                          Text('Platforms', style: Theme.of(context).textTheme.titleLarge),
                          const SizedBox(height: 16),
                          
                          // Multi-Platform Selection
                          platformsAsync.when(
                            data: (platforms) {
                              if (platforms.isEmpty) {
                                return const Text('No platforms available.', style: TextStyle(color: AppTheme.mutedTextColor));
                              }
                              return Wrap(
                                spacing: 8,
                                runSpacing: 8,
                                children: platforms.map((p) {
                                  final name = (p['platform'] ?? p['name']).toString();
                                  final displayName = (p['display_name'] ?? name).toString();
                                  final isConfigured = p['configured'] == true;
                                  final isSelected = _selectedPlatforms.contains(name);
                                  return FilterChip(
                                    label: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Text(displayName),
                                        if (!isConfigured) ...[
                                          const SizedBox(width: 4),
                                          Icon(Icons.circle, size: 6, color: AppTheme.mutedTextColor.withOpacity(0.4)),
                                        ],
                                      ],
                                    ),
                                    selected: isSelected,
                                    onSelected: (selected) {
                                      setState(() {
                                        if (selected) {
                                          _selectedPlatforms.add(name);
                                        } else {
                                          _selectedPlatforms.remove(name);
                                        }
                                        // Reset metric/dimension selection when platforms change
                                        _selectedMetrics.clear();
                                        _selectedDimensions.clear();
                                      });
                                    },
                                    selectedColor: AppTheme.primaryColor.withOpacity(0.2),
                                    checkmarkColor: AppTheme.primaryColor,
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(8),
                                      side: BorderSide(
                                        color: isSelected ? AppTheme.primaryColor : AppTheme.mutedTextColor.withOpacity(0.2),
                                      ),
                                    ),
                                    backgroundColor: AppTheme.surfaceColor,
                                  );
                                }).toList(),
                              );
                            },
                            loading: () => const Center(child: Padding(
                              padding: EdgeInsets.all(16),
                              child: CircularProgressIndicator(),
                            )),
                            error: (e, s) => Text('Error loading platforms: $e'),
                          ),
                          
                          // Schema-driven Metrics & Dimensions
                          if (activePlatform != null) ...[
                            const SizedBox(height: 32),
                            _buildSchemaSection(activePlatform, platformsAsync.value ?? []),
                          ] else if (_selectedPlatforms.length > 1) ...[
                            const SizedBox(height: 16),
                            Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: Colors.orange.withOpacity(0.1),
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: Colors.orange.withOpacity(0.3)),
                              ),
                              child: const Row(
                                children: [
                                  Icon(Icons.info_outline, color: Colors.orange, size: 18),
                                  SizedBox(width: 8),
                                  Expanded(child: Text(
                                    'Select a single platform to load its metric/dimension schema. Batch queries share the selected metrics.',
                                    style: TextStyle(color: Colors.orange, fontSize: 12),
                                  )),
                                ],
                              ),
                            ),
                          ],

                          // Optional context fields based on platform type
                          if (activePlatform != null && platformsAsync.value != null)
                            _buildContextFields(_getPlatformType(platformsAsync.value!, activePlatform)),
                          
                          const SizedBox(height: 24),
                          InkWell(
                            onTap: _pickDateRange,
                            child: InputDecorator(
                              decoration: InputDecoration(
                                labelText: 'Date Range *',
                                prefixIcon: const Icon(Icons.calendar_month),
                                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                              ),
                              child: Text(
                                _selectedDateRange == null 
                                    ? 'Select dates (required)' 
                                    : '${_selectedDateRange!.start.toIso8601String().split('T')[0]} to ${_selectedDateRange!.end.toIso8601String().split('T')[0]}',
                              ),
                            ),
                          ),

                          const SizedBox(height: 32),
                          Row(
                            children: [
                              Expanded(
                                child: ElevatedButton.icon(
                                  onPressed: _isLoading ? null : _runSingleQuery,
                                  icon: _isLoading 
                                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                                      : const Icon(Icons.play_arrow),
                                  label: const Text('Single Query'),
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: OutlinedButton.icon(
                                  onPressed: _isLoading ? null : _runBatchQuery,
                                  icon: const Icon(Icons.layers),
                                  label: const Text('Batch Query'),
                                ),
                              ),
                            ],
                          ),
                          if (_selectedPlatforms.length > 1)
                            const Padding(
                              padding: EdgeInsets.only(top: 12),
                              child: Text(
                                'Note: Single Query will only use the first selected platform.', 
                                style: TextStyle(color: Colors.orange, fontSize: 12),
                              ),
                            ),
                        ],
                      ),
                    ),
                  )
                ],
              ),
            ),
          ),
          const SizedBox(width: 32),
          // Right Column - Results
          Expanded(
            flex: 1,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('Results', style: Theme.of(context).textTheme.headlineLarge),
                    if (_results != null)
                      IconButton(
                        icon: const Icon(Icons.copy),
                        onPressed: _copyResults,
                        tooltip: 'Copy to clipboard',
                      )
                  ],
                ),
                const SizedBox(height: 32),
                Expanded(
                  child: _isLoading 
                      ? const Card(child: Center(child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            CircularProgressIndicator(),
                            SizedBox(height: 16),
                            Text('Fetching data...', style: TextStyle(color: AppTheme.mutedTextColor)),
                          ],
                        )))
                      : _results == null
                          ? Card(child: Center(
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.code, size: 64, color: AppTheme.mutedTextColor.withOpacity(0.5)),
                                  const SizedBox(height: 16),
                                  const Text('No data yet. Run a query to see results.', style: TextStyle(color: AppTheme.mutedTextColor)),
                                  const SizedBox(height: 8),
                                  Text(
                                    'Select a platform, pick metrics, choose dates, and run.',
                                    style: TextStyle(color: AppTheme.mutedTextColor.withOpacity(0.6), fontSize: 12),
                                  ),
                                ],
                              ),
                            ))
                          : (_isBatchResult && _batchResults != null)
                              ? _buildBatchResultsView(_batchResults!)
                              : Card(
                                  child: Container(
                                    width: double.infinity,
                                    padding: const EdgeInsets.all(24),
                                    child: SingleChildScrollView(
                                      child: SelectableText(
                                        _results!,
                                        style: const TextStyle(fontFamily: 'monospace', fontSize: 14),
                                      ),
                                    ),
                                  ),
                                ),
                ),
              ],
            ),
          )
        ],
      ),
    );
  }

  /// Builds a rich batch results view with per-platform status cards.
  Widget _buildBatchResultsView(Map<String, dynamic> batchData) {
    final results = batchData['results'] as List<dynamic>? ?? [];
    final errors = batchData['errors'] as List<dynamic>? ?? [];

    // If the response doesn't have the expected batch structure, fall back to JSON
    if (results.isEmpty && errors.isEmpty) {
      return Card(
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.all(24),
          child: SingleChildScrollView(
            child: SelectableText(
              const JsonEncoder.withIndent('  ').convert(batchData),
              style: const TextStyle(fontFamily: 'monospace', fontSize: 14),
            ),
          ),
        ),
      );
    }

    final successCount = results.length;
    final errorCount = errors.length;
    final total = successCount + errorCount;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Summary bar
        Card(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
            child: Row(
              children: [
                Icon(
                  errorCount == 0 ? Icons.check_circle : Icons.warning_amber_rounded,
                  color: errorCount == 0 ? AppTheme.primaryColor : Colors.orange,
                  size: 20,
                ),
                const SizedBox(width: 10),
                Text(
                  errorCount == 0 
                      ? 'All $total platforms returned data'
                      : '$successCount/$total succeeded · $errorCount failed',
                  style: TextStyle(
                    color: errorCount == 0 ? AppTheme.primaryColor : Colors.orange,
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                  ),
                ),
                const Spacer(),
                TextButton.icon(
                  icon: const Icon(Icons.code, size: 16),
                  label: const Text('Raw JSON', style: TextStyle(fontSize: 12)),
                  onPressed: () {
                    setState(() {
                      _isBatchResult = false; // Toggle to raw view
                    });
                  },
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 8),
        // Per-platform results
        Expanded(
          child: ListView(
            children: [
              // Success results
              for (final result in results)
                _buildBatchPlatformCard(
                  platform: (result['platform'] ?? 'Unknown').toString(),
                  isSuccess: true,
                  data: result,
                ),
              // Errors
              for (final error in errors)
                _buildBatchPlatformCard(
                  platform: (error['platform'] ?? 'Unknown').toString(),
                  isSuccess: false,
                  data: error,
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildBatchPlatformCard({
    required String platform,
    required bool isSuccess,
    required Map<String, dynamic> data,
  }) {
    final color = isSuccess ? AppTheme.primaryColor : Colors.red;
    final dataEntries = (data['data'] as List<dynamic>?) ?? [];
    final errorMsg = data['error']?.toString() ?? '';

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ExpansionTile(
        leading: Container(
          width: 32,
          height: 32,
          decoration: BoxDecoration(
            color: color.withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(
            isSuccess ? Icons.check : Icons.close,
            color: color,
            size: 16,
          ),
        ),
        title: Text(platform, style: TextStyle(fontWeight: FontWeight.w600, color: isSuccess ? null : Colors.red)),
        subtitle: Text(
          isSuccess 
              ? '${dataEntries.length} record${dataEntries.length == 1 ? '' : 's'} returned'
              : errorMsg,
          style: TextStyle(
            color: isSuccess ? AppTheme.mutedTextColor : Colors.red.withOpacity(0.7),
            fontSize: 12,
          ),
        ),
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(
            color: color.withOpacity(0.1),
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: color.withOpacity(0.3)),
          ),
          child: Text(
            isSuccess ? 'OK' : 'ERROR',
            style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.bold),
          ),
        ),
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppTheme.backgroundColor,
                borderRadius: BorderRadius.circular(8),
              ),
              child: SelectableText(
                const JsonEncoder.withIndent('  ').convert(isSuccess ? dataEntries : data),
                style: const TextStyle(fontFamily: 'monospace', fontSize: 12, color: AppTheme.mutedTextColor),
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// Builds the schema-driven metric/dimension selection section.
  Widget _buildSchemaSection(String platform, List<dynamic> allPlatforms) {
    final schemaAsync = ref.watch(schemaProvider(platform));

    return schemaAsync.when(
      data: (schema) {
        final rawMetrics = schema['metrics'] as List<dynamic>? ?? [];
        final rawDimensions = schema['dimensions'] as List<dynamic>? ?? [];

        // Normalize to list of {name, description}
        final metrics = rawMetrics.map((m) {
          if (m is Map) return {'name': m['name'] ?? m.toString(), 'description': m['description'] ?? ''};
          return {'name': m.toString(), 'description': ''};
        }).toList();

        final dimensions = rawDimensions.map((d) {
          if (d is Map) return {'name': d['name'] ?? d.toString(), 'description': d['description'] ?? ''};
          return {'name': d.toString(), 'description': ''};
        }).toList();

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Metrics
            Row(
              children: [
                Text('Metrics *', style: Theme.of(context).textTheme.titleLarge),
                const Spacer(),
                TextButton.icon(
                  icon: const Icon(Icons.select_all, size: 16),
                  label: const Text('All', style: TextStyle(fontSize: 12)),
                  onPressed: () => setState(() {
                    _selectedMetrics
                      ..clear()
                      ..addAll(metrics.map((m) => m['name']!.toString()));
                  }),
                ),
                TextButton.icon(
                  icon: const Icon(Icons.deselect, size: 16),
                  label: const Text('Clear', style: TextStyle(fontSize: 12)),
                  onPressed: () => setState(() => _selectedMetrics.clear()),
                ),
              ],
            ),
            const SizedBox(height: 8),
            if (metrics.isEmpty) 
              const Text('No metrics available for this platform.', style: TextStyle(color: AppTheme.mutedTextColor))
            else
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: metrics.map((m) {
                  final name = m['name']!.toString();
                  final isSelected = _selectedMetrics.contains(name);
                  return Tooltip(
                    message: m['description']!.toString().isNotEmpty ? m['description']!.toString() : name,
                    child: FilterChip(
                      label: Text(name, style: const TextStyle(fontSize: 12)),
                      selected: isSelected,
                      onSelected: (selected) {
                        setState(() {
                          if (selected) {
                            _selectedMetrics.add(name);
                          } else {
                            _selectedMetrics.remove(name);
                          }
                        });
                      },
                      selectedColor: AppTheme.primaryColor.withOpacity(0.2),
                      checkmarkColor: AppTheme.primaryColor,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                        side: BorderSide(
                          color: isSelected ? AppTheme.primaryColor : AppTheme.mutedTextColor.withOpacity(0.2),
                        ),
                      ),
                      backgroundColor: AppTheme.surfaceColor,
                      visualDensity: VisualDensity.compact,
                    ),
                  );
                }).toList(),
              ),
            if (_selectedMetrics.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text('${_selectedMetrics.length} metric${_selectedMetrics.length > 1 ? 's' : ''} selected',
                  style: TextStyle(color: AppTheme.primaryColor.withOpacity(0.7), fontSize: 12)),
            ],

            const SizedBox(height: 24),

            // Dimensions
            Row(
              children: [
                Text('Dimensions', style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(width: 8),
                Text('(optional)', style: TextStyle(color: AppTheme.mutedTextColor.withOpacity(0.6), fontSize: 14)),
                const Spacer(),
                TextButton.icon(
                  icon: const Icon(Icons.select_all, size: 16),
                  label: const Text('All', style: TextStyle(fontSize: 12)),
                  onPressed: () => setState(() {
                    _selectedDimensions
                      ..clear()
                      ..addAll(dimensions.map((d) => d['name']!.toString()));
                  }),
                ),
                TextButton.icon(
                  icon: const Icon(Icons.deselect, size: 16),
                  label: const Text('Clear', style: TextStyle(fontSize: 12)),
                  onPressed: () => setState(() => _selectedDimensions.clear()),
                ),
              ],
            ),
            const SizedBox(height: 8),
            if (dimensions.isEmpty)
              const Text('No dimensions available for this platform.', style: TextStyle(color: AppTheme.mutedTextColor))
            else
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: dimensions.map((d) {
                  final name = d['name']!.toString();
                  final isSelected = _selectedDimensions.contains(name);
                  return Tooltip(
                    message: d['description']!.toString().isNotEmpty ? d['description']!.toString() : name,
                    child: FilterChip(
                      label: Text(name, style: const TextStyle(fontSize: 12)),
                      selected: isSelected,
                      onSelected: (selected) {
                        setState(() {
                          if (selected) {
                            _selectedDimensions.add(name);
                          } else {
                            _selectedDimensions.remove(name);
                          }
                        });
                      },
                      selectedColor: AppTheme.secondaryColor.withOpacity(0.2),
                      checkmarkColor: AppTheme.secondaryColor,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                        side: BorderSide(
                          color: isSelected ? AppTheme.secondaryColor : AppTheme.mutedTextColor.withOpacity(0.2),
                        ),
                      ),
                      backgroundColor: AppTheme.surfaceColor,
                      visualDensity: VisualDensity.compact,
                    ),
                  );
                }).toList(),
              ),
          ],
        );
      },
      loading: () => Padding(
        padding: const EdgeInsets.symmetric(vertical: 24),
        child: Column(
          children: [
            const SizedBox(
              width: 24, height: 24,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            const SizedBox(height: 8),
            Text('Loading schema for $platform...', style: const TextStyle(color: AppTheme.mutedTextColor, fontSize: 12)),
          ],
        ),
      ),
      error: (e, s) => Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.red.withOpacity(0.1),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text('Failed to load schema: $e', style: const TextStyle(color: Colors.red, fontSize: 12)),
      ),
    );
  }

  /// Builds optional context fields based on platform type.
  Widget _buildContextFields(String platformType) {
    final showPostId = platformType == 'organic';
    final showVideoId = platformType == 'organic'; // YouTube, TikTok organic
    final showAppId = platformType == 'app_store';

    if (!showPostId && !showVideoId && !showAppId) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 24),
        Text('Optional Filters', style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppTheme.mutedTextColor)),
        const SizedBox(height: 12),
        if (showPostId)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: TextField(
              controller: _postIdController,
              decoration: const InputDecoration(
                labelText: 'Post ID',
                hintText: 'Specific post/content ID (optional)',
                prefixIcon: Icon(Icons.article_outlined, size: 20),
              ),
            ),
          ),
        if (showVideoId)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: TextField(
              controller: _videoIdController,
              decoration: const InputDecoration(
                labelText: 'Video ID',
                hintText: 'Specific video ID (optional)',
                prefixIcon: Icon(Icons.videocam_outlined, size: 20),
              ),
            ),
          ),
        if (showAppId)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: TextField(
              controller: _appIdController,
              decoration: const InputDecoration(
                labelText: 'App ID',
                hintText: 'Package name or App ID (optional)',
                prefixIcon: Icon(Icons.phone_android_outlined, size: 20),
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildConnectedAccountsSection() {
    // Always watch all OAuth platforms so names resolve even before platform selection
    final allConnections = <Map<String, dynamic>>[];
    bool anyLoading = false;
    bool hasAny = false;

    for (final platform in _oauthPlatforms) {
      final connectionsAsync = ref.watch(oauthConnectionsProvider(platform));
      connectionsAsync.when(
        data: (conns) {
          if (conns.isNotEmpty) hasAny = true;
          for (final c in conns) {
            allConnections.add({...c, '_platform': platform});
          }
        },
        loading: () { anyLoading = true; },
        error: (_, __) {},
      );
    }

    if (!hasAny && !anyLoading) return const SizedBox.shrink();

    // Auto pre-select the first connected account if still using placeholder
    if (_accountIdController.text == 'account_1' && allConnections.isNotEmpty) {
      final firstId = allConnections.first['account_id']?.toString() ?? '';
      if (firstId.isNotEmpty) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted && _accountIdController.text == 'account_1') {
            _accountIdController.text = firstId;
          }
        });
      }
    }

    // Group by platform for display
    final Map<String, List<Map<String, dynamic>>> grouped = {};
    for (final conn in allConnections) {
      final p = conn['_platform'] as String;
      grouped.putIfAbsent(p, () => []).add(conn);
    }

    const platformLabels = {
      'meta_ads': 'Meta Ads',
      'meta_organic': 'Meta / IG',
      'google_ads': 'Google Ads',
      'ga4': 'GA4',
      'youtube': 'YouTube',
      'threads': 'Threads',
      'tiktok_ads': 'TikTok Ads',
      'tiktok_organic': 'TikTok Organic',
    };

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 16),
        Row(
          children: [
            const Icon(Icons.link, size: 14, color: AppTheme.primaryColor),
            const SizedBox(width: 6),
            Text('Connected Accounts', style: Theme.of(context).textTheme.titleSmall?.copyWith(color: AppTheme.primaryColor)),
            if (anyLoading) ...[
              const SizedBox(width: 8),
              const SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 1.5)),
            ],
          ],
        ),
        const SizedBox(height: 10),
        ...grouped.entries.map((entry) {
          final platform = entry.key;
          final connections = entry.value;
          final label = platformLabels[platform] ?? platform;
          return Padding(
            padding: const EdgeInsets.only(bottom: 10.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppTheme.mutedTextColor.withOpacity(0.7), letterSpacing: 0.5),
                ),
                const SizedBox(height: 4),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: connections.map((conn) {
                    final accountId = conn['account_id']?.toString() ?? '';
                    final accountName = conn['account_name']?.toString() ?? '';
                    final displayName = accountName.isNotEmpty && accountName != accountId ? accountName : accountId;
                    final isSelected = _accountIdController.text == accountId;
                    return Tooltip(
                      message: 'ID: $accountId',
                      child: ActionChip(
                        label: Text(
                          displayName,
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                            color: isSelected ? AppTheme.primaryColor : AppTheme.textPrimaryColor,
                          ),
                        ),
                        avatar: Icon(
                          isSelected ? Icons.radio_button_checked : Icons.radio_button_unchecked,
                          size: 14,
                          color: isSelected ? AppTheme.primaryColor : AppTheme.mutedTextColor,
                        ),
                        backgroundColor: isSelected ? AppTheme.primaryColor.withOpacity(0.12) : AppTheme.surfaceColor,
                        side: BorderSide(
                          color: isSelected ? AppTheme.primaryColor : AppTheme.mutedTextColor.withOpacity(0.2),
                          width: isSelected ? 1.5 : 1,
                        ),
                        onPressed: () {
                          setState(() {
                            _accountIdController.text = accountId;
                          });
                        },
                      ),
                    );
                  }).toList(),
                ),
              ],
            ),
          );
        }),
      ],
    );
  }
}
