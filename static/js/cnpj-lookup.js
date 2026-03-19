/**
 * Consulta CNPJ via BrasilAPI e preenche campos automaticamente.
 *
 * Uso: adicionar data-cnpj-lookup no input de CNPJ.
 * Quando o CNPJ estiver completo (14 digitos), busca automaticamente.
 *
 *   <input data-cnpj-lookup
 *          data-cnpj-target-nome="#nome"
 *          data-cnpj-target-porte="#porte"
 *          data-mask="cnpj">
 *
 * Ou via Alpine.js:
 *   @blur="cnpjLookup($el, (d) => { form.nome = d.nome; })"
 */

const BRASIL_API_URL = 'https://brasilapi.com.br/api/cnpj/v1/';

/**
 * Busca dados do CNPJ na BrasilAPI.
 * @param {string} cnpj - CNPJ com ou sem formatacao
 * @returns {Promise<Object|null>} Dados da empresa ou null
 */
async function fetchCNPJ(cnpj) {
  const digits = cnpj.replace(/\D/g, '');
  if (digits.length !== 14) return null;

  try {
    const res = await fetch(`${BRASIL_API_URL}${digits}`);
    if (!res.ok) return null;
    const data = await res.json();

    // Determinar porte
    let porte = 'DEMAIS';
    const porteOriginal = (data.porte || '').toUpperCase();
    const descricao = (data.descricao_porte || '').toUpperCase();
    if (porteOriginal.includes('MICRO') || descricao.includes('MICRO') ||
        porteOriginal.includes('EPP') || descricao.includes('PEQUENO')) {
      porte = 'ME/EPP';
    }

    return {
      cnpj: cnpj,
      nome: data.razao_social || '',
      nome_fantasia: data.nome_fantasia || '',
      porte: porte,
      porte_original: data.porte || '',
      descricao_porte: data.descricao_porte || '',
      uf: data.uf || '',
      municipio: data.municipio || '',
      situacao: data.descricao_situacao_cadastral || '',
      natureza_juridica: data.natureza_juridica || '',
      cnae_principal: data.cnae_fiscal_descricao || '',
    };
  } catch (e) {
    console.warn('Erro ao consultar CNPJ:', e);
    return null;
  }
}

/**
 * Handler para input de CNPJ com auto-preenchimento.
 * Mostra indicador de loading e preenche campos alvo.
 */
function setupCNPJLookup(input) {
  if (input._cnpjSetup) return;
  input._cnpjSetup = true;

  let lastQuery = '';

  const doLookup = async () => {
    const digits = input.value.replace(/\D/g, '');
    if (digits.length !== 14 || digits === lastQuery) return;
    lastQuery = digits;

    // Indicador visual
    input.style.borderColor = '#d4a843';
    input.style.boxShadow = '0 0 0 2px rgba(212, 168, 67, 0.2)';

    const data = await fetchCNPJ(digits);

    // Restaurar visual
    input.style.borderColor = '';
    input.style.boxShadow = '';

    if (!data) return;

    // Preencher campos via data-attributes
    const nomeTarget = input.getAttribute('data-cnpj-target-nome');
    const porteTarget = input.getAttribute('data-cnpj-target-porte');

    if (nomeTarget) {
      const el = document.querySelector(nomeTarget);
      if (el) {
        el.value = data.nome;
        el.dispatchEvent(new Event('input', { bubbles: true }));
      }
    }
    if (porteTarget) {
      const el = document.querySelector(porteTarget);
      if (el) {
        el.value = data.porte;
        el.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }

    // Disparar evento custom para Alpine.js
    input.dispatchEvent(new CustomEvent('cnpj-found', {
      bubbles: true,
      detail: data,
    }));
  };

  input.addEventListener('blur', doLookup);
  input.addEventListener('input', () => {
    const digits = input.value.replace(/\D/g, '');
    if (digits.length === 14) doLookup();
  });
}

/**
 * Funcao helper para Alpine.js.
 * Uso: @blur="cnpjLookup($el, (d) => { nome = d.nome; porte = d.porte; })"
 */
async function cnpjLookup(el, callback) {
  const data = await fetchCNPJ(el.value);
  if (data && callback) callback(data);
}

// Auto-setup inputs com data-cnpj-lookup
function initCNPJLookups(container) {
  const root = container || document;
  root.querySelectorAll('[data-cnpj-lookup]:not([data-cnpj-setup])').forEach(el => {
    setupCNPJLookup(el);
    el.setAttribute('data-cnpj-setup', 'true');
  });
}

document.addEventListener('DOMContentLoaded', () => initCNPJLookups());
document.addEventListener('htmx:afterSwap', (e) => initCNPJLookups(e.detail.target));
