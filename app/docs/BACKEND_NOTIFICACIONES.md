# Especificación de Endpoint para Notificaciones Push

## Endpoint: Registrar Token de Dispositivo

### POST `/api/v1/notificaciones/registrar-token`

**Descripción:** Registra o actualiza el token FCM de un dispositivo asociado a un usuario.

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Body:**
```json
{
  "token_fcm": "string (máximo 500 caracteres)",
  "codigo_trabajador": "string (8 caracteres)",
  "plataforma": "A" o "I",
  "modelo_dispositivo": "string (opcional, máximo 100 caracteres)",
  "version_app": "string (opcional, máximo 20 caracteres)",
  "version_so": "string (opcional, máximo 20 caracteres)"
}
```

**Validaciones:**
1. Verificar que el `codigo_trabajador` corresponde al usuario autenticado
2. El `token_fcm` debe ser único (constraint UNIQUE en la tabla)
3. `plataforma` debe ser 'A' (Android) o 'I' (iOS)

**Lógica:**
1. Buscar si existe un registro con el mismo `token_fcm`
2. Si existe:
   - Actualizar `fecha_ultimo_acceso = GETDATE()`
   - Actualizar `activo = 'S'`
   - Actualizar información del dispositivo si se proporciona
3. Si no existe:
   - Insertar nuevo registro en `ppavac_dispositivo`
   - `fecha_registro = GETDATE()`
   - `fecha_ultimo_acceso = GETDATE()`
   - `activo = 'S'`

**Respuesta exitosa (200/201):**
```json
{
  "mensaje": "Token registrado exitosamente",
  "id_dispositivo": 123
}
```

**Errores posibles:**
- 401: No autenticado
- 403: El código_trabajador no corresponde al usuario autenticado
- 400: Datos inválidos
- 500: Error del servidor

---

## Lógica para Enviar Notificaciones

### Cuando se crea una solicitud

**Trigger:** Después de insertar en `ppavac_solicitud` (POST `/api/v1/vacaciones/solicitar`)

**Pasos:**

1. **Identificar aprobadores:**
   ```sql
   -- Obtener aprobadores según la jerarquía del área del trabajador
   SELECT DISTINCT j.codigo_trabajador_aprobador
   FROM ppavac_jerarquia j
   INNER JOIN trabajadores t ON t.codigo_area = j.codigo_area
   WHERE t.codigo_trabajador = @codigo_trabajador_solicitante
     AND j.activo = 'S'
   ORDER BY j.nivel ASC
   ```

2. **Obtener tokens FCM de los aprobadores:**
   ```sql
   SELECT token_fcm, codigo_trabajador
   FROM ppavac_dispositivo
   WHERE codigo_trabajador IN (@lista_aprobadores)
     AND activo = 'S'
     AND notif_nuevas = 'S'  -- Solo si tienen habilitadas las notificaciones
   ```

3. **Enviar notificación usando Firebase Admin SDK:**

   **Python/FastAPI ejemplo:**
   ```python
   from firebase_admin import messaging
   
   def enviar_notificacion_solicitud(id_solicitud, tipo_solicitud, nombre_trabajador, tokens_fcm):
       message = messaging.MulticastMessage(
           notification=messaging.Notification(
               title="Nueva solicitud pendiente",
               body=f"Solicitud de {'vacaciones' if tipo_solicitud == 'V' else 'permiso'} de {nombre_trabajador}"
           ),
           data={
               "tipo_solicitud": tipo_solicitud,
               "id_solicitud": str(id_solicitud),
               "codigo_trabajador": codigo_trabajador,
               "tipo": "nueva_solicitud"
           },
           tokens=tokens_fcm,
           android=messaging.AndroidConfig(
               priority='high',
               notification=messaging.AndroidNotification(
                   channel_id='fidesoft_channel',
                   sound='default'
               )
           )
       )
       
       response = messaging.send_multicast(message)
       print(f'Notificaciones enviadas: {response.success_count}/{len(tokens_fcm)}')
   ```

   **Node.js ejemplo:**
   ```javascript
   const admin = require('firebase-admin');
   
   async function enviarNotificacionSolicitud(idSolicitud, tipoSolicitud, nombreTrabajador, tokensFcm) {
     const message = {
       notification: {
         title: 'Nueva solicitud pendiente',
         body: `Solicitud de ${tipoSolicitud === 'V' ? 'vacaciones' : 'permiso'} de ${nombreTrabajador}`
       },
       data: {
         tipo_solicitud: tipoSolicitud,
         id_solicitud: idSolicitud.toString(),
         tipo: 'nueva_solicitud'
       },
       android: {
         priority: 'high',
         notification: {
           channelId: 'fidesoft_channel',
           sound: 'default'
         }
       },
       tokens: tokensFcm
     };
     
     const response = await admin.messaging().sendMulticast(message);
     console.log(`Notificaciones enviadas: ${response.successCount}/${tokensFcm.length}`);
   }
   ```

---

## Configuración de Firebase Admin SDK

### 1. Instalar dependencias

**Python:**
```bash
pip install firebase-admin
```

**Node.js:**
```bash
npm install firebase-admin
```

### 2. Inicializar Firebase Admin

**Python:**
```python
import firebase_admin
from firebase_admin import credentials

# Descargar el archivo de credenciales desde Firebase Console
# Project Settings > Service Accounts > Generate New Private Key
cred = credentials.Certificate("path/to/serviceAccountKey.json")
firebase_admin.initialize_app(cred)
```

**Node.js:**
```javascript
const admin = require('firebase-admin');
const serviceAccount = require('./path/to/serviceAccountKey.json');

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount)
});
```

### 3. Obtener credenciales de Firebase

1. Ir a Firebase Console
2. Seleccionar tu proyecto
3. Ir a Project Settings > Service Accounts
4. Click en "Generate New Private Key"
5. Guardar el archivo JSON de forma segura (no commitearlo)
6. Usar este archivo para inicializar Firebase Admin SDK

---

## Estructura de Datos de Notificación

### Payload recomendado:

```json
{
  "notification": {
    "title": "Nueva solicitud pendiente",
    "body": "Solicitud de vacaciones de Juan Pérez"
  },
  "data": {
    "tipo_solicitud": "V",
    "id_solicitud": "123",
    "codigo_trabajador": "PR014793",
    "tipo": "nueva_solicitud"
  }
}
```

### Campos importantes en `data`:
- `tipo_solicitud`: "V" (vacaciones) o "P" (permiso)
- `id_solicitud`: ID de la solicitud creada
- `codigo_trabajador`: Código del trabajador que creó la solicitud
- `tipo`: Tipo de notificación (para futuras expansiones)

---

## Notas Importantes

1. **Tokens inválidos:** Firebase puede marcar tokens como inválidos. Debes manejar estos casos y actualizar `activo = 'N'` en la base de datos.

2. **Múltiples dispositivos:** Un usuario puede tener múltiples dispositivos registrados. Envía la notificación a todos sus tokens activos.

3. **Privacidad:** Los tokens FCM son sensibles. No los expongas en logs públicos.

4. **Rate Limits:** Firebase tiene límites de envío. Para grandes volúmenes, considera usar Firebase Cloud Messaging HTTP v1 API con batching.

5. **Testing:** Usa Firebase Console > Cloud Messaging para enviar notificaciones de prueba antes de implementar en producción.
