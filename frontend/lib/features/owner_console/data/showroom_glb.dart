import 'dart:convert';
import 'dart:math' as math;
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
    'jet' || 'aircraft' => 'assets/showroom/sovereign_900x_jet.glb',
    'coach' || 'team_transport' => 'assets/showroom/vanguard_xii_coach.glb',
    'vehicle' => 'assets/showroom/veloce_gt9_hypercar.glb',
    'stadium' ||
    'stadium_facility' => 'assets/showroom/arena_imperiale_stadium.glb',
    'campus' || 'training_academy_facility' =>
      'assets/showroom/apex_performance_campus.glb',
    _ => 'assets/showroom/chronos_tourbillon_watch.glb',
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
    return model.replaceFirst(RegExp(r'\.glb$'), '.webp');
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
  final List<ShowroomMeshPart> parts = _sceneParts(
    json,
    bin,
    accessors,
    views,
    materials,
  );
  if (parts.isEmpty) {
    throw FormatException('GLB has no triangle mesh: $assetPath');
  }
  return ShowroomGlb(
    assetPath: assetPath,
    byteLength: bytes.length,
    parts: parts,
  );
}

const List<double> _identity = <double>[
  1,
  0,
  0,
  0,
  0,
  1,
  0,
  0,
  0,
  0,
  1,
  0,
  0,
  0,
  0,
  1,
];

List<ShowroomMeshPart> _sceneParts(
  Map<String, dynamic> json,
  Uint8List bin,
  List<dynamic> accessors,
  List<dynamic> views,
  List<dynamic> materials,
) {
  final List<dynamic> meshes =
      json['meshes'] as List<dynamic>? ?? const <dynamic>[];
  final List<dynamic> nodes =
      json['nodes'] as List<dynamic>? ?? const <dynamic>[];
  final List<ShowroomMeshPart> parts = <ShowroomMeshPart>[];
  if (nodes.isEmpty) {
    for (final dynamic mesh in meshes) {
      parts.addAll(
        _meshParts(mesh, _identity, bin, accessors, views, materials),
      );
    }
    return parts;
  }
  final int sceneIndex = json['scene'] as int? ?? 0;
  final List<dynamic> scenes =
      json['scenes'] as List<dynamic>? ?? const <dynamic>[];
  final List<dynamic> roots =
      scenes.isEmpty
          ? <dynamic>[for (int i = 0; i < nodes.length; i++) i]
          : (Map<String, dynamic>.from(scenes[sceneIndex] as Map)['nodes']
                  as List<dynamic>? ??
              const <dynamic>[]);
  void walk(int index, List<double> parent) {
    final Map<String, dynamic> node = Map<String, dynamic>.from(
      nodes[index] as Map,
    );
    final List<double> world = _multiply(parent, _localMatrix(node));
    if (node['mesh'] is int) {
      parts.addAll(
        _meshParts(
          meshes[node['mesh'] as int],
          world,
          bin,
          accessors,
          views,
          materials,
        ),
      );
    }
    for (final dynamic child
        in node['children'] as List<dynamic>? ?? const <dynamic>[]) {
      walk(child as int, world);
    }
  }

  for (final dynamic root in roots) {
    walk(root as int, _identity);
  }
  return parts;
}

List<ShowroomMeshPart> _meshParts(
  dynamic mesh,
  List<double> world,
  Uint8List bin,
  List<dynamic> accessors,
  List<dynamic> views,
  List<dynamic> materials,
) {
  final Map<String, dynamic> meshMap = Map<String, dynamic>.from(mesh as Map);
  final List<ShowroomMeshPart> parts = <ShowroomMeshPart>[];
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
    parts.add(
      ShowroomMeshPart(
        positions: _transformPositions(
          _readPositions(
            bin,
            accessors[attributes['POSITION'] as int] as Map,
            views,
          ),
          world,
        ),
        indices: _readIndices(
          bin,
          accessors[prim['indices'] as int] as Map,
          views,
        ),
        color: _materialColor(materials, prim['material']),
      ),
    );
  }
  return parts;
}

List<double> _localMatrix(Map<String, dynamic> node) {
  final Object? matrix = node['matrix'];
  if (matrix is List && matrix.length == 16) {
    return <double>[
      for (final Object? value in matrix) (value as num).toDouble(),
    ];
  }
  final List<dynamic> translation =
      node['translation'] as List<dynamic>? ?? const <dynamic>[0, 0, 0];
  final List<dynamic> rotation =
      node['rotation'] as List<dynamic>? ?? const <dynamic>[0, 0, 0, 1];
  final List<dynamic> scale =
      node['scale'] as List<dynamic>? ?? const <dynamic>[1, 1, 1];
  double at(List<dynamic> values, int index, double fallback) =>
      index < values.length && values[index] is num
          ? (values[index] as num).toDouble()
          : fallback;
  final double x = at(rotation, 0, 0);
  final double y = at(rotation, 1, 0);
  final double z = at(rotation, 2, 0);
  final double w = at(rotation, 3, 1);
  final double x2 = x + x;
  final double y2 = y + y;
  final double z2 = z + z;
  final double xx = x * x2;
  final double xy = x * y2;
  final double xz = x * z2;
  final double yy = y * y2;
  final double yz = y * z2;
  final double zz = z * z2;
  final double wx = w * x2;
  final double wy = w * y2;
  final double wz = w * z2;
  final double sx = at(scale, 0, 1);
  final double sy = at(scale, 1, 1);
  final double sz = at(scale, 2, 1);
  return <double>[
    (1 - (yy + zz)) * sx,
    (xy + wz) * sx,
    (xz - wy) * sx,
    0,
    (xy - wz) * sy,
    (1 - (xx + zz)) * sy,
    (yz + wx) * sy,
    0,
    (xz + wy) * sz,
    (yz - wx) * sz,
    (1 - (xx + yy)) * sz,
    0,
    at(translation, 0, 0),
    at(translation, 1, 0),
    at(translation, 2, 0),
    1,
  ];
}

List<double> _multiply(List<double> parent, List<double> local) {
  final List<double> out = List<double>.filled(16, 0);
  for (int column = 0; column < 4; column++) {
    for (int row = 0; row < 4; row++) {
      out[column * 4 + row] =
          parent[row] * local[column * 4] +
          parent[4 + row] * local[column * 4 + 1] +
          parent[8 + row] * local[column * 4 + 2] +
          parent[12 + row] * local[column * 4 + 3];
    }
  }
  return out;
}

Float32List _transformPositions(Float32List source, List<double> world) {
  final Float32List out = Float32List(source.length);
  for (int i = 0; i < source.length; i += 3) {
    final double x = source[i];
    final double y = source[i + 1];
    final double z = source[i + 2];
    out[i] = world[0] * x + world[4] * y + world[8] * z + world[12];
    out[i + 1] = world[1] * x + world[5] * y + world[9] * z + world[13];
    out[i + 2] = world[2] * x + world[6] * y + world[10] * z + world[14];
  }
  return out;
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

  double display(int index) {
    final double linear = channel(index, 1).clamp(0, 1);
    final double srgb =
        linear <= 0.0031308
            ? linear * 12.92
            : 1.055 * math.pow(linear, 1 / 2.4) - 0.055;
    return srgb.clamp(0, 1);
  }

  return Color.fromRGBO(
    (display(0) * 255).round().clamp(0, 255),
    (display(1) * 255).round().clamp(0, 255),
    (display(2) * 255).round().clamp(0, 255),
    channel(3, 1).clamp(0, 1),
  );
}
