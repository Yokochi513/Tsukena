import 'package:tsukena/features/transaction/entities/category.dart';

/// 1つの月の、カテゴリ1つ分の支出合計
class CategoryTotal {
  /// カテゴリが未設定（確認待ち）の記録の合計なら null
  Category? category;
  int amount;

  CategoryTotal({required this.category, required this.amount});

  factory CategoryTotal.fromJson(Map<String, dynamic> json) {
    final category = json['category'] as Map<String, dynamic>?;
    return CategoryTotal(
      category: category == null ? null : Category.fromJson(category),
      amount: json['amount'] as int,
    );
  }
}

/// 1つの月の集計。支出は支払日、収入は入金日で月を決める（→ docs/api_list.md 2.1）
class MonthlySummary {
  String month;
  int incomeTotal;
  int total;

  /// 収入合計 - 支出合計。負の数がありうる
  int balance;
  int budget;

  /// 予算 - 支出合計。予算を超えていれば負の数
  int remaining;

  /// 金額の多い順。未分類は最後
  List<CategoryTotal> byCategory;

  MonthlySummary({
    required this.month,
    required this.incomeTotal,
    required this.total,
    required this.balance,
    required this.budget,
    required this.remaining,
    required this.byCategory,
  });

  factory MonthlySummary.fromJson(Map<String, dynamic> json) {
    return MonthlySummary(
      month: json['month'] as String,
      incomeTotal: json['income_total'] as int,
      total: json['total'] as int,
      balance: json['balance'] as int,
      budget: json['budget'] as int,
      remaining: json['remaining'] as int,
      byCategory: (json['by_category'] as List<dynamic>)
          .map((item) => CategoryTotal.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}
