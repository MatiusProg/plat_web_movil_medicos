# Diagrama de redes — prompt para generarlo con ChatGPT

> **Por qué así.** En Lucidchart y en EA el diagrama de redes quedaba pobre, así
> que se genera como imagen con ChatGPT (T-54 del Sprint 4). En el documento va
> como **2.1.1.3 Diagrama de Redes**, después del de capas y el de despliegue.
>
> **Estilo:** el del diagrama de redes del primer parcial
> (`PRIMER_PARCIAL/docs/diagramas/1er Parcial/Diseño de Arquitectura/3.1.3 Diagrama de Redes.jpg`).
> Es vertical y simple, con íconos grandes, flechas naranjas y un rótulo corto por
> flecha, dentro de un marco de EA. La primera versión (12/11), con cinco zonas,
> leyenda y notas, tenía demasiado texto y se notaba hecha por IA. Esta versión
> pide lo contrario: **pocos elementos y casi nada de texto**.
>
> Los datos salen del sistema real (12/11/26). Si algo cambia en producción, se
> corrige acá primero.

## Cómo usarlo

1. Pegar el **prompt** en ChatGPT (con generación de imágenes). Si se puede,
   adjuntar también la imagen del primer parcial y decirle «con este estilo».
2. Revisar la imagen contra la **lista de verificación** del final.
3. Si un rótulo sale mal, pedir sólo esa corrección («cambiá el rótulo X por Y,
   no cambies nada más») en lugar de regenerar todo.
4. Guardar el PNG en `docs/diagramas/png/Sprint4/2.1.1.3 Diagrama de redes.png`.

---

## Prompt

```
Dibujá un diagrama de redes simple, como los de Enterprise Architect que se
hacen para la facultad, no una infografía.

ESTILO (muy importante):
- Fondo blanco. Todo dentro de un marco rectangular fino, con una pestaña arriba
  a la izquierda que dice: «deployment 2.1.1.3 Diagrama de Redes».
- Formato vertical (más alto que ancho). El recorrido va de arriba hacia abajo.
- Íconos grandes y realistas, sin recuadros de colores alrededor: un monitor de
  escritorio, un celular, una nube azul, un servidor, un cilindro de base de
  datos y los logos de cada servicio.
- Flechas NARANJAS gruesas, todas del mismo color.
- Debajo de cada ícono, su nombre en negrita, corto (de 2 a 4 palabras).
- Sobre cada flecha, un rótulo chico y gris: sólo el protocolo y el puerto.
- NO pongas título grande, zonas, recuadros punteados, leyenda, notas,
  numeración ni descripciones largas. Menos texto es mejor.

ELEMENTOS, de arriba hacia abajo:
1. Arriba a la izquierda, un monitor con un navegador: «Cliente Web - React».
   Arriba a la derecha, un celular: «Cliente móvil - Flutter».
2. Las dos flechas bajan y se juntan en una nube azul en el centro: «Internet».
   Rótulo de las dos flechas: «HTTPS / TLS 1.3 (443)».
3. De la nube baja una flecha a un ícono de servidor proxy: «Borde de Railway».
   Rótulo: «HTTPS (443)».
4. Debajo, un recuadro grande con el logo de Railway, rotulado «Railway», que
   contiene DOS contenedores Docker uno al lado del otro:
   «Frontend (React)» y «Backend (Django)».
   Flechas del Borde a cada uno: «HTTP :4173» y «HTTP :8000».
5. Del Backend sale una flecha hacia abajo a la izquierda, a un cilindro de base
   de datos con el logo de Supabase y el elefante de PostgreSQL: «Supabase
   (PostgreSQL)». Rótulo: «PostgreSQL / SSL (5432)».
6. Del Backend sale una flecha hacia abajo a la derecha, a un grupo de cuatro
   logos chicos en fila, con el rótulo general «Servicios externos» y debajo de
   cada logo una sola palabra: «Gemini», «Stripe», «Brevo», «Firebase».
   Rótulo de la flecha: «HTTPS (443)».

No agregues ningún otro elemento, ni texto que no esté en esta lista.
Todos los textos en español y sin faltas de ortografía.
```

---

## Lista de verificación de la imagen

- [ ] Hay exactamente: 2 clientes, la nube, el borde, Railway con 2
      contenedores, Supabase y los 4 servicios externos. Nada más (ni firewall
      ni API Gateway: en producción ese papel lo cumple el borde de Railway).
- [ ] Puertos: **443** público, **4173** frontend, **8000** backend, **5432**
      PostgreSQL. Ninguno inventado.
- [ ] Sin leyenda, sin notas, sin zonas, sin título grande: sólo la pestaña del
      marco.
- [ ] El cliente web dice **React**, no Angular (Angular era el del primer
      parcial).
- [ ] Los textos se leen sin errores. Las IA suelen cambiar letras en los
      rótulos chicos.
