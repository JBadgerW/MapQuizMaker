// Map Quiz Maker worksheet template.
//
// Consumed by a per-build generated file that defines `versions` (an array
// of dicts, one per requested quiz version) and calls `render(versions)`.
// Each version dict has the shape:
//   (
//     class: str, title: str, version: str, instructions: str,
//     image: (filename: str, width-cm: float, height-cm: float),
//     markers: ((display-number: int, x-cm: float, y-cm: float, answer: str), ..),
//     word-bank: (str, ..),  // empty array when not requested
//   )
// marker (x-cm, y-cm) use a bottom-left origin (matching the app's historical
// TikZ/LaTeX convention); this template flips y to Typst's top-down `place()`
// convention via `dy: (image.height-cm - marker.y-cm) * 1cm`.
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

#let marker-overlay(image-info, markers) = box(width: image-info.width-cm * 1cm, {
  image(image-info.filename, width: 100%)
  for m in markers {
    let label = text(weight: "bold")[#m.display-number]
    // `place(top+left, dx:, dy:)` anchors the label's top-left corner at
    // (dx, dy). The app's historical TikZ/Tkinter placement centers the
    // label ON the clicked point instead, so its size is measured and
    // subtracted by half to match -- otherwise every marker prints shifted
    // down and to the right of where it was actually placed.
    context {
      let size = measure(label)
      place(
        top + left,
        dx: m.x-cm * 1cm - size.width / 2,
        dy: (image-info.height-cm - m.y-cm) * 1cm - size.height / 2,
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

#let render-version(ver) = {
  counter(page).update(1)

  set page(
    paper: "us-letter",
    margin: 0.75in,
    header: context {
      if counter(page).get().first() > 1 {
        grid(
          columns: (1fr, auto),
          [#ver.class #ver.title],
          [Page #counter(page).display() of 2],
        )
      }
    },
  )

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

  pagebreak()

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
}

#let render(versions) = {
  set text(font: "Linux Libertine O", size: 12pt)
  set par(justify: false, leading: 0.65em)

  for (i, ver) in versions.enumerate() {
    if i > 0 { pagebreak() }
    render-version(ver)
  }
}
