class CategoryInput {
  String name = '';
  String emoji = '';
  int sortOrder = 0;

  Map<String, dynamic> toJson() {
    return {'name': name, 'emoji': emoji, 'sort_order': sortOrder};
  }
}
