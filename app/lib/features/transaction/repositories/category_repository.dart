import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:tsukena/features/transaction/entities/category.dart';
import 'package:tsukena/features/transaction/entities/category_input.dart';

class CategoryService {
  CategoryService({required this.baseUrl});

  final String baseUrl;

  Future<List<Category>> getCategories() async {
    final response = await http.get(Uri.parse('$baseUrl/categories'));

    if (response.statusCode != 200) {
      throw Exception('カテゴリの取得に失敗しました');
    }

    final items = jsonDecode(response.body) as List<dynamic>;

    return items
        .map((item) => Category.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<Category> postCategory(CategoryInput categoryInput) async {
    final response = await http.post(
      Uri.parse('$baseUrl/categories'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(categoryInput.toJson()),
    );

    if (response.statusCode != 201) {
      throw Exception('カテゴリの登録に失敗しました');
    }

    return Category.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  Future<Category> patchCategory(
    int categoryId,
    CategoryInput categoryInput,
  ) async {
    final response = await http.patch(
      Uri.parse('$baseUrl/categories/$categoryId'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(categoryInput.toJson()),
    );

    if (response.statusCode != 200) {
      throw Exception('カテゴリの修正に失敗しました');
    }

    return Category.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }
}
