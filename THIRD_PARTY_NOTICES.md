# Third-party notices

Engineering Workshop includes code adapted from the project below. Packages installed by npm and pip keep their own license files.

## beautiful-ui

Source: https://github.com/slev12397/beautiful-ui

Adapted in Engineering Workshop:

- Line-numbered code and the line diff (from CodeBlock): `src/components/CodeView.tsx`, `src/components/codeView.css`
- Pixel-grid loader (from LoadingState): `src/components/RunStatus.tsx`, `src/components/runStatus.css`
- Lesson status chips (from FilterTable): `src/components/Overview.tsx`, `src/components/filterChips.css`

```text
MIT License

Copyright (c) 2026 Shane Levine

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## npm packages in the built interface

The built interface in `dist/` includes code from npm packages such as React, CodeMirror, three.js and pdf.js. Minifying removes some of their license comments, so `npm run build` collects the license of every bundled package into `dist/THIRD_PARTY_LICENSES.txt`. In the app, open it from Settings → **Open-source licenses**.

`@uiw/react-codemirror` and `@uiw/codemirror-extensions-basic-setup` ship without a license file, so the list uses the MIT license from their repository, kept in `scripts/licenses/uiw-react-codemirror.txt`.

The PDF reader's fonts (Foxit, Liberation), character maps (Adobe) and decoders (JBIG2, OpenJPEG, QCMS) ship with their own license files in `dist/pdfjs/`.
