import 'package:flutter/foundation.dart'; // Nutné pro kIsWeb

class ApiUrls {
  // Pokud jsme na webu, použij 127.0.0.1. Pokud na Androidu, použij 10.0.2.2.
  static const String baseUrl = kIsWeb 
      ? 'http://127.0.0.1:8000' 
      : 'http://10.0.2.2:8000';

  static String get notes => '$baseUrl/notes/';
  static String noteDetail(int id) => '$baseUrl/notes/$id/';
}