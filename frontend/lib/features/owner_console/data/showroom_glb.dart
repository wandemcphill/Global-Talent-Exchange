import 'dart:convert';
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:flutter/services.dart';

class ShowroomGlb {
  const ShowroomGlb({
    required this.assetPath,
    required this.byteLength,
    required this.positions,
    required this.indices,
    required this.displayPositions,
    required this.displayIndices,
  });

  final String assetPath;
  final int byteLength;
  final Float32List positions;
  final Uint16List indices;
  final Float32List displayPositions;
  final Uint32List displayIndices;

  int get triangleCount => indices.length ~/ 3;

  String get fileName => assetPath.split('/').last;

  String get loadedLabel =>
      'Loaded $fileName · ${(byteLength / 1024).round()} KB · $triangleCount triangles';
}

String showroomModelPath(String category) {
  return switch (category) {
    'jet' => 'assets/showroom/harbour_jet.glb',
    'coach' => 'assets/showroom/lagoon_coach.glb',
    _ => 'assets/showroom/icon_watch.glb',
  };
}

String exhibitModelPath({required String category, String? modelFile}) {
  final String file = (modelFile ?? '').trim();
  if (file.isNotEmpty) {
    return file;
  }
  return showroomModelPath(category);
}

Future<ShowroomGlb> loadShowroomGlb(String assetPath) async {
  final ByteData data = await rootBundle.load(assetPath);
  final Uint8List bytes = data.buffer.asUint8List(
    data.offsetInBytes,
    data.lengthInBytes,
  );
  if (bytes.length < 20) {
    throw FormatException('GLB too small: $assetPath');
  }
  final ByteData view = ByteData.sublistView(bytes);
  final int magic = view.getUint32(0, Endian.little);
  if (magic != 0x46546C67) {
    throw FormatException('Not a GLB file: $assetPath');
  }
  final int declared = view.getUint32(8, Endian.little);
  if (declared != bytes.length) {
    throw FormatException('GLB length mismatch for $assetPath');
  }
  int offset = 12;
  Map<String, dynamic>? json;
  Uint8List? bin;
  while (offset + 8 <= bytes.length) {
    final int chunkLength = view.getUint32(offset, Endian.little);
    final int chunkType = view.getUint32(offset + 4, Endian.little);
    final int start = offset + 8;
    final Uint8List chunk = bytes.sublist(start, start + chunkLength);
    if (chunkType == 0x4E4F534A) {
      json = jsonDecode(utf8.decode(chunk).trim()) as Map<String, dynamic>;
    } else if (chunkType == 0x004E4942) {
      bin = chunk;
    }
    offset = start + chunkLength;
  }
  if (json == null || bin == null) {
    throw FormatException('GLB is missing JSON or BIN: $assetPath');
  }
  final List<dynamic> accessors = json['accessors'] as List<dynamic>;
  final List<dynamic> views = json['bufferViews'] as List<dynamic>;
  final Map<String, dynamic> position = Map<String, dynamic>.from(
    accessors[0] as Map,
  );
  final Map<String, dynamic> index = Map<String, dynamic>.from(
    accessors[1] as Map,
  );
  final Map<String, dynamic> positionView = Map<String, dynamic>.from(
    views[position['bufferView'] as int] as Map,
  );
  final Map<String, dynamic> indexView = Map<String, dynamic>.from(
    views[index['bufferView'] as int] as Map,
  );
  final int posStart = positionView['byteOffset'] as int? ?? 0;
  final int posBytes = (position['count'] as int) * 12;
  final int idxStart = indexView['byteOffset'] as int? ?? 0;
  final int idxCount = index['count'] as int;
  final Uint8List positionBytes = Uint8List.fromList(
    bin.sublist(posStart, posStart + posBytes),
  );
  final Uint8List indexBytes = Uint8List.fromList(
    bin.sublist(idxStart, idxStart + idxCount * 2),
  );
  final Float32List positions = positionBytes.buffer.asFloat32List();
  final Uint16List indices = indexBytes.buffer.asUint16List();
  final ({Float32List positions, Uint32List indices}) display = _displayMesh(
    positions,
    indices,
  );
  return ShowroomGlb(
    assetPath: assetPath,
    byteLength: bytes.length,
    positions: positions,
    indices: indices,
    displayPositions: display.positions,
    displayIndices: display.indices,
  );
}

/// Collapse the loaded mesh onto a coarse grid so the preview fills the shape.
({Float32List positions, Uint32List indices}) _displayMesh(
  Float32List source,
  Uint16List indices,
) {
  const int divisions = 42;
  if (source.length < 3 || indices.length < 3) {
    return (positions: source, indices: Uint32List(0));
  }
  double minX = double.infinity;
  double minY = double.infinity;
  double minZ = double.infinity;
  double maxX = -double.infinity;
  double maxY = -double.infinity;
  double maxZ = -double.infinity;
  for (int i = 0; i < source.length; i += 3) {
    minX = math.min(minX, source[i]);
    minY = math.min(minY, source[i + 1]);
    minZ = math.min(minZ, source[i + 2]);
    maxX = math.max(maxX, source[i]);
    maxY = math.max(maxY, source[i + 1]);
    maxZ = math.max(maxZ, source[i + 2]);
  }
  final double span = math.max(maxX - minX, math.max(maxY - minY, maxZ - minZ));
  final double extent = span == 0 ? 1 : span;
  final Map<int, int> corners = <int, int>{};
  final List<double> verts = <double>[];
  int corner(int vertex) {
    final double x = source[vertex * 3];
    final double y = source[vertex * 3 + 1];
    final double z = source[vertex * 3 + 2];
    final int ix = ((x - minX) / extent * (divisions - 1)).floor().clamp(
      0,
      divisions - 1,
    );
    final int iy = ((y - minY) / extent * (divisions - 1)).floor().clamp(
      0,
      divisions - 1,
    );
    final int iz = ((z - minZ) / extent * (divisions - 1)).floor().clamp(
      0,
      divisions - 1,
    );
    final int key = ix + divisions * (iy + divisions * iz);
    final int? existing = corners[key];
    if (existing != null) {
      return existing;
    }
    final int id = verts.length ~/ 3;
    corners[key] = id;
    verts
      ..add(x)
      ..add(y)
      ..add(z);
    return id;
  }

  final Set<(int, int, int)> seen = <(int, int, int)>{};
  final List<int> out = <int>[];
  for (int triangle = 0; triangle < indices.length; triangle += 3) {
    final int a = corner(indices[triangle]);
    final int b = corner(indices[triangle + 1]);
    final int c = corner(indices[triangle + 2]);
    if (a == b || b == c || a == c) {
      continue;
    }
    int x = a;
    int y = b;
    int z = c;
    if (x > y) {
      final int swap = x;
      x = y;
      y = swap;
    }
    if (y > z) {
      final int swap = y;
      y = z;
      z = swap;
    }
    if (x > y) {
      final int swap = x;
      x = y;
      y = swap;
    }
    if (!seen.add((x, y, z))) {
      continue;
    }
    out
      ..add(a)
      ..add(b)
      ..add(c);
  }
  return (
    positions: Float32List.fromList(verts),
    indices: Uint32List.fromList(out),
  );
}
