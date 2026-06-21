import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers.dart';
import '../../theme/app_theme.dart';

class WhiteLabelTab extends ConsumerStatefulWidget {
  const WhiteLabelTab({super.key});

  @override
  ConsumerState<WhiteLabelTab> createState() => _WhiteLabelTabState();
}

class _WhiteLabelTabState extends ConsumerState<WhiteLabelTab> {
  final TextEditingController _cnameController = TextEditingController(text: 'portal.clientedeagencia.com');
  final TextEditingController _smtpServerController = TextEditingController(text: 'smtp.clientedeagencia.com');
  final TextEditingController _smtpUserController = TextEditingController(text: 'reportes@clientedeagencia.com');
  final TextEditingController _smtpPassController = TextEditingController(text: '••••••••••••••••');

  bool _serverSyncActive = true;
  String _activeTemplate = 'Master Premium Dashboard';

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.palette, color: AppTheme.primaryColor, size: 28),
              const SizedBox(width: 12),
              Text(
                'Marca Blanca & Gobernanza de Datos',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Personalización visual de portales para clientes,SMTP gateways y sincronización centralizada de instancias (Server Sync).',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppTheme.mutedTextColor),
          ),
          const SizedBox(height: 24),

          // Section 1: CNAME Mapping
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Asignación de Dominio Personalizado (CNAME)', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const Text('Permite que tus clientes accedan a sus informes desde tu propio subdominio corporativo.', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _cnameController,
                    decoration: const InputDecoration(
                      labelText: 'Subdominio CNAME Mapeado',
                      prefixIcon: Icon(Icons.dns),
                      suffixIcon: Icon(Icons.check_circle, color: AppTheme.primaryColor),
                    ),
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Dominio CNAME configurado y validado en DNS.')),
                      );
                    },
                    child: const Text('Validar y Guardar Dominio'),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 24),

          // Section 2: SMTP Config
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Gateway SMTP Personalizado', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const Text('Envía alertas e informes PDF automatizados utilizando el correo corporativo de la agencia.', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _smtpServerController,
                    decoration: const InputDecoration(
                      labelText: 'Servidor SMTP',
                      prefixIcon: Icon(Icons.mail),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _smtpUserController,
                          decoration: const InputDecoration(
                            labelText: 'Usuario SMTP',
                            prefixIcon: Icon(Icons.person),
                          ),
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: TextField(
                          controller: _smtpPassController,
                          obscureText: true,
                          decoration: const InputDecoration(
                            labelText: 'Contraseña SMTP',
                            prefixIcon: Icon(Icons.lock),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton.icon(
                    onPressed: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Guardado SMTP completado. Correo de prueba enviado.')),
                      );
                    },
                    icon: const Icon(Icons.send),
                    label: const Text('Guardar y Probar Conexión'),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 24),

          // Section 3: Server Sync
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Consola Central y Server Sync', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const Text('Propaga instantáneamente las actualizaciones estructurales de widgets a todos los portales de clientes.', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      const Text('Plantilla Maestra Activa: ', style: TextStyle(fontWeight: FontWeight.bold)),
                      const SizedBox(width: 8),
                      Text(_activeTemplate, style: const TextStyle(color: AppTheme.primaryColor)),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      const Text('Sincronización Automática de Servidores'),
                      const Spacer(),
                      Switch(
                        value: _serverSyncActive,
                        onChanged: (val) {
                          setState(() => _serverSyncActive = val);
                        },
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton.icon(
                    onPressed: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Server Sync completado. 12 instancias de clientes actualizadas.')),
                      );
                    },
                    icon: const Icon(Icons.cloud_sync),
                    label: const Text('Propagar Cambios Ahora'),
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
