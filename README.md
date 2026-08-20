# Comissões e Premiações — Folha de Pagamento

Aplicativo desktop desenvolvido para o setor de RH preencher e exportar lançamentos de comissões e premiações de gerentes e subgerentes no **Modelo 35 da Senior**.

---

## Principais Funcionalidades

- **Alinhamento Pixel-Perfect**: Tabela com grid uniforme, campos alinhados perfeitamente com os cabeçalhos, sem deslocamento horizontal ou estouro de colunas por nomes longos.
- **Identificação Simplificada**: Coluna de empresa exibe apenas o código numérico (`0018`, `0019`), otimizando o espaço útil na tela.
- **Navegação Eficiente por Teclado**:
  - `Enter`: Salva o valor e avança para a próxima célula/evento.
  - `Shift + Enter`: Retorna para a célula anterior.
  - `Setas Cima / Baixo`: Navega verticalmente entre os colaboradores mantendo o mesmo evento.
- **Persistência Segura**:
  - Em modo empacotado (`.exe`), os dados são persistidos no diretório seguro do aplicativo (`%APPDATA%/ExportGerentes`), evitando que usuários editem planilhas soltas diretamente.
  - Possibilidade de adicionar novos colaboradores e eventos diretamente pela interface do programa.
- **Executável Standalone sem Terminal**:
  - Execução limpa em janela nativa (sem inicializar o prompt de comando).
- **Exportação Modelo 35**:
  - Validação estrita de layout com 62 posições, zeros à esquerda e codificação compatível.

---

## Estrutura do Projeto

```text
gerentes_export/
├── .github/
│   └── workflows/
│       └── release.yml          # Build automatizado de release no GitHub Actions
├── src/
│   └── export_gerentes/
│       ├── __init__.py          # API pública do pacote
│       ├── constants.py         # Constantes, cores, dimensões e eventos padrão
│       ├── models.py            # Dataclasses (Employee, PayrollEvent, Launch)
│       ├── generator.py         # Lógica de cálculo, formatação e Modelo 35 Senior
│       ├── storage.py           # Persistência segura (AppData e dados embutidos)
│       └── ui/
│           ├── __init__.py
│           ├── main_window.py   # Janela principal e tabela uniforme com canvas
│           └── dialogs.py       # Modais de cadastro e prévia de lançamentos
├── main.py                      # Ponto de entrada principal
├── app.py                       # Ponto de entrada retrocompatível
├── test_modelo35.py             # Testes unitários automatizados
├── build_exe.py                 # Script de compilação com PyInstaller
├── build.bat                    # Script executável para build no Windows
├── iniciar.bat                  # Inicializador para modo de desenvolvimento
├── colaboradores.csv            # Dados iniciais de colaboradores
├── eventos.csv                  # Dados iniciais de eventos
└── README.md                    # Documentação do projeto
```

---

## Como Executar em Desenvolvimento

### Opção 1: Arquivo Batch
Dê duplo clique em `iniciar.bat`.

### Opção 2: Linha de comando
```powershell
python main.py
# ou
python app.py
```

---

## Como Compilar o Executável Standalone (.exe)

Para gerar o arquivo `.exe` para distribuição:

1. Certifique-se de ter o `pyinstaller` instalado:
   ```powershell
   pip install pyinstaller
   ```
2. Execute o script de compilação:
   ```powershell
   python build_exe.py
   # ou dê duplo clique em build.bat
   ```
3. O executável standalone será gerado em `dist/ExportGerentes.exe`.

---

## Como Executar os Testes

```powershell
python -m unittest -v
```

---

## Regras de Negócio e Leiaute Modelo 35

Cada lançamento com valor maior que `0,00` gera exatamente uma linha de 62 caracteres:
- **01-02**: Tipo de registro (`01`)
- **03-06**: Código da empresa (`0018` ou `0019`)
- **07-07**: Tipo de colaborador (`1` — Empregado)
- **08-16**: Matrícula do colaborador (9 dígitos com zeros à esquerda)
- **17-21**: Código do cálculo (5 dígitos com zeros à esquerda)
- **22-24**: Tipo de evento (`019`)
- **25-28**: Código do evento (4 dígitos)
- **29-37**: Complemento (`000000000`)
- **38-39**: Origem (`01`)
- **40-50**: Referência (`00000000000`)
- **51-61**: Valor em centavos (11 dígitos com zeros à esquerda)
- **62-62**: Indicador de operação (`I` — Inclusão)
