import 'package:flutter/material.dart';
import 'package:tsukena/features/transaction/entities/transaction.dart';

/// 支出を手短に並べるシートの中身。月の画面でカテゴリの内訳を押したときに、下から出す。
///
/// 見るためだけのもので、押しても修正は開かない。直すときは支出の一覧から開く
class TransactionBriefSheet extends StatelessWidget {
  const TransactionBriefSheet({
    super.key,
    required this.title,
    required this.transactions,
  });

  /// 見出し（「🍚 食費」など）
  final String title;

  /// 出す支出。読み込み中はシートの中でくるくるを出す
  final Future<List<Transaction>> transactions;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return ConstrainedBox(
      // 件数が多くても、画面の上のほうは見えたままにする
      constraints: BoxConstraints(
        maxHeight: MediaQuery.sizeOf(context).height * 0.7,
      ),
      child: FutureBuilder<List<Transaction>>(
        future: transactions,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Padding(
              padding: EdgeInsets.all(32),
              child: Center(child: CircularProgressIndicator()),
            );
          }
          if (snapshot.hasError) {
            return const Padding(
              padding: EdgeInsets.all(32),
              child: Center(child: Text('支出の取得に失敗しました')),
            );
          }

          final items = snapshot.data ?? [];
          final total = items.fold(0, (sum, t) => sum + t.amount);
          return Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                child: Row(
                  children: [
                    Expanded(child: Text(title, style: textTheme.titleMedium)),
                    Text(
                      '${items.length}件・¥${_formatAmount(total)}',
                      style: textTheme.titleMedium,
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              Flexible(
                child: ListView.separated(
                  shrinkWrap: true,
                  padding: const EdgeInsets.only(bottom: 16),
                  itemCount: items.length,
                  separatorBuilder: (context, index) =>
                      const Divider(height: 1, indent: 16, endIndent: 16),
                  itemBuilder: (context, index) {
                    final t = items[index];
                    return ListTile(
                      dense: true,
                      leading: Text(_formatDate(t.occurredDate)),
                      title: Text(t.merchant.isEmpty ? '(店名無し)' : t.merchant),
                      subtitle: t.memo.isEmpty ? null : Text(t.memo),
                      trailing: Text(
                        '¥${_formatAmount(t.amount)}',
                        style: textTheme.bodyLarge,
                      ),
                    );
                  },
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  String _formatDate(DateTime date) {
    final month = date.month.toString().padLeft(2, '0');
    final day = date.day.toString().padLeft(2, '0');
    return '$month/$day';
  }

  String _formatAmount(int amount) {
    return amount.toString().replaceAllMapped(
      RegExp(r'\B(?=(\d{3})+(?!\d))'),
      (match) => ',',
    );
  }
}
