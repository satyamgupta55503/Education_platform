import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../../services/api_service.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common.dart';

class PhoneAuthScreen extends ConsumerStatefulWidget {
  const PhoneAuthScreen({super.key});
  @override ConsumerState<PhoneAuthScreen> createState() => _PhoneAuthScreenState();
}

class _PhoneAuthScreenState extends ConsumerState<PhoneAuthScreen>
    with TickerProviderStateMixin {
  final _phoneCtrl = TextEditingController();
  final _otpCtrl   = TextEditingController();
  late final AnimationController _billiCtrl;

  int  _step    = 0; // 0=phone, 1=otp, 2=profile
  bool _loading = false;
  String? _verificationId;
  int _selectedGrade = 5;
  String _selectedLang = 'hi';

  static const _grades = [1,2,3,4,5,6,7,8,9,10];

  @override
  void initState() {
    super.initState();
    _billiCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 1500))
      ..repeat(reverse: true);
  }

  @override
  void dispose() {
    _billiCtrl.dispose(); _phoneCtrl.dispose(); _otpCtrl.dispose(); super.dispose();
  }

  Future<void> _sendOTP() async {
    if (_phoneCtrl.text.length < 10) { _showError('Enter valid 10-digit number'); return; }
    setState(() => _loading = true);
    try {
      await FirebaseAuth.instance.verifyPhoneNumber(
        phoneNumber: '+91${_phoneCtrl.text.trim()}',
        timeout: const Duration(seconds: 60),
        verificationCompleted: (cred) async => await _signIn(cred),
        verificationFailed: (e) {
          _showError(e.message ?? 'Verification failed');
          setState(() => _loading = false);
        },
        codeSent: (vId, _) => setState(() { _verificationId = vId; _step = 1; _loading = false; }),
        codeAutoRetrievalTimeout: (_) {},
      );
    } catch (e) { _showError(e.toString()); setState(() => _loading = false); }
  }

  Future<void> _verifyOTP() async {
    if (_otpCtrl.text.length != 6 || _verificationId == null) { _showError('Enter 6-digit OTP'); return; }
    setState(() => _loading = true);
    try {
      final cred = PhoneAuthProvider.credential(
        verificationId: _verificationId!, smsCode: _otpCtrl.text.trim());
      await _signIn(cred);
    } catch (_) { _showError('Invalid OTP. Try again.'); setState(() => _loading = false); }
  }

  Future<void> _signIn(PhoneAuthCredential cred) async {
    try {
      await FirebaseAuth.instance.signInWithCredential(cred);
      setState(() { _step = 2; _loading = false; });
    } catch (_) { _showError('Sign in failed'); setState(() => _loading = false); }
  }

  Future<void> _completeProfile() async {
    setState(() => _loading = true);
    try {
      final tok = await FirebaseAuth.instance.currentUser?.getIdToken() ?? '';
      if (tok.isEmpty) throw Exception('No Firebase token');
      await ref.read(apiProvider).verifyFirebase(
        firebaseToken: tok, grade: _selectedGrade, language: _selectedLang);
      if (mounted) context.go('/home');
    } catch (e) { _showError('Failed: $e'); setState(() => _loading = false); }
  }

  void _showError(String msg) => ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text(msg), backgroundColor: AppColors.error,
      behavior: SnackBarBehavior.floating, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))));

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: AppColors.white,
    body: SafeArea(child: SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(children: [
        const SizedBox(height: 40),
        // ── Billi logo ──────────────────────────────────────────────────────
        _BilliLogo(controller: _billiCtrl)
          .animate().scale(duration: 600.ms, curve: Curves.elasticOut),
        const SizedBox(height: 20),
        Text('EduCat AI', style: TextStyle(
          fontSize: 28, fontWeight: FontWeight.w800, color: AppColors.primaryDark))
          .animate().fadeIn(delay: 200.ms),
        Text('Smart tutor for Classes 1–10',
          style: const TextStyle(fontSize: 13, color: AppColors.gray400))
          .animate().fadeIn(delay: 300.ms),
        const SizedBox(height: 40),

        // ── Step indicator ─────────────────────────────────────────────────
        _StepIndicator(step: _step).animate().fadeIn(delay: 350.ms),
        const SizedBox(height: 32),

        // ── Step content ───────────────────────────────────────────────────
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 380),
          transitionBuilder: (child, anim) => FadeTransition(opacity: anim,
            child: SlideTransition(
              position: Tween<Offset>(begin: const Offset(0.08, 0), end: Offset.zero).animate(anim),
              child: child)),
          child: [
            _PhoneStep(ctrl: _phoneCtrl, loading: _loading, onSend: _sendOTP),
            _OTPStep(ctrl: _otpCtrl, phone: _phoneCtrl.text,
              loading: _loading, onVerify: _verifyOTP, onResend: _sendOTP,
              onBack: () => setState(() => _step = 0)),
            _ProfileStep(
              selectedGrade: _selectedGrade, selectedLang: _selectedLang,
              loading: _loading,
              onGrade: (g) => setState(() => _selectedGrade = g),
              onLang:  (l) => setState(() => _selectedLang  = l),
              onDone: _completeProfile,
            ),
          ][_step],
        ),
        const SizedBox(height: 32),
      ]),
    )),
  );
}

// ── Billi Logo ─────────────────────────────────────────────────────────────────
class _BilliLogo extends StatelessWidget {
  final AnimationController controller;
  const _BilliLogo({required this.controller});
  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: controller,
    builder: (_, __) => Transform.translate(
      offset: Offset(0, controller.value * -8),
      child: Container(
        width: 100, height: 100,
        decoration: BoxDecoration(
          gradient: AppDeco.primaryGradient,
          borderRadius: BorderRadius.circular(28),
          boxShadow: [BoxShadow(
            color: AppColors.primary.withOpacity(0.35),
            blurRadius: 20, offset: const Offset(0, 8))],
        ),
        child: const Center(child: Text('🐱', style: TextStyle(fontSize: 52))),
      ),
    ),
  );
}

// ── Step Indicator ─────────────────────────────────────────────────────────────
class _StepIndicator extends StatelessWidget {
  final int step;
  const _StepIndicator({required this.step});
  static const _labels = ['Phone', 'Verify', 'Profile'];
  @override
  Widget build(BuildContext context) => Row(mainAxisAlignment: MainAxisAlignment.center, children: [
    for (int i = 0; i < 3; i++) ...[
      AnimatedContainer(
        duration: const Duration(milliseconds: 300),
        width: i == step ? 32 : 10, height: 10,
        decoration: BoxDecoration(
          color: i <= step ? AppColors.primary : AppColors.gray200,
          borderRadius: BorderRadius.circular(99)),
      ),
      if (i < 2) const SizedBox(width: 6),
    ],
  ]);
}

// ── Phone Step ─────────────────────────────────────────────────────────────────
class _PhoneStep extends StatelessWidget {
  final TextEditingController ctrl;
  final bool loading;
  final VoidCallback onSend;
  const _PhoneStep({required this.ctrl, required this.loading, required this.onSend});

  @override
  Widget build(BuildContext context) => Column(key: const ValueKey('phone'), children: [
    const Align(alignment: Alignment.centerLeft, child: Text('Enter Mobile Number',
      style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: AppColors.gray900))),
    const SizedBox(height: 4),
    const Align(alignment: Alignment.centerLeft, child: Text("We'll send you a verification code",
      style: TextStyle(fontSize: 13, color: AppColors.gray400))),
    const SizedBox(height: 24),
    TextField(
      controller: ctrl, keyboardType: TextInputType.phone, maxLength: 10,
      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600, letterSpacing: 2),
      decoration: InputDecoration(
        counterText: '', hintText: '9876543210',
        prefixIcon: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          child: const Text('+91', style: TextStyle(
            fontWeight: FontWeight.w700, fontSize: 15, color: AppColors.primary))),
      ),
    ),
    const SizedBox(height: 24),
    SizedBox(width: double.infinity, child: GradientButton(
      label: 'Send OTP', onTap: loading ? null : onSend, loading: loading,
      icon: const Icon(Icons.send_rounded, color: Colors.white, size: 18),
    )),
  ]);
}

// ── OTP Step ───────────────────────────────────────────────────────────────────
class _OTPStep extends StatelessWidget {
  final TextEditingController ctrl;
  final String phone;
  final bool loading;
  final VoidCallback onVerify, onResend, onBack;
  const _OTPStep({required this.ctrl, required this.phone, required this.loading,
    required this.onVerify, required this.onResend, required this.onBack});

  @override
  Widget build(BuildContext context) => Column(key: const ValueKey('otp'), children: [
    const Align(alignment: Alignment.centerLeft, child: Text('Enter OTP',
      style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: AppColors.gray900))),
    const SizedBox(height: 4),
    Align(alignment: Alignment.centerLeft,
      child: Text('Sent to +91 $phone', style: const TextStyle(fontSize: 13, color: AppColors.gray400))),
    const SizedBox(height: 24),
    TextField(
      controller: ctrl, keyboardType: TextInputType.number,
      maxLength: 6, textAlign: TextAlign.center,
      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
      style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w800, letterSpacing: 12),
      decoration: const InputDecoration(counterText: '', hintText: '• • • • • •'),
    ),
    const SizedBox(height: 24),
    SizedBox(width: double.infinity, child: GradientButton(
      label: 'Verify OTP', onTap: loading ? null : onVerify, loading: loading,
      colors: const [Color(0xFF059669), Color(0xFF065F46)],
    )),
    const SizedBox(height: 12),
    Row(mainAxisAlignment: MainAxisAlignment.center, children: [
      TextButton(onPressed: onBack,
        child: const Text('← Back', style: TextStyle(color: AppColors.gray400))),
      const SizedBox(width: 12),
      TextButton(onPressed: onResend,
        child: const Text('Resend OTP', style: TextStyle(color: AppColors.primary, fontWeight: FontWeight.w600))),
    ]),
  ]);
}

// ── Profile Step ───────────────────────────────────────────────────────────────
class _ProfileStep extends StatelessWidget {
  final int selectedGrade;
  final String selectedLang;
  final bool loading;
  final void Function(int) onGrade;
  final void Function(String) onLang;
  final VoidCallback onDone;
  const _ProfileStep({required this.selectedGrade, required this.selectedLang,
    required this.loading, required this.onGrade, required this.onLang, required this.onDone});

  @override
  Widget build(BuildContext context) => Column(key: const ValueKey('profile'),
    crossAxisAlignment: CrossAxisAlignment.start, children: [
    const Text('Almost there! 🎉',
      style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: AppColors.gray900)),
    const SizedBox(height: 4),
    const Text('Tell us about yourself',
      style: TextStyle(fontSize: 13, color: AppColors.gray400)),
    const SizedBox(height: 24),
    const Text('Which class are you in?',
      style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.gray700)),
    const SizedBox(height: 12),
    Wrap(spacing: 8, runSpacing: 8, children: [
      for (int g in [1,2,3,4,5,6,7,8,9,10])
        GestureDetector(
          onTap: () => onGrade(g),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            width: 52, height: 52,
            decoration: BoxDecoration(
              color: selectedGrade == g ? AppColors.primary : AppColors.gray100,
              borderRadius: BorderRadius.circular(12),
              boxShadow: selectedGrade == g ? [BoxShadow(
                color: AppColors.primary.withOpacity(0.3), blurRadius: 8)] : [],
            ),
            child: Center(child: Text('$g', style: TextStyle(
              fontWeight: FontWeight.w700, fontSize: 16,
              color: selectedGrade == g ? Colors.white : AppColors.gray600))),
          ),
        ),
    ]),
    const SizedBox(height: 24),
    const Text('Preferred language?',
      style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.gray700)),
    const SizedBox(height: 12),
    Row(children: [
      for (final lang in [('hi','🇮🇳 Hindi'), ('en','🇬🇧 English')])
        Expanded(child: Padding(
          padding: EdgeInsets.only(right: lang.$1 == 'hi' ? 8 : 0),
          child: GestureDetector(
            onTap: () => onLang(lang.$1),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              height: 52,
              decoration: BoxDecoration(
                color: selectedLang == lang.$1 ? AppColors.primaryLight : AppColors.gray100,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                  color: selectedLang == lang.$1 ? AppColors.primary : Colors.transparent, width: 2)),
              child: Center(child: Text(lang.$2, style: TextStyle(
                fontWeight: FontWeight.w600, fontSize: 14,
                color: selectedLang == lang.$1 ? AppColors.primary : AppColors.gray500))),
            ),
          ),
        )),
    ]),
    const SizedBox(height: 28),
    SizedBox(width: double.infinity, child: GradientButton(
      label: 'Start Learning! 🚀', onTap: loading ? null : onDone, loading: loading,
    )),
  ]);
}
