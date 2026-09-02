// Map Quiz Maker worksheet template.
//
// Consumed by a per-build generated file that defines `versions` (an array
// of dicts, one per requested quiz version) and calls `render(versions)`.
// Each version dict has the shape:
//   (
//     class: str, title: str, version: str, instructions: str,
//     image: (filename: str, width-cm: float, height-cm: float),
//     markers: ((display-number: int, x: float, y: float, answer: str), ..),
//     word-bank: (str, ..),  // empty array when not requested
//   )
// marker (x, y) are fractions of the image in 0..1, with a top-left origin --
// the same convention as the canvas the teacher clicks on and as Typst's own
// `place()`. Earlier versions stored centimetres with a bottom-left origin
// and flipped y here, which is what put labels in the wrong place once.
//
// Page/text/header styling follows self-contained-ws-template-1.0.typ (the
// author's shared worksheet style: uniform 0.75in margin, Linux Libertine O
// 12pt, unjustified paragraphs with 0.65em leading, and the pulled-up
// class/title/name/date header grid).

#let answer-blank(width) = box(
  width: width,
  inset: 0pt,
  stroke: (bottom: 0.7pt),
)

#let blank-line() = box(width: 2.5in, height: 1.4em, stroke: (bottom: 0.6pt + black))

#let name-date-header(class, title, version) = [
  #v(-0.25in)
  #grid(
    columns: (1fr, auto),
    column-gutter: 0pt,
    row-gutter: 1.4em,

    [#class],
    align(right)[Name #answer-blank(7cm)],

    [#text(size: 15pt, weight: "bold")[#title]],
    align(right)[Date #answer-blank(3.5cm) Ver: #version],
  )
  #v(1em)
]

// Marker styling, kept in step with map_quiz_maker/render.py, which draws
// the same badge onto the image that travels in an .etqw bundle.
#let marker-ink = rgb("#c0392b")
#let marker-radius = 0.30cm

// A number on its own disappears against dark terrain or a coastline. The
// disc gives it a constant background whatever the map does underneath, and
// sizes to two digits at the default 50-marker ceiling.
#let marker-badge(number) = circle(
  radius: marker-radius,
  fill: white,
  stroke: 0.6pt + marker-ink,
  inset: 0pt,
  align(center + horizon, text(size: 8pt, weight: "bold", fill: marker-ink)[#number]),
)

#let marker-overlay(image-info, markers) = box(width: image-info.width-cm * 1cm, {
  image(image-info.filename, width: 100%)
  for m in markers {
    let label = marker-badge(m.display-number)
    // `place(top+left, dx:, dy:)` anchors the label's top-left corner at
    // (dx, dy). The app's historical TikZ/Tkinter placement centers the
    // label ON the clicked point instead, so its size is measured and
    // subtracted by half to match -- otherwise every marker prints shifted
    // down and to the right of where it was actually placed.
    context {
      let size = measure(label)
      place(
        top + left,
        dx: m.x * image-info.width-cm * 1cm - size.width / 2,
        dy: m.y * image-info.height-cm * 1cm - size.height / 2,
        label,
      )
    }
  }
})

// `columns()` only overflows into a 2nd/3rd column once content exceeds the
// available height, which a short word list never does on a mostly-empty
// page. Chunking explicitly into a 3-column grid guarantees 3 columns
// regardless of how many words there are.
#let chunk-into-columns(items, num-columns) = {
  let per-col = calc.max(1, calc.ceil(items.len() / num-columns))
  range(num-columns).map(c => items.slice(
    calc.min(c * per-col, items.len()),
    calc.min((c + 1) * per-col, items.len()),
  ))
}

#let word-bank-block(bank) = if bank.len() > 0 {
  v(0.2em)
  text(weight: "bold")[Word Bank]
  v(0.1em)
  grid(
    columns: (1fr, 1fr, 1fr),
    column-gutter: 2em,
    ..chunk-into-columns(bank, 3).map(col => stack(
      dir: ttb,
      spacing: 0.3em,
      ..col.map(word => emph[#word]),
    )),
  )
}

// Only from the second page on; a one-page worksheet needs no header. The
// page total used to be hardcoded as "of 2", which became a lie the moment a
// long question list ran to a third page, so it is simply the page number.
#let running-header(ver) = context {
  if counter(page).get().first() > 1 {
    grid(
      columns: (1fr, auto),
      [#ver.class #ver.title],
      [Page #counter(page).display()],
    )
  }
}

#let render-worksheet(ver) = {
  counter(page).update(1)
  set page(paper: "us-letter", margin: 0.75in, header: running-header(ver))

  name-date-header(ver.class, ver.title, ver.version)

  // Instructions sit above the map, directly under the header, so they read
  // before the thing they describe and don't compete with the word bank for
  // the tight space between the image and the question list. Suppressed
  // entirely when blank, so an unused field costs no vertical space.
  if ver.instructions.trim() != "" {
    emph(ver.instructions)
    v(0.6em)
  }

  marker-overlay(ver.image, ver.markers)

  word-bank-block(ver.word-bank)

  columns(2, gutter: 4em, enum(
    numbering: "1.",
    ..ver.markers.map(m => blank-line()),
  ))
}

#let render-key(ver) = {
  counter(page).update(1)
  set page(paper: "us-letter", margin: 0.75in, header: running-header(ver))

  [#ver.class]
  linebreak()
  text(size: 14pt, weight: "bold")[#ver.title]
  linebreak()
  [Version: #ver.version]

  v(1em)
  align(center, text(size: 14pt, weight: "bold")[Answer Key])
  v(1em)

  columns(2, gutter: 4em, enum(
    numbering: "1.",
    ..ver.markers.map(m => [#m.answer]),
  ))

  // The build code identifies which shuffle produced this sheet, so a
  // student's paper can be matched back to a rebuild of the same version.
  // Teacher-facing only -- it appears on the key, never on the worksheet.
  if ver.at("code", default: "") != "" {
    place(bottom + right, text(size: 8pt, fill: luma(130))[#ver.code])
  }
}

// `part` selects which halves of each version to emit:
//   "worksheet" -- student copies only (the default output)
//   "key"       -- answer keys only, so the key is a separate PDF that
//                  cannot be handed out by accident with the worksheets
//   "both"      -- worksheet then key per version, in one document
#let render(versions, part: "worksheet") = {
  set text(font: "Linux Libertine O", size: 12pt)
  set par(justify: false, leading: 0.65em)

  let parts = if part == "both" { ("worksheet", "key") } else { (part,) }

  let first = true
  for ver in versions {
    for which in parts {
      if not first { pagebreak() }
      first = false
      if which == "worksheet" { render-worksheet(ver) } else { render-key(ver) }
    }
  }
}
