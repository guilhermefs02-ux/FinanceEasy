# FinanceEasy

Aplicativo web de gestão financeira pessoal desenvolvido com **Python e Django**, voltado especialmente para pessoas que precisam organizar suas contas, controlar dívidas, acompanhar seus objetivos financeiros e entender quanto dinheiro podem utilizar com segurança até o final do mês.

O projeto tem como persona principal o **“Equilibrista Sobrecarregado”**: uma pessoa que enfrenta dificuldades para organizar as finanças, está preocupada com vencimentos e juros por atraso e precisa de informações claras para tomar decisões financeiras melhores.

O FinanceEasy prioriza a organização financeira sem julgamentos, a prevenção de atrasos e a visualização de uma sobra financeira mais segura.

**Repositório:** https://github.com/guilhermefs02-ux/FinanceEasy

**Hospedagem:** Render

**Modelo de desenvolvimento:** Django MTV (Model, Template, View)

---

## 1. Tecnologias utilizadas

- **Python:** linguagem principal.
- **Django:** framework web, utilizando a arquitetura MTV.
- **HTML5, CSS3 e JavaScript:** estrutura, estilos e interatividade.
- **Bootstrap 5:** componentes e interface responsiva.
- **PostgreSQL:** banco de dados utilizado em produção, hospedado no Neon.
- **Neon:** serviço de banco de dados PostgreSQL na nuvem.
- **Render:** hospedagem da aplicação web e execução do deploy.
- **GitHub:** repositório do código-fonte e controle de versões.
- **HG Brasil Finance API:** integração para informações financeiras e cotações, conforme configuração.
- **Hugging Face Inference API:** integração para auxiliar na categorização de despesas importadas, conforme configuração.

### Arquitetura de publicação

O fluxo de funcionamento do FinanceEasy é:

1. **GitHub:** armazena o código-fonte e recebe as alterações.
2. **Render:** publica e executa a aplicação Django.
3. **Neon PostgreSQL:** armazena os dados persistentes da aplicação em produção.

As credenciais e os endereços de conexão são configurados por variáveis de ambiente. Senhas, tokens e URLs de conexão que contenham credenciais não devem ser publicados no repositório.

O SQLite pode ser utilizado em um ambiente local somente se a configuração do projeto permitir; ele não deve ser apresentado como o banco principal de produção.

### 2.2. Painel financeiro

O painel principal reúne informações para facilitar a compreensão da situação financeira do usuário.

Recursos:

- Visualização de indicadores financeiros.
- Acompanhamento de receitas e despesas.
- Consulta por competência mensal.
- Organização das despesas por categoria.
- Exibição da **Sobra Segura**, considerando o saldo disponível e os valores previstos para os próximos sete dias.
- Modo de privacidade para ocultar valores financeiros na interface.
- Acompanhamento de objetivos financeiros e respectivos progressos.
- Acesso às funcionalidades de receitas, despesas, contas fixas, dívidas e metas.

A Sobra Segura deve continuar considerando os vencimentos futuros relevantes para o cálculo. A Central de Avisos pode ser acessada separadamente, sem precisar ocupar espaço no painel principal.

### 2.3. Receitas e despesas

O módulo de transações organiza as movimentações financeiras registradas no sistema.

Recursos previstos e documentados:

- Registro de receitas.
- Registro de despesas.
- Associação das movimentações a categorias.
- Consulta e filtragem do extrato.
- Importação de arquivos financeiros nos formatos suportados pelos respectivos parsers.
- Apoio à categorização das despesas importadas.
- Conciliação e revisão de transações, conforme os fluxos implementados.

A disponibilidade de cada formato de importação depende do parser correspondente e de sua compatibilidade com o arquivo fornecido.

### 2.4. Importação de extratos

O projeto possui serviços para leitura e interpretação de arquivos financeiros.

Arquivos contemplados na estrutura do projeto:

- OFX.
- CSV.
- PDF.

A leitura de PDF pode depender do formato do extrato bancário e não garante reconhecimento de todos os layouts.

A importação e a categorização são etapas distintas: quando uma categoria não é identificada automaticamente, a transação pode exigir revisão manual.

### 2.5. Categorização de despesas

A categorização auxilia na organização das movimentações financeiras.

O projeto contempla:

- Regras de identificação por palavras-chave.
- Sugestão de categorias para transações importadas.
- Integração com a Hugging Face Inference API, quando configurada.
- Revisão manual de despesas cuja classificação não seja identificada corretamente.

A classificação automática deve ser tratada como uma sugestão que pode precisar de correção pelo usuário.

### 2.6. Contas fixas e pagamentos

O módulo de contas fixas permite acompanhar compromissos financeiros recorrentes.

Recursos trabalhados no projeto:

- Cadastro e acompanhamento de contas fixas.
- Controle dos vencimentos.
- Registro do pagamento de contas.
- Integração dos pagamentos com as despesas financeiras.
- Recuperação e vinculação de despesas históricas relacionadas a pagamentos de contas fixas, melhoria confirmada após deploy em outubro de 2026.
- Utilização dos vencimentos no cálculo da Sobra Segura e na Central de Avisos.

**Regra importante:** o registro do pagamento e a despesa financeira correspondente precisam permanecer coerentes, evitando duplicidade ou perda de lançamentos históricos.

### 2.7. Dívidas, cartões e parcelamentos

O módulo de dívidas organiza os compromissos financeiros parcelados.

A estrutura do projeto contempla:

- Cadastro e acompanhamento de dívidas.
- Organização de cartões e parcelamentos, conforme os modelos implementados.
- Acompanhamento das parcelas.
- Identificação de parcelas vencidas ou próximas do vencimento.
- Consideração dos compromissos financeiros pertinentes nos avisos e indicadores.

A baixa automática ou manual de parcelas deve respeitar as regras específicas do módulo de dívidas, sem pressupor que todas as ações disponíveis para contas fixas também estejam disponíveis para parcelas.

### 2.8. Metas e reservas financeiras

O módulo de objetivos permite acompanhar a evolução das metas financeiras.

A documentação do projeto contempla uma reserva de segurança e objetivos de economia com contribuições de pequenos valores.

Recursos importantes para a evolução do módulo:

- Cadastro e acompanhamento dos objetivos.
- Registro do progresso em direção ao valor pretendido.
- Visualização dos valores acumulados e restantes, conforme os campos disponíveis.
- Acompanhamento do prazo e da conclusão dos objetivos.
- Mensagem de conclusão da meta.
- Regras de permanência e arquivamento de objetivos concluídos.

**Regra de experiência do usuário:** a conclusão de um objetivo deve ser comunicada claramente. Quando houver prazo de permanência antes do arquivamento, esse comportamento precisa ser preservado, sem apagar indevidamente o histórico da meta.

### 2.9. Central de Avisos

A Central de Avisos é uma página própria para consultar compromissos financeiros que precisam de atenção.

**Rota da página:** `/painel/avisos/`

A página está organizada em duas seções:

- **Contas e parcelas vencidas:** compromissos que já passaram do vencimento e precisam de atenção.
- **A vencer nos próximos sete dias:** compromissos com vencimento próximo.

A interface apresenta indicadores de resumo:

- Total de pendências.
- Quantidade de vencimentos atrasados.
- Quantidade de vencimentos próximos.

Também contempla:

- Nome do compromisso.
- Tipo de compromisso.
- Data de vencimento.
- Valor, respeitando o modo de privacidade.
- Identificação visual de itens vencidos e pendentes.
- Acesso de retorno ao painel principal.
- Botão verde **“Marcar como paga”** para contas fixas elegíveis que ainda não estejam pagas.

O botão de pagamento utiliza a rota Django `dashboard:marcar_conta_paga` e envia a solicitação por POST com proteção CSRF.

O botão é disponibilizado para contas fixas que possuam o registro de pagamento correspondente e ainda estejam pendentes. A presença do botão não significa que todas as parcelas de dívidas possam ser quitadas diretamente nessa página.

A Central de Avisos permanece acessível pela navegação do sistema, mesmo sem aparecer como uma seção do painel principal.

O contador vermelho da navegação deve continuar indicando a quantidade de avisos conforme a regra implementada no sistema.

### 2.10. Sobra Segura e vencimentos

A Sobra Segura busca oferecer uma referência prudente do dinheiro disponível ao longo do mês.

O cálculo documentado utiliza o saldo disponível e desconta os compromissos financeiros previstos para os próximos sete dias.

Esse indicador depende da consistência dos dados de receitas, despesas, contas fixas e vencimentos.

Alterações na Central de Avisos não devem remover a lógica de cálculo da Sobra Segura nem eliminar os dados utilizados por ela.

### 2.11. Modo de privacidade

O modo de privacidade permite ocultar valores financeiros na interface.

O recurso deve ser respeitado nas telas que exibem informações monetárias e deve ser considerado durante a implementação de novos componentes.

A ocultação visual de valores não substitui as medidas de segurança e autorização aplicadas aos dados financeiros.

---

## 3. Estrutura do projeto

A estrutura abaixo representa a organização principal documentada do código-fonte. Os nomes e caminhos devem ser conferidos com a versão atual da branch `main`.

```text
FinanceEasy/
├── accounts/
│   └── Cadastro, autenticação e contas de usuários
├── core/
│   ├── services/
│   │   ├── due_date_scan.py
│   │   └── budget_alerts.py
│   ├── management/
│   │   └── commands/
│   │       └── varredura_vencimentos.py
│   └── Infraestrutura e recursos compartilhados
├── dashboard/
│   ├── views.py
│   ├── urls.py
│   ├── services/
│   │   └── hgbrasil.py
│   └── templates/
│       └── dashboard/
│           ├── painel.html
│           └── avisos.html
├── debts/
│   └── Dívidas, cartões e parcelas
├── goals/
│   └── Metas e reservas financeiras
├── transactions/
│   ├── services/
│   │   ├── import_parser.py
│   │   └── categorizer.py
│   └── Receitas, despesas, extrato e importações
├── financeeasy/
│   ├── settings.py
│   └── urls.py
├── templates/
│   └── Templates compartilhados
├── static/
│   └── Arquivos CSS e JavaScript
├── manage.py
├── requirements.txt
├── .env.example
├── smoke_test.py
└── README.md
```

A árvore é ilustrativa: alguns serviços, diretórios e templates podem ter sido reorganizados ao longo das alterações. Para confirmar o caminho exato de um arquivo, consulte a estrutura atual no GitHub.

---

## 4. Ambiente de desenvolvimento

### 4.1. Pré-requisitos

- Python compatível com a versão do Django e das dependências do projeto.
- pip.
- Git, caso deseje clonar o repositório.
- Editor de código, como o Visual Studio Code.

Para o ambiente local, recomenda-se utilizar uma versão estável do Python compatível com todas as dependências do `requirements.txt`.

### 4.2. Clonar o projeto

```bash
git clone https://github.com/guilhermefs02-ux/FinanceEasy.git
cd FinanceEasy
```

### 4.3. Criar o ambiente virtual

```bash
python -m venv .venv
```

No Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Se o PowerShell bloquear a ativação por política de execução, uma alternativa temporária para a sessão atual é:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

No Windows CMD:

```bat
.venv\Scripts\activate.bat
```

No Linux ou macOS:

```bash
source .venv/bin/activate
```

### 4.4. Instalar as dependências

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Utilize o interpretador associado ao ambiente virtual para evitar erros de módulos não encontrados.

### 4.5. Configurar as variáveis de ambiente

Crie um arquivo `.env` a partir do exemplo, se esse arquivo estiver disponível e for compatível com a configuração atual.

PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux ou macOS:

```bash
cp .env.example .env
```

Preencha somente as variáveis necessárias para o ambiente. Não publique chaves de API, senhas, tokens ou segredos no GitHub.

### 4.6. Aplicar migrações

```bash
python manage.py migrate
```

O comando aplica as migrações disponíveis ao banco de dados configurado.

### 4.7. Criar um administrador

Opcionalmente:

```bash
python manage.py createsuperuser
```

Esse usuário permite acessar o painel administrativo do Django, conforme as permissões configuradas.

### 4.8. Executar localmente

```bash
python manage.py runserver
```

Acesse:

http://127.0.0.1:8000/

A rota inicial depende da configuração de URLs e poderá redirecionar para a tela de autenticação.

---

## 5. Configuração das integrações externas

### 5.1. HG Brasil Finance

O projeto contempla uma integração para obtenção de informações financeiras e cotações.

Caso o serviço esteja habilitado no ambiente atual, configure a variável esperada pelo código, documentada anteriormente como:

```env
HGBRASIL_API_KEY=sua_chave_aqui
```

A ausência da chave ou a indisponibilidade do serviço pode impedir a exibição das informações externas, sem necessariamente impedir o uso das demais funcionalidades financeiras.

Consulte a documentação oficial para obter credenciais e condições atualizadas:

https://hgbrasil.com/

### 5.2. Hugging Face Inference API

A integração com a Hugging Face foi prevista para auxiliar na categorização de despesas.

Variável documentada anteriormente:

```env
HUGGINGFACE_API_TOKEN=seu_token_aqui
```

A variável e o nome do modelo efetivamente utilizado devem ser conferidos no código atual antes de configurar o ambiente.

Documentação oficial:

https://huggingface.co/docs

A categorização por regras locais pode continuar disponível independentemente da integração externa, desde que esteja implementada e habilitada na versão utilizada.

---

## 6. Hospedagem e deploy

O código-fonte do FinanceEasy é mantido no GitHub e a aplicação está hospedada no Render.

O fluxo de publicação utilizado no projeto é:

1. Editar os arquivos no GitHub.
2. Confirmar as alterações por meio de um commit na branch `main`.
3. Aguardar o processo de deploy automático do Render, quando habilitado.
4. Verificar se o deploy foi concluído com sucesso.
5. Abrir a aplicação publicada e testar a funcionalidade alterada.

### Cuidados importantes

- Um commit não garante, sozinho, que o deploy foi concluído.
- Verifique o status do serviço no Render antes de testar uma alteração.
- Não remova variáveis de ambiente já utilizadas pela aplicação.
- Confirme a configuração do banco de dados de produção antes de executar migrações ou alterar configurações.
- Não utilize dados reais de clientes ou informações financeiras sensíveis em testes desnecessários.
- Não compartilhe o conteúdo de arquivos `.env` com credenciais.

O endereço público da aplicação e o banco de dados de produção devem ser consultados nas configurações atuais do projeto.

---

## 7. Varredura de vencimentos

O projeto possui um comando de gerenciamento associado à varredura de vencimentos:

```bash
python manage.py varredura_vencimentos
```

A implementação documentada contempla a identificação de vencimentos e avisos preventivos.

A execução automática em horário específico depende do mecanismo de agendamento configurado no ambiente.

Em um computador local, é possível utilizar o Agendador de Tarefas do Windows ou o cron em Linux/macOS.

Em uma hospedagem como o Render, a execução periódica exige um agendador ou serviço compatível devidamente configurado. Não se deve presumir que o comando seja executado diariamente apenas por existir no código.

Antes de criar um agendamento, confira se o comando continua presente e se a aplicação não possui outro mecanismo de execução automática para evitar duplicidade.

---

## 8. Testes e validação

O repositório contém ou documenta um script de teste de fumaça:

```bash
python smoke_test.py
```

O teste de fumaça tem como objetivo verificar fluxos essenciais da aplicação sem exigir navegação manual em todas as telas.

A cobertura descrita anteriormente inclui operações de usuário, receitas, despesas, categorias, importações, dívidas, metas, filtros e vencimentos.

A cobertura real deve ser confirmada no conteúdo atual do script.

Após alterações relevantes, recomenda-se executar também:

```bash
python manage.py check
```

Esse comando verifica problemas comuns na configuração do Django.

Para validar uma alteração publicada, confira:

- Se a página abre sem erro.
- Se o usuário autenticado visualiza apenas seus próprios dados.
- Se os formulários continuam enviando os dados corretamente.
- Se pagamentos e despesas permanecem coerentes.
- Se os indicadores financeiros apresentam valores compatíveis com os registros.
- Se as telas funcionam em computadores e dispositivos móveis.
- Se o deploy do Render terminou sem erros.

A existência de um script de teste não significa que todos os cenários estejam cobertos ou que todos tenham passado na versão publicada.

---

## 9. Regras de manutenção do projeto

As próximas alterações devem respeitar as seguintes prioridades:

1. **Preservar os dados financeiros:** evitar exclusões ou duplicações acidentais de receitas, despesas, pagamentos e parcelas.
2. **Manter o isolamento por usuário:** não permitir acesso aos dados de outra conta.
3. **Preservar a Sobra Segura:** mudanças visuais na Central de Avisos não devem remover os dados ou cálculos utilizados pelo indicador.
4. **Preservar a navegação:** a Central de Avisos deve continuar acessível pela navegação e o contador deve continuar respeitando a lógica implementada.
5. **Manter a coerência dos pagamentos:** marcar uma conta como paga deve respeitar o fluxo existente e atualizar os registros relacionados corretamente.
6. **Preservar as metas:** mudanças no painel não devem eliminar o progresso ou o histórico dos objetivos.
7. **Respeitar o modo de privacidade:** novos componentes financeiros devem considerar a ocultação dos valores.
8. **Priorizar responsividade:** manter os principais fluxos utilizáveis em telas pequenas.
9. **Evitar alterações desnecessárias:** modificar somente os arquivos relacionados ao objetivo solicitado.
10. **Validar cada publicação:** testar as funcionalidades relacionadas após o deploy.

---

## 10. Decisões de escopo

- A funcionalidade de dicas de consumo sem julgamento, identificada anteriormente como UC13, foi retirada do escopo original.
- A priorização do MVP considera dívidas, prevenção de atrasos, alertas de limites e privacidade como elementos importantes para a persona do projeto.
- O requisito original identificado como RF17 apresentava texto semelhante ao RF16, situação anteriormente sinalizada como possível erro de cópia.
- As funcionalidades descritas neste documento devem ser confrontadas com o código atual antes de serem consideradas integralmente concluídas.

---

## 11. Melhorias futuras

Os itens abaixo são possibilidades de evolução, não declarações de que estejam necessariamente pendentes ou ausentes na versão atual:

- Melhorar a robustez da leitura de PDFs de diferentes instituições financeiras.
- Ampliar a cobertura dos testes automatizados.
- Aprimorar os indicadores e a visualização do progresso financeiro.
- Melhorar os fluxos de revisão e categorização de transações.
- Revisar as mensagens de sucesso, erro e confirmação nas operações financeiras.
- Aprimorar a experiência em dispositivos móveis.
- Revisar a estratégia de agendamento e monitoramento dos vencimentos em produção.
- Avaliar novas integrações externas conforme a necessidade do projeto.
- Revisar periodicamente a segurança, as permissões e o tratamento de dados financeiros.

---

## 12. Documentação e referências

- **Repositório:** https://github.com/guilhermefs02-ux/FinanceEasy
- **Django:** https://docs.djangoproject.com/
- **Python:** https://docs.python.org/3/
- **Bootstrap:** https://getbootstrap.com/docs/5.3/
- **Render:** https://render.com/docs
- **HG Brasil:** https://hgbrasil.com/
- **Hugging Face:** https://huggingface.co/docs

---

## 13. Objetivo do FinanceEasy

O FinanceEasy busca ajudar o usuário a compreender sua situação financeira de maneira clara e prática.

Mais do que registrar entradas e saídas, o projeto pretende facilitar o acompanhamento dos compromissos, a prevenção de atrasos, a organização de dívidas e a construção gradual de reservas financeiras.

A evolução do sistema deve priorizar **confiabilidade dos dados, clareza dos indicadores, segurança e facilidade de uso**, preservando as funcionalidades já consolidadas a cada nova atualização.
