import 'package:flutter/material.dart';
import 'package:tsukena/features/transaction/entities/category.dart';
import 'package:tsukena/features/transaction/repositories/category_repository.dart';
import 'package:tsukena/features/transaction/widgets/category_add_dialog.dart';

// TODO: カテゴリの名前・絵文字・表示順の変更を足す（→ docs/design.md 5.1）
/// カテゴリの一覧と追加。設定の画面から開く
class CategoryListPage extends StatefulWidget {
  const CategoryListPage({super.key});

  @override
  State<CategoryListPage> createState() => _CategoryListPageState();
}

class _CategoryListPageState extends State<CategoryListPage> {
  late Future<List<Category>> _categories;

  @override
  initState() {
    super.initState();
    _reload();
  }

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Scaffold(
      appBar: AppBar(title: const Text('カテゴリ')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _addCategory,
        icon: const Icon(Icons.add),
        label: const Text('カテゴリを追加'),
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 600),
          child: FutureBuilder<List<Category>>(
            future: _categories,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snapshot.hasError) {
                return const Center(child: Text('カテゴリの取得に失敗しました'));
              }
              final categories = snapshot.data ?? <Category>[];
              return ListView(
                // 追加のボタンに最後の行が隠れないよう、下に余白を取る
                padding: const EdgeInsets.only(top: 8, bottom: 88),
                children: [
                  for (final category in categories)
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
        ),
      ),
    );
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

  void _showMessage(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  void _reload() {
    setState(() {
      _categories = CategoryService().getCategories();
    });
  }
}
