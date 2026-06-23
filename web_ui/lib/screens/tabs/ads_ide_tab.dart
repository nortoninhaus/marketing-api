import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:math';
import '../../core/providers.dart';
import '../../theme/app_theme.dart';

class AdsIdeTab extends ConsumerStatefulWidget {
  const AdsIdeTab({super.key});

  @override
  ConsumerState<AdsIdeTab> createState() => _AdsIdeTabState();
}

class _AdsIdeTabState extends ConsumerState<AdsIdeTab> {
  final TextEditingController _promptController = TextEditingController(text: 'Reasignar presupuesto de campañas Meta con ROAS < 1.5 hacia Google Ads');
  List<dynamic> _proposals = [];
  bool _loading = false;
  int _currentStep = 0;
  
  // Terminal logs state
  bool _terminalExpanded = true;
  final List<String> _terminalLogs = [];

  // AdButler inspired variables
  String _selectedAdZone = 'leaderboard_top';
  double _targetClicks = 25000;
  double _targetCtr = 2.4; // %
  double _dailyBudgetCap = 450; // $

  // Sub-tab Navigation
  int _subTabIndex = 0; // 0 = Capital Governance, 1 = Tag Simulator, 2 = Native Template Editor

  // Tag Simulator Variables
  bool _isBatchedRequest = false;
  String _sessionPid = '849201';
  int _placeCounter = 0;
  bool _pixelFired = false;
  bool _renderRichMedia = false;
  
  final TextEditingController _ipController = TextEditingController(text: '190.156.45.12');
  final TextEditingController _uaController = TextEditingController(
    text: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  );

  String _apiSimRequestJson = '';
  String _apiSimResponseJson = '';
  final List<String> _apiSimLogs = [];

  // Native Template Variables (Variables 41, 42, 43)
  final TextEditingController _nativeNameController = TextEditingController(text: 'Anuncio de Marca del Cliente A');
  final TextEditingController _var41Controller = TextEditingController(text: 'Compra las mejores zapatillas running aquí');
  final TextEditingController _var42Controller = TextEditingController(text: 'https://clientea.com/running');
  final TextEditingController _var43Controller = TextEditingController(text: 'https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/6a18c4e6f58810f313b89b59.png');

  @override
  void initState() {
    super.initState();
    _loadProposals();
    _randomizePid();
    _simulateAdserve();
  }

  void _addLog(String msg) {
    if (!mounted) return;
    setState(() {
      final timeStr = DateTime.now().toIso8601String().substring(11, 19);
      _terminalLogs.add('[$timeStr] $msg');
    });
  }

  void _randomizePid() {
    setState(() {
      _sessionPid = (100000 + Random().nextInt(899999)).toString();
      _placeCounter = 0;
      _pixelFired = false;
      _apiSimLogs.add('[SESSION] Generado nuevo Page Session ID: pid=$_sessionPid. Contador place reiniciado.');
    });
  }

  Future<void> _loadProposals() async {
    setState(() {
      _loading = true;
      _terminalLogs.clear();
    });
    _addLog('Iniciando compilación de optimización conversacional...');
    _addLog('Prompt: "${_promptController.text}"');
    
    try {
      final client = ref.read(apiClientProvider);
      final res = await client.getCampaignProposals();
      
      // Inject zone properties for interactive demo
      final mapped = List<Map<String, dynamic>>.from(res.map((item) => Map<String, dynamic>.from(item)));
      for (int i = 0; i < mapped.length; i++) {
        mapped[i]['zone'] = i % 2 == 0 ? 'leaderboard_top' : 'sidebar_rectangle';
      }

      await Future.delayed(const Duration(milliseconds: 300));
      _addLog('Consultando propuestas vigentes en base de datos de campañas...');
      await Future.delayed(const Duration(milliseconds: 350));
      _addLog('Mapeando zonas AdButler para leaderboard_top y sidebar_rectangle...');
      
      setState(() {
        _proposals = mapped;
        _currentStep = 0; // Draft
      });
      _addLog('Compilación exitosa. ${mapped.length} propuestas generadas en Borrador.');
    } catch (e) {
      _addLog('ERROR de compilación: $e');
      debugPrint('Failed to load proposals: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _processProposal(String id, bool approved) async {
    _addLog('Enviando instrucción de ${approved ? 'APROBACIÓN' : 'RECHAZO'} para campaña $id...');
    try {
      final client = ref.read(apiClientProvider);
      final res = await client.confirmProposal(id, approved);
      _addLog('Respuesta API para campaña $id: ${res['detail']}');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Acción confirmada: ${res['detail']}')),
      );
      _loadProposals();
    } catch (e) {
      _addLog('ERROR de API en campaña $id: $e');
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    }
  }

  void _simulateAdserve() {
    final ip = _ipController.text;
    final ua = _uaController.text;
    
    // Fallback safe values if MediaQuery is not ready in initState
    double swVal = 1920;
    double shVal = 1080;
    double sprVal = 2.0;
    if (mounted) {
      final mediaQuery = MediaQuery.of(context);
      swVal = mediaQuery.size.width;
      shVal = mediaQuery.size.height;
      sprVal = mediaQuery.devicePixelRatio;
    }

    final sw = swVal.toInt();
    final sh = shVal.toInt();
    final spr = sprVal;
    
    setState(() {
      _pixelFired = false;
    });

    if (_isBatchedRequest) {
      // Batched request simulation
      _apiSimRequestJson = '''{
  "ID": "167283",
  "zoneIDs": [212491, 212492],
  "ads": "one",
  "kw": ["running", "deportes"],
  "click_mode": "callback",
  "_abdk_json": { "membership_tier": "gold" },
  "visitor_meta": {
    "ip": "$ip",
    "ua": "$ua",
    "sw": $sw,
    "sh": $sh,
    "spr": $spr
  }
}''';
      
      _apiSimResponseJson = '''{
  "status": "SUCCESS",
  "placements": {
    "placement_212491": {
      "banner_id": 1016336,
      "width": 300,
      "height": 250,
      "image_url": "https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/6a18c4e6f58810f313b89b59.png",
      "redirect_url": "https://servedbyadbutler.com/click;ID=167283;bannerID=1016336",
      "accupixel_url": "https://servedbyadbutler.com/accupixel;ID=167283;bannerID=1016336",
      "alt_text": "Anuncio Batched 1",
      "body": null
    },
    "placement_212492": {
      "banner_id": 1016337,
      "width": 728,
      "height": 90,
      "image_url": "https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/6a18c4e6f58810f313b89b59.png",
      "redirect_url": "https://servedbyadbutler.com/click;ID=167283;bannerID=1016337",
      "accupixel_url": "https://servedbyadbutler.com/accupixel;ID=167283;bannerID=1016337",
      "alt_text": "Anuncio Batched 2",
      "body": null
    }
  }
}''';
      
      setState(() {
        _apiSimLogs.add('[API POST] Solicitud agrupada enviada a /adserve/multi para zonas [212491, 212492]');
        _apiSimLogs.add('[API RESPONSE] Servidor de AdButler respondió con 2 placements activos.');
        _pixelFired = true;
        _apiSimLogs.add('[DOM] Inyectados píxeles accupixel de impresión para banner 1016336 y 1016337.');
      });
    } else {
      // Single request with unique placement parameters
      final currentPlace = _placeCounter;
      _apiSimRequestJson = '''{
  "ID": 171230,
  "size": "300x250",
  "setID": 373469,
  "type": "json",
  "pid": "$_sessionPid",
  "place": $currentPlace,
  "visitor_meta": {
    "ip": "$ip",
    "ua": "$ua",
    "sw": $sw,
    "sh": $sh,
    "spr": $spr
  }
}''';
      
      if (_renderRichMedia) {
        _apiSimResponseJson = '''{
  "status": "SUCCESS",
  "placements": {
    "placement_1": {
      "banner_id": 1016338,
      "width": 300,
      "height": 250,
      "image_url": null,
      "redirect_url": "https://servedbyadbutler.com/click;ID=171230;bannerID=1016338",
      "accupixel_url": "https://servedbyadbutler.com/accupixel;ID=171230;bannerID=1016338",
      "alt_text": "Inhaus Rich Media",
      "body": "<div style='background: linear-gradient(45deg, #ffd700, #ff9933); color: black; padding: 20px; text-align: center; border-radius: 8px; font-family: sans-serif;'><h3>🚀 ¡Oferta Exclusiva Inhaus!</h3><p>Obtén 20% de descuento en tu primer plan de publicidad programática.</p></div>"
    }
  }
}''';
      } else {
        _apiSimResponseJson = '''{
  "status": "SUCCESS",
  "placements": {
    "placement_1": {
      "banner_id": 1016336,
      "width": 300,
      "height": 250,
      "image_url": "https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/6a18c4e6f58810f313b89b59.png",
      "redirect_url": "https://servedbyadbutler.com/click;ID=171230;bannerID=1016336",
      "accupixel_url": "https://servedbyadbutler.com/accupixel;ID=171230;bannerID=1016336",
      "alt_text": "Anuncio Patrocinado de Zapatillas",
      "body": null
    }
  }
}''';
      }
      
      setState(() {
        _placeCounter++;
        _apiSimLogs.add('[API POST] Solicitud enviada a /adserve;pid=$_sessionPid;place=$currentPlace');
        _apiSimLogs.add('[API RESPONSE] Servido placement_1 (banner_id=${_renderRichMedia ? 1016338 : 1016336}).');
        _pixelFired = true;
        _apiSimLogs.add('[DOM] Cargado pixel de impresión invisible: accupixel;ID=171230;bannerID=1016336.');
      });
    }
  }

  Widget _buildSubTabBar() {
    return Container(
      margin: const EdgeInsets.only(bottom: 24),
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: AppTheme.surfaceColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white10),
      ),
      child: Row(
        children: [
          _buildSubTabButton(0, Icons.pie_chart_outline, 'Gobernanza de Capital'),
          _buildSubTabButton(1, Icons.code_rounded, 'Tag Simulator & API Console'),
          _buildSubTabButton(2, Icons.dashboard_customize_outlined, 'Native Template Editor'),
        ],
      ),
    );
  }

  Widget _buildSubTabButton(int index, IconData icon, String label) {
    final active = _subTabIndex == index;
    return Expanded(
      child: InkWell(
        onTap: () => setState(() => _subTabIndex = index),
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: active ? AppTheme.secondaryColor.withOpacity(0.15) : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: active ? AppTheme.secondaryColor : Colors.transparent),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: active ? AppTheme.secondaryColor : AppTheme.mutedTextColor, size: 18),
              const SizedBox(width: 8),
              Text(
                label,
                style: TextStyle(
                  color: active ? AppTheme.primaryColor : AppTheme.mutedTextColor,
                  fontWeight: active ? FontWeight.bold : FontWeight.normal,
                  fontSize: 13,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // --- SUB TAB 0: CAPITAL GOVERNANCE ---
  Widget _buildGovernanceTab() {
    final proposalsInSelectedZone = _proposals.where((p) => p['zone'] == _selectedAdZone).toList();
    
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Left Column: Webpage wireframe and Stepper confirmation
        Expanded(
          flex: 4,
          child: Column(
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Ubicación de Anuncios: Zonas del Portal del Cliente', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                      const Text('Haz click en las zonas marcadas para ver los presupuestos y propuestas asignados.', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
                      const SizedBox(height: 16),
                      _buildWebpageWireframe(),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),
              // Governance actions
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Consola de Control del Presupuesto (Write API)', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 16),
                      _buildSafetyGauge(),
                      const SizedBox(height: 8),
                      _loading
                          ? const Center(child: CircularProgressIndicator())
                          : proposalsInSelectedZone.isEmpty
                              ? const Center(child: Text('No hay propuestas de optimización asociadas a esta zona.'))
                              : Column(
                                  crossAxisAlignment: CrossAxisAlignment.stretch,
                                  children: [
                                    Text('Propuestas en Zona Seleccionada ($_selectedAdZone):', style: const TextStyle(fontWeight: FontWeight.bold)),
                                    const SizedBox(height: 12),
                                    ...proposalsInSelectedZone.map((p) => _buildProposalTile(p)),
                                    const SizedBox(height: 16),
                                    Row(
                                      mainAxisAlignment: MainAxisAlignment.center,
                                      children: [
                                        ElevatedButton(
                                          onPressed: () {
                                            _addLog('Iniciando aprobación masiva de API para zona $_selectedAdZone...');
                                            for (var p in proposalsInSelectedZone) {
                                              _processProposal(p['campaign_id'], true);
                                            }
                                          },
                                          style: ElevatedButton.styleFrom(backgroundColor: AppTheme.secondaryColor),
                                          child: const Text('Aprobar Zona (Write API)'),
                                        ),
                                        const SizedBox(width: 12),
                                        OutlinedButton(
                                          onPressed: () {
                                            _addLog('Operación de rechazo ejecutada para zona $_selectedAdZone.');
                                            for (var p in proposalsInSelectedZone) {
                                              _processProposal(p['campaign_id'], false);
                                            }
                                          },
                                          style: OutlinedButton.styleFrom(foregroundColor: AppTheme.neonRed, side: const BorderSide(color: AppTheme.neonRed)),
                                          child: const Text('Rechazar Todo'),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(width: 24),
        // Right Column: Forecasters and logs
        Expanded(
          flex: 3,
          child: Column(
            children: [
              _buildForecastingPanel(),
              const SizedBox(height: 24),
              _buildTerminal(),
            ],
          ),
        ),
      ],
    );
  }

  // --- SUB TAB 1: TAG SIMULATOR & API CONSOLE ---
  Widget _buildApiConsoleTab() {
    final sw = MediaQuery.of(context).size.width.toInt();
    final sh = MediaQuery.of(context).size.height.toInt();
    final spr = MediaQuery.of(context).devicePixelRatio;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Left Column: Targeting Meta Form & Request trigger
        Expanded(
          flex: 3,
          child: Column(
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Segmentación Avanzada y Metadatos', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                      const Text('Variables del visitante propagadas en llamadas server-to-server.', style: TextStyle(fontSize: 11, color: AppTheme.mutedTextColor)),
                      const Divider(color: Colors.white10, height: 24),
                      TextField(
                        controller: _ipController,
                        decoration: const InputDecoration(
                          labelText: 'Client IP address (ip)',
                          hintText: 'e.g., 190.156.45.12',
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _uaController,
                        decoration: const InputDecoration(
                          labelText: 'Visitor User-Agent (ua)',
                        ),
                      ),
                      const SizedBox(height: 16),
                      const Text('Métricas de Pantalla Detectadas (Navegador):', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.secondaryColor)),
                      const SizedBox(height: 6),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.black26,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text('Ancho (sw): ${sw}px', style: const TextStyle(fontSize: 11, fontFamily: 'monospace')),
                            Text('Alto (sh): ${sh}px', style: const TextStyle(fontSize: 11, fontFamily: 'monospace')),
                            Text('Ratio (spr): ${spr.toStringAsFixed(1)}', style: const TextStyle(fontSize: 11, fontFamily: 'monospace')),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Control de Entrega y Duplicidad (Unique Delivery)', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                      const Text('Coordinación de parámetros para evitar la repetición del mismo anuncio.', style: TextStyle(fontSize: 11, color: AppTheme.mutedTextColor)),
                      const Divider(color: Colors.white10, height: 24),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text('Page Session ID (pid): $_sessionPid', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                          OutlinedButton(
                            onPressed: _randomizePid,
                            style: OutlinedButton.styleFrom(padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8)),
                            child: const Text('Reset Session', style: TextStyle(fontSize: 10)),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Text('Siguiente Placement Index (place): $_placeCounter', style: const TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
                      const SizedBox(height: 16),
                      SwitchListTile(
                        title: const Text('Petición en Lote (Batched Request)', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                        subtitle: const Text('Agrupa múltiples zonas en un único hilo', style: TextStyle(fontSize: 10)),
                        value: _isBatchedRequest,
                        activeColor: AppTheme.secondaryColor,
                        onChanged: (val) {
                          setState(() {
                            _isBatchedRequest = val;
                          });
                          _simulateAdserve();
                        },
                      ),
                      SwitchListTile(
                        title: const Text('Formato Rich Media / HTML', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                        subtitle: const Text('Inyecta HTML personalizado en lugar de una imagen', style: TextStyle(fontSize: 10)),
                        value: _renderRichMedia,
                        activeColor: AppTheme.secondaryColor,
                        onChanged: (val) {
                          setState(() {
                            _renderRichMedia = val;
                          });
                          _simulateAdserve();
                        },
                      ),
                      const SizedBox(height: 16),
                      ElevatedButton.icon(
                        onPressed: _simulateAdserve,
                        icon: const Icon(Icons.send_rounded, size: 16),
                        label: const Text('Solicitar Anuncio (API Call)'),
                        style: ElevatedButton.styleFrom(
                          minimumSize: const Size(double.infinity, 44),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(width: 24),
        // Right Column: JSON payloads & output logs
        Expanded(
          flex: 4,
          child: Column(
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('AdButler JSON Ad API Terminal', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 12),
                      const Text('HTTP Request Body:', style: TextStyle(fontSize: 11, color: AppTheme.neonBlue, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 6),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: Colors.black,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.white10),
                        ),
                        child: Text(
                          _apiSimRequestJson,
                          style: const TextStyle(fontFamily: 'monospace', fontSize: 10, color: AppTheme.neonBlue),
                        ),
                      ),
                      const SizedBox(height: 12),
                      const Text('HTTP Response (JSON Metadata):', style: TextStyle(fontSize: 11, color: AppTheme.neonGreen, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 6),
                      Container(
                        width: double.infinity,
                        height: 160,
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: Colors.black,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.white10),
                        ),
                        child: SingleChildScrollView(
                          child: Text(
                            _apiSimResponseJson,
                            style: const TextStyle(fontFamily: 'monospace', fontSize: 10, color: AppTheme.neonGreen),
                          ),
                        ),
                      ),
                      
                      // Invisible accupixel trigger visualizer
                      if (_pixelFired) ...[
                        const SizedBox(height: 16),
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: AppTheme.neonGreen.withOpacity(0.08),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: AppTheme.neonGreen.withOpacity(0.3)),
                          ),
                          child: Row(
                            children: const [
                              Icon(Icons.check_circle_outline, color: AppTheme.neonGreen, size: 16),
                              SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  'DOM: Píxel accupixel cargado e impresión registrada.',
                                  style: TextStyle(fontSize: 10, color: AppTheme.neonGreen, fontWeight: FontWeight.bold),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              // Live simulated web page container rendering HTML body injection
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Vista de Renderizado Real en DOM', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 12),
                      Container(
                        height: 120,
                        width: double.infinity,
                        decoration: BoxDecoration(
                          color: Colors.black45,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.white10),
                        ),
                        alignment: Alignment.center,
                        child: _renderRichMedia
                            ? Container(
                                margin: const EdgeInsets.all(8),
                                padding: const EdgeInsets.all(12),
                                decoration: BoxDecoration(
                                  gradient: const LinearGradient(colors: [Color(0xFFFFD700), Color(0xFFFF9933)]),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: const [
                                    Text('🚀 ¡Oferta Exclusiva Inhaus!', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold, fontSize: 12)),
                                    SizedBox(height: 4),
                                    Text('Obtén 20% de descuento en tu primer plan.', style: TextStyle(color: Colors.black87, fontSize: 10)),
                                  ],
                                ),
                              )
                            : Image.network(
                                'https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/6a18c4e6f58810f313b89b59.png',
                                height: 80,
                                fit: BoxFit.contain,
                                errorBuilder: (context, error, stackTrace) => const Icon(Icons.broken_image, color: Colors.white24),
                              ),
                      ),
                      const SizedBox(height: 12),
                      // API Simulator Console logs
                      const Text('API Simulator Execution Logs:', style: TextStyle(fontSize: 10, color: AppTheme.mutedTextColor)),
                      const SizedBox(height: 6),
                      Container(
                        height: 90,
                        width: double.infinity,
                        color: Colors.black87,
                        padding: const EdgeInsets.all(6),
                        child: ListView.builder(
                          itemCount: _apiSimLogs.length,
                          itemBuilder: (ctx, idx) {
                            final log = _apiSimLogs[idx];
                            return Text(
                              log,
                              style: const TextStyle(fontFamily: 'monospace', fontSize: 9, color: Colors.white54),
                            );
                          },
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // --- SUB TAB 2: NATIVE TEMPLATE EDITOR ---
  Widget _buildNativeTemplateTab() {
    final mockTemplateJson = '''{
  "name": "${_nativeNameController.text}",
  "template": 56,
  "variables": {
    "41": "${_var41Controller.text}",
    "42": "${_var42Controller.text}",
    "43": "${_var43Controller.text}"
  },
  "width": 300,
  "height": 250
}''';

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Left Column: Native Template Form
        Expanded(
          flex: 4,
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Creación de Anuncio Nativo (Variable Mapping)', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const Text('Rellena las variables dinámicas de la plantilla maestra de AdButler.', style: TextStyle(fontSize: 11, color: AppTheme.mutedTextColor)),
                  const Divider(color: Colors.white10, height: 24),
                  TextField(
                    controller: _nativeNameController,
                    decoration: const InputDecoration(
                      labelText: 'Nombre del Anuncio Nativo',
                    ),
                    onChanged: (val) => setState(() {}),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _var41Controller,
                    decoration: const InputDecoration(
                      labelText: 'Variable 41: Título o Texto Copy',
                    ),
                    onChanged: (val) => setState(() {}),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _var42Controller,
                    decoration: const InputDecoration(
                      labelText: 'Variable 42: URL de Destino (Click URL)',
                    ),
                    onChanged: (val) => setState(() {}),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _var43Controller,
                    decoration: const InputDecoration(
                      labelText: 'Variable 43: Enlace del Asset de Imagen',
                    ),
                    onChanged: (val) => setState(() {}),
                  ),
                  const SizedBox(height: 20),
                  const Text('JSON Payload a Enviar (POST /v2/ad-items/native):', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.neonBlue)),
                  const SizedBox(height: 6),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: Colors.black,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      mockTemplateJson,
                      style: const TextStyle(fontFamily: 'monospace', fontSize: 10, color: AppTheme.neonBlue),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(width: 24),
        // Right Column: Client Responsive Preview
        Expanded(
          flex: 3,
          child: Column(
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Renderizado Nativo en el Portal', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                      const Text('Previsualiza cómo la agencia integra el contenido sin alterar su CSS.', style: TextStyle(fontSize: 11, color: AppTheme.mutedTextColor)),
                      const Divider(color: Colors.white10, height: 24),
                      
                      // Live dynamic native card
                      GestureDetector(
                        onTap: () {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text('Redirigiendo a: ${_var42Controller.text}')),
                          );
                        },
                        child: Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: Colors.black45,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: AppTheme.secondaryColor.withOpacity(0.5)),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              ClipRRect(
                                borderRadius: BorderRadius.circular(8),
                                child: Image.network(
                                  _var43Controller.text,
                                  height: 120,
                                  width: double.infinity,
                                  fit: BoxFit.cover,
                                  errorBuilder: (ctx, err, stack) {
                                    return Container(
                                      height: 120,
                                      color: Colors.white10,
                                      alignment: Alignment.center,
                                      child: const Icon(Icons.broken_image, color: Colors.white24),
                                    );
                                  },
                                ),
                              ),
                              const SizedBox(height: 12),
                              Text(
                                _var41Controller.text,
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, height: 1.4),
                              ),
                              const SizedBox(height: 8),
                              Row(
                                children: const [
                                  Text('Patrocinado', style: TextStyle(fontSize: 9, color: AppTheme.mutedTextColor)),
                                  Spacer(),
                                  Text('Más Información ↗️', style: TextStyle(fontSize: 10, color: AppTheme.secondaryColor, fontWeight: FontWeight.bold)),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 20),
                      ElevatedButton(
                        onPressed: () {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Registrando y compilando anuncio en AdButler...')),
                          );
                        },
                        style: ElevatedButton.styleFrom(
                          minimumSize: const Size(double.infinity, 44),
                        ),
                        child: const Text('Registrar Anuncio'),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    Widget activeContent = const SizedBox.shrink();
    if (_subTabIndex == 0) {
      activeContent = _buildGovernanceTab();
    } else if (_subTabIndex == 1) {
      activeContent = _buildApiConsoleTab();
    } else if (_subTabIndex == 2) {
      activeContent = _buildNativeTemplateTab();
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.campaign, color: AppTheme.secondaryColor, size: 28),
              const SizedBox(width: 12),
              Text(
                'Ad Server & Capital Governance (AdButler Style)',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Zonas de anuncios de marca blanca, gestión de distribución inteligente y pacing de capital.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppTheme.mutedTextColor),
          ),
          const SizedBox(height: 24),
          _buildSubTabBar(),
          activeContent,
        ],
      ),
    );
  }

  Widget _buildWebpageWireframe() {
    return Container(
      height: 300,
      width: double.infinity,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.shade300, width: 2),
      ),
      child: Column(
        children: [
          // Mock Browser Header
          Container(
            color: Colors.grey.shade100,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Row(
              children: [
                Icon(Icons.circle, color: Colors.red.shade400, size: 8),
                const SizedBox(width: 4),
                Icon(Icons.circle, color: Colors.amber.shade400, size: 8),
                const SizedBox(width: 4),
                Icon(Icons.circle, color: Colors.green.shade400, size: 8),
                const SizedBox(width: 16),
                Expanded(
                  child: Container(
                    height: 20,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(color: Colors.grey.shade300),
                    ),
                    alignment: Alignment.centerLeft,
                    padding: const EdgeInsets.only(left: 8),
                    child: const Text('https://portal-agencia-cliente.com', style: TextStyle(fontSize: 10, color: Colors.black54)),
                  ),
                ),
              ],
            ),
          ),
          // Webpage Content with Ad Zones
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(12),
              child: Column(
                children: [
                  // Header Leaderboard Zone
                  _buildWireframeAdZone(
                    zoneId: 'leaderboard_top',
                    label: 'Header Leaderboard (728x90)',
                    width: double.infinity,
                    height: 50,
                  ),
                  const SizedBox(height: 12),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Main Article Body
                      Expanded(
                        flex: 2,
                        child: Container(
                          padding: const EdgeInsets.all(12),
                          color: Colors.grey.shade100,
                          height: 140,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Container(width: 100, height: 12, color: Colors.grey.shade300),
                              const SizedBox(height: 8),
                              Container(width: double.infinity, height: 6, color: Colors.grey.shade200),
                              const SizedBox(height: 4),
                              Container(width: double.infinity, height: 6, color: Colors.grey.shade200),
                              const SizedBox(height: 4),
                              Container(width: double.infinity, height: 6, color: Colors.grey.shade200),
                              const SizedBox(height: 4),
                              Container(width: 120, height: 6, color: Colors.grey.shade200),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      // Sidebar Zone
                      Expanded(
                        flex: 1,
                        child: _buildWireframeAdZone(
                          zoneId: 'sidebar_rectangle',
                          label: 'Sidebar (300x250)',
                          width: double.infinity,
                          height: 140,
                        ),
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

  Widget _buildWireframeAdZone({required String zoneId, required String label, required double width, required double height}) {
    final isSelected = _selectedAdZone == zoneId;
    final proposalsInZone = _proposals.where((p) => p['zone'] == zoneId).toList();
    
    return InkWell(
      onTap: () => setState(() => _selectedAdZone = zoneId),
      child: Container(
        width: width,
        height: height,
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.secondaryColor.withOpacity(0.12) : Colors.grey.shade50,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isSelected ? AppTheme.secondaryColor : Colors.grey.shade300,
            width: isSelected ? 2 : 1,
            style: BorderStyle.solid,
          ),
        ),
        alignment: Alignment.center,
        child: proposalsInZone.isNotEmpty
            ? Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.ads_click, color: AppTheme.secondaryColor, size: 16),
                  const SizedBox(height: 4),
                  Text(
                    'Campañas en Zona: ${proposalsInZone.length}',
                    style: const TextStyle(fontSize: 10, color: Colors.black, fontWeight: FontWeight.bold),
                  ),
                ],
              )
            : Text(
                label,
                style: TextStyle(fontSize: 9, color: Colors.grey.shade500, fontWeight: FontWeight.bold),
              ),
      ),
    );
  }

  Widget _buildSafetyGauge() {
    double currentProposed = 0.0;
    for (var p in _proposals) {
      currentProposed += (p['proposed_budget'] as num?)?.toDouble() ?? 0.0;
    }
    final maxSafetyCeiling = _dailyBudgetCap * 6; // relative budget cap scaling
    final ratio = (currentProposed / maxSafetyCeiling).clamp(0.0, 1.0);
    final isExceeded = currentProposed > maxSafetyCeiling;
    
    return Container(
      margin: const EdgeInsets.only(bottom: 20),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.black26,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: isExceeded ? AppTheme.neonRed : Colors.white10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Row(
                children: [
                  Icon(Icons.shield, color: AppTheme.secondaryColor, size: 18),
                  SizedBox(width: 8),
                  Text(
                    'Límite de Seguridad del Presupuesto (Daily Cap)',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                  ),
                ],
              ),
              Text(
                '\$${currentProposed.toStringAsFixed(2)} / \$${maxSafetyCeiling.toStringAsFixed(2)}',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: isExceeded ? AppTheme.neonRed : (ratio > 0.8 ? AppTheme.neonOrange : AppTheme.neonGreen),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
              value: ratio,
              minHeight: 10,
              backgroundColor: Colors.white10,
              valueColor: AlwaysStoppedAnimation<Color>(
                isExceeded ? AppTheme.neonRed : (ratio > 0.8 ? AppTheme.neonOrange : AppTheme.neonGreen),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildForecastingPanel() {
    // Basic forecasting math
    final forecastedImpressions = (_targetClicks / (_targetCtr / 100)).round();
    final spendRate = (forecastedImpressions * 0.005).clamp(20.0, _dailyBudgetCap * 10);
    final pacingRatio = (spendRate / (_dailyBudgetCap * 10)).clamp(0.1, 0.95);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Pronóstico y Ritmo de Entrega (AdButler Pacing)', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const Text('Simula el comportamiento de entrega e impresiones basadas en CTR y presupuestos caps.', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
            const SizedBox(height: 20),
            
            // Interactive sliders
            Text('Objetivo de Clicks: ${_targetClicks.toInt()}', style: const TextStyle(fontSize: 12)),
            Slider(
              value: _targetClicks,
              min: 5000,
              max: 100000,
              divisions: 19,
              activeColor: AppTheme.secondaryColor,
              onChanged: (val) => setState(() => _targetClicks = val),
            ),
            
            Text('CTR Estimado: ${_targetCtr.toStringAsFixed(1)}%', style: const TextStyle(fontSize: 12)),
            Slider(
              value: _targetCtr,
              min: 0.5,
              max: 8.0,
              divisions: 15,
              activeColor: AppTheme.secondaryColor,
              onChanged: (val) => setState(() => _targetCtr = val),
            ),

            Text('Presupuesto Diario Máximo: \$${_dailyBudgetCap.toInt()}', style: const TextStyle(fontSize: 12)),
            Slider(
              value: _dailyBudgetCap,
              min: 100,
              max: 2000,
              divisions: 19,
              activeColor: AppTheme.secondaryColor,
              onChanged: (val) => setState(() => _dailyBudgetCap = val),
            ),
            
            const Divider(color: Colors.white10, height: 24),
            
            // Forecast results & Graph
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Impresiones Pronosticadas', style: TextStyle(fontSize: 10, color: AppTheme.mutedTextColor)),
                    Text(forecastedImpressions.toString(), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.secondaryColor)),
                  ],
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Gasto Pacing Estimado', style: TextStyle(fontSize: 10, color: AppTheme.mutedTextColor)),
                    Text('\$${spendRate.toStringAsFixed(2)}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.neonGreen)),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 16),
            Container(
              height: 140,
              width: double.infinity,
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.black26,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.white10),
              ),
              child: CustomPaint(
                painter: PacingChartPainter(pacingRatio: pacingRatio),
              ),
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: const [
                Text('Inicio Campaña', style: TextStyle(fontSize: 8, color: AppTheme.mutedTextColor)),
                Text('Curva de Ritmo Real vs Proyección Ideal', style: TextStyle(fontSize: 8, color: AppTheme.secondaryColor)),
                Text('Fin de Pacing', style: TextStyle(fontSize: 8, color: AppTheme.mutedTextColor)),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTerminal() {
    return Card(
      child: Column(
        children: [
          ListTile(
            dense: true,
            title: Row(
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: const BoxDecoration(
                    color: AppTheme.neonGreen,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 10),
                const Text(
                  'Consola de Operación Central (API Logs)',
                  style: TextStyle(fontFamily: 'Sora', fontWeight: FontWeight.bold, fontSize: 12),
                ),
              ],
            ),
            trailing: IconButton(
              icon: Icon(_terminalExpanded ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down),
              onPressed: () => setState(() => _terminalExpanded = !_terminalExpanded),
            ),
          ),
          if (_terminalExpanded)
            Container(
              height: 140,
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              color: Colors.black,
              child: _terminalLogs.isEmpty
                  ? const Center(
                      child: Text(
                        'Sin logs de ejecución. Inicia una compilación.',
                        style: TextStyle(color: AppTheme.mutedTextColor, fontFamily: 'monospace', fontSize: 12),
                      ),
                    )
                  : ListView.builder(
                      itemCount: _terminalLogs.length,
                      itemBuilder: (context, index) {
                        final log = _terminalLogs[index];
                        Color logColor = AppTheme.neonGreen;
                        if (log.contains('ERROR')) {
                          logColor = AppTheme.neonRed;
                        } else if (log.contains('WARN') || log.contains('Borrador') || log.contains('AdButler')) {
                          logColor = AppTheme.neonYellow;
                        } else if (log.contains('Prompt:')) {
                          logColor = AppTheme.neonBlue;
                        }
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 4),
                          child: Text(
                            log,
                            style: TextStyle(
                              color: logColor,
                              fontFamily: 'monospace',
                              fontSize: 11,
                            ),
                          ),
                        );
                      },
                    ),
            ),
        ],
      ),
    );
  }

  Widget _buildProposalTile(dynamic p) {
    return Card(
      color: Colors.black26,
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Row(
          children: [
            Icon(
              p['platform'] == 'meta_ads' ? Icons.facebook : Icons.ads_click,
              color: AppTheme.secondaryColor,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${p['action']} - Campaña ${p['campaign_id']}', style: const TextStyle(fontWeight: FontWeight.bold)),
                  Text(p['description'], style: const TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text('Presupuesto: \$${p['current_budget']} -> \$${p['proposed_budget']}', style: const TextStyle(fontSize: 12)),
                Text('ROAS: ${p['roas']}', style: const TextStyle(fontSize: 10, color: AppTheme.neonGreen)),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class PacingChartPainter extends CustomPainter {
  final double pacingRatio;

  PacingChartPainter({required this.pacingRatio});

  @override
  void paint(Canvas canvas, Size size) {
    final gridPaint = Paint()
      ..color = Colors.white10
      ..strokeWidth = 1.0;

    for (double i = 0; i <= size.width; i += size.width / 4) {
      canvas.drawLine(Offset(i, 0), Offset(i, size.height), gridPaint);
    }
    for (double i = 0; i <= size.height; i += size.height / 3) {
      canvas.drawLine(Offset(0, i), Offset(size.width, i), gridPaint);
    }

    final idealPaint = Paint()
      ..color = Colors.white24
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke;
      
    final actualPaint = Paint()
      ..color = AppTheme.secondaryColor
      ..strokeWidth = 3.0
      ..style = PaintingStyle.stroke;

    final dotPaint = Paint()
      ..color = AppTheme.neonGreen
      ..style = PaintingStyle.fill;

    // Draw ideal projection line
    canvas.drawLine(Offset(0, size.height), Offset(size.width, 0), idealPaint);

    // Draw actual delivery curve
    final path = Path()..moveTo(0, size.height);
      
    path.cubicTo(
      size.width * 0.3, size.height * (1.0 - 0.25 * pacingRatio),
      size.width * 0.7, size.height * (1.0 - 0.75 * pacingRatio),
      size.width, size.height * (1.0 - pacingRatio),
    );
    canvas.drawPath(path, actualPaint);
    
    // Draw current progress dot
    canvas.drawCircle(Offset(size.width, size.height * (1.0 - pacingRatio)), 5, dotPaint);
  }

  @override
  bool shouldRepaint(covariant PacingChartPainter oldDelegate) => oldDelegate.pacingRatio != pacingRatio;
}
