# Troubleshooting Guide

## "Illegal instruction" Error

### Problem
When running `sw-search` with embedding generation, you may encounter an "Illegal instruction" error that crashes the process.

### Root Cause
This error occurs when PyTorch was compiled with newer CPU instruction sets (like AVX2 or AVX-512) that aren't supported by your CPU. This is common on older server hardware.

### Diagnosis
1. **Check your CPU capabilities:**
   ```bash
   cat /proc/cpuinfo | grep -E "(model name|flags)" | head -5
   ```

2. **Check PyTorch version:**
   ```bash
   python -c "import torch; print('PyTorch version:', torch.__version__)"
   ```

3. **Test model loading:**
   ```bash
   python -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')"
   ```

### Solution
Set environment variables to disable unsupported instruction sets:

```bash
export PYTORCH_DISABLE_AVX2=1
export PYTORCH_DISABLE_AVX512=1
```

Then run your commands:
```bash
PYTORCH_DISABLE_AVX2=1 PYTORCH_DISABLE_AVX512=1 sw-search ./docs --output index.swsearch
```

### Permanent Fix
Add these to your shell profile (`.bashrc`, `.zshrc`, etc.):
```bash
export PYTORCH_DISABLE_AVX2=1
export PYTORCH_DISABLE_AVX512=1
```

## Chunking Strategy Guide

The `sw-search` tool supports four different chunking strategies, each with different trade-offs:

### 1. Sentence-based Chunking (Default)
**Best for:** Most use cases, balanced content quality

```bash
sw-search ./docs --chunking-strategy sentence --max-sentences-per-chunk 8
```

**Characteristics:**
- Groups content by sentences for natural boundaries
- Default: 8 sentences per chunk
- Good balance of context and searchability
- Respects sentence boundaries for readability

**Results:** Medium-sized chunks with complete thoughts and good context.

### 2. Sliding Window Chunking
**Best for:** Dense content, overlapping context needed

```bash
sw-search ./docs --chunking-strategy sliding --chunk-size 100 --overlap-size 20
```

**Characteristics:**
- Word-based chunks with overlap
- Default: 100 words per chunk, 20 words overlap
- Ensures no information is lost at boundaries
- More chunks but better coverage

**Results:** Smaller, overlapping chunks that capture all content nuances.

### 3. Paragraph-based Chunking
**Best for:** Well-structured documents with clear paragraph breaks

```bash
sw-search ./docs --chunking-strategy paragraph
```

**Characteristics:**
- Splits on double newlines (paragraph boundaries)
- Chunk size varies based on paragraph length
- Preserves document structure
- Can create very small or very large chunks

**Results:** Variable-sized chunks that respect document structure.

### 4. Page-based Chunking
**Best for:** PDFs, presentations, or documents with page boundaries

```bash
sw-search ./docs --chunking-strategy page
```

**Characteristics:**
- Splits on page boundaries or form feeds
- For text files, creates roughly equal-sized pages
- Good for documents with natural page breaks
- Preserves page-level context

**Results:** Page-sized chunks that maintain document flow.

### Choosing the Right Strategy

| Use Case | Recommended Strategy | Reason |
|----------|---------------------|---------|
| General documentation | `sentence` | Balanced, readable chunks |
| Technical manuals | `sliding` | Overlapping context prevents information loss |
| Blog posts/articles | `paragraph` | Respects natural structure |
| PDFs/presentations | `page` | Maintains original pagination |
| Code documentation | `sentence` with `--split-newlines 2` | Respects code blocks |

### Quality Comparison

Based on search results for "how to deploy agents":

- **Sentence chunking:** Provides substantial, readable content with good context
- **Sliding window:** Captures more detail but may have fragmented text
- **Paragraph chunking:** Can create very small chunks (just headers) or very large ones
- **Page chunking:** Good for maintaining document flow but may split related content

### Recommendations

1. **Start with sentence chunking** (default) for most use cases
2. **Use sliding window** if you need comprehensive coverage and don't mind more chunks
3. **Use paragraph chunking** only for well-structured documents with consistent paragraph sizes
4. **Use page chunking** for PDFs or when document structure is important

### Advanced Configuration

```bash
# Fine-tuned sentence chunking
sw-search ./docs \
  --chunking-strategy sentence \
  --max-sentences-per-chunk 30 \
  --split-newlines 2

# Optimized sliding window
sw-search ./docs \
  --chunking-strategy sliding \
  --chunk-size 150 \
  --overlap-size 30

# Combined with other options
sw-search ./docs \
  --chunking-strategy sentence \
  --max-sentences-per-chunk 40 \
  --file-types md,txt,rst,py \
  --exclude "**/test/**" \
  --verbose
``` 