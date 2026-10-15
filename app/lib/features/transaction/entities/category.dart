class Category {
  int id;
  String name;
  String emoji;
  int sortOrder;

  Category({
    required this.id,
    required this.name,
    required this.emoji,
    required this.sortOrder,
  });

  factory Category.fromJson(Map<String, dynamic> json) {
    return Category(
      id: json['id'] as int,
      name: json['name'] as String,
      emoji: json['emoji'] as String,
      sortOrder: json['sort_order'] as int,
    );
  }
}
