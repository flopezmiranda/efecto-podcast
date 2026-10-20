# Sitio web de Efecto Podcast

Sitio estático que importa solo todos los videos de [youtube.com/@efecto_podcast](https://www.youtube.com/@efecto_podcast) y crea una página por episodio, optimizada para Google y lista para AdSense. Se actualiza solo todos los días y el hosting es gratis (GitHub Pages).

## Qué incluye

- **Una página por episodio** con dirección propia (`/episodios/nombre-del-episodio/`), reproductor, resumen, capítulos con salto al minuto, temas y transcripción.
- **SEO**: título y descripción por página, URL canónica, datos estructurados (`PodcastEpisode`, `VideoObject`, migas de pan), `sitemap.xml` con video, `robots.txt`, RSS y vista previa al compartir en redes.
- **Rendimiento**: el reproductor de YouTube carga solo al hacer clic, así la página abre rápido (Google lo premia).
- **Temas automáticos** a partir de los hashtags y etiquetas de tus videos (solo los que tienen 3 o más episodios, para no crear páginas pobres).
- **Buscador**, episodios relacionados y paginación.
- **AdSense**: código del sitio, `ads.txt` y espacios de anuncios en la portada y en cada episodio. Se activa poniendo tu ID en la configuración.
- **Páginas que AdSense exige**: Sobre nosotros, Contacto, Política de privacidad y Términos.
- Los videos de menos de 3 minutos (Shorts) no se publican: son páginas con poco texto y perjudican la aprobación de AdSense.

## Puesta en marcha (una sola vez)

### 1. Comprar el dominio
Compra `efectopodcast.com` (o el que prefieras) en Cloudflare Registrar, Namecheap o NIC Chile (`.cl`). Si es otro dominio, cámbialo en `base_url` dentro de `site.config.json`.

### 2. Subir el proyecto a GitHub
Crea un repositorio en GitHub (por ejemplo `efecto-podcast`) y sube esta carpeta.

### 3. Conseguir una API key de YouTube (gratis)
1. Entra a <https://console.cloud.google.com/>, crea un proyecto.
2. En **APIs y servicios → Biblioteca**, activa **YouTube Data API v3**.
3. En **Credenciales → Crear credenciales → Clave de API**. Cópiala.
4. En tu repositorio de GitHub: **Settings → Secrets and variables → Actions → New repository secret**, nombre `YOUTUBE_API_KEY`, y pega la clave.

### 4. Activar GitHub Pages
En el repositorio: **Settings → Pages → Source: GitHub Actions**. Luego **Actions → "Importar episodios y publicar" → Run workflow**. En unos minutos el sitio queda publicado con todos tus episodios.

### 5. Conectar el dominio
En **Settings → Pages → Custom domain** escribe tu dominio y sigue las instrucciones de DNS que muestra GitHub. Activa **Enforce HTTPS**.

### 6. Google Search Console
Entra a <https://search.google.com/search-console>, agrega tu dominio, y en **Sitemaps** envía `sitemap.xml`. Así Google empieza a indexar todos los episodios.

### 7. AdSense
1. Antes de postular: completa **Sobre nosotros** (`content/pages/sobre-nosotros.html`, donde dice `EDITA`) y revisa el correo de contacto en `site.config.json`.
2. Postula en <https://adsense.google.com> con tu dominio.
3. Copia tu ID de editor (`ca-pub-...`) en `adsense_client` dentro de `site.config.json` y súbelo. El sitio agrega el código y `ads.txt` solo.
4. En AdSense, en **Privacidad y mensajes**, activa el mensaje de consentimiento (lo exige Google para visitantes de Europa).
5. Opcional: crea bloques de anuncios en AdSense y pega sus IDs en `adsense_slots`. Si los dejas vacíos, los espacios usan anuncios automáticos.

## Lo que más ayuda al SEO y a AdSense: transcripciones

Google posiciona texto, no video. Una página con la transcripción completa del episodio tiene miles de palabras originales y aparece en muchas más búsquedas. AdSense también rechaza sitios con "contenido de poco valor", y las transcripciones resuelven eso.

Desde tu computador (YouTube bloquea esta descarga desde los servidores de GitHub):

```bash
pip install yt-dlp jinja2
python scripts/fetch_transcripts.py
git add content/transcripts && git commit -m "Transcripciones" && git push
```

Descarga los subtítulos de cada video (los automáticos sirven) y los guarda en `content/transcripts/<id-del-video>.txt`. Puedes corregirlos a mano cuando quieras.

## Mejorar un episodio a mano

Crea `content/notes/<id-del-video>.html` con texto extra (resumen escrito, frases destacadas, links mencionados). Se muestra bajo la descripción del episodio.

## Consejos para posicionar

- **Títulos de YouTube descriptivos**: el título del video es el título de la página. "Cómo salir de deudas con Juan Pérez" posiciona mucho mejor que "Ep. 45".
- **Descripciones largas** con marcas de tiempo (`00:00 Introducción`): se convierten en capítulos en el sitio.
- **Hashtags y etiquetas consistentes** (#emprendimiento, #saludmental): crean las páginas de temas.
- Pon el link al episodio en el sitio en la descripción de YouTube y en tus redes: los enlaces de entrada ayudan a posicionar.

## Ver el sitio en tu computador

```bash
python scripts/build.py
python -m http.server -d dist 8000
```

Luego abre <http://localhost:8000>.

## Estructura

| Archivo / carpeta | Para qué sirve |
|---|---|
| `site.config.json` | Nombre, dominio, canal, AdSense, redes, correo |
| `data/episodes.json` | Episodios importados (se actualiza solo; no editar) |
| `content/pages/` | Páginas fijas: nosotros, contacto, privacidad, términos |
| `content/transcripts/` | Transcripciones por video |
| `content/notes/` | Texto extra por video |
| `templates/`, `static/` | Diseño del sitio |
| `scripts/` | Importador y generador |
