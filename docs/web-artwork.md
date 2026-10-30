# Web temple fresco artwork

The 2026-10-29 revision makes the complete temple the central architectural
subject, viewed through the foreground colonnade. A triangular pediment, full
front column rhythm, recessed doorway and broad steps distinguish it from the
previous lakeside view. Morning and moonlit versions share the same composition.

## Assets and generation

- [Morning painting](../pantheon/web/static/temple-fresco-day-v2.png)
- [Moonlit painting](../pantheon/web/static/temple-fresco-night-v2.png)

Both paintings were produced with the built-in `image_gen` tool through the
imagegen skill. No Pantheon provider key was used. Original 1448×1086 PNG outputs
were copied into the project without pixel editing or color conversion.
The existing static-file package rule bundles the assets for local serving.

The morning edit starts from the previous ivory colonnade painting, adds the
complete temple, and then moves it farther away to leave a broad courtyard for
live interface content. The moonlit image changes only lighting and palette.
The active CSS uses the versioned v2 files. Earlier candidates are retained only
in the local design backup and are not bundled with the published Web update.

The image contains no baked-in interface, title or role cards. The Web interface
adds those controls, applies a reading wash, keeps the artwork centered when
panels open and reduces its opacity during conversations. Artwork generation
is separate from browser tests, which intercept model responses.

## Morning temple edit prompt

Input: previous morning colonnade painting, `temple-fresco-day.png`.

```text
Use case: precise-object-edit.
Asset type: original background painting for the Pantheon Web AI workspace, no interface.
Input image 1 is the edit target: the current approved warm ivory fresco/oil painting of a lakeside marble colonnade.
Primary request: make this unmistakably a temple sanctuary, seen through the near colonnade toward a complete, clearly recognizable classical temple. Preserve the refined soft oil/fresco brushwork, plaster grain, ivory marble texture, quiet morning light, and framing foreground columns at the two outer edges.
Main change: replace the central open mountain-and-lake vista in the upper part with a handsome complete freestanding Greco-Roman marble temple in the middle distance. Show one coherent broad triangular pediment, continuous entablature, a straight rhythm of six or eight columns across the full front facade, a dark recessed sanctuary doorway, a hint of the side colonnade for depth, and broad shallow stone steps. The WHOLE temple roof silhouette and front facade must be visible and recognizable at a glance, large enough to be the primary architectural subject, not a tiny ruin hidden in the scenery. Keep structurally straight columns and coherent classical proportions. No dome, no cathedral.
Composition: keep landscape 4:3. Center the complete temple in the UPPER THIRD of the canvas, approximately the central 50 percent of width and between 6 and 36 percent of height, so the temple roof, columns and steps read ABOVE live interface headings placed around the middle. Let a broad, softly painted ivory courtyard occupy the middle and lower half with low detail and no strong vanishing lines. The near edge columns continue to frame the composition but do not obstruct the complete temple. Distant muted hills may appear only behind and beside the temple, as secondary atmosphere. Restrained olive twigs remain near the outer upper corners.
Light and style: diffused ivory-and-pale-gold morning light with blue-gray shadows, gentle painted depth, subtly weathered marble and soft pigment edges. Keep the central and lower reading area calm; the temple silhouette should be legible without black outlines or harsh contrast.
Constraints: painting only. No people, statues, flowers, text, lettering, logos, watermarks, interface elements, diagrams, floor grid, blueprint, line-art building, neon, shiny CGI or photographic rendering. Do not return an empty vista with only several foreground pillars; the complete temple is the essential new subject.
```

## Final morning composition refinement

Input: the preceding temple edit. This refined result is the saved morning asset.

```text
Use case: precise-object-edit.
Asset type: painted background for the Pantheon Web workspace.
Input image 1 is the edit target: the warm morning painting with the complete central temple.
Make a single composition adjustment: move the complete central temple farther away and upward in the canvas. Reduce that entire temple, including every column, triangular pediment and staircase, to about 60 percent of its present size. Its new bounding area should be approximately x=34 to 70 percent of canvas width, y=6 to 35 percent of canvas height. Keep the temple fully visible, detailed enough to recognize, centered in the UPPER THIRD; the roof apex should be around y=7 percent and the lowest step above y=36 percent. The interface headings will occupy y=40 to 60 percent, so the complete temple must sit ABOVE that zone. Do not leave the temple large in the center.
Extend the pale low-detail courtyard and gentle atmospheric mist naturally into the area vacated by the temple. Distant scenery stays secondary. Keep the large framing foreground columns, upper foliage, overall camera, existing ivory-and-pale-gold morning colors, soft fresco/oil paint and marble texture unchanged.
Preserve the triangular pediment, coherent six-column facade, recessed sanctuary doorway and broad stairs as one intact recognizable architectural subject. No added structures, figures, statues, text, interface, borders or logos. Painting only, landscape 4:3.
```

## Final moonlit edit prompt

Input: the refined morning painting, supplied as the single edit target.

```text
Use case: lighting-weather.
Asset type: matching dark-theme background painting for the Pantheon Web workspace.
Input image 1 is the edit target: the approved morning sanctuary painting with a complete small temple beyond the foreground colonnade.
Change only time of day, illumination and palette to a refined moonlit night. Preserve the exact full temple silhouette, triangular pediment, every front column, doorway, broad stair, scale and UPPER-THIRD position; preserve all foreground framing columns, foliage, courtyard, distant mountains, camera perspective and canvas framing. Do not enlarge, move or obscure the complete central temple. It must remain easy to recognize against the dark atmosphere.
Color and light: deep indigo and muted blue-violet night, silver-blue moonlight grazing the temple roof and columns, warm gray marble, only a trace of pale gold reflected stone. Foreground columns are subdued blue-gray rather than bright white. The courtyard in the middle and lower half should be a calm dark low-contrast blue atmosphere suitable for light live interface text. Keep softly brushed fresco/oil pigment texture and gentle depth, no flat black field. Moonlight source stays outside the frame, no moon disk or glowing objects.
Constraints: only a lighting/color edit. No changes to architecture or composition, no additional buildings, people, statues, flowers, labels, UI, logos, lettering, watermark, border, blueprint or shiny 3D render. Same landscape 4:3.
```
