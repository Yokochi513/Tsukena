import 'package:flutter/material.dart';
import 'package:tsukena/features/transaction/entities/category_input.dart';
import 'package:tsukena/features/transaction/repositories/category_repository.dart';

/// カテゴリを追加するダイアログ。追加したら true を返して閉じる。
///
/// 表示順は送らず、サーバーに末尾へ入れてもらう。削除はできないので、追加の前に確かめてもらう
class CategoryAddDialog extends StatefulWidget {
  const CategoryAddDialog({super.key});

  @override
  State<CategoryAddDialog> createState() => _CategoryAddDialogState();
}

class _CategoryAddDialogState extends State<CategoryAddDialog> {
  final fieldInput = CategoryInput();
  bool _saving = false;
  String? _error;

  bool get _canSave =>
      !_saving &&
      fieldInput.name.trim().isNotEmpty &&
      fieldInput.emoji.trim().isNotEmpty;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('カテゴリを追加'),
      content: SizedBox(
        width: 400,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextFormField(
              decoration: const InputDecoration(labelText: '名前'),
              keyboardType: TextInputType.text,
              autofocus: true,
              onChanged: (value) {
                setState(() => fieldInput.name = value);
              },
            ),
            const SizedBox(height: 16),
            TextFormField(
              decoration: const InputDecoration(
                labelText: '絵文字',
                helperText: 'Discord の返事とリアクションに使います',
              ),
              keyboardType: TextInputType.text,
              onChanged: (value) {
                setState(() => fieldInput.emoji = value);
              },
            ),
            const SizedBox(height: 16),
            Text(
              'カテゴリは追加した後に削除できません',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            if (_error case final error?) ...[
              const SizedBox(height: 8),
              Text(
                error,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
          ],
        ),
      ),
      actions: [
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            TextButton(
              onPressed: _canSave ? _save : null,
              child: const Text('追加'),
            ),
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('キャンセル'),
            ),
          ],
        ),
      ],
    );
  }

  Future<void> _save() async {
    setState(() {
      _saving = true;
      _error = null;
    });
    fieldInput
      ..name = fieldInput.name.trim()
      ..emoji = fieldInput.emoji.trim();
    try {
      await CategoryService().postCategory(fieldInput);
    } on InvalidCategoryException {
      _showError('同じ名前か絵文字のカテゴリが既にあります');
      return;
    } catch (_) {
      _showError('カテゴリの追加に失敗しました');
      return;
    }
    if (!mounted) return;
    Navigator.of(context).pop(true);
  }

  void _showError(String message) {
    if (!mounted) return;
    setState(() {
      _saving = false;
      _error = message;
    });
  }
}
