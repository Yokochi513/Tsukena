class CategoryInput {
  String name = '';
  String emoji = '';

  // 追加では省略すると末尾、変更では省略すると今の表示順のまま（→ docs/api_list.md 2.4）
  int? sortOrder;

  Map<String, dynamic> toJson() {
    return {'name': name, 'emoji': emoji, 'sort_order': ?sortOrder};
  }
}
