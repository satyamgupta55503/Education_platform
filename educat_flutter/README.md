# EduCat AI — Flutter App

## Setup

### 1. Firebase Setup
```bash
# Install FlutterFire CLI
dart pub global activate flutterfire_cli

# Configure Firebase (creates google-services.json + GoogleService-Info.plist)
flutterfire configure --project=YOUR_FIREBASE_PROJECT_ID
```

### 2. Environment Config
Create `lib/config/env.dart`:
```dart
const String kApiBase = 'http://YOUR_BACKEND_IP:8000/api/v1';
// Android emulator → http://10.0.2.2:8000/api/v1
// iOS simulator    → http://127.0.0.1:8000/api/v1
// Real device      → http://192.168.x.x:8000/api/v1
```

### 3. Run
```bash
flutter pub get
flutter run
```

## Screens
- **Splash** → Auth check → Home or Login
- **Phone Auth** → Firebase OTP → Profile setup
- **Home** → Subject grid + recent sessions + quick stats  
- **Chat** → SSE streaming with Billi states + thumbs up/down
- **Profile** → EduCat ID + mastery tabs + achievements
- **Leaderboard** → Podium + ranked list + grade filter

## Architecture
- **State**: Riverpod (FutureProvider + StateNotifier)
- **Navigation**: GoRouter with shell route (bottom nav)
- **API**: Dio + auto token refresh interceptor
- **Auth**: Firebase Phone OTP → FastAPI RS256 JWT
- **Streaming**: Raw HttpClient SSE for /chat/send
