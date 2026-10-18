# Foto Cluster

Aplicativo desktop que lê uma pasta de fotos, reconhece os rostos e cria uma pasta para cada pessoa.

- **Leve:** usa Python, Tkinter e OpenCV, com modelos de cerca de 39 MB (YuNet + SFace). Roda só na CPU, sem GPU.
- **Seguro:** as fotos originais **nunca são movidas ou alteradas**, apenas copiadas.
- **Offline:** depois de baixar os modelos na primeira execução, não precisa mais de internet.

## Como usar

1. Abra **`FotoCluster.exe`** e digite a senha de acesso (são 5 tentativas). Leva alguns segundos para abrir, enquanto isso aparece uma tela de abertura.
2. Escolha a **pasta com as fotos** e onde **salvar** as pastas organizadas.
3. Clique em **Analisar fotos**.
4. Confira os grupos e dê um nome a cada pessoa:
   - Dê o **mesmo nome** a dois grupos para juntá-los numa só pasta.
   - **Desmarque** um grupo para ignorá-lo.
   - Ajuste o **rigor** e clique em **Reagrupar** sem precisar analisar de novo:
     - Uma pessoa dividida em vários grupos → mova para *tolerante*.
     - Pessoas diferentes misturadas → mova para *rigoroso*.
5. Clique em **Criar pastas**.

Uma foto com várias pessoas é copiada para a pasta de cada uma delas. Fotos sem rostos vão para `Sem rostos`, e rostos que não formaram grupo vão para `Não identificados` (essa opção pode ser desligada).

## Gerar o executável (.exe)

Depois de alterar o código, rode `Gerar_EXE.bat` (precisa de Python 3.10+) para recriar o `FotoCluster.exe` na raiz. É um arquivo único, com tudo incluído (inclusive os modelos): basta copiá-lo para outro PC, que não precisa ter Python. As configurações do build ficam em `FotoCluster.spec`.

Para rodar direto do código, sem gerar o `.exe`: `.venv\Scripts\python.exe main.py`.

O ícone e a tela de abertura (`assets/`) são gerados por `assets/make_icon.py`.

## Estrutura

```
main.py                 ponto de entrada
fotocluster/app.py      interface (Tkinter)
fotocluster/engine.py   detecção, reconhecimento, agrupamento e cópia
fotocluster/auth.py     senha de acesso
assets/                 ícone do aplicativo
models/                 modelos ONNX (baixados automaticamente)
```
