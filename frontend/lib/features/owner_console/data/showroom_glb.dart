import 'dart:convert';
import 'dart:typed_data';
import 'dart:ui';

import 'package:flutter/services.dart';

class ShowroomMeshPart {
  const ShowroomMeshPart({
    required this.positions,
    required this.indices,
    required this.color,
  });

  final Float32List positions;
  final Uint32List indices;
  final Color color;
}

class ShowroomGlb {
  const ShowroomGlb({
    required this.assetPath,
    required this.byteLength,
    required this.parts,
  });

  final String assetPath;
  final int byteLength;
  final List<ShowroomMeshPart> parts;

  int get triangleCount => parts.fold(
    0,
    (int sum, ShowroomMeshPart part) => sum + part.indices.length ~/ 3,
  );

  String get fileName => assetPath.split('/').last;

  String get loadedLabel =>
      'Loaded $fileName · ${(byteLength / 1024).round()} KB · $triangleCount triangles';

  double get sourceExtent {
    double minX = double.infinity;
    double minY = double.infinity;
    double minZ = double.infinity;
    double maxX = -double.infinity;
    double maxY = -double.infinity;
    double maxZ = -double.infinity;
    for (final ShowroomMeshPart part in parts) {
      for (int i = 0; i < part.positions.length; i += 3) {
        final double x = part.positions[i];
        final double y = part.positions[i + 1];
        final double z = part.positions[i + 2];
        if (x < minX) minX = x;
        if (y < minY) minY = y;
        if (z < minZ) minZ = z;
        if (x > maxX) maxX = x;
        if (y > maxY) maxY = y;
        if (z > maxZ) maxZ = z;
      }
    }
    final double spanX = maxX - minX;
    final double spanY = maxY - minY;
    final double spanZ = maxZ - minZ;
    if (spanX >= spanY && spanX >= spanZ) return spanX;
    if (spanY >= spanZ) return spanY;
    return spanZ;
  }
}

String showroomModelPath(String category) {
  return switch (category) {
    'jet' || 'aircraft' => 'assets/showroom/aurelius_x1_private_jet.glb',
    'coach' ||
    'team_transport' => 'assets/showroom/gtex_voyager_club_coach.glb',
    'vehicle' => 'assets/showroom/velocity_r_hypercar.glb',
    'stadium' ||
    'stadium_facility' => 'assets/showroom/legacy_arena_stadium.glb',
    'campus' || 'training_academy_facility' =>
      'assets/showroom/gtex_performance_campus.glb',
    _ => 'assets/showroom/meridian_luxury_watch.glb',
  };
}

String exhibitModelPath({required String category, String? modelFile}) {
  final String file = (modelFile ?? '').trim();
  if (file.isNotEmpty) {
    return file;
  }
  return showroomModelPath(category);
}

String exhibitPreviewPath({
  required String category,
  String? previewFile,
  String? modelFile,
}) {
  final String preview = (previewFile ?? '').trim();
  if (preview.isNotEmpty) {
    return preview;
  }
  final String model = exhibitModelPath(
    category: category,
    modelFile: modelFile,
  );
  if (model.endsWith('.glb')) {
    return model.replaceFirst(RegExp(r'\.glb$'), '.png');
  }
  return model;
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
  final List<dynamic> accessors =
      json['accessors'] as List<dynamic>? ?? const <dynamic>[];
  final List<dynamic> views =
      json['bufferViews'] as List<dynamic>? ?? const <dynamic>[];
  final List<dynamic> materials =
      json['materials'] as List<dynamic>? ?? const <dynamic>[];
  final List<ShowroomMeshPart> parts = <ShowroomMeshPart>[];
  for (final dynamic mesh
      in json['meshes'] as List<dynamic>? ?? const <dynamic>[]) {
    final Map<String, dynamic> meshMap = Map<String, dynamic>.from(mesh as Map);
    for (final dynamic primitive
        in meshMap['primitives'] as List<dynamic>? ?? const <dynamic>[]) {
      final Map<String, dynamic> prim = Map<String, dynamic>.from(
        primitive as Map,
      );
      if (prim['mode'] != null && prim['mode'] != 4) {
        continue;
      }
      final Map<String, dynamic> attributes = Map<String, dynamic>.from(
        prim['attributes'] as Map? ?? const <String, dynamic>{},
      );
      if (attributes['POSITION'] == null || prim['indices'] == null) {
        continue;
      }
      final int positionIndex = attributes['POSITION'] as int;
      final int indexIndex = prim['indices'] as int;
      final Color color = _materialColor(materials, prim['material']);
      parts.add(
        ShowroomMeshPart(
          positions: _readPositions(
            bin,
            accessors[positionIndex] as Map,
            views,
          ),
          indices: _readIndices(bin, accessors[indexIndex] as Map, views),
          color: color,
        ),
      );
    }
  }
  if (parts.isEmpty) {
    throw FormatException('GLB has no triangle mesh: $assetPath');
  }
  return ShowroomGlb(
    assetPath: assetPath,
    byteLength: bytes.length,
    parts: parts,
  );
}

Float32List _readPositions(
  Uint8List bin,
  Map<dynamic, dynamic> accessor,
  List<dynamic> views,
) {
  final Map<String, dynamic> view = Map<String, dynamic>.from(
    views[accessor['bufferView'] as int] as Map,
  );
  final int start =
      (view['byteOffset'] as int? ?? 0) + (accessor['byteOffset'] as int? ?? 0);
  final int count = accessor['count'] as int;
  final Uint8List bytes = Uint8List.fromList(
    bin.sublist(start, start + count * 12),
  );
  return bytes.buffer.asFloat32List();
}

Uint32List _readIndices(
  Uint8List bin,
  Map<dynamic, dynamic> accessor,
  List<dynamic> views,
) {
  final Map<String, dynamic> view = Map<String, dynamic>.from(
    views[accessor['bufferView'] as int] as Map,
  );
  final int component = accessor['componentType'] as int;
  final int count = accessor['count'] as int;
  final int width =
      component == 5125
          ? 4
          : component == 5123
          ? 2
          : 1;
  final int start =
      (view['byteOffset'] as int? ?? 0) + (accessor['byteOffset'] as int? ?? 0);
  final Uint8List bytes = Uint8List.fromList(
    bin.sublist(start, start + count * width),
  );
  final ByteData data = ByteData.sublistView(bytes);
  final Uint32List indices = Uint32List(count);
  for (int i = 0; i < count; i++) {
    indices[i] = switch (component) {
      5125 => data.getUint32(i * 4, Endian.little),
      5123 => data.getUint16(i * 2, Endian.little),
      _ => data.getUint8(i),
    };
  }
  return indices;
}

Color _materialColor(List<dynamic> materials, Object? materialIndex) {
  const Color fallback = Color(0xFFE0B84A);
  if (materialIndex is! int ||
      materialIndex < 0 ||
      materialIndex >= materials.length) {
    return fallback;
  }
  final Map<String, dynamic> material = Map<String, dynamic>.from(
    materials[materialIndex] as Map,
  );
  final Object? pbr = material['pbrMetallicRoughness'];
  if (pbr is! Map || pbr['baseColorFactor'] is! List) {
    return fallback;
  }
  final List<dynamic> factor = pbr['baseColorFactor'] as List<dynamic>;
  double channel(int index, double fallbackValue) {
    if (index >= factor.length || factor[index] is! num) {
      return fallbackValue;
    }
    return (factor[index] as num).toDouble();
  }

  return Color.fromRGBO(
    (channel(0, 1) * 255).round().clamp(0, 255),
    (channel(1, 1) * 255).round().clamp(0, 255),
    (channel(2, 1) * 255).round().clamp(0, 255),
    channel(3, 1).clamp(0, 1),
  );
}
