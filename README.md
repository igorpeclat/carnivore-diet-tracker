# Super Bot Nutri IA

Este é um bot do Telegram projetado para atuar como um assistente de nutrição pessoal. Ele utiliza uma combinação de modelos de IA locais e baseados em nuvem para fornecer análises nutricionais a partir de mensagens de voz e imagens.

## Descrição

O Super Bot Nutri IA permite que os usuários monitorem sua dieta e obtenham informações sobre os alimentos que consomem. Os usuários podem enviar notas de voz descrevendo suas refeições, e o bot irá transcrevê-las e analisá-las. Eles também podem enviar fotos de seus alimentos para uma análise visual. O bot mantém um registro diário da dieta e das notas de voz de cada usuário.

A principal característica deste bot é sua capacidade de realizar a maior parte do processamento localmente, garantindo a privacidade do usuário. A transcrição de áudio e a análise de texto são feitas com modelos executados localmente, enquanto a análise de imagem é realizada através da API Gemini do Google.

## Funcionalidades

- **Transcrição de Áudio:** Transcreve notas de voz em português usando o modelo Faster-Whisper localmente.
- **Análise de Refeição por Texto:** Analisa o texto transcrito para identificar menções a alimentos e estimar calorias usando um modelo Ollama local.
- **Análise Nutricional Avançada:** Fornece uma análise detalhada da refeição, incluindo macronutrientes, impacto metabólico e dicas de saúde, usando um modelo Ollama local para raciocínio.
- **Análise de Imagem de Alimentos:** Analisa fotos de alimentos para identificar os itens, estimar macros e fornecer dicas usando o Gemini 1.5 Flash.
- **Diário de Dieta:** Salva automaticamente as refeições analisadas no diário do usuário.
- **Notas de Voz:** Mantém um histórico das notas de voz enviadas pelo usuário.
- **Comandos do Bot:**
    - `/start`: Inicia a interação com o bot.
    - `/diet`: Exibe um resumo das refeições do dia.
    - `/notes`: Mostra as notas de voz do dia.
- **Teclado de Menu:** Interface fácil de usar com botões para as principais ações.

## Como Usar

1.  **Inicie o Bot:** Encontre o bot no Telegram e pressione "Iniciar".
2.  **Enviar Áudio:** Pressione "🎙️ Enviar Áudio" e grave uma nota de voz descrevendo sua refeição. O bot irá transcrever o áudio e fornecer uma análise nutricional.
3.  **Analisar Comida por Foto:** Pressione "📸 Analisar Comida" e envie uma foto da sua refeição. O bot irá analisar a imagem e retornar informações nutricionais.
4.  **Consultar Dieta:** Pressione "🥗 Minha Dieta" para ver um resumo de suas refeições registradas no dia.
5.  **Ver Notas:** Pressione "📝 Minhas Notas" para ver as transcrições de suas notas de voz do dia.

## Instalação

1.  **Clone o repositório:**
    ```bash
    git clone <url-do-repositorio>
    cd <nome-do-repositorio>
    ```

2.  **Crie e ative um ambiente virtual:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Nota: Um arquivo `requirements.txt` precisa ser criado com as dependências listadas abaixo.)*

4.  **Configure as chaves de API:**
    Edite o arquivo `bot.py` e insira suas chaves nos seguintes campos:
    - `TELEGRAM_TOKEN`
    - `GEMINI_API_KEY`

5.  **Execute o bot:**
    ```bash
    python3 bot.py
    ```

## Configuração

-   **`TELEGRAM_TOKEN`**: O token para seu bot do Telegram, obtido com o @BotFather.
-   **`GEMINI_API_KEY`**: Sua chave de API para o Google Gemini.
-   **`OLLAMA_MODEL`**: O nome do modelo Ollama a ser usado para análise de texto (ex: "mistral"). Certifique-se de que o Ollama esteja em execução e o modelo especificado esteja disponível.
-   **`whisper_model`**: O modelo Faster-Whisper a ser usado para transcrição (ex: "small").

## Dependências

-   `python-telegram-bot`
-   `google-generativeai`
-   `Pillow`
-   `faster-whisper`
-   `ollama`
-   `numpy`
-   `torch` (se estiver usando GPU para Whisper)

Crie um arquivo `requirements.txt` com o conteúdo acima para facilitar a instalação.
