import 'package:flutter/material.dart';
import 'package:tsukena/features/budget/entities/budget.dart';
import 'package:tsukena/features/budget/repositories/budget_repository.dart';
import 'package:tsukena/features/budget/widgets/budget_edit_dialog.dart';
import 'package:tsukena/features/gmail_link/repositories/gmail_link_repository.dart';
import 'package:tsukena/features/import_failure/entities/import_failure.dart';
import 'package:tsukena/features/import_failure/repositories/import_failure_repository.dart';
import 'package:tsukena/features/transaction/entities/category.dart';
import 'package:tsukena/features/transaction/repositories/category_repository.dart';
import 'package:tsukena/pages/category_list_page.dart';
import 'package:tsukena/pages/import_failure_page.dart';
import 'package:url_launcher/url_launcher.dart';

/// 設定の画面を開くボタン。下のタブの各画面の右上に置く
class SettingsButton extends StatelessWidget {
  const SettingsButton({super.key});

  @override
  Widget build(BuildContext context) {
    return IconButton(
      icon: const Icon(Icons.settings_outlined),
      tooltip: '設定',
      onPressed: () => Navigator.of(
        context,
      ).push(MaterialPageRoute<void>(builder: (_) => const SettingsPage())),
    );
  }
}

/// 設定の項目を1行ずつ並べる。行には今の値や件数だけを出し、一覧や操作は開いた先の画面で行う
class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  late Future<Budget> _budget;
  late Future<List<Category>> _categories;
  late Future<List<ImportFailure>> _failures;
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
              _sectionTitle('家計', textTheme),
              FutureBuilder<Budget>(
                future: _budget,
                builder: (context, snapshot) {
                  final budget = snapshot.data;
                  return ListTile(
                    leading: const Icon(Icons.savings_outlined),
                    title: const Text('月の予算'),
                    trailing: _trailing(
                      snapshot,
                      (budget) =>
                          Text('¥${_formatAmount(budget.monthlyBudget)}'),
                    ),
                    // 今の値が分からないとダイアログに初期値を出せないため、取れるまでは押せない
                    onTap: budget == null ? null : () => _editBudget(budget),
                  );
                },
              ),
              FutureBuilder<List<Category>>(
                future: _categories,
                builder: (context, snapshot) {
                  return ListTile(
                    leading: const Icon(Icons.label_outline),
                    title: const Text('カテゴリ'),
                    trailing: _trailing(
                      snapshot,
                      (categories) => Text('${categories.length}件'),
                    ),
                    onTap: () => _open(const CategoryListPage()),
                  );
                },
              ),
              const Divider(height: 32),
              _sectionTitle('メールの取り込み', textTheme),
              ListTile(
                leading: const Icon(Icons.mail_outline),
                title: const Text('Gmail と連携する'),
                subtitle: const Text('連携が切れたと Discord に届いたときも、ここからやり直します'),
                trailing: _linking
                    ? const SizedBox.square(
                        dimension: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.chevron_right),
                onTap: _linking ? null : _startGmailLink,
              ),
              FutureBuilder<List<ImportFailure>>(
                future: _failures,
                builder: (context, snapshot) {
                  return ListTile(
                    leading: const Icon(Icons.report_outlined),
                    title: const Text('取り込めなかったメール'),
                    trailing: _trailing(snapshot, _failureCount),
                    onTap: () => _open(const ImportFailurePage()),
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
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
      child: Text(
        title,
        style: textTheme.titleSmall?.copyWith(
          color: Theme.of(context).colorScheme.primary,
        ),
      ),
    );
  }

  /// 行の右端。値を取れたら value で作った表示と「›」を、取れていなければその状態を出す
  Widget _trailing<T>(AsyncSnapshot<T> snapshot, Widget Function(T) value) {
    final Widget shown;
    if (snapshot.connectionState != ConnectionState.done) {
      shown = const SizedBox.square(
        dimension: 16,
        child: CircularProgressIndicator(strokeWidth: 2),
      );
    } else if (snapshot.data case final data?) {
      shown = value(data);
    } else {
      shown = Text(
        '取得できません',
        style: TextStyle(color: Theme.of(context).colorScheme.error),
      );
    }
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        shown,
        const SizedBox(width: 4),
        const Icon(Icons.chevron_right),
      ],
    );
  }

  // 取り込めなかったメールは片付けるまで気づいてほしいので、1件以上なら目立たせる
  Widget _failureCount(List<ImportFailure> failures) {
    if (failures.isEmpty) return const Text('なし');
    return Badge(
      label: Text('${failures.length}件'),
      padding: const EdgeInsets.symmetric(horizontal: 8),
    );
  }

  Future<void> _open(Widget page) async {
    await Navigator.of(
      context,
    ).push(MaterialPageRoute<void>(builder: (_) => page));
    // 開いた先で追加や取り込み直しをしたかもしれないので、件数を取り直す
    _reload();
  }

  Future<void> _editBudget(Budget budget) async {
    final changed = await showDialog<bool>(
      context: context,
      builder: (context) => BudgetEditDialog(budget: budget),
    );
    if (changed != true) return;
    _showMessage('予算を変更しました');
    _reload();
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

  String _formatAmount(int amount) {
    return amount.toString().replaceAllMapped(
      RegExp(r'\B(?=(\d{3})+(?!\d))'),
      (match) => ',',
    );
  }

  void _showMessage(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  void _reload() {
    setState(() {
      _budget = BudgetService().getBudget();
      _categories = CategoryService().getCategories();
      _failures = ImportFailureService().getImportFailures();
    });
  }
}
