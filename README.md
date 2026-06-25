# export-skoob-data

Exporte toda a sua biblioteca do [Skoob](https://www.skoob.com.br) para
JSON limpo — todas as prateleiras, todos os livros, sem duplicatas, sem
serviços de terceiros e com **zero dependências** (apenas a biblioteca
padrão do Python 3.8+).

O Skoob não tem exportação oficial. Esta ferramenta usa a mesma API
privada que o site do Skoob usa (`prd-api.skoob.com.br`), somente
leitura (apenas `GET` — nunca altera a sua conta).

## O que você obtém

```
output/
  books.json                 todos os livros únicos, sem duplicatas, cada
                              um marcado com as prateleiras a que pertence
  raw/{type}__{filter}.json   um arquivo por prateleira, exatamente como a
                              API retorna
```

Cada livro inclui: `title`, `author`, `publisher`, `year`, `pages`,
`cover_filename`, `slug`, `status`, `progress`, `finished_at`, `book_id`,
`edition_id`, além de `shelves` (em quais prateleiras está),
`bookshelf_types` e `in_library`.

> Observação: a API da estante **não** retorna ISBN, sinopse ou gêneros —
> esses dados ficam em um endpoint separado por livro e foram deixados de
> fora de propósito, para manter esta ferramenta rápida e leve.

## Requisitos

- Python 3.8 ou mais recente. Nada além disso — sem `pip install`.

## Como obter seu token do Skoob

O Skoob autentica as chamadas de API com um JWT que fica em um **cookie
HttpOnly**, então ele não pode ser lido do armazenamento — você precisa
capturá-lo de uma requisição real feita pelo seu navegador. Ele expira em
cerca de **15 dias** após ser emitido, então você vai repetir este passo
quando ele parar de funcionar.

1. Abra <https://www.skoob.com.br/> e **faça login**.
2. Abra o DevTools → **Console** (`F12`, ou `Cmd+Option+J` /
   `Ctrl+Shift+J`).
3. Cole todo o conteúdo de [`get-jwt.js`](./get-jwt.js) e pressione Enter.
   Você verá `Interceptor armed (fetch + XHR). Now click any shelf...`.
4. **Clique em qualquer prateleira** no menu lateral esquerdo (ex.: *Lido*,
   *Lendo*, *Quero ler*), ou abra a página da sua estante.
5. O console exibe `SKOOB JWT: eyJ...` e copia o token (já sem o prefixo
   `Bearer `) para a área de transferência.

O script é somente leitura: ele apenas observa uma requisição de saída
para ler o cabeçalho `Authorization` e depois se remove. Ele nunca envia,
armazena ou transmite nada.

> ⚠️ **Não apareceu nenhum `SKOOB JWT:` (e a página da estante mostra
> "Ops, algo deu errado")?** Quase sempre é um **bloqueador no navegador**
> (uBlock, AdGuard, Privacy Badger, antivírus com proteção web, etc.)
> barrando o host `prd-api.skoob.com.br` — o erro
> `net::ERR_BLOCKED_BY_CLIENT` aparece no console. Se o host é bloqueado,
> **nenhuma requisição é feita**, então não há cabeçalho `Authorization`
> para capturar. Veja [Solução de problemas](#solução-de-problemas).

Seu `user_id` é lido automaticamente a partir do token — você não precisa
descobri-lo manualmente.

## Uso

```bash
git clone <url-do-seu-fork>
cd export-skoob-data

cp .env.example .env
# abra o .env e cole seu token depois de SKOOB_JWT=

python3 export_skoob.py
```

Ou sem um arquivo:

```bash
SKOOB_JWT="eyJ..." python3 export_skoob.py
```

Saída esperada:

```
Token OK — user_id 6xxxxxxxxxxxxxxxxxxxxxxx, ~12.4 day(s) until expiry.
  book     all            total=1060  got=1060
  book     read           total=137   got=137
  ...
Done. 1062 unique books.
  -> output/books.json
  -> output/raw/  (one file per shelf)
```

## Privacidade e segurança

- **Seu token e seus dados exportados nunca são versionados.** `.env` e
  `output/` estão no `.gitignore`. Apenas o código é versionado.
- Somente leitura: a ferramenta e o script do console só fazem
  requisições `GET`.
- O token dá acesso à sua conta — trate-o como uma senha. Não cole em
  issues, logs ou capturas de tela. Se vazá-lo, saia do Skoob (ou espere
  ≤15 dias) para invalidá-lo.

## Como funciona

- Percorre todos os `bookshelf_type` que o Skoob aceita (`book`,
  `magazine`) e todos os `filter` de prateleira, paginando cada um até o
  fim.
- O `total_items` da API é a fonte autoritativa; a ferramenta pagina até
  uma página curta indicar o fim e então confere a contagem coletada.
- `filter=all` é a lista mestra da biblioteca; as prateleiras **não** são
  mutuamente exclusivas (um livro pode estar em `read`, `rated` e `owned`
  ao mesmo tempo), então a associação é registrada por prateleira e `all`
  é rastreado como `in_library`.

## Solução de problemas

### `ERR_BLOCKED_BY_CLIENT` / a estante mostra "Ops, algo deu errado"

Um **bloqueador do lado do cliente** está barrando o host
`prd-api.skoob.com.br`. É a causa mais comum de o `get-jwt.js` "não fazer
nada": ele arma o interceptador, mas a requisição nunca sai, então não há
token para capturar. O próprio site também fica quebrado (a estante não
carrega), porque ele depende da mesma API.

Tente, em ordem:

1. **Desative o bloqueador para `skoob.com.br`** (uBlock, AdGuard, Privacy
   Badger, AdBlock, Ghostery, DuckDuckGo) e **recarregue**. A estante
   carregar os livros = bloqueio resolvido.
2. **Pode haver mais de uma extensão.** Desativar só o uBlock pode não
   bastar — antivírus com proteção web (Malwarebytes, Avast, Kaspersky,
   Norton) e extensões de privacidade/VPN também causam isso.
3. **Use outro navegador sem essas extensões** (ex.: **Firefox**) ou uma
   **janela anônima**. Foi assim que este projeto foi validado: o Firefox,
   sem as extensões do Chrome, capturou o token de primeira.
   - No Firefox, antes de colar no console, digite `allow pasting` e
     Enter (proteção anti-self-XSS).
4. **Se bloquear até no Firefox/anônimo, não é extensão** — é
   sistema/rede: VPN, **filtro de DNS** (NextDNS, AdGuard DNS, Pi-hole,
   ControlD), firewall ou antivírus. Permita `prd-api.skoob.com.br` lá.

Observação: o `export_skoob.py` roda no **terminal**, fora do navegador,
então esses bloqueios **não** o afetam — basta capturar o token uma vez.

### Capturar o token pela aba Network (sem console, sem script)

Alternativa ao `get-jwt.js`, útil se o console estiver bloqueando colar:

1. DevTools → aba **Network**, filtre por `prd-api`.
2. Recarregue a estante ou clique numa prateleira.
3. Clique numa requisição para `prd-api.skoob.com.br` → painel
   **Headers** → **Request Headers** → copie o valor de
   `Authorization` (o `eyJ...`, sem o `Bearer `).

## Limitações

- O token expira (~15 dias) — capture um novo quando receber um erro de
  autenticação.
- Sem ISBN/sinopse/gêneros (endpoint separado, fora do escopo aqui).
- Prateleiras/tags personalizadas criadas pelo usuário não são expostas
  pela API do Skoob; apenas as prateleiras nativas são exportadas.
- API não oficial: o Skoob pode alterá-la ou restringi-la a qualquer
  momento.

## Aviso legal

Projeto independente, sem afiliação ou endosso do Skoob. Destinado a
exportar **os seus próprios** dados. Use com responsabilidade e por sua
conta e risco.

## Licença

MIT — veja [LICENSE](./LICENSE).
