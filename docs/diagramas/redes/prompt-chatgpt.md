# Diagrama de redes — prompt para generarlo con ChatGPT

> **Por qué así.** En Lucidchart y en EA el diagrama de redes quedaba pobre, así
> que se genera como imagen con ChatGPT (T-54 del Sprint 4). Este archivo guarda
> el prompt para que se pueda regenerar igual o corregir sin empezar de cero.
> En el documento va **después del diagrama de capas y del de despliegue**
> (2.1.1.3 del Sprint 4).
>
> Los datos salen del sistema real (12/11/26): `scripts/start.sh`,
> `config/settings.py`, `notifications/push.py`, `payments/` y la memoria del
> despliegue. Si algo cambia en producción, se corrige acá primero.

## Cómo usarlo

1. Pegar el **prompt** en ChatGPT (con generación de imágenes).
2. Revisar la imagen contra la **lista de verificación** del final: las IA de
   imagen se equivocan seguido en los textos chicos y en los números de puerto.
3. Si un rótulo sale mal, pedir sólo esa corrección («corregí el rótulo X por
   Y, no cambies nada más») en lugar de regenerar todo.
4. Guardar el PNG final en `docs/diagramas/png/Sprint4/2.1.1.3 Diagrama de redes.png`.

---

## Prompt

```
Generá una imagen: un DIAGRAMA DE REDES técnico, profesional, para un documento
académico de ingeniería de sistemas. Formato horizontal 16:9, fondo blanco,
estilo plano (flat) y limpio, con íconos de red estándar (como los de Cisco o
los de los diagramas de arquitectura de nube), líneas rectas con flechas y
rótulos legibles en español. Nada de estilo caricatura, nada de 3D exagerado,
nada de personas dibujadas.

Título arriba, centrado: «Diagrama de redes — Plataforma Médica SaaS (producción)».

Organizá el diagrama en CINCO ZONAS, de izquierda a derecha, cada una dentro de
un recuadro con borde punteado y su nombre arriba:

ZONA 1 — «Clientes (red del usuario)»
  - Un ícono de computadora con navegador, rótulo: «Navegador web — personal y pacientes».
  - Un ícono de teléfono Android, rótulo: «App móvil Flutter (APK) — pacientes».
  - Un ícono de router Wi-Fi / red móvil 4G debajo de ambos, rótulo: «Wi-Fi / 4G».

ZONA 2 — «Internet»
  - Una nube grande al centro, rótulo: «Internet».

ZONA 3 — «Railway (PaaS) — región us-west»
  - Un ícono de balanceador / proxy en la entrada, rótulo:
    «Borde de Railway — TLS 1.3, HTTPS :443, redirección 301 de HTTP».
  - Detrás, DOS servidores (contenedores) uno encima del otro:
    a) «Servicio frontend — React + Vite (serve) :4173»
    b) «Servicio backend — API Django + gunicorn :8000».
       Dentro del recuadro del backend, tres cajitas chicas con ícono de
       engranaje: «Copias automáticas», «Recordatorios de fichas»,
       «Reentrenamiento del modelo».

ZONA 4 — «Supabase — AWS us-east-1»
  - Un ícono de base de datos (cilindro), rótulo:
    «PostgreSQL 16 + pgvector — Row Level Security por organización».
  - Delante del cilindro, un ícono chico de pool de conexiones, rótulo:
    «Pooler de conexiones :5432».

ZONA 5 — «Servicios externos (APIs HTTPS :443)»
  Cuatro íconos en columna, cada uno con su rótulo:
  - «Google Gemini — IA generativa y embeddings»
  - «Stripe — pagos en línea (Checkout)»
  - «Brevo — correo transaccional (API v3)»
  - «Firebase Cloud Messaging — notificaciones push»

CONEXIONES (flechas con rótulo corto sobre la línea):
  1. Navegador → Internet → Borde de Railway: «HTTPS :443».
  2. App Android → Internet → Borde de Railway: «HTTPS :443 — API REST + JWT».
  3. Borde de Railway → Servicio frontend: «HTTP interno :4173».
  4. Borde de Railway → Servicio backend: «HTTP interno :8000».
  5. Servicio backend → Pooler de Supabase: «PostgreSQL :5432 — TLS».
  6. Servicio backend → Gemini: «HTTPS :443».
  7. Servicio backend → Stripe: «HTTPS :443».
  8. Stripe → Servicio backend, flecha punteada en sentido contrario: «Webhook HTTPS (firmado)».
  9. Servicio backend → Brevo: «HTTPS :443».
 10. Servicio backend → Firebase Cloud Messaging: «HTTPS :443 (FCM v1)».
 11. Firebase Cloud Messaging → App Android, flecha punteada: «Push».
 12. Navegador → Stripe, flecha punteada: «Pago con tarjeta (Checkout)».

Usá un color por tipo de tramo y poné una LEYENDA abajo a la derecha:
  - Verde: «Tráfico cifrado (TLS)».
  - Gris: «Tráfico interno de la plataforma».
  - Línea punteada: «Conexión iniciada por el servicio externo».

Abajo a la izquierda, un recuadro chico de notas con tres líneas:
  - «Todo el tráfico público va cifrado (HTTPS/TLS); no hay puertos expuestos salvo el 443.»
  - «Cada organización ve sólo sus datos: RLS en PostgreSQL.»
  - «Las claves (Gemini, Stripe, Brevo, Firebase) viven en variables de entorno de Railway.»

Que todos los textos estén en español, sin faltas de ortografía, y que los
números de puerto se lean claramente. No agregues componentes que no estén en
esta lista.
```

---

## Lista de verificación de la imagen

- [ ] Están los 2 clientes, la nube de Internet, el borde de Railway, los 2
      servicios, Supabase con su pooler y los 4 servicios externos. Nada más.
- [ ] Puertos: **443** público, **4173** frontend, **8000** backend, **5432**
      PostgreSQL. Ninguno inventado (ni 80 abierto, ni 3306, ni 6379).
- [ ] La flecha del webhook va **de Stripe al backend** y la del push **de FCM
      al teléfono**.
- [ ] Los tres procesos de fondo están **dentro** del backend, no como
      servidores aparte (corren en el mismo contenedor, lanzados por
      `scripts/start.sh`).
- [ ] Supabase dice **us-east-1**. La región de Railway hay que **confirmarla en
      el panel** (Settings → Region) antes de dejar «us-west»; si es otra, se
      corrige en el prompt.
- [ ] Los textos se leen sin errores. Las IA suelen cambiar letras en los
      rótulos chicos.

> **Ojo con «Reentrenamiento del modelo».** Lo agrega US-38 (Daniel) en este
> sprint. Si el 20/11 todavía no está en `scripts/start.sh`, se saca del
> prompt: el diagrama muestra lo que hay en producción, no lo planeado.
