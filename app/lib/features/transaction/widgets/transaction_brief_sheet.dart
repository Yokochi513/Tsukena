import 'package:flutter/material.dart';
import 'package:tsukena/features/transaction/entities/transaction.dart';
import 'package:tsukena/features/transaction/widgets/transaction_quick_edit_dialog.dart';

/// 支出を手短に並べるシートの中身。月の画面でカテゴリの内訳を押したときに、下から出す。
///
/// 行を押すと支払日とメモを直せる。金額やカテゴリなど、ほかの項目を直すときは支出の一覧から開く
class TransactionBriefSheet extends StatefulWidget {
  const TransactionBriefSheet({
    super.key,
    required this.title,
    required this.month,
    required this.transactions,
    this.onPaidDateChanged,
  });

  /// 見出し（「🍚 食費」など）
  final String title;

  /// 出す支出。読み込み中はシートの中でくるくるを出す
  final Future<List<Transaction>> transactions;

  /// 出している支出の、支払日の月の初日。支払日を別の月に移した支出は、シートから外す
  final DateTime month;

  /// 支払日を直したときに呼ぶ。月の集計が変わるので、呼んだ側で取り直す
  final VoidCallback? onPaidDateChanged;

  @override
  State<TransactionBriefSheet> createState() => _TransactionBriefSheetState();
}

class _TransactionBriefSheetState extends State<TransactionBriefSheet> {
  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return ConstrainedBox(
      // 件数が多くても、画面の上のほうは見えたままにする
      constraints: BoxConstraints(
        maxHeight: MediaQuery.sizeOf(context).height * 0.7,
      ),
      child: FutureBuilder<List<Transaction>>(
        future: widget.transactions,
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
          // 月の集計と同じく、分割などはその月の引き落とし額で数える
          final total = items.fold(
            0,
            (sum, t) => sum + t.amountIn(widget.month),
          );
          return Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(widget.title, style: textTheme.titleMedium),
                    ),
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
                    // 月は支払日で数えるので、左にはこの月の引き落とし日を出す。カードなどで利用日が違えば添える
                    final paid = t.chargesIn(widget.month).first.paidDate;
                    final occurred = DateUtils.isSameDay(t.occurredDate, paid)
                        ? null
                        : '利用 ${_formatDate(t.occurredDate)}';
                    final subtitle = [
                      ?occurred,
                      ?t.planLabelIn(widget.month),
                      if (t.memo.isNotEmpty) t.memo,
                    ].join('\n');
                    return ListTile(
                      dense: true,
                      onTap: () => _edit(items, index),
                      leading: Text(_formatDate(paid)),
                      title: Text(t.merchant.isEmpty ? '(店名無し)' : t.merchant),
                      subtitle: subtitle.isEmpty ? null : Text(subtitle),
                      trailing: Text(
                        '¥${_formatAmount(t.amountIn(widget.month))}',
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

  // 直したら、取り直さずにその行だけ差し替える。支払日を別の月に移したときは、この月の明細ではなくなるので外す
  Future<void> _edit(List<Transaction> items, int index) async {
    final original = items[index];
    final updated = await showDialog<Transaction>(
      context: context,
      builder: (_) => TransactionQuickEditDialog(transaction: original),
    );
    if (updated == null || !mounted) return;

    // 分割などは、この月に引き落としの回が残っているかで決める
    final stillInMonth = updated.chargesIn(widget.month).isNotEmpty;
    setState(() {
      if (stillInMonth) {
        items[index] = updated;
      } else {
        items.removeAt(index);
      }
    });
    if (!DateUtils.isSameDay(updated.paidDate, original.paidDate)) {
      widget.onPaidDateChanged?.call();
    }
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
