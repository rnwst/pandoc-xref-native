// 1. Find all elements that can be cross-referenced ===========================

const sections = Array.from(document.querySelectorAll(
    'h1:not(h1.title), h2, h3, h4, h5, h6'));
// Only select equations which are numbered. See
// https://docs.mathjax.org/en/latest/input/tex/eqnumbers.html.
const numberedEquations = Array.from(
    document.querySelectorAll('span.math.display'))
    .filter( (equation) => !/\\(?:notag|nonumber)/.exec(equation.innerHTML) );
// Pandoc will wrap equations in `<span class="math display">` tags, but without
// IDs. Therefore, IDs need to be added to the numbered equations.
numberedEquations.forEach( (equation) => {
  match = /\\label\{(?<label>[a-zA-Z0-9-_:\.]*?)\}/.exec(equation.innerHTML);
  if (match) {
    equation.id = match.groups.label;
  }
} );
const figs = Array.from(document.querySelectorAll('img:not(div.subfigs img)'));
const subfigs = Array.from(document.querySelectorAll('div.subfigs figure'));
const tables = Array.from(document.querySelectorAll('table'));


// 2. Number cross-references one at a time ====================================

const crossRefs = document.querySelectorAll('a.cross-ref');
for (const crossRef of crossRefs) {
  let resolvedCrossRef = false;

  // remove leading '#'
  const id = crossRef.getAttribute('href').slice(1);
  const node = document.getElementById(id);

  // Check sections for ID -----------------------------------------------------
  if (sections.includes(node) && !resolvedCrossRef) {
    const section = node;
    const index = sections.indexOf(section);
    const counters = new Array(6).fill(0);
    const sectionTags = ['H1', 'H2', 'H3', 'H4', 'H5', 'H6'];
    for (let i = 0; i <= index; i++) {
      const level = sectionTags.indexOf(sections[i].tagName) + 1;
      counters[level - 1] += 1;
      if (level < 6) {
        let countersToBeReset = counters.slice(level);
        // eslint-disable-next-line no-unused-vars
        countersToBeReset = new Array(6 - level).fill(0);
      }
    }
    let label = '';
    let reachedNonZero = false;
    for (const counter of counters.slice().reverse()) {
      if (counter !== 0) reachedNonZero = true;
      if (reachedNonZero) label = counter + '.' + label;
    }
    // strip trailing period
    crossRef.innerHTML += label.slice(0, -1);

    resolvedCrossRef = true;
  }

  // Check numbered equations for ID -------------------------------------------
  if (numberedEquations.includes(node) && !resolvedCrossRef) {
    const equation = node;
    const equationNum = numberedEquations.indexOf(equation) + 1;
    const label = '(' + equationNum + ')';
    crossRef.innerHTML += label;

    resolvedCrossRef = true;
  }

  // Check figures for ID ------------------------------------------------------
  if (figs.includes(node) && !resolvedCrossRef) {
    const fig = node;
    const figNum = figs.indexOf(fig) + 1;
    const label = '' + figNum;
    crossRef.innerHTML += label;

    resolvedCrossRef = true;
  }

  // Check subfigures for ID ---------------------------------------------------
  if (subfigs.includes(node) && !resolvedCrossRef) {
    const subfig = node;
    const fig = node.parentNode.parentNode;
    if ((fig.tagName === 'FIGURE') && figs.includes(fig)) {
      const figNum = figs.indexOf(fig) + 1;
      const localSubfigs = fig.querySelectorAll('figure');
      const subfigNum = localSubfigs.indexOf(subfig) + 1;
      // convert number to letter by converting to base 36:
      // 1->a, 2->b, ...
      const subfigLetter = (subfigNum + 9).toString(36);
      const label = '' + figNum + subfigLetter;
      crossRef.innerHTML += label;

      resolvedCrossRef = true;
    }
  }

  // Check tables for ID -------------------------------------------------------
  if (tables.includes(node) && !resolvedCrossRef) {
    const table = node;
    const tableNum = tables.indexOf(table) + 1;
    const label = '' + tableNum;
    crossRef.innerHTML += label;

    resolvedCrossRef = true;
  }

  // Add class cross-ref-success to remove ::after CSS pseudo-element
  // `content: "??";`.
  if (resolvedCrossRef) {
    crossRef.classList.add('cross-ref-success');
  }
}
