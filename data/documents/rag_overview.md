# What is Retrieval-Augmented Generation (RAG)?

Retrieval-Augmented Generation is a pattern for building AI assistants that answer
questions using a specific set of documents, instead of relying only on what a
language model memorized during training. It works in three steps: retrieve the
passages most relevant to a question, augment the model's prompt with those
passages as context, and generate an answer grounded in that context.

The main benefit of RAG is that answers can be traced back to a source. If a
document doesn't mention something, a well-instructed assistant should say it
doesn't know rather than inventing a plausible-sounding answer. This is
especially useful for small, private knowledge bases such as course notes,
internal manuals, or FAQs, where a general-purpose model has never seen the
content and would otherwise have to guess.

RAG is not the only way to give a model outside knowledge - you could also
fine-tune a model on your documents - but retrieval is much cheaper to update:
adding a new document just means re-indexing one file, not retraining a model.

## Why chunking matters

Documents are usually split into smaller passages ("chunks") of a few hundred
to a couple thousand characters before indexing. Chunking matters because
retrieval compares a query against each chunk independently: a chunk that is
too large mixes multiple topics together and dilutes the match; a chunk that
is too small loses surrounding context needed to make sense of it. A common
strategy is to split on paragraph or section boundaries and allow a small
amount of overlap between consecutive chunks so information near a boundary
isn't lost.

## Retrieval quality vs. generation quality

A RAG system can fail in two different places. If retrieval returns the wrong
passages, even a perfect language model will answer the wrong question well.
If retrieval is correct but the prompt doesn't clearly instruct the model to
stick to the provided context, the model may still hallucinate extra details.
Both halves of the pipeline need to be evaluated separately when debugging bad
answers.
