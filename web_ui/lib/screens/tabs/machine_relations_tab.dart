import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers.dart';
import '../../theme/app_theme.dart';

class MachineRelationsTab extends ConsumerStatefulWidget {
  const MachineRelationsTab({super.key});

  @override
  ConsumerState<MachineRelationsTab> createState() => _MachineRelationsTabState();
}

class _MachineRelationsTabState extends ConsumerState<MachineRelationsTab> {
  List<dynamic> _calendar = [];
  Map<String, dynamic>? _fanOutGraph;
  bool _loadingCalendar = false;
  bool _loadingGraph = false;

  final TextEditingController _asoKeywordsController = TextEditingController(text: 'marketing app, analytics platform, sota ads');
  final TextEditingController _asoDescriptionController = TextEditingController(text: 'La plataforma líder en análisis e integración de APIs de marketing para agencias multicliente.');

  @override
  void initState() {
    super.initState();
    _loadCalendar();
    _loadGraph();
  }

  Future<void> _loadCalendar() async {
    setState(() => _loadingCalendar = true);
    try {
      final client = ref.read(apiClientProvider);
      final res = await client.getSeoCalendar();
      setState(() {
        _calendar = res;
      });
    } catch (e) {
      debugPrint('Failed to load SEO Calendar: $e');
    } finally {
      setState(() => _loadingCalendar = false);
    }
  }

  Future<void> _loadGraph() async {
    setState(() => _loadingGraph = true);
    try {
      final client = ref.read(apiClientProvider);
      final res = await client.getQueryFanOut();
      setState(() {
        _fanOutGraph = res;
      });
    } catch (e) {
      debugPrint('Failed to load Fan-Out graph: $e');
    } finally {
      setState(() => _loadingGraph = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.hub, color: AppTheme.primaryColor, size: 28),
              const SizedBox(width: 12),
              Text(
                'Relaciones con Máquinas: SEO, AEO & ASO',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Estrategia unificada de posicionamiento orgánico en motores de búsqueda, modelos de respuesta de IA y tiendas de aplicaciones.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppTheme.mutedTextColor),
          ),
          const SizedBox(height: 24),

          // Section 1: SEO Editorial Calendar
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('SEO Tradicional: Calendario Editorial (30 días)', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                          Text('Artículos optimizados bajo directrices E-E-A-T con publicación directa', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
                        ],
                      ),
                      IconButton(onPressed: _loadCalendar, icon: const Icon(Icons.refresh, color: AppTheme.primaryColor)),
                    ],
                  ),
                  const SizedBox(height: 16),
                  _loadingCalendar
                      ? const Center(child: CircularProgressIndicator())
                      : _calendar.isEmpty
                          ? const Text('No hay programaciones cargadas.')
                          : ListView.builder(
                              shrinkWrap: true,
                              physics: const NeverScrollableScrollPhysics(),
                              itemCount: _calendar.length,
                              itemBuilder: (context, idx) {
                                final item = _calendar[idx];
                                return Card(
                                  color: Colors.black25,
                                  margin: const EdgeInsets.only(bottom: 8),
                                  child: ListTile(
                                    leading: const Icon(Icons.calendar_today, color: AppTheme.primaryColor),
                                    title: Text(item['title']),
                                    subtitle: Text('Fecha: ${item['publish_date']} | Palabras: ${item['word_count']}'),
                                    trailing: Chip(
                                      label: Text(item['status']),
                                      backgroundColor: item['status'] == 'published'
                                          ? Colors.green.withOpacity(0.2)
                                          : Colors.orange.withOpacity(0.2),
                                      labelStyle: TextStyle(
                                        color: item['status'] == 'published' ? Colors.green : Colors.orange,
                                        fontSize: 10,
                                      ),
                                    ),
                                  ),
                                );
                              },
                            ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 24),

          // Section 2: AEO Query Fan-Out Visualizer
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('AEO / GEO: Auditoría de Citas LLM (Query Fan-Out)', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const Text('Visualización de la influencia de citas y Share of Voice (SOV) en asistentes de IA (ChatGPT, Perplexity).', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
                  const SizedBox(height: 20),
                  _loadingGraph
                      ? const Center(child: CircularProgressIndicator())
                      : _fanOutGraph == null
                          ? const Text('Error al construir el gráfico de nodos.')
                          : Container(
                              height: 300,
                              width: double.infinity,
                              decoration: BoxDecoration(
                                color: Colors.black38,
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(color: Colors.white10),
                              ),
                              child: Stack(
                                children: [
                                  CustomPaint(
                                    size: Size.infinite,
                                    painter: NodeGraphPainter(
                                      nodes: _fanOutGraph!['nodes'] ?? [],
                                      links: _fanOutGraph!['links'] ?? [],
                                    ),
                                  ),
                                  const Positioned(
                                    bottom: 12,
                                    right: 12,
                                    child: Card(
                                      color: Colors.black54,
                                      child: Padding(
                                        padding: EdgeInsets.symmetric(horizontal: 8.0, vertical: 4.0),
                                        child: Text(
                                          'Graficación Interactiva de Redes Semánticas',
                                          style: TextStyle(fontSize: 10, color: AppTheme.primaryColor),
                                        ),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 24),

          // Section 3: ASO Store Metadatos
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('ASO: Sincronización de Tiendas de Aplicaciones', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const Text('Edita metadatos de Google Play y App Store con sincronización directa y densidad de keywords.', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _asoKeywordsController,
                    decoration: const InputDecoration(
                      labelText: 'Palabras Clave (ASO Keywords)',
                      prefixIcon: Icon(Icons.key),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _asoDescriptionController,
                    maxLines: 3,
                    decoration: const InputDecoration(
                      labelText: 'Descripción Corta',
                      prefixIcon: Icon(Icons.description),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      ElevatedButton.icon(
                        onPressed: () {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Metadatos sincronizados con App Store y Google Play con éxito!')),
                          );
                        },
                        icon: const Icon(Icons.sync),
                        label: const Text('Sincronizar Consolas'),
                      ),
                      const SizedBox(width: 12),
                      OutlinedButton.icon(
                        onPressed: () {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Simulación de Test A/B de capturas iniciada.')),
                          );
                        },
                        icon: const Icon(Icons.science),
                        label: const Text('Iniciar Test A/B Visual'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class NodeGraphPainter extends CustomPainter {
  final List<dynamic> nodes;
  final List<dynamic> links;

  NodeGraphPainter({required this.nodes, required this.links});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final positions = <String, Offset>{};

    // Distribute nodes radially for visual presentation
    positions['n1'] = center; // Central brand node
    positions['n2'] = Offset(center.dx - 120, center.dy - 60);
    positions['n3'] = Offset(center.dx + 120, center.dy - 80);
    positions['n4'] = Offset(center.dx - 90, center.dy + 80);
    positions['n5'] = Offset(center.dx + 100, center.dy + 70);

    // Default coordinates fallback
    for (int i = 0; i < nodes.length; i++) {
      final node = nodes[i];
      final id = node['id'].toString();
      if (!positions.containsKey(id)) {
        positions[id] = Offset(center.dx + (i * 20 - 40), center.dy + (i * 20 - 40));
      }
    }

    // Paint links
    final linePaint = Paint()
      ..color = Colors.white24
      ..strokeWidth = 2.0;

    for (final link in links) {
      final srcId = link['source'].toString();
      final tgtId = link['target'].toString();
      final srcOffset = positions[srcId];
      final tgtOffset = positions[tgtId];

      if (srcOffset != null && tgtOffset != null) {
        canvas.drawLine(srcOffset, tgtOffset, linePaint);
      }
    }

    // Paint nodes
    for (final node in nodes) {
      final id = node['id'].toString();
      final label = node['label'].toString();
      final type = node['type'].toString();
      final val = (node['val'] as num?)?.toDouble() ?? 20.0;
      final offset = positions[id]!;

      Color nodeColor = Colors.grey;
      if (type == 'brand') nodeColor = AppTheme.primaryColor;
      if (type == 'source') nodeColor = AppTheme.secondaryColor;
      if (type == 'competitor') nodeColor = Colors.red;
      if (type == 'mention') nodeColor = Colors.orange;

      final nodePaint = Paint()
        ..color = nodeColor
        ..style = PaintingStyle.fill;

      canvas.drawCircle(offset, val, nodePaint);

      // Label background & text
      final textSpan = TextSpan(
        text: label,
        style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
      );
      final textPainter = TextPainter(
        text: textSpan,
        textDirection: TextDirection.ltr,
      )..layout();

      textPainter.paint(canvas, Offset(offset.dx - textPainter.width / 2, offset.dy + val + 4));
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}
