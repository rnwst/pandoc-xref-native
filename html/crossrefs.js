/**
 * @param {string} id - Id of element to be cross-referenced
 * @param {array} type - Array containing both singular and plural type
 * @param {string} label - Cross-reference label
 */
function resolveCrossRefs(id, type, label) {
  if (!id) return;
  const crossRefs = document.querySelectorAll(`a.cross-ref[href="${id}"`);
  for (const crossRef of crossRefs) {
    let crossRefText = '';
    if (crossRef.classList.includes('include-type')) {
      if (crossRef.classList.includes('pluralize')) {
        crossRefText = type[1] + ' ';
      } else {
        crossRefText = type[0] + ' ';
      }
    }
    crossRefText += label;
    crossRef.textContent = crossRefText;
  }
}

// Sections --------------------------------------------------------------------
let sections =
    [...document.querySelectorAll('h1:not(.title), h2, h3, h4, h5, h6')];
sections =
    sections.filter((section) => !section.classList.contains('unnumbered'));
const sectionCounters = new Array(6).fill(0);
const sectionTags = ['H2', 'H3', 'H4', 'H5', 'H6'];
for (const section of sections) {
  const level = sectionTags.indexOf(section.tagName) + 1;
  sectionCounters[level - 1] += 1;
  let countersToBeReset = sectionCounters.slice(level);
  // eslint-disable-next-line no-unused-vars
  countersToBeReset = new Array(5 - level).fill(0);
  // Remove trailing zeroes.
  const label = sectionCounters.join('.').replace(/(\.0)*$/, '');
  const span = document.createElement('span');
  span.textContent = label;
  section.prepend(span);
  resolveCrossRefs(section.id, ['Section', 'Sections'], label);
}

// Equations -------------------------------------------------------------------
const equations =
    [...document.querySelectorAll('.math.display:not(.unnumbered)')];
let equationCounter = 0;
for (const equation of equations) {
  equationCounter++;
  const span = document.createElement('span');
  span.textContent = '(' + equationCounter + ')';
  equation.appendChild(span);
  resolveCrossRefs(equation.id, ['Equation', 'Equations'], equationCounter);
}

// Figures ---------------------------------------------------------------------
const figures = [...document.querySelectorAll(
    'figure:has(> figcaption):not(figure > figure, .unnumbered)')];
let figureCounter = 0;
for (const figure of figures) {
  figureCounter++;
  const span = document.createElement('span');
  span.textContent = 'Figure ' + figureCounter + ':';
  const figcaption = figure.querySelector(':scope > figcaption');
  figcaption.prepend(span);
  resolveCrossRefs(figure.id, ['Figure', 'Figures'], figureCounter);
  // Subfigures
  const subfigures =
      figure.querySelector(':scope > figure:has(> figcaption):not(.unnumbered');
  let subfigureCounter = 0;
  for (const subfigure of subfigures) {
    subfigureCounter++;
    // Convert number to letter by converting to base 36: 1->a, 2->b, ...
    const subfigureLetter = (subfigureCounter + 9).toString(36);
    const span = document.createElement('span');
    span.textContent = '(' + subfigureLetter + ')';
    const figcaption = subfigure.querySelector(':scope > figcaption');
    figcaption.prepend(span);
    const label = figureCounter + '(' + subfigureLetter + ')';
    resolveCrossRefs(subfigure.id, ['Figure', 'Figures'], label);
  }
}

// Tables ----------------------------------------------------------------------
const tables =
    [...document.querySelectorAll('table:has(> caption):not(.unnumbered)')];
let tableCounter = 0;
for (const table of tables) {
  tableCounter++;
  const span = document.createElement('span');
  span.textContent = 'Table ' + tableCounter + ':';
  const tableCaption = table.querySelector(':scope > caption');
  tableCaption.prepend(span);
  resolveCrossRefs(table.id, ['Table', 'Tables'], tableCounter);
}
