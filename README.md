# OS Service

Serviço independente responsável pelo ciclo de vida da Ordem de Serviço (OS).
Ele é a fonte de verdade para clientes, veículos, ordens e histórico de status.

## Responsabilidades

- Criar e consultar ordens de serviço com cliente, veículo e descrição do problema;
- Atualizar o status geral e manter o histórico;
- Validar que veículo e cliente pertencem ao mesmo contexto;
- Registrar o evento `OrderCreated` em uma outbox transacional;
- Refletir os eventos `BudgetCreated`, `PaymentApproved`, `ExecutionStarted`,
  `ExecutionFinished` e `RefundProcessed` no status e histórico.

O envio da outbox ao RabbitMQ será conectado na etapa de integração assíncrona.
O mesmo protocolo AMQP será usado no Docker e na AWS; apenas a URL de conexão
mudará por ambiente. Até lá, nenhum banco ou módulo de outro serviço é acessado
por este serviço.

## Execução via Docker

O serviço é executado exclusivamente em containers Docker. Não há suporte para
subir a aplicação diretamente com Python no host.

```bash
docker compose up --build
```

API: `http://localhost:8001`
Documentação: `http://localhost:8001/docs`

Para executar os testes dentro do container:

```bash
docker compose run --rm api sh -c "alembic upgrade head && pytest -q"

Para publicar a outbox no broker:

```bash
python -m app.messaging.outbox_publisher
```

Para consumir eventos do RabbitMQ:

```bash
python -m app.messaging.consumer
```
```

## Endpoints

- `POST /orders`
- `GET /orders/{id}`
- `PATCH /orders/{id}/status`
- `GET /orders`

## Fluxo de diagnóstico

A OS é aberta com a descrição do problema e status `OPEN`; ela não recebe
serviços ou peças. O Execution Service os identifica durante o diagnóstico e
o Billing Service gera o orçamento a partir desse resultado. A comunicação
entre os serviços será feita por eventos no RabbitMQ.

## Dados iniciais

As tabelas deste serviço começam vazias por decisão arquitetural. Não haverá
migração de `clients`, `vehicles` ou `service_orders` do monólito: novas ordens
de serviço e seus dados relacionados passarão a ser criados diretamente neste
serviço quando o roteamento for ativado.
