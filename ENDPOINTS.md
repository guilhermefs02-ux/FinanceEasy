# Mapeamento de Rotas HTTP, Endpoints e APIs Externas — FINANCEEASY

Este documento mapeia todas as rotas internas do Django, endpoints de funcionalidades e integrações com APIs/CDNs externas necessárias para o funcionamento local e para o deploy em nuvem.

---

## 1. Mapeamento de Módulos, Views e Rotas Internas

| Módulo Django | Caso de Uso (UC) | Descrição da Tela / View | Nome da Rota Interna (Django) | Rota Relativa (Path) |
| :--- | :--- | :--- | :--- | :--- |
| **accounts** | UC01 | Tela de Login | `accounts:login` | `/contas/login/` |
| **accounts** | UC01 | Encerramento de Sessão (Logout) | `accounts:logout` | `/contas/logout/` |
| **accounts** | UC01 | Security Reset: Zerar Todos os Dados | `accounts:zerar_dados` | `/contas/zerar-dados/` |
| **dashboard** | UC08, UC13 | Painel Principal + Modais de Detalhamento | `dashboard:painel` | `/painel/` |
| **dashboard** | UC08 | Alternar Modo Privacidade (Ocultar Valores) | `dashboard:alternar_privacidade` | `/painel/alternar-privacidade/` |
| **dashboard** | UC08 | Marcar Notificações como Lidas | `dashboard:marcar_notificacoes_lidas` | `/painel/marcar-notificacoes-lidas/` |
| **transactions** | UC01 | Formulário de Nova Receita | `transactions:registrar_receita` | `/financas/nova-receita/` |
| **transactions** | UC01 | Formulário de Nova Despesa | `transactions:registrar_despesa` | `/financas/nova-despesa/` |
| **transactions** | UC07 | Lançamento em Lote de Despesas | `transactions:lote_despesas` | `/financas/lote/despesas/` |
| **transactions** | UC07 | Lançamento em Lote de Receitas | `transactions:lote_receitas` | `/financas/lote/receitas/` |
| **transactions** | UC07 | Lançamento em Lote de Despesas Fixas | `transactions:lote_despesas_fixas` | `/financas/lote/despesas-fixas/` |
| **transactions** | UC03 | Importar Extrato (OFX / CSV) | `transactions:importar_extrato` | `/financas/importar/` |
| **transactions** | UC03 | Conciliação Bancária de Extrato | `transactions:conciliar` | `/financas/importar/<batch_id>/conciliar/` |
| **transactions** | UC04 | Extrato Consolidado Mensal | `transactions:extrato` | `/financas/extrato/` |
| **transactions** | UC02 | Edição / Exclusão de Transação | `transactions:editar_transacao` | `/financas/extrato/<pk>/editar/` |
| **transactions** | UC05 | Gestão de Assinaturas e Contas Fixas | `transactions:assinaturas` | `/financas/assinaturas/` |
| **transactions** | UC08 | Configuração de Tetos Orçamentários | `transactions:orcamentos` | `/financas/orcamentos/` |
| **transactions** | UC06 | Projeção e Lançamentos Futuros | `transactions:futuros` | `/financas/futuros/` |
| **transactions** | UC09 | Reajuste em Lote por Grupo Recorrente | `transactions:reajustar_grupo` | `/financas/reajustar-grupo/<grupo_id>/` |
| **transactions** | UC10 | Relatórios Gráficos (6M, 12M e Ano a Ano) | `transactions:comparativo_mensal` | `/financas/comparativo/` |
| **debts** | UC11, UC12 | Painel de Dívidas e Priorização (Avalanche) | `debts:lista` | `/dividas/` |
| **goals** | UC12 | Reserva de Segurança / Objetivos | `goals:lista` | `/objetivos/` |

---

## 2. Mapeamento de APIs e CDNs Externas

| Serviço / API | Finalidade no Sistema | Endereço / URL Base | Variável de Ambiente / Chave |
| :--- | :--- | :--- | :--- |
| **HG Brasil Finance** | Cotações em tempo real (Dólar, Euro, Selic, CDI) no Painel | `https://api.hgbrasil.com/finance` | `HGBRASIL_API_KEY` |
| **Hugging Face Inference API** | Categorização inteligente de transações importadas via ML | `https://api-inference.huggingface.co/models/` | `HUGGINGFACE_API_TOKEN` |
| **CDN Chart.js** | Renderização dos Gráficos Comparativos Mensais e Anuais | `https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js` | N/A (Frontend CDN) |
| **CDN Bootstrap 5** | Interface de Usuário e Componentes de Layout | `https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/` | N/A (Frontend CDN) |
| **CDN Bootstrap Icons** | Conjunto de Ícones do Sistema | `https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/` | N/A (Frontend CDN) |

---

## 3. Configurações de Domínio e Hospedagem para Deploy na Nuvem

Estas variáveis são gerenciadas pelo `financeeasy/settings.py` com suporte a arquivos `.env`:

| Configuração | Desenvolvimento (Local) | Produção (Nuvem / Servidor) |
| :--- | :--- | :--- |
| **`DEBUG`** | `True` | `False` |
| **`ALLOWED_HOSTS`** | `['localhost', '127.0.0.1']` | `['seu-app.onrender.com', 'financeeasy.com.br']` |
| **`CSRF_TRUSTED_ORIGINS`**| `['http://localhost:8000', 'http://127.0.0.1:8000']` | `['https://seu-app.onrender.com', 'https://financeeasy.com.br']` |
| **`STATIC_URL`** | `/static/` | `/static/` (com WhiteNoise ou Cloud Storage) |
| **`MEDIA_URL`** | `/media/` | Bucket S3 / Cloud Storage |