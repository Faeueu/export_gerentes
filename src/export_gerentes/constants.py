"""
Constantes e configurações visuais do aplicativo Export Gerentes.
"""

from __future__ import annotations

APP_TITLE = "Comissões e Premiações — Folha de Pagamento"
APP_SUBTITLE = "Geração de lançamentos do Modelo 35 para gerentes e subgerentes"

EMPLOYEE_COLUMNS = ("empresa", "nome", "matricula", "funcao")
EVENT_COLUMNS = ("codigo", "nome")

COMPANIES = {
    "0018": "Lojão",
    "0019": "Ideal Serviço",
}

# Larguras fixas das colunas para alinhamento uniforme e perfeito
COMPANY_COL_WIDTH = 70
NAME_COL_WIDTH = 310
REGISTRATION_COL_WIDTH = 105
ROLE_COL_WIDTH = 130
EVENT_COL_WIDTH = 145

STATIC_WIDTHS = (
    COMPANY_COL_WIDTH,
    NAME_COL_WIDTH,
    REGISTRATION_COL_WIDTH,
    ROLE_COL_WIDTH,
)

# Paleta de cores profissional
NAVY = "#111B31"
BLUE = "#2457D6"
GREEN = "#008C67"
CANVAS = "#F4F6F9"
SURFACE = "#FFFFFF"
INK = "#172033"
MUTED = "#526078"
BORDER = "#CFD6E2"
HEADER_BG = "#E8ECF3"
ROW_ALT_BG = "#F8FAFC"
ROW_HOVER_BG = "#EEF2F8"
ERROR = "#B42318"
ERROR_BG = "#FFF0EE"
