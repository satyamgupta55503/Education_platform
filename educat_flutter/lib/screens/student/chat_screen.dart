import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../services/api_service.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common.dart';

// ── Billi States ──────────────────────────────────────────────────────────────
enum BilliState { idle, thinking, talking, happy, sleeping }
extension BilliExt on BilliState {
  String get emoji => const {'idle':'😺','thinking':'🤔','talking':'😸','happy':'😻','sleeping':'😴'}[name]!;
  String get label => const {'idle':'Ready!','thinking':'Thinking...','talking':'Answering...','happy':'Great question!','sleeping':'Zzz...'}[name]!;
  Color  get color => const {'idle':AppColors.gray400,'thinking':AppColors.warning,
    'talking':AppColors.primary,'happy':AppColors.success,'sleeping':AppColors.info}[name]!;
  static BilliState from(String s) => BilliState.values.firstWhere((e) => e.name == s, orElse: () => BilliState.idle);
}

// ── Message Model ─────────────────────────────────────────────────────────────
class Msg {
  final String id, role;
  String content;
  bool streaming;
  String? cacheHit, difficulty, videoUrl;
  final DateTime time;
  Msg({required this.id, required this.role, required this.content, required this.time,
    this.streaming=false, this.cacheHit, this.difficulty, this.videoUrl});
  bool get isUser => role == 'user';
}

// ── Notifier ──────────────────────────────────────────────────────────────────
class ChatNotifier extends StateNotifier<List<Msg>> {
  ChatNotifier() : super([]);
  BilliState billiState = BilliState.idle;
  String? sessionId;

  void add(Msg m) => state = [...state, m];
  void append(String token) {
    if (state.isEmpty) return;
    final last = state.last;
    state = [...state.sublist(0, state.length-1),
      Msg(id: last.id, role: last.role, content: last.content+token,
        time: last.time, streaming: true, cacheHit: last.cacheHit,
        difficulty: last.difficulty, videoUrl: last.videoUrl)];
  }
  void finalise({String? cacheHit, String? difficulty, String? videoUrl}) {
    if (state.isEmpty) return;
    final last = state.last;
    state = [...state.sublist(0, state.length-1),
      Msg(id: last.id, role: last.role, content: last.content,
        time: last.time, streaming: false,
        cacheHit: cacheHit ?? last.cacheHit,
        difficulty: difficulty ?? last.difficulty,
        videoUrl: videoUrl ?? last.videoUrl)];
  }
  void setBilli(String s) => billiState = BilliExt.from(s);
}

final chatProvider = StateNotifierProvider.autoDispose
    .family<ChatNotifier, List<Msg>, String>((ref, _) => ChatNotifier());

// ── Chat Screen ───────────────────────────────────────────────────────────────
class ChatScreen extends ConsumerStatefulWidget {
  final String subject;
  final int grade;
  final String language;
  const ChatScreen({super.key, required this.subject, required this.grade, required this.language});
  @override ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> with TickerProviderStateMixin {
  final _scroll  = ScrollController();
  final _input   = TextEditingController();
  final _focus   = FocusNode();
  late final AnimationController _billiAnim;

  String? _sid;
  bool _init = true, _sending = false;
  BilliState _billi = BilliState.idle;
  StreamSubscription? _sub;

  String get _uid => 'chat_${widget.subject}';

  @override
  void initState() {
    super.initState();
    _billiAnim = AnimationController(vsync: this, duration: const Duration(milliseconds: 800))
      ..repeat(reverse: true);
    _initSession();
  }

  @override
  void dispose() {
    _sub?.cancel(); _billiAnim.dispose();
    _scroll.dispose(); _input.dispose(); _focus.dispose(); super.dispose();
  }

  Future<void> _initSession() async {
    try {
      final data = await ref.read(apiProvider).createSession(
        subject: widget.subject, grade: widget.grade, language: widget.language);
      _sid = data['session_id'] as String;
      final n = ref.read(chatProvider(_uid).notifier)..sessionId = _sid;

      // Welcome message
      final welcome = widget.language == 'hi'
        ? 'Namaste! Main Billi hoon 🐱 Aaj ${_subLabel(widget.subject)} '
          'ke baare mein kya poochna hai?'
        : "Hello! I'm Billi 🐱 What would you like to learn about "
          '${_subLabel(widget.subject)} today?';
      n.add(Msg(id: 'w0', role: 'assistant', content: welcome, time: DateTime.now()));
    } catch (e) {
      _showSnack('Could not start session. Check connection.');
    } finally { if (mounted) setState(() => _init = false); }
  }

  Future<void> _send(String text) async {
    if (text.trim().isEmpty || _sid == null || _sending) return;
    final trimmed = text.trim();
    _input.clear(); _focus.unfocus();
    final n = ref.read(chatProvider(_uid).notifier);

    n.add(Msg(id: DateTime.now().millisecondsSinceEpoch.toString(),
      role: 'user', content: trimmed, time: DateTime.now()));
    n.add(Msg(id: 'r${DateTime.now().ms}', role: 'assistant',
      content: '', time: DateTime.now(), streaming: true));

    setState(() { _sending = true; _billi = BilliState.thinking; });
    _scrollBottom();

    String? vid;
    try {
      await for (final e in ref.read(apiProvider).sendMessage(sessionId: _sid!, message: trimmed)) {
        if (!mounted) break;
        final type = e['type'] as String? ?? '';
        if (type == 'billi_state') setState(() => _billi = BilliExt.from(e['state'] as String? ?? 'idle'));
        else if (type == 'token')  { n.append(e['content'] as String? ?? ''); _scrollBottom(); }
        else if (type == 'video_suggestion') vid = e['url'] as String?;
        else if (type == 'complete') {
          setState(() => _billi = BilliExt.from(e['billi_state'] as String? ?? 'happy'));
          n.finalise(cacheHit: e['cache_hit'] as String?,
            difficulty: e['difficulty'] as String?, videoUrl: vid);
        }
      }
    } catch (e) {
      n.finalise();
      _showSnack('Network error. Try again.');
    } finally { if (mounted) setState(() => _sending = false); }
  }

  void _scrollBottom() => WidgetsBinding.instance.addPostFrameCallback((_) {
    if (_scroll.hasClients) _scroll.animateTo(
      _scroll.position.maxScrollExtent,
      duration: const Duration(milliseconds: 280), curve: Curves.easeOut);
  });

  void _showSnack(String msg) => ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text(msg), backgroundColor: AppColors.error,
      behavior: SnackBarBehavior.floating, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))));

  @override
  Widget build(BuildContext context) {
    final msgs  = ref.watch(chatProvider(_uid));
    final color = AppColors.forSubject(widget.subject);
    final emoji = AppColors.emojiForSubject(widget.subject);

    return Scaffold(
      backgroundColor: const Color(0xFFF7F9FC),
      appBar: AppBar(
        backgroundColor: color, foregroundColor: Colors.white,
        title: Row(children: [
          Container(width: 34, height: 34,
            decoration: BoxDecoration(color: Colors.white.withOpacity(0.2),
              borderRadius: BorderRadius.circular(10)),
            child: Center(child: Text(emoji, style: const TextStyle(fontSize: 18)))),
          const SizedBox(width: 10),
          Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(_subLabel(widget.subject), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 15)),
            Text('Class ${widget.grade}', style: TextStyle(color: Colors.white.withOpacity(0.75), fontSize: 11)),
          ]),
        ]),
        actions: [
          if (_sid != null) IconButton(
            icon: const Icon(Icons.add_comment_outlined, color: Colors.white),
            tooltip: 'New session',
            onPressed: () => showDialog(context: context, builder: (_) => AlertDialog(
              title: const Text('Start New Session?'),
              content: const Text('Current chat is saved. Start fresh?'),
              actions: [
                TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
                ElevatedButton(onPressed: () { Navigator.pop(context); setState(() { _sid = null; _init = true; }); _initSession(); }, child: const Text('New Chat')),
              ],
            )),
          ),
        ],
        elevation: 0,
      ),
      body: Column(children: [
        // Billi status bar
        _BilliBar(state: _billi),

        // Messages
        Expanded(child: _init
          ? const Center(child: CircularProgressIndicator())
          : msgs.isEmpty
            ? _QuickQuestions(subject: widget.subject, lang: widget.language, onAsk: _send)
            : ListView.builder(
                controller: _scroll,
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                itemCount: msgs.length,
                itemBuilder: (ctx, i) => _MsgBubble(
                  msg: msgs[i], color: color,
                  onFeedback: (pos) => ref.read(apiProvider).sendFeedback(
                    sessionId: _sid!, messageId: msgs[i].id, isPositive: pos),
                ).animate(delay: (i < 15 ? i * 25 : 0).ms).fadeIn(),
              ),
        ),

        // Input
        _InputBar(ctrl: _input, focus: _focus, sending: _sending,
          color: color, lang: widget.language, onSend: _send),
      ]),
    );
  }

  String _subLabel(String s) => const {'science':'Science','maths':'Maths','hindi':'Hindi',
    'english':'English','sst':'Social Science','gk':'General Knowledge'}[s] ?? s;
}

extension on DateTime {
  int get ms => millisecondsSinceEpoch;
}

// ── Billi Status Bar ──────────────────────────────────────────────────────────
class _BilliBar extends StatelessWidget {
  final BilliState state;
  const _BilliBar({required this.state});
  @override
  Widget build(BuildContext context) => AnimatedContainer(
    duration: const Duration(milliseconds: 250),
    color: state.color.withOpacity(0.08),
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
    child: Row(children: [
      AnimatedSwitcher(duration: const Duration(milliseconds: 250),
        child: Text(state.emoji, key: ValueKey(state), style: const TextStyle(fontSize: 22))),
      const SizedBox(width: 10),
      AnimatedSwitcher(duration: const Duration(milliseconds: 250),
        child: Text(state.label, key: ValueKey(state.label),
          style: TextStyle(color: state.color, fontWeight: FontWeight.w600, fontSize: 13))),
      const Spacer(),
      if (state == BilliState.thinking || state == BilliState.talking)
        SizedBox(width: 16, height: 16,
          child: CircularProgressIndicator(strokeWidth: 2, color: state.color)),
    ]),
  );
}

// ── Message Bubble ────────────────────────────────────────────────────────────
class _MsgBubble extends StatelessWidget {
  final Msg msg;
  final Color color;
  final Function(bool)? onFeedback;
  const _MsgBubble({required this.msg, required this.color, this.onFeedback});

  @override
  Widget build(BuildContext context) {
    final isUser = msg.isUser;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (!isUser) ...[
            Container(width: 32, height: 32,
              decoration: BoxDecoration(color: color.withOpacity(0.12), shape: BoxShape.circle),
              child: const Center(child: Text('🐱', style: TextStyle(fontSize: 16)))),
            const SizedBox(width: 8),
          ],
          Flexible(child: Column(
            crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
                decoration: BoxDecoration(
                  color: isUser ? color : AppColors.white,
                  borderRadius: BorderRadius.only(
                    topLeft:     const Radius.circular(18),
                    topRight:    const Radius.circular(18),
                    bottomLeft:  Radius.circular(isUser ? 18 : 4),
                    bottomRight: Radius.circular(isUser ? 4 : 18),
                  ),
                  boxShadow: const [BoxShadow(color: Color(0x0D000000), blurRadius: 6, offset: Offset(0,2))],
                ),
                child: msg.streaming && msg.content.isEmpty
                  ? _TypingDots()
                  : Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(msg.content, style: TextStyle(
                        color: isUser ? Colors.white : AppColors.gray900,
                        fontSize: 14, height: 1.55)),
                      if (msg.streaming && msg.content.isNotEmpty)
                        Text('▋', style: TextStyle(color: color, fontSize: 14))
                            .animate(onPlay: (c)=>c.repeat()).fadeIn(duration: 400.ms).then().fadeOut(duration: 400.ms),
                    ]),
              ),
              if (!isUser) ...[
                const SizedBox(height: 5),
                Row(children: [
                  if (msg.cacheHit != null && msg.cacheHit != 'none')
                    _MetaBadge('⚡ ${msg.cacheHit!.toUpperCase()}', AppColors.success),
                  if (msg.difficulty != null) ...[
                    const SizedBox(width: 4),
                    _MetaBadge(msg.difficulty!,
                      msg.difficulty == 'hard' ? AppColors.error : msg.difficulty == 'medium' ? AppColors.warning : AppColors.success),
                  ],
                  const Spacer(),
                  if (!msg.streaming) ...[
                    _FbBtn(Icons.thumb_up_outlined, () => onFeedback?.call(true)),
                    _FbBtn(Icons.thumb_down_outlined, () => onFeedback?.call(false)),
                  ],
                ]),
              ],
              if (msg.videoUrl != null) _VideoCard(url: msg.videoUrl!),
            ],
          )),
          if (isUser) const SizedBox(width: 8),
        ],
      ),
    );
  }
}

class _MetaBadge extends StatelessWidget {
  final String label; final Color color;
  const _MetaBadge(this.label, this.color);
  @override Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
    decoration: BoxDecoration(color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(10)),
    child: Text(label, style: TextStyle(color: color, fontSize: 9, fontWeight: FontWeight.w700)));
}

class _FbBtn extends StatefulWidget {
  final IconData icon; final VoidCallback onTap;
  const _FbBtn(this.icon, this.onTap);
  @override State<_FbBtn> createState() => _FbBtnState();
}
class _FbBtnState extends State<_FbBtn> {
  bool _done = false;
  @override Widget build(BuildContext context) => GestureDetector(
    onTap: () { if (_done) return; setState(() => _done = true); widget.onTap(); },
    child: Padding(padding: const EdgeInsets.symmetric(horizontal: 4),
      child: Icon(widget.icon, size: 16, color: _done ? AppColors.success : AppColors.gray300)));
}

class _VideoCard extends StatelessWidget {
  final String url;
  const _VideoCard({required this.url});
  @override Widget build(BuildContext context) => GestureDetector(
    onTap: () {},
    child: Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(color: AppColors.errorLight,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.error.withOpacity(0.2))),
      child: const Row(children: [
        Icon(Icons.play_circle_outline_rounded, color: AppColors.error, size: 18),
        SizedBox(width: 8),
        Expanded(child: Text('Related video available', style: TextStyle(
          fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.error))),
        Icon(Icons.arrow_forward_ios_rounded, size: 11, color: AppColors.error),
      ]),
    ),
  );
}

class _TypingDots extends StatelessWidget {
  @override Widget build(BuildContext context) => Row(mainAxisSize: MainAxisSize.min,
    children: List.generate(3, (i) => Container(
      width: 7, height: 7, margin: const EdgeInsets.symmetric(horizontal: 2),
      decoration: const BoxDecoration(color: AppColors.gray300, shape: BoxShape.circle),
    ).animate(delay: (i*200).ms, onPlay: (c)=>c.repeat())
     .scaleY(end: 1.5, duration: 400.ms).then().scaleY(end: 1.0, duration: 400.ms)),
  );
}

// ── Input Bar ─────────────────────────────────────────────────────────────────
class _InputBar extends StatelessWidget {
  final TextEditingController ctrl;
  final FocusNode focus;
  final bool sending;
  final Color color;
  final String lang;
  final Function(String) onSend;
  const _InputBar({required this.ctrl, required this.focus, required this.sending,
    required this.color, required this.lang, required this.onSend});

  @override Widget build(BuildContext context) => Container(
    color: AppColors.white,
    padding: EdgeInsets.only(
      left: 12, right: 12, top: 10,
      bottom: MediaQuery.of(context).viewPadding.bottom + 10),
    child: Row(children: [
      // Mic button
      GestureDetector(
        onTap: () {},
        child: Container(width: 44, height: 44,
          decoration: BoxDecoration(color: AppColors.gray100, shape: BoxShape.circle),
          child: const Icon(Icons.mic_outlined, color: AppColors.gray400, size: 20)),
      ),
      const SizedBox(width: 8),
      Expanded(child: TextField(
        controller: ctrl, focusNode: focus, enabled: !sending,
        maxLines: 4, minLines: 1,
        textInputAction: TextInputAction.send,
        onSubmitted: onSend,
        style: const TextStyle(fontSize: 14),
        decoration: InputDecoration(
          hintText: lang == 'hi' ? 'Billi se poochho... 🐱' : 'Ask Billi... 🐱',
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: BorderSide.none),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(24), borderSide: BorderSide(color: color, width: 2)),
          filled: true, fillColor: AppColors.gray100,
        ),
      )),
      const SizedBox(width: 8),
      GestureDetector(
        onTap: sending ? null : () => onSend(ctrl.text),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          width: 44, height: 44,
          decoration: BoxDecoration(
            color: sending ? AppColors.gray200 : color,
            shape: BoxShape.circle,
            boxShadow: sending ? [] : [BoxShadow(color: color.withOpacity(0.35), blurRadius: 8, offset: const Offset(0,3))]),
          child: sending
            ? const Center(child: SizedBox(width: 18, height: 18,
                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)))
            : const Icon(Icons.send_rounded, color: Colors.white, size: 20),
        ),
      ),
    ]),
  );
}

// ── Quick Questions ───────────────────────────────────────────────────────────
class _QuickQuestions extends StatelessWidget {
  final String subject, lang;
  final Function(String) onAsk;
  const _QuickQuestions({required this.subject, required this.lang, required this.onAsk});

  static const _hi = {'science':['Photosynthesis kya hai?','Newton ke niyam batao','Cell kya hoti hai?'],
    'maths':['Pythagoras theorem samjhao','Fraction kya hota hai?','Area formula batao'],
    'hindi':['Sangya ke prakar batao','Samas kya hai?','Muhavare ka arth batao'],
    'english':['What is a noun?','Explain past tense','What is metaphor?'],
    'sst':['Loktantra kya hai?','French Revolution batao','Bharat ka map samjhao'],
    'gk':['Solar system batao','Olympic games kab hote hain?','Bharat ki rajdhani kya hai?']};
  static const _en = {'science':['What is photosynthesis?','Explain Newton\'s laws','What is a cell?'],
    'maths':['Explain Pythagoras theorem','How to add fractions?','Area formula for circle'],
    'english':['What is a noun?','Explain past tense','What is a metaphor?'],
    'sst':['What is democracy?','Tell me about French Revolution','Explain the water cycle'],
    'gk':['Tell me about solar system','When are Olympics held?','Capital of India?']};

  @override Widget build(BuildContext context) {
    final color = AppColors.forSubject(subject);
    final qs = (lang == 'hi' ? _hi : _en)[subject] ?? [];
    return SingleChildScrollView(padding: const EdgeInsets.all(20), child: Column(children: [
      const SizedBox(height: 24),
      Text(AppColors.emojiForSubject(subject), style: const TextStyle(fontSize: 64))
          .animate(onPlay: (c) => c.repeat(reverse: true)).moveY(begin: 0, end: -8, duration: 1200.ms),
      const SizedBox(height: 14),
      Text('I\'m Billi! Ask me anything 😸',
        style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700, color: AppColors.primaryDark),
        textAlign: TextAlign.center),
      const SizedBox(height: 24),
      Wrap(spacing: 8, runSpacing: 8, children: qs.map((q) => GestureDetector(
        onTap: () => onAsk(q),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
          decoration: BoxDecoration(
            color: color.withOpacity(0.08), borderRadius: BorderRadius.circular(20),
            border: Border.all(color: color.withOpacity(0.25))),
          child: Text(q, style: TextStyle(color: color, fontSize: 13, fontWeight: FontWeight.w500))),
      )).toList()),
    ]));
  }
}
