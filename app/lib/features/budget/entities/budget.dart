/// 月の予算。全体で1つだけ持ち、月ごとには持たない（→ docs/api_list.md 2.5）
class Budget {
  int monthlyBudget;

  Budget({required this.monthlyBudget});

  factory Budget.fromJson(Map<String, dynamic> json) {
    return Budget(monthlyBudget: json['monthly_budget'] as int);
  }

  Map<String, dynamic> toJson() => {'monthly_budget': monthlyBudget};
}
