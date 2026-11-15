// lib/services/api_service.dart — Full backend API client
import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

// ── Config ─────────────────────────────────────────────────────────────────────
const String kApiBase = String.fromEnvironment(
  'API_BASE', defaultValue: 'http://10.0.2.2:8000/api/v1');
// 10.0.2.2 = localhost from Android emulator
// For iOS simulator use 127.0.0.1
// For real device: use your machine's LAN IP e.g. 192.168.1.100

// ── Storage keys ───────────────────────────────────────────────────────────────
class SK {
  static const access   = 'access_token';
  static const refresh  = 'refresh_token';
  static const family   = 'token_family_id';
  static const userId   = 'user_id';
  static const tier     = 'user_tier';
  static const grade    = 'user_grade';
  static const language = 'user_language';
  static const educatId = 'educat_id';
  static const name     = 'display_name';
}

// ── Models ─────────────────────────────────────────────────────────────────────
class UserProfile {
  final String userId, educatId, displayName, tier, language;
  final int grade, brainCoins, streakDays;
  final int monthlyRemaining, dailyRemaining, monthlyMax, dailyMax;
  final List<dynamic> subjectMastery, activity7d, achievements;
  final Map<String, dynamic> stats;

  const UserProfile({
    required this.userId, required this.educatId,
    required this.displayName, required this.tier,
    required this.language, required this.grade,
    required this.brainCoins, required this.streakDays,
    required this.monthlyRemaining, required this.dailyRemaining,
    required this.monthlyMax, required this.dailyMax,
    required this.subjectMastery, required this.activity7d,
    required this.achievements, required this.stats,
  });

  factory UserProfile.fromJson(Map<String, dynamic> j) {
    final p = j['profile'] as Map<String, dynamic>;
    final g = j['gamification'] as Map<String, dynamic>;
    final q = j['quota'] as Map<String, dynamic>;
    return UserProfile(
      userId:   p['user_id'] as String,
      educatId: p['educat_id'] as String,
      displayName: p['display_name'] as String? ?? 'Student',
      tier:     p['tier'] as String? ?? 'free',
      language: p['language'] as String? ?? 'hi',
      grade:    (p['grade'] as num?)?.toInt() ?? 5,
      brainCoins:  (g['brain_coins'] as num?)?.toInt() ?? 0,
      streakDays:  (g['brain_coins'] as num?)?.toInt() ?? 0,
      monthlyRemaining: (q['monthly_remaining'] as num?)?.toInt() ?? 0,
      dailyRemaining:   (q['daily_remaining'] as num?)?.toInt() ?? 0,
      monthlyMax: (q['monthly_max'] as num?)?.toInt() ?? 25,
      dailyMax:   (q['daily_max'] as num?)?.toInt() ?? 2,
      subjectMastery: j['subject_mastery'] as List<dynamic>? ?? [],
      activity7d:    j['activity_7d'] as List<dynamic>? ?? [],
      achievements:  (j['gamification'] as Map)['achievements'] as List<dynamic>? ?? [],
      stats: j['stats'] as Map<String, dynamic>? ?? {},
    );
  }
}

// ── API Service ────────────────────────────────────────────────────────────────
class ApiService {
  late final Dio _dio;
  final _storage = const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true));

  ApiService() {
    _dio = Dio(BaseOptions(
      baseUrl: kApiBase,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 60),
      headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
    ));

    // Auth interceptor
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (opts, handler) async {
        final tok = await _storage.read(key: SK.access);
        if (tok != null) opts.headers['Authorization'] = 'Bearer $tok';
        handler.next(opts);
      },
      onError: (err, handler) async {
        if (err.response?.statusCode == 401) {
          final ok = await _refreshTokens();
          if (ok) {
            final tok = await _storage.read(key: SK.access);
            err.requestOptions.headers['Authorization'] = 'Bearer $tok';
            try {
              final res = await _dio.fetch(err.requestOptions);
              return handler.resolve(res);
            } catch (_) {}
          }
        }
        handler.next(err);
      },
    ));
  }

  Future<bool> _refreshTokens() async {
    try {
      final rt  = await _storage.read(key: SK.refresh);
      if (rt == null) return false;
      final res = await Dio().post('$kApiBase/auth/refresh',
        data: {'refresh_token': rt});
      final data = (res.data as Map<String, dynamic>)['data'] as Map<String, dynamic>? ?? res.data as Map<String, dynamic>;
      await _saveTokens(data);
      return true;
    } catch (_) { await logout(); return false; }
  }

  Future<void> _saveTokens(Map<String, dynamic> d) async {
    await _storage.write(key: SK.access,  value: d['access_token']  as String?);
    await _storage.write(key: SK.refresh, value: d['refresh_token'] as String?);
    if (d.containsKey('family_id')) {
      await _storage.write(key: SK.family, value: d['family_id'] as String?);
    }
  }

  // ── Auth ────────────────────────────────────────────────────────────────────
  Future<Map<String, dynamic>> verifyFirebase({
    required String firebaseToken, required int grade, required String language,
  }) async {
    final res = await _dio.post('/auth/phone/verify', data: {
      'firebase_token': firebaseToken, 'grade': grade, 'language': language,
    });
    final raw = res.data as Map<String, dynamic>;
    final data = raw['data'] as Map<String, dynamic>? ?? raw;
    await _saveTokens(data);
    final user = data['user'] as Map<String, dynamic>? ?? {};
    await _storage.write(key: SK.userId,   value: user['user_id']?.toString());
    await _storage.write(key: SK.tier,     value: user['subscription_tier']?.toString() ?? user['tier']?.toString());
    await _storage.write(key: SK.grade,    value: user['grade']?.toString());
    await _storage.write(key: SK.language, value: user['language']?.toString());
    return data;
  }

  Future<void> logout() async {
    try { await _dio.delete('/auth/logout'); } catch (_) {}
    await _storage.deleteAll();
  }

  Future<bool> get isLoggedIn async {
    final t = await _storage.read(key: SK.access);
    return t != null;
  }

  Future<String> get cachedTier    async => await _storage.read(key: SK.tier)     ?? 'free';
  Future<int>    get cachedGrade   async => int.tryParse(await _storage.read(key: SK.grade) ?? '5') ?? 5;
  Future<String> get cachedLang    async => await _storage.read(key: SK.language) ?? 'hi';
  Future<String> get cachedUserId  async => await _storage.read(key: SK.userId)   ?? '';
  Future<String> get cachedName    async => await _storage.read(key: SK.name)     ?? 'Student';
  Future<String> get cachedEducat  async => await _storage.read(key: SK.educatId) ?? '';

  // ── Student Profile ─────────────────────────────────────────────────────────
  Future<UserProfile> getProfile() async {
    final res = await _dio.get('/users/me');
    final raw = res.data as Map<String, dynamic>;
    final data = raw['data'] as Map<String, dynamic>? ?? raw;
    final profile = UserProfile.fromJson(data);
    await _storage.write(key: SK.educatId, value: profile.educatId);
    await _storage.write(key: SK.name,     value: profile.displayName);
    return profile;
  }

  Future<void> updateProfile(Map<String, dynamic> updates) async {
    await _dio.patch('/users/me', data: updates);
  }

  Future<Map<String, dynamic>> updateStreak() async {
    // Streak is auto-managed by backend on activity; this is a no-op placeholder
    return {'success': true, 'streak_days': 0};
  }

  Future<Map<String, dynamic>> getLeaderboard({int? grade}) async {
    // Leaderboard endpoint — uses analytics data
    final res = await _dio.get('/users/me/analytics');
    final raw = res.data as Map<String, dynamic>;
    return raw['data'] as Map<String, dynamic>? ?? raw;
  }

  Future<Map<String, dynamic>> getAchievements() async {
    final res = await _dio.get('/users/me/analytics');
    final raw = res.data as Map<String, dynamic>;
    return raw['data'] as Map<String, dynamic>? ?? raw;
  }

  // ── Chat ───────────────────────────────────────────────────────────────────
  Future<Map<String, dynamic>> createSession({
    required String subject, required int grade, required String language,
  }) async {
    final res = await _dio.post('/chat/session/create', data: {
      'subject': subject, 'topic': subject, 'grade': grade,
    });
    final raw = res.data as Map<String, dynamic>;
    return raw['data'] as Map<String, dynamic>? ?? raw;
  }

  /// SSE streaming — yields events as Map
  Stream<Map<String, dynamic>> sendMessage({
    required String sessionId, required String message,
  }) async* {
    final token = await _storage.read(key: SK.access) ?? '';
    final client = HttpClient();
    final uri = Uri.parse('$kApiBase/chat/send');
    final req = await client.postUrl(uri);
    req.headers.set('Authorization', 'Bearer $token');
    req.headers.set('Content-Type', 'application/json');
    req.headers.set('Accept', 'text/event-stream');
    req.headers.set('Cache-Control', 'no-cache');
    req.write(jsonEncode({'session_id': sessionId, 'question': message}));

    final res = await req.close().timeout(const Duration(minutes: 3));
    final lines = res.transform(utf8.decoder).transform(const LineSplitter());
    await for (final line in lines) {
      if (line.startsWith('data: ')) {
        final raw = line.substring(6).trim();
        if (raw.isEmpty) continue;
        try { yield jsonDecode(raw) as Map<String, dynamic>; }
        catch (_) {}
      }
    }
  }

  Future<void> sendFeedback({
    required String sessionId, required String messageId,
    required bool isPositive,
  }) async {
    // Feedback endpoint — fire and forget
    try {
      await _dio.post('/chat/quiz/submit', data: {
        'quiz_id': messageId,
        'answers': {'feedback': isPositive ? 1 : 0},
      });
    } catch (_) {}
  }

  Future<Map<String, dynamic>> getSessions({String? subject}) async {
    final res = await _dio.get('/chat/sessions',
      queryParameters: subject != null ? {'subject': subject} : null);
    final raw = res.data as Map<String, dynamic>;
    return raw['data'] as Map<String, dynamic>? ?? raw;
  }

  Future<Map<String, dynamic>> getHistory(String sessionId) async {
    final res = await _dio.get('/chat/sessions/$sessionId/messages');
    final raw = res.data as Map<String, dynamic>;
    return raw['data'] as Map<String, dynamic>? ?? raw;
  }

  // ── TTS ────────────────────────────────────────────────────────────────────
  Future<Map<String, dynamic>> tts({
    required String text, required String language,
    double speed = 1.0, bool lipSync = true,
  }) async {
    // TTS not yet implemented in backend — return empty placeholder
    return {'audio_url': null, 'lip_sync': null};
  }

  // ── Parent dashboard ───────────────────────────────────────────────────────
  Future<Map<String, dynamic>> getParentDashboard(String userId) async {
    final res = await _dio.get('/users/me/parent-report');
    final raw = res.data as Map<String, dynamic>;
    return raw['data'] as Map<String, dynamic>? ?? raw;
  }
}

// ── Providers ──────────────────────────────────────────────────────────────────
final apiProvider = Provider<ApiService>((ref) => ApiService());

final profileProvider = FutureProvider.autoDispose<UserProfile>((ref) async {
  return ref.read(apiProvider).getProfile();
});

final sessionsProvider = FutureProvider.autoDispose
    .family<Map<String, dynamic>, String?>((ref, subject) async {
  return ref.read(apiProvider).getSessions(subject: subject);
});

final leaderboardProvider = FutureProvider.autoDispose
    .family<Map<String, dynamic>, int?>((ref, grade) async {
  return ref.read(apiProvider).getLeaderboard(grade: grade);
});
