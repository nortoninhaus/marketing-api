import 'dart:convert';
import 'package:dio/dio.dart';


/// Callback type for handling unauthorized (401) responses.
typedef OnUnauthorizedCallback = void Function();

class ApiClient {
  final Dio _dio;
  final OnUnauthorizedCallback? onUnauthorized;
  final bool useMockOAuth;

  ApiClient({
    String? baseUrl,
    String? apiKey,
    this.onUnauthorized,
    this.useMockOAuth = true,
  }) : _dio = Dio() {
    if (baseUrl != null && baseUrl.isNotEmpty) {
      _dio.options.baseUrl = baseUrl;
    }
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          if (apiKey != null && apiKey.isNotEmpty) {
            options.headers['X-API-Key'] = apiKey;
          }
          return handler.next(options);
        },
        onError: (error, handler) {
          if (error.response?.statusCode == 401 && onUnauthorized != null) {
            onUnauthorized!();
          }
          return handler.next(error);
        },
      ),
    );
  }

  Exception _handleError(dynamic e) {
    if (e is DioException) {
      if (e.response?.statusCode == 401) {
        return Exception('Invalid API Key or unauthorized access (401).');
      }
      final detail = e.response?.data;
      if (detail is Map && detail.containsKey('detail')) {
        return Exception('API Error ${e.response?.statusCode}: ${detail['detail']}');
      }
      return Exception('API Error: ${e.response?.statusCode} - ${e.message}');
    }
    return Exception('Unexpected error: $e');
  }

  dynamic _parseResponse(dynamic data, {bool expectList = false}) {
    if (data is String) {
      try {
        final decoded = jsonDecode(data);
        if (expectList && decoded is! List) {
          throw Exception('Expected a JSON list but got ${decoded.runtimeType}');
        }
        if (!expectList && decoded is! Map) {
          throw Exception('Expected a JSON map but got ${decoded.runtimeType}');
        }
        return decoded;
      } catch (e) {
        final preview = data.substring(0, data.length > 200 ? 200 : data.length);
        throw Exception('Failed to parse response as JSON. Data: $preview');
      }
    }
    if (expectList && data is! List) {
      throw Exception('Expected a list but got ${data.runtimeType}');
    }
    if (!expectList && data is! Map) {
      if (data is Map) {
        return Map<String, dynamic>.from(data);
      }
      throw Exception('Expected a map but got ${data.runtimeType}');
    }
    if (data is Map) {
      return Map<String, dynamic>.from(data);
    }
    return data;
  }

  Future<Map<String, dynamic>> checkHealth() async {
    try {
      final response = await _dio.get('/health');
      return _parseResponse(response.data) as Map<String, dynamic>;
    } catch (e) {
      throw _handleError(e);
    }
  }

  Future<List<dynamic>> getPlatforms() async {
    try {
      final response = await _dio.get('/api/v1/platforms');
      return _parseResponse(response.data, expectList: true) as List<dynamic>;
    } catch (e) {
      throw _handleError(e);
    }
  }

  /// Fetches the full metric/dimension schema for a specific platform.
  Future<Map<String, dynamic>> getSchema(String platform) async {
    try {
      final response = await _dio.get('/api/v1/schema/$platform');
      return _parseResponse(response.data) as Map<String, dynamic>;
    } catch (e) {
      throw _handleError(e);
    }
  }

  Future<Map<String, dynamic>> runSingleQuery(Map<String, dynamic> requestData) async {
    try {
      final response = await _dio.post('/api/v1/campaign-data', data: requestData);
      return _parseResponse(response.data) as Map<String, dynamic>;
    } catch (e) {
      throw _handleError(e);
    }
  }

  Future<Map<String, dynamic>> runBatchQuery(Map<String, dynamic> requestData) async {
    try {
      final response = await _dio.post('/api/v1/batch', data: requestData);
      return _parseResponse(response.data) as Map<String, dynamic>;
    } catch (e) {
      throw _handleError(e);
    }
  }

  // OAuth Methods
  Future<Map<String, dynamic>> getOAuthAuthorizeUrl(String platform) async {
    if (useMockOAuth) {
      await Future.delayed(const Duration(milliseconds: 500));
      return {'url': 'https://example.com/oauth/authorize?platform=$platform&mock=true'};
    }
    try {
      // Pass the current browser origin so the backend redirects back here after OAuth
      final currentOrigin = Uri.base.origin;
      final response = await _dio.get('/api/v1/oauth/authorize', queryParameters: {
        'platform': platform,
        'redirect_url': currentOrigin,
      });
      return response.data;
    } catch (e) {
      throw _handleError(e);
    }
  }

  Future<List<dynamic>> getOAuthConnections(String platform) async {
    if (useMockOAuth) {
      await Future.delayed(const Duration(milliseconds: 500));
      // Return fake data based on platform
      if (platform == 'meta_ads') {
        return [
          {'account_id': 'act_123456', 'account_name': 'Inhaus Meta Marketing', 'platform': 'meta_ads'},
          {'account_id': 'act_654321', 'account_name': 'Client Meta Ads', 'platform': 'meta_ads'},
        ];
      } else if (platform == 'google_ads') {
        return [
          {'account_id': '987-654-3210', 'account_name': 'Inhaus Google Ads', 'platform': 'google_ads'},
        ];
      }
      return [];
    }
    try {
      final response = await _dio.get('/api/v1/oauth/connections', queryParameters: {'platform': platform});
      return response.data;
    } catch (e) {
      throw _handleError(e);
    }
  }

  Future<void> disconnectOAuthAccount(String platform, String accountId) async {
    if (useMockOAuth) {
      await Future.delayed(const Duration(milliseconds: 500));
      return;
    }
    try {
      await _dio.delete('/api/v1/oauth/connections/$platform/$accountId');
    } catch (e) {
      throw _handleError(e);
    }
  }
}
