---
id: web-bge-m3
title: BGE-M3 — BGE documentation
tags: BGE-M3
url: https://bge-model.com/bge/bge_m3.html
---

BGE-M3 — BGE documentation Skip to main content Back to top Ctrl + K BGE Home Introduction BGE Tutorials API More FAQ Community HF Models Search Ctrl + K System Settings Light Dark GitHub PyPI HF Models Search Ctrl + K Home Introduction BGE Tutorials API FAQ Community HF Models System Settings Light Dark GitHub PyPI HF Models Collapse Sidebar Expand Sidebar Section Navigation Embedder BGE v1 & v1.5 BGE-M3 BGE-EN-ICL BGE-VL BGE-Code-v1 Reranker BGE-Reranker BGE-Reranker-v2 BGE BGE-M3 BGE-M3 # BGE-M3 is a compound and powerful embedding model distinguished for its versatility in: Multi-Functionality : It can simultaneously perform the three common retrieval functionalities of embedding model: dense retrieval, multi-vector retrieval, and sparse retrieval. Multi-Linguality : It can support more than 100 working languages. Multi-Granularity : It is able to process inputs of different granularities, spanning from short sentences to long documents of up to 8192 tokens. Model Language Parameters Model Size Description BAAI/bge-m3 Multi-Lingual 569M 2.27 GB Multi-Functionality, Multi-Linguality, and Multi-Granularity Multi-Linguality # BGE-M3 was trained on multiple datasets covering up to 170+ different languages. While the amount of training data on languages are highly unbalanced, the actual model performance on different languages will have difference. For more information of datasets and evaluation results, please check out our paper for details. Multi-Granularity # We extend the max position to 8192, enabling the embedding of larger corpus. Proposing a simple but effective method: MCLS (Multiple CLS) to enhance the model’s ability on long text without additional fine-tuning. Multi-Functionality # from FlagEmbedding import BGEM3FlagModel model = BGEM3FlagModel ( 'BAAI/bge-m3' ) sentences_1 = [ "What is BGE M3?" , "Defination of BM25" ] sentences_2 = [ "BGE M3 is an embedding model supporting dense retrieval, lexical matching and multi-vector interaction." , "BM25 is a bag-of-words retrieval function that ranks a set of documents based on the query terms appearing in each document" ] Dense Retrieval # Similar to BGE v1 or v1.5 models, BGE-M3 use the normalized hidden state of the special token [CLS] as the dense embedding: \[e_q = norm(H_q[0])\] Next, to compute the relevance score between the query and passage: \[s_{dense}=f_{sim}(e_p, e_q)\] where \(e_p, e_q\) are the embedding vectors of passage and query, respectively. \(f_{sim}\) is the score function (such as inner product and L2 distance) for comupting two embeddings’ similarity. Sparse Retrieval # BGE-M3 generates sparce embeddings by adding a linear layer and a ReLU activation function following the hidden states: \[w_{qt} = \text{Relu}(W_{lex}^T H_q [i])\] where \(W_{lex}\) representes the weights of linear layer and \(H_q[i]\) is the encoder’s output of the \(i^{th}\) token. Based on the tokens’ weights of query and passage, the relevance score between them is computed by the joint importance of the co-existed terms within the query and passage: \[s_{lex} = \sum_{t\in q\cap p}(w_{qt} * w_{pt})\] where \(w_{qt}, w_{pt}\) are the importance weights of each co-existed term \(t\) in query and passage, respectively. Multi-Vector # The multi-vector method utilizes the entire output embeddings for the representation of query \(E_q\) and passage \(E_p\) . \[ \begin{align}\begin{aligned}E_q = norm(W_{mul}^T H_q)\\E_p = norm(W_{mul}^T H_p)\end{aligned}\end{align} \] where \(W_{mul}\) is the learnable projection matrix. Following ColBert, BGE-M3 use late-interaction to compute the fine-grained relevance score: \[s_{mul}=\frac{1}{N}\sum_{i=1}^N\max_{j=1}^M E_q[i]\cdot E_p^T[j]\] where \(E_q, E_p\) are the entire output embeddings of query and passage, respectively. This is a summation of average of maximum similarity of each \(v\in E_q\) with vectors in \(E_p\) . Hybrid Ranking # BGE-M3’s multi-functionality gives the possibility of hybrid ranking to improve retrieval. Firstly, due

```evidence
id: web-bge-m3-1
option: BGE-M3
dimension: 资料原句
stance: info
quote: Model Language Parameters Model Size Description BAAI/bge-m3 Multi-Lingual 569M 2.
```

```evidence
id: web-bge-m3-2
option: BGE-M3
dimension: 资料原句
stance: info
quote: 27 GB Multi-Functionality, Multi-Linguality, and Multi-Granularity Multi-Linguality # BGE-M3 was trained on multiple datasets covering up to 170+ different languages.
```

```evidence
id: web-bge-m3-3
option: BGE-M3
dimension: 资料原句
stance: info
quote: Multi-Functionality # from FlagEmbedding import BGEM3FlagModel model = BGEM3FlagModel ( 'BAAI/bge-m3' ) sentences_1 = [ "What is BGE M3?
```

```evidence
id: web-bge-m3-4
option: BGE-M3
dimension: 资料原句
stance: info
quote: Hybrid Ranking # BGE-M3’s multi-functionality gives the possibility of hybrid ranking to improve retrieval.
```
