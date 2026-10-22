import 'package:flutter/material.dart';
import 'package:tsukena/features/import_failure/entities/import_failure.dart';
import 'package:tsukena/features/import_failure/repositories/import_failure_repository.dart';
import 'package:tsukena/features/import_failure/widgets/import_failure_list.dart';

/// 取り込めなかったメールの一覧と、取り込み直し。設定の画面から開く
class ImportFailurePage extends StatefulWidget {
  const ImportFailurePage({super.key});

  @override
  State<ImportFailurePage> createState() => _ImportFailurePageState();
}

class _ImportFailurePageState extends State<ImportFailurePage> {
  late Future<List<ImportFailure>> _failures;

  @override
  initState() {
    super.initState();
    _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('取り込めなかったメール'),
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
          child: FutureBuilder<List<ImportFailure>>(
            future: _failures,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snapshot.hasError) {
                return const Center(child: Text('取り込めなかったメールの取得に失敗しました'));
              }
              return ListView(
                padding: const EdgeInsets.symmetric(vertical: 8),
                children: [
                  ImportFailureList(
                    failures: snapshot.data ?? [],
                    onRetry: _retryImport,
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
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
      _failures = ImportFailureService().getImportFailures();
    });
  }
}
