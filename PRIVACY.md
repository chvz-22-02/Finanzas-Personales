# Política de privacidad

**Última actualización:** 14 de octubre de 2026

Esta política describe cómo **Finanzas-Personales** (el "Extractor de Gastos Bancarios desde Gmail") accede a la información de la cuenta de Google y qué hace con ella.

## Alcance

Esta aplicación es de **uso personal**. Su único usuario es su autor, y solo accede a la cuenta de Gmail de su propio autor. No está ofrecida como servicio a terceros.

Si en el futuro la aplicación se abre a otros usuarios, esta política se actualizará antes de que eso ocurra.

## Datos a los que accede

La aplicación solicita un único permiso de Google:

- `https://www.googleapis.com/auth/gmail.readonly`: **lectura** de correos. La aplicación no puede enviar, modificar ni eliminar correos.

Dentro de ese permiso, la aplicación solo consulta los correos enviados por estos remitentes de notificaciones bancarias:

- `notificaciones@notificacionesbcp.com.pe` (BCP)
- `app@pichincha.pe` y `notificaciones@pichincha.pe` (Banco Pichincha)
- `notificaciones@yape.pe` (Yape)

El resto de correos de la cuenta no se lee ni se procesa.

## Qué datos se extraen

De cada correo de notificación se extraen únicamente los datos del movimiento: el identificador del correo, la fecha, el monto, la moneda, el tipo (gasto o ingreso), la categoría, la descripción o el beneficiario, el banco, el número de cuenta enmascarado y el número de operación.

## Dónde se almacenan

Los datos extraídos se guardan exclusivamente en almacenamiento controlado por el propio usuario:

- archivos locales en su computadora, y/o
- un bucket de Google Cloud Storage de su propio proyecto de Google Cloud.

Las credenciales de acceso (el token OAuth) se guardan en el equipo del usuario o en Google Secret Manager dentro de su propio proyecto.

## Compartición con terceros

Los datos **no se venden, no se comparten y no se transfieren** a terceros. Tampoco se usan con fines publicitarios ni para entrenar modelos de inteligencia artificial.

El uso de la información recibida de las API de Google se ajusta a la [Política de datos de usuario de los servicios de API de Google](https://developers.google.com/terms/api-services-user-data-policy), incluidos los requisitos de uso limitado.

## Conservación y eliminación

Los datos se conservan mientras el usuario los mantenga en su almacenamiento, y puede eliminarlos en cualquier momento borrando los archivos locales o los objetos del bucket.

## Revocar el acceso

El acceso a Gmail se puede revocar en cualquier momento desde [myaccount.google.com/permissions](https://myaccount.google.com/permissions). Después de revocarlo, la aplicación deja de poder leer correos.

## Contacto

Para cualquier consulta sobre esta política, abre un *issue* en el [repositorio del proyecto](https://github.com/chvz-22-02/Finanzas-Personales/issues).
