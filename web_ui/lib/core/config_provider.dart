import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ConfigState {
  final String? baseUrl;
  final String? apiKey;
  final bool isLoading;

  ConfigState({
    this.baseUrl,
    this.apiKey,
    this.isLoading = false,
  });

  bool get hasCredentials => 
      baseUrl != null && baseUrl!.isNotEmpty && 
      apiKey != null && apiKey!.isNotEmpty;

  bool get isConfigured => hasCredentials;

  ConfigState copyWith({
    String? baseUrl,
    String? apiKey,
    bool? isLoading,
  }) {
    return ConfigState(
      baseUrl: baseUrl ?? this.baseUrl,
      apiKey: apiKey ?? this.apiKey,
      isLoading: isLoading ?? this.isLoading,
    );
  }
}

class ConfigNotifier extends AsyncNotifier<ConfigState> {
  final _secureStorage = const FlutterSecureStorage();

  @override
  Future<ConfigState> build() async {
    return _loadCredentials();
  }

  Future<ConfigState> _loadCredentials() async {
    final prefs = await SharedPreferences.getInstance();
    final baseUrl = prefs.getString('api_base_url');
    final apiKey = await _secureStorage.read(key: 'api_key');
    
    return ConfigState(
      baseUrl: baseUrl,
      apiKey: apiKey,
      isLoading: false,
    );
  }

  Future<void> saveCredentials(String baseUrl, String apiKey) async {
    state = const AsyncValue.loading();
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('api_base_url', baseUrl);
      await _secureStorage.write(key: 'api_key', value: apiKey);
      state = AsyncValue.data(ConfigState(baseUrl: baseUrl, apiKey: apiKey));
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }

  Future<void> clearCredentials() async {
    state = const AsyncValue.loading();
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('api_base_url');
      await _secureStorage.delete(key: 'api_key');
      state = AsyncValue.data(ConfigState(baseUrl: null, apiKey: null));
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }
}

final configProvider = AsyncNotifierProvider<ConfigNotifier, ConfigState>(() {
  return ConfigNotifier();
});
