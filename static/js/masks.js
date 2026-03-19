/**
 * Mascaras de input para formularios brasileiros.
 * Usa IMask.js para CNPJ, CPF, moeda (R$) e percentual.
 *
 * Uso: adicionar atributo data-mask no input.
 *   data-mask="cnpj"       → 00.000.000/0000-00
 *   data-mask="cpf"        → 000.000.000-00
 *   data-mask="cpf-cnpj"   → auto-detecta CPF ou CNPJ pelo tamanho
 *   data-mask="moeda"      → 1.234.567,89 (separador milhar, decimal virgula)
 *   data-mask="percentual" → 0,00 a 100,00
 *   data-mask="telefone"   → (00) 00000-0000
 *
 * Inicializa automaticamente ao carregar a pagina e apos HTMX swaps.
 */

function initMasks(container) {
  const root = container || document;

  // CNPJ: 00.000.000/0000-00
  root.querySelectorAll('[data-mask="cnpj"]:not([data-masked])').forEach(el => {
    IMask(el, { mask: '00.000.000/0000-00' });
    el.setAttribute('data-masked', 'true');
  });

  // CPF: 000.000.000-00
  root.querySelectorAll('[data-mask="cpf"]:not([data-masked])').forEach(el => {
    IMask(el, { mask: '000.000.000-00' });
    el.setAttribute('data-masked', 'true');
  });

  // CPF ou CNPJ (auto-detecta pelo tamanho)
  root.querySelectorAll('[data-mask="cpf-cnpj"]:not([data-masked])').forEach(el => {
    IMask(el, {
      mask: [
        { mask: '000.000.000-00', maxLength: 14 },
        { mask: '00.000.000/0000-00' },
      ],
      dispatch: (appended, dynamicMasked) => {
        const digits = (dynamicMasked.value + appended).replace(/\D/g, '');
        return dynamicMasked.compiledMasks[digits.length > 11 ? 1 : 0];
      },
    });
    el.setAttribute('data-masked', 'true');
  });

  // Moeda brasileira: 1.234.567,89
  root.querySelectorAll('[data-mask="moeda"]:not([data-masked])').forEach(el => {
    const mask = IMask(el, {
      mask: Number,
      scale: 2,
      thousandsSeparator: '.',
      radix: ',',
      mapToRadix: ['.'],
      min: 0,
      max: 999999999999.99,
      normalizeZeros: true,
      padFractionalZeros: true,
    });
    // Guardar referencia para poder pegar valor limpo
    el._imask = mask;
    el.setAttribute('data-masked', 'true');
  });

  // Percentual: 0,00 a 100,00
  root.querySelectorAll('[data-mask="percentual"]:not([data-masked])').forEach(el => {
    const mask = IMask(el, {
      mask: Number,
      scale: 2,
      thousandsSeparator: '',
      radix: ',',
      mapToRadix: ['.'],
      min: 0,
      max: 100,
      normalizeZeros: true,
      padFractionalZeros: true,
    });
    el._imask = mask;
    el.setAttribute('data-masked', 'true');
  });

  // Telefone: (00) 00000-0000
  root.querySelectorAll('[data-mask="telefone"]:not([data-masked])').forEach(el => {
    IMask(el, {
      mask: [
        { mask: '(00) 0000-0000' },
        { mask: '(00) 00000-0000' },
      ],
      dispatch: (appended, dynamicMasked) => {
        const digits = (dynamicMasked.value + appended).replace(/\D/g, '');
        return dynamicMasked.compiledMasks[digits.length > 10 ? 1 : 0];
      },
    });
    el.setAttribute('data-masked', 'true');
  });
}

/**
 * Pega o valor numerico limpo de um input com mascara moeda.
 * "1.234.567,89" → "1234567.89"
 */
function getUnmaskedValue(el) {
  if (el._imask) return el._imask.unmaskedValue;
  return el.value.replace(/\./g, '').replace(',', '.');
}

// Inicializar ao carregar
document.addEventListener('DOMContentLoaded', () => initMasks());

// Re-inicializar apos HTMX swaps (conteudo dinamico)
document.addEventListener('htmx:afterSwap', (e) => initMasks(e.detail.target));
document.addEventListener('htmx:afterSettle', (e) => initMasks(e.detail.target));
