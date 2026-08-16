# Los tres posts de builder.aws — 0,6 puntos extra

✅ **Verificado el 2026-08-16** en `agentsforhumans.devpost.com/rules`, textual:

> *"Submissions that advance to Stage Two may earn up to 0.6 additional points
> on top of their score by publishing a builder.aws Blog Post covering your
> journey building and implementing AWS for this hackathon."*

Y las condiciones, de la misma página:

| | |
|---|---|
| Cuántos | **hasta 3 posts**, 0,2 puntos cada uno |
| Máximo | **0,6 puntos** |
| Dónde | **builder.aws** (no `community.aws`), públicos |
| Título | debe incluir **"Agents for Humans"** |
| Contenido | el recorrido de construirlo e implementar AWS |

## La letra pequeña que importa

**"Submissions that advance to Stage Two."** Los puntos extra solo cuentan si el
proyecto pasa la fase 1, que es un pass/fail sobre si encaja en el tema y usa de
verdad el SDK exigido. No es un atajo para entrar: es un desempate una vez
dentro.

Los cinco criterios pesan lo mismo. **0,6 puntos deciden un empate, y en un
hackathon con 10 premios los empates existen.**

## No necesitas cuenta nueva

`builder.aws` entra con el **mismo AWS Builder ID** que ya hace falta para
enviar en Devpost. Es un solo registro para las dos cosas.

## Los tres

| # | Fichero | Ángulo |
|---|---|---|
| 1 | `post_1_por_que.md` | Por qué existe: leímos tres convocatorias de $223.765 y ninguna pagaba dinero |
| 2 | `post_2_arquitectura.md` | Cómo está hecho: el modelo lee, el código decide |
| 3 | `post_3_fallos.md` | Qué se rompió: cuatro fallos encontrados ejecutando, no imaginando |

Cada uno se sostiene solo. Se pueden publicar los tres el mismo día o
espaciados; las reglas no exigen fechas distintas.

## Antes de publicar

- [ ] Los has leído. **Salen bajo tu nombre.**
- [ ] AWS Builder ID creado (mismo login que Devpost)
- [ ] El repo ya público, porque los tres enlazan a él
- [ ] Título con **"Agents for Humans"** dentro — está en las tres cabeceras, no
      lo edites al pegar
- [ ] Enlazar los posts desde la candidatura de Devpost, para que el jurado los
      encuentre sin buscar

## Un aviso honesto

Los tres dicen que usamos **Strands Agents SDK con el proveedor LiteLLM, no
Bedrock**. Es verdad y es deliberado —un juez puede clonarlo sin poner una
tarjeta— pero la regla habla de *"implementing AWS"*. Si un juez lo lee como
"tiene que ser Bedrock", esto lo pone delante en vez de esconderlo.

Esconderlo sería peor: es lo primero que se ve abriendo el repo.
