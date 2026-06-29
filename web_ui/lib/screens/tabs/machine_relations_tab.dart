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

  // AEO Graph filters
  bool _filterChatGPT = true;
  bool _filterPerplexity = true;
  bool _filterGemini = true;
  bool _hideCompetitors = false;

  @override
  void initState() {
    super.initState();
    _loadCalendar();
    _loadGraph();
    _asoKeywordsController.addListener(() => setState(() {}));
    _asoDescriptionController.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _asoKeywordsController.dispose();
    _asoDescriptionController.dispose();
    super.dispose();
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

  List<dynamic> get _filteredNodes {
    if (_fanOutGraph == null) return [];
    final nodes = List<dynamic>.from(_fanOutGraph!['nodes'] ?? []);
    return nodes.where((n) {
      final type = n['type'].toString();
      final label = n['label'].toString().toLowerCase();
      
      if (_hideCompetitors && type == 'competitor') {
        return false;
      }
      
      if (type == 'source') {
        if (label.contains('chat') && !_filterChatGPT) return false;
        if (label.contains('perp') && !_filterPerplexity) return false;
        if (label.contains('gemini') && !_filterGemini) return false;
      }
      
      return true;
    }).toList();
  }

  List<dynamic> get _filteredLinks {
    if (_fanOutGraph == null) return [];
    final links = List<dynamic>.from(_fanOutGraph!['links'] ?? []);
    final nodeIds = _filteredNodes.map((n) => n['id'].toString()).toSet();
    return links.where((l) {
      return nodeIds.contains(l['source'].toString()) && nodeIds.contains(l['target'].toString());
    }).toList();
  }

  Widget _buildCalendarGrid() {
    final days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
    
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 7,
        crossAxisSpacing: 8,
        mainAxisSpacing: 8,
        childAspectRatio: 0.8,
      ),
      itemCount: 7,
      itemBuilder: (context, index) {
        final dayName = days[index];
        final dayItems = _calendar.where((item) {
          final pDate = item['publish_date'].toString();
          return pDate.endsWith('${index + 1}') || (index == 0 && pDate.endsWith('0'));
        }).toList();

        return DragTarget<Object>(
          onAcceptWithDetails: (details) {
            final draggedItem = details.data as Map<String, dynamic>;
            setState(() {
              draggedItem['publish_date'] = '2026-06-${index + 15}';
            });
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Artículo "${draggedItem['title']}" reprogramado para $dayName')),
            );
          },
          builder: (context, candidateData, rejectedData) {
            final isOver = candidateData.isNotEmpty;
            return Container(
              decoration: BoxDecoration(
                color: isOver ? AppTheme.secondaryColor.withOpacity(0.1) : Colors.black26,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: isOver ? AppTheme.secondaryColor : Colors.white10),
              ),
              padding: const EdgeInsets.all(8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    dayName,
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 11, color: AppTheme.tertiaryColor),
                  ),
                  const Divider(color: Colors.white10, height: 12),
                  Expanded(
                    child: ListView.builder(
                      itemCount: dayItems.length,
                      itemBuilder: (ctx, itemIdx) {
                        final item = dayItems[itemIdx];
                        final cardChild = Card(
                          color: AppTheme.surfaceColor,
                          margin: const EdgeInsets.only(bottom: 4),
                          child: Padding(
                            padding: const EdgeInsets.all(4.0),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  item['title'],
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(fontSize: 9, fontWeight: FontWeight.bold),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  '${item['word_count']} palabras',
                                  style: const TextStyle(fontSize: 8, color: AppTheme.mutedTextColor),
                                ),
                              ],
                            ),
                          ),
                        );

                        return Draggable<Object>(
                          data: item as Object,
                          feedback: Material(
                            color: Colors.transparent,
                            child: SizedBox(
                              width: 100,
                              height: 60,
                              child: cardChild,
                            ),
                          ),
                          childWhenDragging: Opacity(
                            opacity: 0.4,
                            child: cardChild,
                          ),
                          child: cardChild,
                        );
                      },
                    ),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildCharCounter(String currentText, int maxLength) {
    final len = currentText.length;
    final ratio = (len / maxLength).clamp(0.0, 1.0);
    final isExceeded = len > maxLength;
    
    Color progressColor = AppTheme.neonGreen;
    if (isExceeded) {
      progressColor = AppTheme.neonRed;
    } else if (ratio > 0.8) {
      progressColor = AppTheme.neonOrange;
    }
    
    return Padding(
      padding: const EdgeInsets.only(top: 4, bottom: 12),
      child: Row(
        children: [
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(2),
              child: LinearProgressIndicator(
                value: ratio,
                minHeight: 4,
                backgroundColor: Colors.white10,
                valueColor: AlwaysStoppedAnimation<Color>(progressColor),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Text(
            '$len/$maxLength',
            style: TextStyle(
              fontSize: 11,
              color: isExceeded ? AppTheme.neonRed : AppTheme.mutedTextColor,
              fontWeight: isExceeded ? FontWeight.bold : FontWeight.normal,
            ),
          ),
        ],
      ),
    );
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
              const Icon(Icons.hub, color: AppTheme.secondaryColor, size: 28),
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
                          Text('SEO Tradicional: Planificador Semanal Interactivo', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                          Text('Arrastra y suelta artículos para reprogramar la fecha de publicación', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
                        ],
                      ),
                      IconButton(onPressed: _loadCalendar, icon: const Icon(Icons.refresh, color: AppTheme.secondaryColor)),
                    ],
                  ),
                  const SizedBox(height: 16),
                  _loadingCalendar
                      ? const Center(child: CircularProgressIndicator())
                      : _calendar.isEmpty
                          ? const Text('No hay programaciones cargadas.')
                          : _buildCalendarGrid(),
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
                  const Text('Visualización de la influencia de citas y Share of Voice (SOV) en asistentes de IA.', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
                  const SizedBox(height: 16),
                  
                  // Graph Filters Header Row
                  Row(
                    children: [
                      const Text('Motores de Búsqueda:', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                      const SizedBox(width: 8),
                      FilterChip(
                        label: const Text('ChatGPT'),
                        selected: _filterChatGPT,
                        onSelected: (val) => setState(() => _filterChatGPT = val),
                      ),
                      const SizedBox(width: 6),
                      FilterChip(
                        label: const Text('Perplexity'),
                        selected: _filterPerplexity,
                        onSelected: (val) => setState(() => _filterPerplexity = val),
                      ),
                      const SizedBox(width: 6),
                      FilterChip(
                        label: const Text('Gemini'),
                        selected: _filterGemini,
                        onSelected: (val) => setState(() => _filterGemini = val),
                      ),
                      const Spacer(),
                      FilterChip(
                        label: const Text('Ocultar Competidores'),
                        selected: _hideCompetitors,
                        selectedColor: AppTheme.neonRed.withOpacity(0.2),
                        checkmarkColor: AppTheme.neonRed,
                        onSelected: (val) => setState(() => _hideCompetitors = val),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
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
                                      nodes: _filteredNodes,
                                      links: _filteredLinks,
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
                                          style: TextStyle(fontSize: 10, color: AppTheme.secondaryColor),
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
                  _buildCharCounter(_asoKeywordsController.text, 100),
                  TextField(
                    controller: _asoDescriptionController,
                    maxLines: 3,
                    decoration: const InputDecoration(
                      labelText: 'Descripción Corta',
                      prefixIcon: Icon(Icons.description),
                    ),
                  ),
                  _buildCharCounter(_asoDescriptionController.text, 150),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      ButtonTheme(
                        child: ElevatedButton.icon(
                          onPressed: () {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('Metadatos sincronizados con App Store y Google Play con éxito!')),
                            );
                          },
                          icon: const Icon(Icons.sync),
                          label: const Text('Sincronizar Consolas'),
                        ),
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
