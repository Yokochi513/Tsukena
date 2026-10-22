import 'package:flutter/material.dart';
import 'package:tsukena/features/gmail_link/repositories/gmail_link_repository.dart';
import 'package:tsukena/features/import_failure/entities/import_failure.dart';
import 'package:tsukena/features/import_failure/repositories/import_failure_repository.dart';
import 'package:tsukena/features/import_failure/widgets/import_failure_list.dart';
import 'package:tsukena/features/transaction/entities/category.dart';
import 'package:tsukena/features/transaction/repositories/category_repository.dart';
import 'package:tsukena/features/transaction/widgets/category_add_dialog.dart';
import 'package:url_launcher/url_launcher.dart';

// TODO: 予算の API ができたら月の予算の変更を、カテゴリの名前・絵文字・表示順の変更を足す（→ docs/design.md 5.1）
class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  late Future<List<ImportFailure>> _failures;
  late Future<List<Category>> _categories;
  bool _linking = false;

  @override
  initState() {
    super.initState();
    _reload();
  }

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('設定'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: '読み込み',
            onPressed: _reload,
          ),
        ],
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 600),
          child: ListView(
            padding: const EdgeInsets.symmetric(vertical: 8),
            children: [
              _sectionTitle('カテゴリ', textTheme),
              FutureBuilder<List<Category>>(
                future: _categories,
                builder: (context, snapshot) {
                  if (snapshot.connectionState != ConnectionState.done) {
                    return const Padding(
                      padding: EdgeInsets.all(16),
                      child: Center(child: CircularProgressIndicator()),
                    );
                  }
                  if (snapshot.hasError) {
                    return const ListTile(title: Text('カテゴリの取得に失敗しました'));
                  }
                  return Column(
                    children: [
                      for (final category in snapshot.data ?? <Category>[])
                        ListTile(
                          leading: Text(
                            category.emoji,
                            style: textTheme.titleLarge,
                          ),
                          title: Text(category.name),
                        ),
                    ],
                  );
                },
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: OutlinedButton.icon(
                  onPressed: _addCategory,
                  icon: const Icon(Icons.add),
                  label: const Text('カテゴリを追加'),
                ),
              ),
              const SizedBox(height: 24),
              _sectionTitle('Gmail 連携', textTheme),
              const ListTile(
                subtitle: Text(
                  '利用通知メールを取り込むために、Gmail の読み取りを許可します。'
                  '連携が切れたと Discord に届いたときも、ここからやり直してください。',
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: FilledButton.icon(
                  onPressed: _linking ? null : _startGmailLink,
                  icon: _linking
                      ? const SizedBox.square(
                          dimension: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.mail_outline),
                  label: const Text('Gmail と連携する'),
                ),
              ),
              const SizedBox(height: 24),
              _sectionTitle('取り込めなかったメール', textTheme),
              FutureBuilder<List<ImportFailure>>(
                future: _failures,
                builder: (context, snapshot) {
                  if (snapshot.connectionState != ConnectionState.done) {
                    return const Padding(
                      padding: EdgeInsets.all(16),
                      child: Center(child: CircularProgressIndicator()),
                    );
                  }
                  if (snapshot.hasError) {
                    return const ListTile(title: Text('取り込めなかったメールの取得に失敗しました'));
                  }
                  return ImportFailureList(
                    failures: snapshot.data ?? [],
                    onRetry: _retryImport,
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _sectionTitle(String title, TextTheme textTheme) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
      child: Text(title, style: textTheme.titleMedium),
    );
  }

  Future<void> _startGmailLink() async {
    setState(() => _linking = true);
    try {
      final url = await GmailLinkService().getAuthorizationUrl();
      // Web 版では同じタブで開く。API の応答を待った後に新しいタブを開くと、ブラウザにポップアップとして止められるため。
      // 連携が終わったら、ブラウザの「戻る」でアプリに戻れる
      final opened = await launchUrl(url, webOnlyWindowName: '_self');
      if (!opened) _showMessage('ブラウザを開けませんでした');
    } on GmailLinkNotConfiguredException {
      _showMessage('サーバーで Gmail 連携の準備ができていません（docs/deploy.md 7）');
    } catch (_) {
      _showMessage('Gmail 連携の開始に失敗しました');
    } finally {
      if (mounted) setState(() => _linking = false);
    }
  }

  Future<void> _addCategory() async {
    final added = await showDialog<bool>(
      context: context,
      builder: (context) => const CategoryAddDialog(),
    );
    if (added != true) return;
    _showMessage('カテゴリを追加しました');
    _reload();
  }

  Future<void> _retryImport(ImportFailure failure) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('取り込み直す'),
        content: const Text(
          'このメールを Gmail から取り直し、もう一度解析します。\n'
          '解析を直した後に押してください。直していないと、また取り込めずに一覧に残ります。',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('やめる'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('取り込み直す'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    try {
      final recorded = await ImportFailureService().retryImport(
        failure.messageId,
      );
      _showMessage('$recorded件を取り込みました。支出の一覧で確かめてください');
    } on ImportRetryFailedException catch (e) {
      _showMessage('取り込めませんでした: ${e.reason}');
    } catch (_) {
      _showMessage('取り込み直しに失敗しました');
    }
    _reload();
  }

  void _showMessage(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  void _reload() {
    setState(() {
      _categories = CategoryService().getCategories();
      _failures = ImportFailureService().getImportFailures();
    });
  }
}
