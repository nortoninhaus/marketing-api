import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
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

  @override
  void initState() {
    super.initState();
    _loadProposals();
  }

  void _addLog(String msg) {
    if (!mounted) return;
    setState(() {
      final timeStr = DateTime.now().toIso8601String().substring(11, 19);
      _terminalLogs.add('[$timeStr] $msg');
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

  @override
  Widget build(BuildContext context) {
    final proposalsInSelectedZone = _proposals.where((p) => p['zone'] == _selectedAdZone).toList();

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

          // Layout Builder for Split Pane
          Row(
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
                    // Governanace actions
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
                  ],
                ),
              ),
            ],
          ),
          
          const SizedBox(height: 24),
          _buildTerminal(),
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
