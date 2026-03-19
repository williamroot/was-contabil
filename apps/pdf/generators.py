"""Gerador de PDFs via WeasyPrint + Django templates.

Gera documentos PDF A4 a partir de templates Django com CSS inline.
Usado para relatórios de diagnóstico, simulação avançada e TPV.

References:
    - WeasyPrint 68.x (HTML/CSS to PDF)
    - Django template engine (render_to_string)
"""

from datetime import datetime

from weasyprint import HTML

from django.template.loader import render_to_string


def gerar_pdf(template_name: str, context: dict) -> bytes:
    """Gera PDF a partir de template Django via WeasyPrint.

    O template deve estar em ``templates/pdf/<template_name>``.
    Se ``data_geracao`` não estiver no context, é preenchido automaticamente.

    Args:
        template_name: Nome do template dentro de ``templates/pdf/``.
            Ex: ``"diagnostico.html"``, ``"tpv_relatorio.html"``.
        context: Dicionário com variáveis de contexto para o template.

    Returns:
        Bytes do PDF gerado (header %PDF-).

    Raises:
        django.template.exceptions.TemplateDoesNotExist: Se o template não existir.
    """
    context.setdefault("data_geracao", datetime.now().strftime("%d/%m/%Y %H:%M"))
    html_string = render_to_string(f"pdf/{template_name}", context)
    return HTML(string=html_string).write_pdf()
