# Guía de Despliegue a Producción

## 📋 Checklist Pre-Producción

### 1. Variables de Entorno en Producción

Configura las siguientes variables de entorno en tu plataforma de despliegue (Render, Railway, Heroku, etc.):

#### Variables de Base de Datos
```
DB_SERVER=tu-servidor-produccion.database.windows.net
DB_PORT=1433
DB_DATABASE=tu-base-datos-produccion
DB_USER=tu-usuario-produccion
DB_PASSWORD=tu-password-seguro-produccion
```

#### Variables de Seguridad
```
SECRET_KEY=genera-una-clave-secreta-muy-segura-y-larga
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ALGORITHM=HS256
```

#### Variables de Firebase (IMPORTANTE)
```
FIREBASE_CREDENTIALS_PATH=/app/firebase-credentials.json
FIREBASE_PROJECT_ID=sistema-vacaciones-permisos
```

**O alternativamente:**
```
GOOGLE_APPLICATION_CREDENTIALS=/app/firebase-credentials.json
GOOGLE_CLOUD_PROJECT=sistema-vacaciones-permisos
```

#### Variables de Entorno
```
ENVIRONMENT=production
LOG_LEVEL=INFO
```

#### Variables de CORS
```
ALLOWED_ORIGINS=https://tu-dominio-frontend.com,https://tu-app-mobile.com
```

### 2. Archivo JSON de Firebase en Producción

**⚠️ IMPORTANTE: NO subas el archivo JSON al repositorio Git**

#### Opción A: Variable de Entorno (Recomendado)
Convierte el contenido del archivo JSON a una variable de entorno:

1. Lee el contenido del archivo JSON
2. Conviértelo a una sola línea (sin saltos de línea)
3. Configura la variable de entorno `FIREBASE_CREDENTIALS_JSON` con el contenido
4. Modifica el código para leer desde esta variable si existe

#### Opción B: Secret Manager (Más Seguro)
- Usa el Secret Manager de tu plataforma (AWS Secrets Manager, Azure Key Vault, etc.)
- O usa variables de entorno secretas en Render/Railway/Heroku

#### Opción C: Montar como Volumen (Docker)
Si usas Docker, monta el archivo como volumen secreto:
```dockerfile
# En Dockerfile o docker-compose.yml
VOLUME ["/app/firebase-credentials"]
```

### 3. Actualizar CORS para Producción

Actualiza `app/core/config.py` para incluir tus dominios de producción:

```python
ALLOWED_ORIGINS: List[str] = [
    "https://tu-dominio-frontend.com",
    "https://tu-app-mobile.com",
    # Mantén localhost solo para desarrollo local
    "http://localhost:3000",  # Solo en desarrollo
    "http://localhost:5173",  # Solo en desarrollo
]
```

### 4. Configuración de Logging en Producción

Asegúrate de que los logs estén configurados correctamente:
- Los logs no deben mostrar información sensible (passwords, tokens)
- Configura rotación de logs
- Considera usar un servicio de logging externo (Sentry, LogRocket, etc.)

### 5. Seguridad Adicional

- ✅ Cambia `SECRET_KEY` por una clave segura y única
- ✅ Usa HTTPS en producción
- ✅ Configura rate limiting
- ✅ Revisa permisos de archivos (el JSON de Firebase debe tener permisos restrictivos)
- ✅ Desactiva debug mode en producción

### 6. Actualizar render.yaml (si usas Render)

Agrega las variables de Firebase:

```yaml
envVars:
  # ... variables existentes ...
  
  # Firebase
  - key: FIREBASE_CREDENTIALS_PATH
    sync: false  # No sincronizar desde Git
  - key: FIREBASE_PROJECT_ID
    value: sistema-vacaciones-permisos
  - key: GOOGLE_CLOUD_PROJECT
    value: sistema-vacaciones-permisos
```

### 7. Actualizar Dockerfile (si usas Docker)

Asegúrate de que el Dockerfile no copie el archivo JSON:

```dockerfile
# NO incluir esto:
# COPY sistema-vacaciones-permisos-firebase-adminsdk-*.json .

# En su lugar, el archivo debe montarse como volumen o leerse desde variable de entorno
```

## 🔧 Cambios Necesarios en el Código

### 1. Mejorar lectura de credenciales desde variable de entorno

El código actual busca el archivo JSON automáticamente, pero en producción es mejor usar variables de entorno o secretos.

### 2. Deshabilitar búsqueda automática en producción

En producción, deshabilita la búsqueda automática del archivo JSON por seguridad.

## 📝 Pasos para Desplegar

1. **Preparar variables de entorno** en tu plataforma de despliegue
2. **Subir el archivo JSON** como secreto o variable de entorno (NO en Git)
3. **Actualizar CORS** con tus dominios de producción
4. **Cambiar SECRET_KEY** por una clave segura
5. **Verificar que ENVIRONMENT=production**
6. **Desplegar y verificar** que Firebase se inicializa correctamente
7. **Probar notificaciones** con el endpoint de prueba

## ✅ Verificación Post-Despliegue

1. Verifica el estado de Firebase:
   ```
   GET https://tu-api-produccion.com/api/v1/notificaciones/estado-firebase
   ```

2. Prueba el envío de notificaciones:
   ```
   POST https://tu-api-produccion.com/api/v1/notificaciones/test-envio?token_fcm=tu-token
   ```

3. Verifica los logs del servidor para confirmar que Firebase se inicializó correctamente

## 🚨 Problemas Comunes

### Firebase no se inicializa
- Verifica que la variable `FIREBASE_CREDENTIALS_PATH` apunte al archivo correcto
- Verifica que el archivo JSON tenga permisos de lectura
- Revisa los logs del servidor para ver errores específicos

### Notificaciones no funcionan
- Verifica que Firebase esté inicializado con `project_id`
- Verifica que los tokens FCM sean válidos
- Revisa los logs para ver errores de Firebase

### CORS errors
- Verifica que `ALLOWED_ORIGINS` incluya tu dominio de producción
- Verifica que `allow_credentials=True` esté configurado correctamente
