import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers.dart';
import '../../theme/app_theme.dart';

class SocialMediaTab extends ConsumerStatefulWidget {
  const SocialMediaTab({super.key});

  @override
  ConsumerState<SocialMediaTab> createState() => _SocialMediaTabState();
}

class _SocialMediaTabState extends ConsumerState<SocialMediaTab> {
  final TextEditingController _urlController = TextEditingController(text: 'https://tiktok.com/@viral_example/video/12345');
  final TextEditingController _promptController = TextEditingController(text: 'A clean cinematic shot of a marketer looking at high-performing graphs, hyperrealistic.');
  
  bool _analyzing = false;
  Map<String, dynamic>? _analysisResults;
  
  bool _generating = false;
  Map<String, dynamic>? _generationResults;
  String _selectedModel = 'veo_3';

  List<dynamic> _tickets = [];
  List<dynamic> _alerts = [];
  bool _loadingTickets = false;
  bool _loadingAlerts = false;

  @override
  void initState() {
    super.initState();
    _loadSocialData();
  }

  Future<void> _loadSocialData() async {
    setState(() {
      _loadingTickets = true;
      _loadingAlerts = true;
    });
    try {
      final client = ref.read(apiClientProvider);
      final tickets = await client.getSocialTickets();
      final alerts = await client.getListeningAlerts();
      setState(() {
        _tickets = tickets;
        _alerts = alerts;
      });
    } catch (e) {
      debugPrint('Failed to load social data: $e');
    } finally {
      setState(() {
        _loadingTickets = false;
        _loadingAlerts = false;
      });
    }
  }

  Future<void> _analyzeVideo() async {
    setState(() {
      _analyzing = true;
      _analysisResults = null;
    });
    try {
      final client = ref.read(apiClientProvider);
      final res = await client.analyzeVideo(_urlController.text);
      setState(() {
        _analysisResults = res;
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      setState(() {
        _analyzing = false;
      });
    }
  }

  Future<void> _generateMedia() async {
    setState(() {
      _generating = true;
      _generationResults = null;
    });
    try {
      final client = ref.read(apiClientProvider);
      final res = await client.generateMedia(_promptController.text, _selectedModel);
      setState(() {
        _generationResults = res;
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      setState(() {
        _generating = false;
      });
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
              const Icon(Icons.trending_up, color: AppTheme.primaryColor, size: 28),
              const SizedBox(width: 12),
              Text(
                'Social Media Automation (SOTA)',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Ideación de viralidad, generación automatizada multimodelo y flujos de soporte colaborativo.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppTheme.mutedTextColor),
          ),
          const SizedBox(height: 24),
          
          // Section 1: Viral Video Deconstruction
          _buildCard(
            title: 'Ingeniería Inversa de Viralidad',
            subtitle: 'Analiza vídeos virales públicos para convertirlos en prompts estructurados (ViraFlow)',
            icon: Icons.psychology,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _urlController,
                        decoration: const InputDecoration(
                          hintText: 'Enlace del vídeo (TikTok, Reels, Shorts)',
                          prefixIcon: Icon(Icons.link),
                        ),
                      ),
                    ),
                    const SizedBox(width: 16),
                    ElevatedButton.icon(
                      onPressed: _analyzing ? null : _analyzeVideo,
                      icon: _analyzing
                          ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                          : const Icon(Icons.analytics),
                      label: const Text('Deconstruir'),
                    ),
                  ],
                ),
                if (_analysisResults != null) ...[
                  const SizedBox(height: 20),
                  const Divider(color: Color(0xFF2E364F)),
                  const SizedBox(height: 12),
                  _buildResultsField('Gancho (Hook)', _analysisResults!['hook'] ?? ''),
                  _buildResultsField('Arco Narrativo', _analysisResults!['narrative_arc'] ?? ''),
                  _buildResultsField('Tipos de Planos', (_analysisResults!['shot_types'] as List?)?.join(', ') ?? ''),
                  _buildResultsField('Ritmo de Edición', _analysisResults!['editing_pace'] ?? ''),
                  _buildResultsField('Carga Emocional', _analysisResults!['emotional_charge'] ?? ''),
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppTheme.secondaryColor.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppTheme.secondaryColor.withOpacity(0.3)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Prompt Generado:', style: TextStyle(fontWeight: FontWeight.bold, color: AppTheme.secondaryColor)),
                        const SizedBox(height: 4),
                        Text(_analysisResults!['script_prompt'] ?? ''),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
          
          const SizedBox(height: 24),

          // Section 2: Multimodel Media Generation
          _buildCard(
            title: 'Generación Automatizada Multimodelo',
            subtitle: 'Unifica suites de generación de imagen y vídeo cinematográfico en un solo panel',
            icon: Icons.video_camera_back,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Text('Modelo IA:'),
                    const SizedBox(width: 12),
                    DropdownButton<String>(
                      value: _selectedModel,
                      dropdownColor: AppTheme.surfaceColor,
                      items: const [
                        DropdownMenuItem(value: 'veo_3', child: Text('Google Veo 3 (4K Nativo)')),
                        DropdownMenuItem(value: 'sora_2', child: Text('OpenAI Sora 2')),
                        DropdownMenuItem(value: 'ideogram_v2', child: Text('Ideogram V2 (Tipografías)')),
                        DropdownMenuItem(value: 'recraft_v3', child: Text('Recraft V3 (Vectores/Logos)')),
                      ],
                      onChanged: (val) {
                        if (val != null) setState(() => _selectedModel = val);
                      },
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _promptController,
                        maxLines: 2,
                        decoration: const InputDecoration(
                          hintText: 'Ingresa el prompt detallado para el generador...',
                        ),
                      ),
                    ),
                    const SizedBox(width: 16),
                    ElevatedButton(
                      onPressed: _generating ? null : _generateMedia,
                      child: _generating
                          ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                          : const Text('Generar Activo'),
                    ),
                  ],
                ),
                if (_generationResults != null) ...[
                  const SizedBox(height: 20),
                  Container(
                    height: 200,
                    width: double.infinity,
                    decoration: BoxDecoration(
                      color: Colors.black45,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.white10),
                    ),
                    child: Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.play_circle_outline, size: 64, color: AppTheme.primaryColor),
                          const SizedBox(height: 8),
                          Text('Vista previa del activo (${_generationResults!['task_id']})'),
                          const SizedBox(height: 4),
                          Text(_generationResults!['media_url'] ?? '', style: const TextStyle(color: Colors.blue, fontSize: 12)),
                        ],
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),

          const SizedBox(height: 24),

          // Section 3: Social Support Tickets & Brand Listening
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: _buildCard(
                  title: 'Bandeja de Entrada Multicanal',
                  subtitle: 'Mensajes unificados y respuestas automáticas por IA',
                  icon: Icons.question_answer,
                  child: _loadingTickets
                      ? const Center(child: CircularProgressIndicator())
                      : _tickets.isEmpty
                          ? const Text('Sin tickets pendientes')
                          : ListView.builder(
                              shrinkWrap: true,
                              physics: const NeverScrollableScrollPhysics(),
                              itemCount: _tickets.length,
                              itemBuilder: (context, idx) {
                                final t = _tickets[idx];
                                return Card(
                                  color: Colors.black26,
                                  margin: const EdgeInsets.only(bottom: 8),
                                  child: ListTile(
                                    title: Text('${t['user']} (${t['platform']})'),
                                    subtitle: Text(t['message']),
                                    trailing: Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                      decoration: BoxDecoration(
                                        color: t['sentiment'] == 'positive'
                                            ? Colors.green.withOpacity(0.2)
                                            : Colors.orange.withOpacity(0.2),
                                        borderRadius: BorderRadius.circular(4),
                                      ),
                                      child: Text(
                                        t['sentiment'],
                                        style: TextStyle(
                                          color: t['sentiment'] == 'positive' ? Colors.green : Colors.orange,
                                          fontSize: 10,
                                        ),
                                      ),
                                    ),
                                  ),
                                );
                              },
                            ),
                ),
              ),
              const SizedBox(width: 24),
              Expanded(
                child: _buildCard(
                  title: 'Escucha Social Activa (Alertas)',
                  subtitle: 'Monitorización del sentimiento y menciones de marca',
                  icon: Icons.record_voice_over,
                  child: _loadingAlerts
                      ? const Center(child: CircularProgressIndicator())
                      : _alerts.isEmpty
                          ? const Text('Sin alertas recientes')
                          : ListView.builder(
                              shrinkWrap: true,
                              physics: const NeverScrollableScrollPhysics(),
                              itemCount: _alerts.length,
                              itemBuilder: (context, idx) {
                                final a = _alerts[idx];
                                return Card(
                                  color: Colors.black26,
                                  margin: const EdgeInsets.only(bottom: 8),
                                  child: ListTile(
                                    title: Text('${a['keyword']} - ${a['source']}'),
                                    subtitle: Text(a['excerpt']),
                                    leading: const Icon(Icons.notification_important, color: AppTheme.primaryColor),
                                  ),
                                );
                              },
                            ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildCard({
    required String title,
    required String subtitle,
    required IconData icon,
    required Widget child,
  }) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: AppTheme.primaryColor, size: 24),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                      Text(subtitle, style: const TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            child,
          ],
        ),
      ),
    );
  }

  Widget _buildResultsField(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('$label: ', style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.mutedTextColor)),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}
