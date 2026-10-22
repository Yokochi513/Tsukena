import 'package:flutter/material.dart';
import 'package:tsukena/features/import_failure/entities/import_failure.dart';

/// 取り込めなかったメールの一覧。画面の ListView の中に置くため、自分ではスクロールしない。
class ImportFailureList extends StatelessWidget {
  const ImportFailureList({super.key, required this.failures, this.onRetry});

  final List<ImportFailure> failures;

  /// 「取り込み直す」を押したときに呼ぶ。null ならボタンを出さない
  final ValueChanged<ImportFailure>? onRetry;

  @override
  Widget build(BuildContext context) {
    if (failures.isEmpty) {
      return const ListTile(title: Text('取り込めなかったメールはありません'));
    }

    final textTheme = Theme.of(context).textTheme;

    return Column(
      children: [
        for (final failure in failures) ...[
          ListTile(
            title: Text(failure.subject.isEmpty ? '（件名なし）' : failure.subject),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(failure.sender),
                Text(
                  '${_formatDateTime(failure.failedAt)}　${failure.reason}',
                  style: textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.error,
                  ),
                ),
                if (onRetry != null)
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton.icon(
                      onPressed: () => onRetry!(failure),
                      icon: const Icon(Icons.replay),
                      label: const Text('取り込み直す'),
                    ),
                  ),
              ],
            ),
            isThreeLine: true,
          ),
          const Divider(height: 1),
        ],
      ],
    );
  }

  String _formatDateTime(DateTime dateTime) {
    // サーバーは JST のタイムゾーン付きで返す。端末の時刻に直して表示する
    final local = dateTime.toLocal();
    final month = local.month.toString().padLeft(2, '0');
    final day = local.day.toString().padLeft(2, '0');
    final hour = local.hour.toString().padLeft(2, '0');
    final minute = local.minute.toString().padLeft(2, '0');
    return '${local.year}/$month/$day $hour:$minute';
  }
}
