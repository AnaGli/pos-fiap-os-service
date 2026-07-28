# OS Service

Serviço responsável pelo ciclo de vida da Ordem de Serviço (OS). Ele é o dono
dos dados de cliente, veículo, descrição do problema, status global da OS e
histórico de transições.

Para a visão consolidada da solução, incluindo os três microsserviços,
diagramas da arquitetura e explicação da Saga, consulte:

- [Documentação Geral da Solução](./docs/README.md)

## Responsabilidades

- abrir ordens de serviço;
- consultar ordens, clientes, veículos e histórico;
- atualizar o status global da OS;
- publicar `OrderCreated` via outbox transacional;
- refletir no histórico os eventos consumidos de Billing e Execution.

## Banco de Dados

- relacional: PostgreSQL
- banco: `os_service`

## Eventos

### Publicados

- `OrderCreated`

### Consumidos

- `BudgetCreated`
- `PaymentApproved`
- `ExecutionStarted`
- `ExecutionFinished`
- `RefundProcessed`

## Status da OS

Estados atualmente suportados:

- `OPEN`
- `WAITING_DIAGNOSIS`
- `WAITING_APPROVAL`
- `PAYMENT_PENDING`
- `PAID`
- `IN_EXECUTION`
- `COMPLETED`
- `EXECUTION_FAILED`
- `CANCELLED`

## Endpoints

Principais endpoints:

- `POST /orders`
- `GET /orders`
- `GET /orders/{order_id}`
- `PATCH /orders/{order_id}/status`
- `GET /health`

Swagger:

- `http://localhost:8001/docs`

## Execução Local

O serviço é executado exclusivamente via Docker.

Subida local:

```bash
docker compose up --build
```

API:

- `http://localhost:8001`

## Testes

Para executar os testes dentro do container:

```bash
docker compose run --rm api sh -c "alembic upgrade head && pytest -q"
```

## Mensageria

Publicar a outbox manualmente:

```bash
docker compose run --rm publisher python -m app.messaging.outbox_publisher
```

Consumir eventos manualmente:

```bash
docker compose run --rm consumer python -m app.messaging.consumer
```

## Observabilidade

O serviço possui integração com Datadog para:

- traces HTTP;
- traces de publish/consume no RabbitMQ;
- traces SQL;
- logs estruturados com `correlation_id`.

Serviços esperados no Datadog:

- `os-service`
- `os-service-publisher`
- `os-service-consumer`
- `os-service-db`

## CI/CD e Deploy

Artefatos de entrega presentes no repositório:

- Dockerfile
- manifestos Kubernetes em `k8s/`
- pipeline em `.github/workflows/ci-cd.yml`

O pipeline contempla:

- build;
- testes automatizados;
- validação de qualidade;
- deploy automatizado em Kubernetes.
