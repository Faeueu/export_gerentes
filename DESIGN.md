# Design System

## Direction

Aplicativo operacional de alta densidade inspirado no exportador de vendedores já utilizado: cabeçalho azul-marinho, superfície clara, tabela como elemento central e verde reservado para a exportação.

## Color

- Navy: `#111B31` — cabeçalho e identidade.
- Blue: `#2457D6` — foco, seleção e ações secundárias.
- Green: `#008C67` — ação primária de exportação e sucesso.
- Canvas: `#F4F6F9` — fundo da aplicação.
- Surface: `#FFFFFF` — barras, tabela e diálogos.
- Ink: `#172033` — texto principal.
- Muted: `#526078` — texto auxiliar.
- Border: `#CFD6E2` — divisores e campos.
- Error: `#B42318` — validação impeditiva.

## Typography

Uma única família nativa do Windows: Segoe UI. Título 18px em negrito, subtítulo 11px, corpo e campos 10–11px, valores monetários com algarismos tabulares quando disponíveis.

## Layout

Escala de espaçamento baseada em 4px: 4, 8, 12, 16, 24 e 32. Cabeçalho compacto, barra de controles, resumo em linha e tabela ocupando o restante da janela. Densidade adequada a cerca de 100 colaboradores.

## Interaction

Enter avança horizontalmente por todos os eventos visíveis e, depois do último, segue para o primeiro evento do próximo colaborador. Shift+Enter retorna. Setas e Tab continuam disponíveis. O foco usa azul de alto contraste. Eventos adicionais criam novas colunas e a tabela oferece rolagem horizontal sincronizada com o cabeçalho.

## Components

- Campos cadastrais bloqueados com fundo neutro.
- Campos monetários alinhados à direita e iniciados em `0,00`.
- Botão primário verde `Exportar TXT`.
- Botão secundário azul `Visualizar lançamentos`.
- Ações `Adicionar gerente` e `Adicionar evento` abrem diálogos curtos, com validação antes de salvar.
- Mensagens de erro específicas e acionáveis.
